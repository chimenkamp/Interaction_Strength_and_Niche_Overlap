import abc
import datetime
import math
from collections import defaultdict
from copy import copy
from random import choice
from typing import Optional, Generator, Iterator, Union, Tuple, Any, Set, List, Dict

from pm4py.objects.log.obj import Event
from pm4py.objects.petri_net.obj import Marking
from pm4py.util import xes_constants

import uuid
from src.generation.constants import SimPetriNet, ClassicPetriNetSemantics, BaseSemantics, BaseResource, RobotArm
from typing import Final
from tabulate import tabulate
from concurrent.futures import ThreadPoolExecutor

class PetriNetEventGenerator:
    """Generator class for continuous Petri net simulation"""

    def __init__(
            self,
            net: SimPetriNet,
            initial_marking: Marking,
            final_marking: Optional[Marking] = None,
            max_trace_length: int = 10_000,
            activity_key: str = xes_constants.DEFAULT_NAME_KEY,
            timestamp_key: str = xes_constants.DEFAULT_TIMESTAMP_KEY,
            case_id_key: str = xes_constants.DEFAULT_TRACEID_KEY,
            petri_net_semantics: BaseSemantics = ClassicPetriNetSemantics(),
            initial_case_id: int = 0,
            initial_timestamp: Optional[datetime.datetime] = None,
            add_only_if_fm_is_reached: bool = False,
            fm_leq_accepted: bool = False
    ):
        """
        Initialize the Petri net event generator.

        Args:
            net: The Petri net to simulate
            initial_marking: Initial marking of the Petri net
            final_marking: Optional final marking to check against
            max_trace_length: Maximum length of each trace
            activity_key: Key for activity name in events
            timestamp_key: Key for timestamp in events
            case_id_key: Key for case ID in events
            petri_net_semantics: Petri net semantics to use
            initial_case_id: Starting case ID number
            initial_timestamp: Starting timestamp (defaults to current time)
            add_only_if_fm_is_reached: Only generate events for traces reaching final marking
            fm_leq_accepted: Accept traces ending in supersets of final marking
        """
        # Initialize parameters
        self.net: SimPetriNet = net
        self.initial_marking: Marking = initial_marking
        self.final_marking: Optional[Marking] = final_marking
        self.max_trace_length: int = max_trace_length
        self.activity_key: str = activity_key
        self.timestamp_key: str = timestamp_key
        self.case_id_key: str = case_id_key
        self.petri_net_semantics: BaseSemantics = petri_net_semantics
        self.current_case_id: int = initial_case_id
        self.current_timestamp: datetime.datetime = initial_timestamp or datetime.datetime.now()
        self.add_only_if_fm_is_reached: bool = add_only_if_fm_is_reached
        self.fm_leq_accepted: bool = fm_leq_accepted

        # Unique ID prefix for the case notion (dont change in runtime)
        self.UNIQUE_ID_PREFIX: Final[str] = str(uuid.uuid4())[:8]

        # State for current trace
        self.current_marking: Optional[Marking] = None
        self.visible_transitions_count: int = 0
        self._initialize_trace()

    def _get_current_state(self) -> Tuple[Marking, int]:
        """Return the current state of the generator"""
        return self.current_marking, self.current_case_id

    def _initialize_trace(self) -> None:
        """Initialize state for a new trace"""
        self.current_marking = copy(self.initial_marking)
        self.visible_transitions_count = 0

    def _is_trace_acceptable(self, marking: Marking) -> bool:
        """Check if current trace meets acceptance criteria"""
        return (
                not self.add_only_if_fm_is_reached or
                self.final_marking == marking or
                (self.final_marking is not None and self.final_marking <= marking and self.fm_leq_accepted)
        )

    def _fire_transition(self, enabled_transitions: set[SimPetriNet.SimTransition]) \
            -> Optional[SimPetriNet.SimTransition]:
        """Select next transition based on current state"""
        if (self.final_marking is not None and
                self.final_marking <= self.current_marking and
                (self.final_marking == self.current_marking or self.fm_leq_accepted)):
            return choice(list(enabled_transitions.union({None})))
        return choice(list(enabled_transitions))

    def _should_start_new_trace(self) -> bool:
        """Check if we need to start a new trace based on current state"""
        return (
                self.visible_transitions_count >= self.max_trace_length or
                not self.petri_net_semantics.enabled_transitions(self.net, self.current_marking)
        )

    def _handle_invalid_trace(self) -> bool:
        """Handle invalid trace and return whether to continue iteration"""
        if not self._is_trace_acceptable(self.current_marking):
            self._initialize_trace()
            self.current_timestamp = datetime.datetime.now()  # Reset timestamp
            return True
        return False

    def _start_new_trace(self) -> None:
        """Initialize state for a new trace and increment case ID"""
        self.current_case_id += 1
        self._initialize_trace()

    def _handle_enabled_transition(self) -> Optional[set[SimPetriNet.SimTransition]]:
        """Handle next transition and whether to continue iteration"""
        enabled: set[SimPetriNet.SimTransition] = self.petri_net_semantics.enabled_transitions(self.net,
                                                                                               self.current_marking)
        return enabled

    def _execute_transition(self, trans: Optional[SimPetriNet.SimTransition]) -> Optional[Event]:
        """Execute the selected transition and return event if transition is visible"""
        if trans is None:
            self._start_new_trace()
            return None

        if not trans.all_resources_available():
            return None

        # Execute transition and update marking
        self.current_marking = self.petri_net_semantics.execute(trans, self.net, self.current_marking)

        if trans.on_fire_callback is not None:
            trans.on_fire_callback(self.current_marking, self.current_case_id, trans)

        # Return event if transition has a label
        if trans.label is not None:
            return self._create_event(trans)
        return None

    def _create_event(self, trans: SimPetriNet.SimTransition) -> Event:
        """Create an event from the executed transition"""
        self.visible_transitions_count += 1
        self.current_timestamp += trans.duration

        e_ref: Event = Event()
        e_ref[self.activity_key] = trans.label
        e_ref[self.timestamp_key] = self.current_timestamp.isoformat()
        e_ref["case:concept:name"] = f"{self.UNIQUE_ID_PREFIX}_{str(self.current_case_id)}"

        for key, value in trans.attributes.items():
            e_ref["attr:" + key] = value

        return e_ref

    def __next__(self) -> Event:
        """Generate next event in the Petri net simulation"""
        while True:
            # Check if we need to start a new trace
            if self._should_start_new_trace():
                # Handle invalid trace
                if self._handle_invalid_trace():
                    continue
                # Start new trace
                self._start_new_trace()

            enabled_transitions: set[SimPetriNet.SimTransition] = self._handle_enabled_transition()

            if not enabled_transitions:
                self._start_new_trace()
                continue

            # Select and fire transition
            current_transition: Optional[SimPetriNet.SimTransition] = self._fire_transition(enabled_transitions)
            event_yield = self._execute_transition(current_transition)

            if event_yield:
                return event_yield

    def __iter__(self) -> Iterator[Event]:
        """Return self as an iterator"""
        return self


