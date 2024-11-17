import pandas as pd
import pm4py
from mermaid.__main__ import Mermaid
from mermaid.graph import Graph
from pm4py import PetriNet, Marking, BPMN
from pm4py.objects.log.obj import EventLog

from src.utils.mermaid_parser import MermaidToBPMNConverter
from mermaid import *

SEPSIS_FEATHER_FILE_PATH: str = "/Users/christianimenkamp/Documents/Data-Repository/Community/sepsis/Sepsis Cases - Event Log.feather"

if __name__ == "__main__":

    # SEPSIS_LOG: pd.DataFrame = pd.read_feather(SEPSIS_FEATHER_FILE_PATH)
    #
    # net, im, fm = pm4py.discover_petri_net_inductive(SEPSIS_LOG)
    #
    # new_event_log: EventLog = pm4py.sim.play_out(net, im, fm)
    #
    # df: pd.DataFrame = pm4py.convert_to_dataframe(new_event_log)
    # bpmn: BPMN = pm4py.convert_to_bpmn(net, im, fm)
    # pm4py.view_bpmn(bpmn)

    with open("/Users/christianimenkamp/Documents/Git-Repositorys/Interaction_Strength_and_Niche Overlap/resources/mutualistic-bpmn.mermaid", "r") as file:
        mermaid_content = file.read()
        sequence = Graph('Sequence-diagram', mermaid_content)
        render = Mermaid(sequence)

        render.to_png("sequence-diagram.png")


