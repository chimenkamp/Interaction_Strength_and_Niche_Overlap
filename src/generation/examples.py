from datetime import timedelta, datetime
from typing import List

from pm4py import Marking

from src.generation.constants import SimPetriNet, add_sim_arc_from_to, BaseResource, RobotArm
from faker import Faker
def create_online_order_net() -> tuple[SimPetriNet, Marking, Marking]:
    """Create a Petri net modeling an online order process."""
    net = SimPetriNet("ONLINE ORDER")

    # Define places
    places: dict[str: SimPetriNet.SimPlace] = {
        "p1": SimPetriNet.SimPlace("Ready for Order"),
        "p2": SimPetriNet.SimPlace("Open Online-Shop"),
        "p3": SimPetriNet.SimPlace("Show Results"),
        "p4": SimPetriNet.SimPlace("Alternatives article found"),
        "p5": SimPetriNet.SimPlace("Article selected"),
        "p6": SimPetriNet.SimPlace("Ready to Pay"),
        "p7": SimPetriNet.SimPlace("Enter Order Data"),
        "p8": SimPetriNet.SimPlace("Input mask for shipping details opened"),
        "p9": SimPetriNet.SimPlace("Input mask for credit card details opened"),
        "p10": SimPetriNet.SimPlace("Credit card details entered"),
        "p11": SimPetriNet.SimPlace("Credit card details checked"),
        "p12": SimPetriNet.SimPlace("Credit card details verified"),
        "p13": SimPetriNet.SimPlace("Address and shipping method entered"),
        "p14": SimPetriNet.SimPlace("Order completed")
    }

    # Add places to net
    for place in places.values():
        net.places.add(place)

    # Define transitions
    transitions: dict[str: SimPetriNet.SimTransition] = {
        "t1": SimPetriNet.SimTransition("t1", "Open Online-Shop", duration=timedelta(seconds=5)),
        "t2": SimPetriNet.SimTransition("t2", "Start searching", duration=timedelta(minutes=20)),
        "t3": SimPetriNet.SimTransition("t3", "Search alternative article", duration=timedelta(minutes=15)),
        "t4": SimPetriNet.SimTransition("t4", "Select alternative article", duration=timedelta(seconds=5)),
        "t5": SimPetriNet.SimTransition("t5", "Select Article", duration=timedelta(seconds=5)),
        "t6": SimPetriNet.SimTransition("t6", "Added to shopping cart", duration=timedelta(seconds=5)),
        "t7": SimPetriNet.SimTransition("t7", "Enter login data", duration=timedelta(minutes=1)),
        "t8": SimPetriNet.SimTransition("t8", "Login data is incorrect", duration=timedelta(seconds=5)),
        "t9": SimPetriNet.SimTransition("t9", "Login data is correct", duration=timedelta(seconds=35)),
        "t10": SimPetriNet.SimTransition("t10", "Enter address and shipping method", duration=timedelta(minutes=5)),
        "t11": SimPetriNet.SimTransition("t11", "Enter credit card details", duration=timedelta(minutes=2)),
        "t12": SimPetriNet.SimTransition("t12", "Mark credit card details as verified", duration=timedelta(seconds=5)),
        "t13": SimPetriNet.SimTransition("t13", "Confirm order", duration=timedelta(seconds=5)),
        "t14": SimPetriNet.SimTransition("t14", "Check credit card details", duration=timedelta(minutes=2)),
        "t15": SimPetriNet.SimTransition("t15", "Mark credit card details as incorrect", duration=timedelta(seconds=5))
    }

    faker = Faker("de_DE")
    city: str = faker.city()
    name: str = faker.name()
    address: str = faker.address()

    # Add transitions to net
    for transition in transitions.values():
        transition.update_attributes({
            "location": city,
            "name": name,
            "address": address
        })
        net.transitions.add(transition)

    # Create arcs
    arcs: List[SimPetriNet.SimArc] = [
        add_sim_arc_from_to(places["p1"], transitions["t1"], net),
        add_sim_arc_from_to(transitions["t1"], places["p2"], net),
        add_sim_arc_from_to(places["p2"], transitions["t2"], net),
        add_sim_arc_from_to(transitions["t2"], places["p3"], net),
        add_sim_arc_from_to(places["p3"], transitions["t3"], net),
        add_sim_arc_from_to(places["p3"], transitions["t5"], net),
        add_sim_arc_from_to(transitions["t3"], places["p4"], net),
        add_sim_arc_from_to(places["p4"], transitions["t4"], net),
        add_sim_arc_from_to(transitions["t4"], places["p5"], net),
        add_sim_arc_from_to(transitions["t5"], places["p5"], net),
        add_sim_arc_from_to(places["p5"], transitions["t6"], net),
        add_sim_arc_from_to(transitions["t6"], places["p6"], net),
        add_sim_arc_from_to(places["p6"], transitions["t7"], net),
        add_sim_arc_from_to(transitions["t7"], places["p7"], net),
        add_sim_arc_from_to(places["p7"], transitions["t8"], net),
        add_sim_arc_from_to(transitions["t8"], places["p6"], net),
        add_sim_arc_from_to(places["p7"], transitions["t9"], net),
        add_sim_arc_from_to(transitions["t9"], places["p9"], net),
        add_sim_arc_from_to(places["p9"], transitions["t11"], net),
        add_sim_arc_from_to(transitions["t11"], places["p10"], net),
        add_sim_arc_from_to(places["p10"], transitions["t14"], net),
        add_sim_arc_from_to(transitions["t14"], places["p11"], net),
        add_sim_arc_from_to(places["p11"], transitions["t12"], net),
        add_sim_arc_from_to(places["p11"], transitions["t15"], net),
        add_sim_arc_from_to(transitions["t15"], places["p9"], net),
        add_sim_arc_from_to(transitions["t9"], places["p8"], net),
        add_sim_arc_from_to(places["p8"], transitions["t10"], net),
        add_sim_arc_from_to(transitions["t10"], places["p13"], net),
        add_sim_arc_from_to(places["p13"], transitions["t13"], net),
        add_sim_arc_from_to(transitions["t12"], places["p12"], net),
        add_sim_arc_from_to(places["p12"], transitions["t13"], net),
        add_sim_arc_from_to(transitions["t13"], places["p14"], net)
    ]

    # Add arcs to net
    for arc in arcs:
        net.arcs.add(arc)

    # Define initial marking (start with 1 token in p1)
    initial_marking = Marking()
    initial_marking[places["p1"]] = 1

    # Define final marking (1 token in p14)
    final_marking = Marking()
    final_marking[places["p14"]] = 1

    return net, initial_marking, final_marking


