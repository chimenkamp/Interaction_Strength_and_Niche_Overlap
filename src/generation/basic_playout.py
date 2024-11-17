import datetime
from copy import copy
from enum import Enum
from random import choice
from typing import Optional, Dict, Any, Union, List

import pm4py.objects.log.obj
from pm4py.objects import petri_net
from pm4py.objects.log import obj as log_instance
from pm4py.objects.log.obj import EventLog
from pm4py.objects.petri_net.obj import Marking
from pm4py.util import constants
from pm4py.util import exec_utils
from pm4py.util import xes_constants
from pm4py.util.dt_parsing.variants import strpfromiso

from src.generation.constants import SimPetriNet

SimNode = Union[SimPetriNet.SimPlace, SimPetriNet.SimTransition]


class Parameters(Enum):
    ACTIVITY_KEY = constants.PARAMETER_CONSTANT_ACTIVITY_KEY
    TIMESTAMP_KEY = constants.PARAMETER_CONSTANT_TIMESTAMP_KEY
    CASE_ID_KEY = constants.PARAMETER_CONSTANT_CASEID_KEY
    RETURN_VISITED_ELEMENTS = "return_visited_elements"  # Deprecated
    NO_TRACES = "noTraces"
    MAX_TRACE_LENGTH = "maxTraceLength"
    PETRI_SEMANTICS = "petri_semantics"
    ADD_ONLY_IF_FM_IS_REACHED = "add_only_if_fm_is_reached"
    FM_LEQ_ACCEPTED = "fm_leq_accepted"
    INITIAL_TIMESTAMP = "initial_timestamp"
    INITIAL_CASE_ID = "initial_case_id"


def execute_single_trace(
        net: SimPetriNet,
        initial_marking: Marking,
        max_trace_length: int,
        final_marking: Optional[Marking],
        semantics: petri_net.semantics.Semantics,
        fm_leq_accepted: bool) -> tuple[List[SimNode], Marking]:
    """
    Execute a single trace through the Petri net and return visited elements.
    """
    visited_elements: List[SimNode] = []
    visible_transitions_visited: List[SimPetriNet.SimTransition] = []
    marking = copy(initial_marking)

    while len(visible_transitions_visited) < max_trace_length:
        visited_elements.append(marking)

        if not semantics.enabled_transitions(net, marking):  # supports nets with possible deadlocks
            break

        all_enabled_trans = semantics.enabled_transitions(net, marking)
        trans: SimPetriNet.SimTransition = select_transition(all_enabled_trans, final_marking, marking, fm_leq_accepted)

        if trans is None:
            break

        visited_elements.append(trans)
        if trans.label is not None:
            visible_transitions_visited.append(trans)

        marking = semantics.execute(trans, net, marking)

    return visited_elements, marking


def select_transition(
        all_enabled_trans: List[SimPetriNet.SimTransition],
        final_marking: Marking,
        marking: Marking,
        fm_leq_accepted: bool) -> SimPetriNet.SimTransition:
    """
    Select the next transition based on the current state and final marking requirements.
    """
    if final_marking is not None and final_marking <= marking and (final_marking == marking or fm_leq_accepted):
        return choice(list(all_enabled_trans.union({None})))
    else:
        return choice(list(all_enabled_trans))


def convert_to_event_log(
        visited_elements_list: List[List[SimNode]],
        initial_timestamp: datetime.datetime,
        initial_case_id: int,
        case_id_key: str,
        activity_key: str,
        timestamp_key: str) -> EventLog:
    """
    Convert a list of visited elements into an event log.
    """
    log = log_instance.EventLog()
    curr_timestamp: datetime.datetime = initial_timestamp

    for index, visited_elements in enumerate(visited_elements_list):
        trace = log_instance.Trace()
        trace.attributes[case_id_key] = str(index + initial_case_id)

        for element in visited_elements:
            if type(element) is SimPetriNet.SimTransition and element.label is not None:
                event = log_instance.Event()
                event[activity_key] = element.label
                new_timestamp = curr_timestamp + element.duration
                event[timestamp_key] = new_timestamp.isoformat()
                trace.append(event)
                curr_timestamp = new_timestamp

        log.append(trace)

    return log


