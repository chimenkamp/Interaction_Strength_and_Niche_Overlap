import datetime
from datetime import timedelta

import pm4py
import simpy
from typing import Dict, Set, Optional, List
from pm4py import Marking
from pm4py.objects.petri_net.utils import petri_utils

from src.generation.basic_playout import apply_playout, Parameters
from src.generation.constants import SimPetriNet, add_sim_arc_from_to
from src.generation.examples import create_online_order_net


def build_parameters() -> Dict[Parameters, any]:
    """
    Parameters.NO_TRACES -> Number of traces of the log to generate
    Parameters.MAX_TRACE_LENGTH -> Maximum trace length
    Parameters.INITIAL_TIMESTAMP -> The first event is set with INITIAL_TIMESTAMP increased from 1970
    Parameters.INITIAL_CASE_ID -> Numeric case id for the first trace
    Parameters.PETRI_SEMANTICS -> Petri net semantics to be used (default: petri_nets.semantics.ClassicSemantics())
    Parameters.ADD_ONLY_IF_FM_IS_REACHED -> adds the case only if the final marking is reached
    Parameters.FM_LEQ_ACCEPTED -> Accepts traces ending in a marking that is a superset of the final marking
    :return: A dictionary of parameters for the playout algorithm.
    """
    return {
        Parameters.NO_TRACES: 1,
        # Parameters.MAX_TRACE_LENGTH: 10,
        Parameters.INITIAL_TIMESTAMP: datetime.datetime.now(),
        Parameters.INITIAL_CASE_ID: 0,
        Parameters.PETRI_SEMANTICS: pm4py.objects.petri_net.semantics.ClassicSemantics(),
        Parameters.ADD_ONLY_IF_FM_IS_REACHED: True,
        Parameters.FM_LEQ_ACCEPTED: False
    }


def simulate_order_process():
    net, im, fm = create_online_order_net()
    ev = apply_playout(net, im, fm, build_parameters())
    dataframe = pm4py.convert_to_dataframe(ev)
    # pm4py.view_petri_net(net, initial_marking=im, final_marking=fm)
    print(dataframe.to_string())


if __name__ == "__main__":
    simulate_order_process()