def create_order_process_net() -> tuple[SimPetriNet, Marking, Marking]:
    """Create a simple order processing Petri net."""
    net = SimPetriNet("Order Process")

    # Create places
    start = SimPetriNet.SimPlace("start")
    order_received = SimPetriNet.SimPlace("order_received")
    payment_pending = SimPetriNet.SimPlace("payment_pending")
    order_confirmed = SimPetriNet.SimPlace("order_confirmed")
    end = SimPetriNet.SimPlace("end")

    # Add places to net
    for p in [start, order_received, payment_pending, order_confirmed, end]:
        net.places.add(p)

    # Create transitions with labels
    receive_order = SimPetriNet.SimTransition("t_receive", "Receive Order")
    check_payment = SimPetriNet.SimTransition("t_check", "Check Payment")
    confirm_order = SimPetriNet.SimTransition("t_confirm", "Confirm Order")
    complete_order = SimPetriNet.SimTransition("t_complete", "Complete Order")

    # Add transitions to net
    for t in [receive_order, check_payment, confirm_order, complete_order]:
        net.transitions.add(t)

    # Create arcs
    arcs: List[SimPetriNet.SimArc] = [
        add_sim_arc_from_to(start, receive_order, net),
        add_sim_arc_from_to(receive_order, order_received, net),
        add_sim_arc_from_to(order_received, check_payment, net),
        add_sim_arc_from_to(check_payment, payment_pending, net),
        add_sim_arc_from_to(payment_pending, confirm_order, net),
        add_sim_arc_from_to(confirm_order, order_confirmed, net),
        add_sim_arc_from_to(order_confirmed, complete_order, net),
        add_sim_arc_from_to(complete_order, end, net)
    ]

    # Add arcs to net
    for arc in arcs:
        net.arcs.add(arc)

    # Define initial marking (5 process instances will be started)
    initial_marking = Marking()
    initial_marking[start] = 1

    final_marking = Marking()
    final_marking[end] = 1

    return net, Marking(initial_marking), Marking(final_marking)