class NetSimulator:
    def __init__(self, processes: List[Tuple[SimPetriNet, Marking, Marking]]):
        self.processes: List[Tuple[SimPetriNet, Marking, Marking]] = processes
        print(f"Initialized NetSimulator with {len(processes)} processes")

    def simulate(self, max_traces: int = 100) -> List[Event]:
        print(f"Starting simulation with max_traces={max_traces}")
        event_log: list[Event] = []

        with ThreadPoolExecutor() as executor:
            futures = [executor.submit(self._simulate_process, net, im, fm, max_traces) for net, im, fm in
                       self.processes]

            for future in futures:
                result = future.result()
                print(f"Process simulation completed with {len(result)} events")
                event_log.extend(result)

        print(f"Simulation completed with total {len(event_log)} events")
        return event_log

    def _simulate_process(self, net, im, fm, max_traces):
        print(f"Simulating process {net.name} with max_traces={max_traces}")
        generator: PetriNetEventGenerator = PetriNetEventGenerator(net, im, fm)
        process_event_log = []
        for event in generator:
            process_event_log.append(event)
            if len(process_event_log) >= max_traces:
                break
        print(f"Process {net.name} simulation generated {len(process_event_log)} events")
        return process_event_log


class AgentBasedNetSimulator:
    """
    Agent-based simulator that models interactions between different process agents
    and generates event logs for process mining analysis.
    """

    def __init__(self, processes: List[Tuple[SimPetriNet, Marking, Marking]]):
        self.processes = processes
        self.agents: Dict[str, ProcessAgent] = {}
        self.shared_resources: Dict[str, BaseResource] = {}
        self.event_log: List[Event] = []

        # Initialize process agents
        for i, (net, im, fm) in enumerate(processes):
            agent = ProcessAgent(
                agent_id=f"agent_{i}",
                petri_net=net,
                initial_marking=im,
                final_marking=fm
            )
            self.agents[agent.agent_id] = agent

        print(f"Initialized AgentBasedNetSimulator with {len(processes)} process agents")

    def register_resource(self, resource: BaseResource):
        """Register a shared resource that agents can compete for"""
        self.shared_resources[resource.name] = resource
        print(f"Registered shared resource: {resource}")

    def simulate(self, max_traces: int = 100, max_time: datetime.timedelta = datetime.timedelta(hours=24)) -> List[Event]:
        """
        Run the multi-agent simulation with resource competition and interaction

        Args:
            max_traces: Maximum number of traces to generate per process
            max_time: Maximum simulation time
        """
        print(f"Starting agent-based simulation with max_traces={max_traces}")

        start_time = datetime.datetime.now()
        end_time = start_time + max_time

        # Initialize agents' event generators
        for agent in self.agents.values():
            agent.initialize_generator()

        while datetime.datetime.now() < end_time:
            # Let each agent attempt to execute its next action
            for agent in self.agents.values():
                if len(agent.event_log) >= max_traces:
                    continue

                # Try to execute next transition
                event = agent.execute_next_transition(self.shared_resources)
                if event:
                    self.event_log.append(event)

                # Agent interaction/collaboration logic can be added here
                self._handle_agent_interactions(agent)

            # Check if all agents have completed their traces
            if all(len(agent.event_log) >= max_traces for agent in self.agents.values()):
                break

        print(f"Simulation completed with {len(self.event_log)} total events")
        return self.event_log

    def _handle_agent_interactions(self, current_agent: 'ProcessAgent'):
        """Handle interactions between agents"""
        # Example: Agents can communicate about resource availability
        for other_agent in self.agents.values():
            if other_agent != current_agent:
                self._coordinate_resources(current_agent, other_agent)

    def _coordinate_resources(self, agent1: 'ProcessAgent', agent2: 'ProcessAgent'):
        """Coordinate resource usage between agents"""
        # Example: Simple resource coordination
        for resource in self.shared_resources.values():
            if not resource.is_available():
                # Agents could negotiate or adjust their strategies here
                pass