def playout_algorithm(net: SimPetriNet,
                      initial_marking: Marking,
                      no_traces: int = 100,
                      max_trace_length: int = 100,
                      initial_timestamp: datetime.datetime = datetime.datetime.now(),
                      initial_case_id: int = 0,
                      case_id_key: str = xes_constants.DEFAULT_TRACEID_KEY,
                      activity_key: str = xes_constants.DEFAULT_NAME_KEY,
                      timestamp_key: str = xes_constants.DEFAULT_TIMESTAMP_KEY,
                      final_marking: Optional[Marking] = None,
                      semantics: petri_net.semantics.Semantics = petri_net.semantics.ClassicSemantics(),
                      add_only_if_fm_is_reached: bool = False,
                      fm_leq_accepted: bool = False) -> EventLog:
    """
    Main playout algorithm that simulates traces through a Petri net.
    """

    all_visited_elements: List[List[SimNode]] = []
    i = 0

    while True:
        if len(all_visited_elements) >= no_traces:
            break

        if i >= no_traces:
            if not add_only_if_fm_is_reached:
                break

            if len(all_visited_elements) == 0:
                # likely, the final marking is not reachable, therefore terminate here the playout
                break

        visited_elements, marking = execute_single_trace(
            net, initial_marking, max_trace_length,
            final_marking, semantics, fm_leq_accepted
        )

        # Check if we should add the trace based on final marking conditions
        if should_add_trace(marking, final_marking, add_only_if_fm_is_reached, fm_leq_accepted):
            all_visited_elements.append(visited_elements)

        i += 1

    return convert_to_event_log(
        all_visited_elements, initial_timestamp, initial_case_id,
        case_id_key, activity_key, timestamp_key
    )


def should_add_trace(
        marking: Marking,
        final_marking: Optional[Marking],
        add_only_if_fm_is_reached: bool,
        fm_leq_accepted: bool) -> bool:
    """
    Determine if a trace should be added based on final marking conditions.
    """
    return (
            not add_only_if_fm_is_reached or
            final_marking == marking or
            (final_marking <= marking and fm_leq_accepted)
    )


def apply_playout(
        net: SimPetriNet,
        initial_marking: Marking,
        final_marking: Marking = None,
        parameters: Optional[Dict[Union[str, Parameters], Any]] = None) -> EventLog:
    """
    Do the playout of a Petrinet generating a log

    Parameters
    -----------
    net
        Petri net to play-out
    initial_marking
        Initial marking of the Petri net
    final_marking
        If provided, the final marking of the Petri net
    parameters
        Parameters of the algorithm:
            Parameters.NO_TRACES -> Number of traces of the log to generate
            Parameters.MAX_TRACE_LENGTH -> Maximum trace length
            Parameters.INITIAL_TIMESTAMP -> The first event is set with INITIAL_TIMESTAMP increased from 1970
            Parameters.INITIAL_CASE_ID -> Numeric case id for the first trace
            Parameters.PETRI_SEMANTICS -> Petri net semantics to be used (default: petri_nets.semantics.ClassicSemantics())
            Parameters.ADD_ONLY_IF_FM_IS_REACHED -> adds the case only if the final marking is reached
            Parameters.FM_LEQ_ACCEPTED -> Accepts traces ending in a marking that is a superset of the final marking
    """
    if parameters is None:
        parameters = {}
    case_id_key = exec_utils.get_param_value(Parameters.CASE_ID_KEY, parameters, xes_constants.DEFAULT_TRACEID_KEY)
    activity_key = exec_utils.get_param_value(Parameters.ACTIVITY_KEY, parameters, xes_constants.DEFAULT_NAME_KEY)
    timestamp_key = exec_utils.get_param_value(Parameters.TIMESTAMP_KEY, parameters,
                                               xes_constants.DEFAULT_TIMESTAMP_KEY)
    no_traces = exec_utils.get_param_value(Parameters.NO_TRACES, parameters, 1000)
    max_trace_length = exec_utils.get_param_value(Parameters.MAX_TRACE_LENGTH, parameters, 1000)

    it: Any = exec_utils.get_param_value(Parameters.INITIAL_TIMESTAMP, parameters, datetime.datetime.now())
    initial_timestamp: datetime.datetime = datetime.datetime.fromtimestamp(it.timestamp())

    initial_case_id = exec_utils.get_param_value(Parameters.INITIAL_CASE_ID, parameters, 0)

    semantics = exec_utils.get_param_value(Parameters.PETRI_SEMANTICS, parameters,
                                           petri_net.semantics.ClassicSemantics())
    add_only_if_fm_is_reached = exec_utils.get_param_value(Parameters.ADD_ONLY_IF_FM_IS_REACHED, parameters, False)
    fm_leq_accepted = exec_utils.get_param_value(Parameters.FM_LEQ_ACCEPTED, parameters, False)

    return playout_algorithm(
        net,
        initial_marking,
        max_trace_length=max_trace_length,
        initial_timestamp=initial_timestamp,
        initial_case_id=initial_case_id,
        no_traces=no_traces,
        case_id_key=case_id_key,
        activity_key=activity_key,
        timestamp_key=timestamp_key,
        final_marking=final_marking,
        semantics=semantics,
        add_only_if_fm_is_reached=add_only_if_fm_is_reached,
        fm_leq_accepted=fm_leq_accepted
    )