def example_mutualistic_net() -> List[tuple[SimPetriNet, Marking, Marking]]:
    """
    Create a Petri net modeling a mutualistic relationship.

    graph LR
    subgraph "Process A: Welding"
        Start1[...] -->  A[Check Robot Availability]
        A --> |is available| B[Weld components \n on welding robot]
        B --> C[Report robot availability]
        C --> D[Package Welded\nComponents]
        D --> End1[...]
    end

    subgraph "Process B: Painting"
        Start2[...] -->  A1[Check Robot Availability]
        A1 --> |is available| B1[Remodel Robot for \nPainting]
        B1 --> C1[Paint Components on robot]
        C1 --> G1[Report robot availability]
        G1 --> End2[...]
    end

    C -.-> A1
    G1 <-.- A
    """

    res_robot_arm: BaseResource = RobotArm()

    net_a = SimPetriNet("Welding Process")

    # Define places
    places_a: dict[str: SimPetriNet.SimPlace] = {
        "p1": SimPetriNet.SimPlace("Check Robot Availability"),
        "p2": SimPetriNet.SimPlace("Weld components on welding robot"),
        "p3": SimPetriNet.SimPlace("Report robot availability"),
        "p4": SimPetriNet.SimPlace("Package Welded Components")
    }

    # Add places to net
    for place in places_a.values():
        net_a.places.add(place)

    # Define transitions
    transitions_a: dict[str: SimPetriNet.SimTransition] = {
        "t1": SimPetriNet.SimTransition("t1", "Check Robot Availability", duration=timedelta(seconds=5)),
        "t2": SimPetriNet.SimTransition("t2", "Weld components on welding robot", duration=timedelta(minutes=20)),
        "t3": SimPetriNet.SimTransition("t3", "Report robot availability", duration=timedelta(seconds=5)),
        "t4": SimPetriNet.SimTransition("t4", "Package Welded Components", duration=timedelta(seconds=5))
    }

    # Add transitions to net
    for transition in transitions_a.values():
        net_a.transitions.add(transition)

    # Create arcs
    arcs_a: List[SimPetriNet.SimArc] = [
        add_sim_arc_from_to(places_a["p1"], transitions_a["t1"], net_a),
        add_sim_arc_from_to(transitions_a["t1"], places_a["p2"], net_a),
        add_sim_arc_from_to(places_a["p2"], transitions_a["t2"], net_a),
        add_sim_arc_from_to(transitions_a["t2"], places_a["p3"], net_a),
        add_sim_arc_from_to(places_a["p3"], transitions_a["t3"], net_a),
        add_sim_arc_from_to(transitions_a["t3"], places_a["p4"], net_a)
    ]

    # Add arcs to net
    for arc in arcs_a:
        net_a.arcs.add(arc)

    # Define initial marking (start with 1 token in p1)
    initial_a = Marking()
    initial_a[places_a["p1"]] = 1

    final_a = Marking()
    final_a[places_a["p4"]] = 1

    net_b = SimPetriNet("Painting Process")

    # Define places
    places_b: dict[str: SimPetriNet.SimPlace] = {
        "p1": SimPetriNet.SimPlace("Check Robot Availability"),
        "p2": SimPetriNet.SimPlace("Remodel Robot for Painting"),
        "p3": SimPetriNet.SimPlace("Paint Components on robot"),
        "p4": SimPetriNet.SimPlace("Report robot availability")
    }

    # Add places to net
    for place in places_b.values():
        net_b.places.add(place)


    # Define transitions
    transitions_b: dict[str: SimPetriNet.SimTransition] = {
        "t1": SimPetriNet.SimTransition("t1", "Check Robot Availability", duration=timedelta(seconds=5)),
        "t2": SimPetriNet.SimTransition("t2", "Remodel Robot for Painting", duration=timedelta(minutes=20), resources=[res_robot_arm]),
        "t3": SimPetriNet.SimTransition("t3", "Paint Components on robot", duration=timedelta(minutes=15), resources=[res_robot_arm]),
        "t4": SimPetriNet.SimTransition("t4", "Report robot availability", duration=timedelta(seconds=5), resources=[res_robot_arm])
    }

    transitions_b["t2"].on_fire_callback = lambda marking, time, tr: res_robot_arm.acquire()
    transitions_b["t4"].on_fire_callback = lambda marking, time, tr: res_robot_arm.release(datetime.now())

    # Add transitions to net
    for transition in transitions_b.values():
        net_b.transitions.add(transition)

    # Create arcs
    arcs_b: List[SimPetriNet.SimArc] = [
        add_sim_arc_from_to(places_b["p1"], transitions_b["t1"], net_b),
        add_sim_arc_from_to(transitions_b["t1"], places_b["p2"], net_b),
        add_sim_arc_from_to(places_b["p2"], transitions_b["t2"], net_b),
        add_sim_arc_from_to(transitions_b["t2"], places_b["p3"], net_b),
        add_sim_arc_from_to(places_b["p3"], transitions_b["t3"], net_b),
        add_sim_arc_from_to(transitions_b["t3"], places_b["p4"], net_b)
    ]

    # Add arcs to net

    for arc in arcs_b:
        net_b.arcs.add(arc)

    # Define initial marking (start with 1 token in p1)
    initial_b = Marking()
    initial_b[places_b["p1"]] = 1

    final_b = Marking()
    final_b[places_b["p4"]] = 1

    return [(net_a, initial_a, final_a), (net_b, initial_b, final_b)]