class ProcessAgent:
    """
    Autonomous agent that executes a business process and generates events
    """

    def __init__(self, agent_id: str, petri_net: SimPetriNet,
                 initial_marking: Marking, final_marking: Marking):
        self.agent_id = agent_id
        self.petri_net = petri_net
        self.initial_marking = initial_marking
        self.final_marking = final_marking
        self.event_log: List[Event] = []
        self.generator: Optional[PetriNetEventGenerator] = None

    def initialize_generator(self):
        """Initialize the event generator for this agent"""
        self.generator = PetriNetEventGenerator(
            net=self.petri_net,
            initial_marking=self.initial_marking,
            final_marking=self.final_marking,
        )

    def execute_next_transition(self, available_resources: Dict[str, BaseResource]) -> Optional[Event]:
        """
        Execute next transition if possible, considering resource availability
        """
        if not self.generator:
            return None

        try:
            # Get next possible transition
            enabled = self.generator._handle_enabled_transition()
            if not enabled:
                return None

            # Check resource availability before executing
            selected_transition = self.generator._fire_transition(enabled)
            if selected_transition and self._can_acquire_resources(selected_transition, available_resources):
                event = self.generator._execute_transition(selected_transition)
                if event:
                    event['agent_id'] = self.agent_id
                    self.event_log.append(event)
                return event

        except StopIteration:
            return None

        return None

    def _can_acquire_resources(self, transition: SimPetriNet.SimTransition,
                               available_resources: Dict[str, BaseResource]) -> bool:
        """Check if all required resources are available"""
        for resource in transition.resources:
            if resource.name in available_resources:
                if not available_resources[resource.name].is_available():
                    return False
        return True

if __name__ == "__main__":
    from src.generation.examples import create_online_order_net, example_mutualistic_net

    processes: List[Tuple[SimPetriNet, Marking, Marking]] = example_mutualistic_net()

    # robot_arm = RobotArm()
    #
    # # Create simulator with processes
    # simulator = AgentBasedNetSimulator(processes)
    # simulator.register_resource(robot_arm)
    #
    # # Run simulation
    # event_log = simulator.simulate(max_traces=100, max_time=datetime.timedelta(hours=8))
    #
    # print(tabulate(event_log, headers='keys', tablefmt='pretty'))

    net, im, fm = create_online_order_net()
    # pm4py.view_petri_net(net, initial_marking=im, final_marking=fm)
    generator: PetriNetEventGenerator = PetriNetEventGenerator(net, im, fm)

    event_log: list[Event] = []

    for i, event in enumerate(generator):
        event_log.append(event)
        if len(event_log) >= 100:
            break

    print(tabulate(event_log, headers='keys', tablefmt='pretty'))
