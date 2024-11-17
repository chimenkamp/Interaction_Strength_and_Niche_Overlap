import abc
from copy import copy
from datetime import timedelta, datetime
from typing import Optional, List, Any, Callable, Self, Set

import pm4py
from pm4py import PetriNet, Marking


class BaseResource(abc.ABC):
    """
    Base class for resources in the simulation
    """

    def __init__(self, name: str, capacity: int):
        self.name: str = name
        self.capacity: int = capacity
        self.available: int = capacity
        self.latest_release_time: Optional[datetime] = None

    def acquire(self) -> bool:
        """ Acquire the resource if available """
        if self.is_available():
            self.available -= 1
            return True
        return False

    def is_available(self) -> bool:
        """ Check if the resource is available """
        return self.available > 0

    def release(self, release_time: datetime) -> None:
        """ Release the resource """
        self.available += 1
        self.latest_release_time = release_time

    def __str__(self):
        """ Return the string representation of the resource """
        return f"{self.name} ({self.available}/{self.capacity})"


class RobotArm(BaseResource):
    def __init__(self):
        super().__init__("Robot Arm (Welding/Painting)", 1)


class SimPetriNet(pm4py.PetriNet):
    def __init__(self,
                 name: str,
                 places: Optional[List['SimPlace']] = None,
                 transitions: Optional[List['SimTransition']] = None,
                 arcs: Optional[List['Arc']] = None,
                 properties: dict = None):
        super().__init__(name, places, transitions, arcs, properties)

    class SimArc(PetriNet.Arc):
        def __init__(self,
                     source: Any,
                     target: Any,
                     weight: int = 1,
                     properties: dict = None):
            super().__init__(source, target, weight, properties)

    class SimPlace(PetriNet.Place):
        def __init__(self,
                     name: str,
                     in_arcs: Optional[List["SimPetriNet.SimArc"]] = None,
                     out_arcs: Optional[List["SimPetriNet.SimArc"]] = None,
                     properties: dict = None):
            super().__init__(name, in_arcs, out_arcs, properties)

    class SimTransition(PetriNet.Transition):
        def __init__(self,
                     name: str,
                     label: str,
                     duration: timedelta = timedelta(minutes=10),
                     attributes: Optional[dict[str, Any]] = None,
                     resources: Optional[List[BaseResource]] = None,
                     on_fire_callback: Optional[Callable[[Marking, int, Self], None]] = None,
                     in_arcs: Optional[List["SimPetriNet.SimArc"]] = None,
                     out_arcs: Optional[List["SimPetriNet.SimArc"]] = None,
                     properties: dict = None):
            super().__init__(name, label, in_arcs, out_arcs, properties)
            self.duration = duration
            self.attributes: dict[str, Any] = attributes if attributes is not None else {}
            self.on_fire_callback: Optional[Callable[[Marking, int, Self], None]] = on_fire_callback
            self.resources: List[BaseResource] = resources if resources is not None else []

        def get_attributes(self) -> dict[str, Any]:
            """ Get attributes for the transition """
            return self.attributes

        def update_attributes(self, attributes: dict[str, Any]):
            """ Update attributes for the transition """
            self.attributes.update(attributes)

        def all_resources_available(self) -> bool:
            """ Check if all resources are available """
            return all(r.is_available() for r in self.resources)


def add_sim_arc_from_to(fr, to, net: SimPetriNet, weight=1) -> SimPetriNet.SimArc:
    """
    Adds an arc from a specific element to another element in some net. Assumes from and to are in the net!

    Parameters
    ----------
    fr: transition/place from
    to:  transition/place to
    net: net to use
    weight: weight associated to the arc

    Returns
    -------
    None
    """
    a = SimPetriNet.SimArc(fr, to, weight)
    net.arcs.add(a)
    fr.out_arcs.add(a)
    to.in_arcs.add(a)
    return a

class BaseSemantics(abc.ABC):
    @abc.abstractmethod
    def is_enabled(self, t: SimPetriNet.SimTransition, pn: SimPetriNet, m: Marking, **kwargs) -> bool: ...

    @abc.abstractmethod
    def execute(self, t: SimPetriNet.SimTransition, pn: SimPetriNet, m: Marking, **kwargs) -> Optional[Marking]: ...

    @abc.abstractmethod
    def weak_execute(self, t: SimPetriNet.SimTransition, pn: SimPetriNet, m: Marking, **kwargs) -> Marking: ...

    @abc.abstractmethod
    def enabled_transitions(self, pn: SimPetriNet, m: Marking, **kwargs) -> Set[SimPetriNet.SimTransition]: ...


class ClassicPetriNetSemantics(BaseSemantics):
    def is_enabled(self, t: SimPetriNet.SimTransition, pn: SimPetriNet, m: Marking, **kwargs) -> bool:
        """ Check if the transition is enabled in the Petri net with strong semantics """
        if t in pn.transitions:
            for a in t.in_arcs:
                if m[a.source] < a.weight:
                    return False
            return True
        return False

    def execute(self, t: SimPetriNet.SimTransition, pn: SimPetriNet, m: Marking, **kwargs) -> Optional[Marking]:
        """ Execute the transition in the Petri net with strong semantics """
        if not self.is_enabled(t, pn, m):
            return None

        m_out: Marking = copy(m)
        a: SimPetriNet.SimArc
        for a in t.in_arcs:
            m_out[a.source] -= a.weight
            if m_out[a.source] == 0:
                del m_out[a.source]

        a: SimPetriNet.SimArc
        for a in t.out_arcs:
            m_out[a.target] += a.weight

        return m_out

    def weak_execute(self, t: SimPetriNet.SimTransition, pn: SimPetriNet, m: Marking, **kwargs) -> Marking:
        """ Execute the transition in the Petri net with weak semantics """
        m_out: Marking = copy(m)

        a: SimPetriNet.SimArc
        for a in t.in_arcs:
            m_out[a.source] -= a.weight
            if m_out[a.source] <= 0:
                del m_out[a.source]

        a: SimPetriNet.SimArc
        for a in t.out_arcs:
            m_out[a.target] += a.weight
        return m_out

    def enabled_transitions(self, pn: SimPetriNet, m: Marking, **kwargs) -> Set[SimPetriNet.SimTransition]:
        """ Return a set of enabled transitions in a Petri net and given marking """
        enabled: Set[SimPetriNet.SimTransition] = set()
        # Cast to SimTransition
        t: SimPetriNet.SimTransition
        for t in pn.transitions:
            if self.is_enabled(t, pn, m):
                enabled.add(t)
        return enabled


