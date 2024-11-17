import numpy as np
import pandas as pd
from typing import Tuple, List, Dict

from pandas.core.groupby import DataFrameGroupBy

# Constants
CASE_ID_KEY = 'case:concept:name'
TIMESTAMP_KEY = 'time:timestamp'
ACTIVITY_KEY = 'concept:name'
RESOURCE_KEY = 'org:group'

# Paths
SEPSIS_FEATHER_FILE_PATH: str = "/Users/christianimenkamp/Documents/Data-Repository/Community/sepsis/Sepsis Cases - Event Log.feather"


def calculate_interaction_strength(
        performance_a: List[float],
        performance_b: List[float],
        interaction_coeff_ab: float,
        interaction_coeff_ba: float
) -> Tuple[float, float]:
    """
    Calculates the interaction strength between two processes A and B.

    :param performance_a: List of performance metrics for Process A over time.
    :param performance_b: List of performance metrics for Process B over time.
    :param interaction_coeff_ab: The coefficient representing how Process B affects Process A.
    :param interaction_coeff_ba: The coefficient representing how Process A affects Process B.
    :return: A tuple containing the interaction strength of A on B and B on A.
    """

    delta_performance_a = performance_a[-1] - performance_a[0]  # Change in A's performance
    delta_performance_b = performance_b[-1] - performance_b[0]  # Change in B's performance

    # Interaction strength of Process A on Process B
    is_a_to_b = interaction_coeff_ab * (delta_performance_b / delta_performance_a)

    # Interaction strength of Process B on Process A
    is_b_to_a = interaction_coeff_ba * (delta_performance_a / delta_performance_b)

    return is_a_to_b, is_b_to_a


def calculate_niche_overlap(
        resource_usage_a: List[float],
        resource_usage_b: List[float]
) -> float:
    """
    Calculates the niche overlap between two processes A and B using Pianka's Index.

    :param resource_usage_a: A list of resource usage proportions by Process A.
    :param resource_usage_b: A list of resource usage proportions by Process B.
    :return: The niche overlap between Process A and Process B.
    """

    # Numerator: sum of the product of resource usage by both processes
    numerator = sum([a * b for a, b in zip(resource_usage_a, resource_usage_b)])

    # Denominator: normalization factor
    denominator = (
            (sum([a ** 2 for a in resource_usage_a]) ** 0.5) *
            (sum([b ** 2 for b in resource_usage_b]) ** 0.5)
    )

    niche_overlap = numerator / denominator if denominator != 0 else 0.0

    return niche_overlap


def extract_performance_metrics(log: pd.DataFrame) -> List[float]:
    """
    Extracts performance metrics (throughput time) from the event log.

    :param log: Event log for a process (DataFrame containing 'CaseID' and 'Timestamp').
    :return: List of throughput times for each case.
    """

    THROUGHPUT_TIME_KEY = 'ThroughputTime'

    # Convert Timestamp column to datetime format if necessary
    log[TIMESTAMP_KEY] = pd.to_datetime(log[TIMESTAMP_KEY])

    # Group by 'CaseID' to get start and end times of each case
    case_durations = log.groupby(CASE_ID_KEY)[TIMESTAMP_KEY].agg(['min', 'max'])

    # Calculate throughput time for each case (duration between start and end)
    case_durations[THROUGHPUT_TIME_KEY] = (case_durations['max'] - case_durations[
        'min']).dt.total_seconds() / 3600  # in hours

    return case_durations[THROUGHPUT_TIME_KEY].tolist()


def infer_resource_usage(log: pd.DataFrame) -> Dict[str, float]:
    """
    Infers resource usage proportions from the event log.

    :param log: Event log for a process (DataFrame containing 'Activity' and 'Resource').
    :return: A dictionary of resources and their inferred usage proportions.
    """
    # Count occurrences of each resource
    resource_counts = log[RESOURCE_KEY].value_counts()

    # Calculate the total number of events in the log
    total_events = len(log)

    # Calculate proportion of each resource usage
    resource_proportions = (resource_counts / total_events).to_dict()

    return resource_proportions


def estimate_interaction_coeff(
        performance_a: List[float],
        performance_b: List[float]
) -> Tuple[float, float]:
    """
    Estimates the interaction coefficients between two processes A and B using correlation.

    :param performance_a: List of performance metrics for Process A over time.
    :param performance_b: List of performance metrics for Process B over time.
    :return: Estimated interaction coefficients (ab, ba).
    """

    if len(performance_a) != len(performance_b):
        min_length = min(len(performance_a), len(performance_b))
        performance_a = performance_a[:min_length]
        performance_b = performance_b[:min_length]

    # Calculate correlation coefficients
    correlation_ab = np.corrcoef(performance_a, performance_b)[0, 1]
    correlation_ba = np.corrcoef(performance_b, performance_a)[0, 1]

    return correlation_ab, correlation_ba


def calculate_interaction_strength_from_logs(
        log_a: pd.DataFrame,
        log_b: pd.DataFrame,
) -> Tuple[float, float]:
    """
    Calculates the interaction strength between two processes from event logs.

    :param log_a: Event log for Process A.
    :param log_b: Event log for Process B.
    :param interaction_coeff_ab: Interaction coefficient for Process B affecting Process A.
    :param interaction_coeff_ba: Interaction coefficient for Process A affecting Process B.
    :return: Interaction strengths (A -> B and B -> A).
    """
    # Extract performance metrics (throughput time) for both logs
    performance_a: list[float] = extract_performance_metrics(log_a)
    performance_b: list[float] = extract_performance_metrics(log_b)
    interaction_coeff_ab, interaction_coeff_ba = estimate_interaction_coeff(performance_a, performance_b)

    print("Interaction Coefficients: ", interaction_coeff_ab, interaction_coeff_ba)
    # Calculate interaction strength using the previously defined function
    return calculate_interaction_strength(performance_a, performance_b, interaction_coeff_ab, interaction_coeff_ba)


def calculate_niche_overlap_from_logs(
        log_a: pd.DataFrame,
        log_b: pd.DataFrame
) -> float:
    """
    Calculates niche overlap between two processes based on resource usage from event logs.

    :param log_a: Event log for Process A.
    :param log_b: Event log for Process B.
    :return: Niche overlap between Process A and Process B.
    """
    # Infer resource usage from the event logs
    resource_usage_a = infer_resource_usage(log_a)
    resource_usage_b = infer_resource_usage(log_b)

    # Convert resource usage dictionaries to lists of proportions based on shared resources
    shared_resources = set(resource_usage_a.keys()).union(set(resource_usage_b.keys()))

    resource_usage_a_values = [resource_usage_a.get(resource, 0.0) for resource in shared_resources]
    resource_usage_b_values = [resource_usage_b.get(resource, 0.0) for resource in shared_resources]

    # Calculate niche overlap using the previously defined function
    return calculate_niche_overlap(resource_usage_a_values, resource_usage_b_values)


if __name__ == "__main__":
    # Example event logs for Process A and Process B
    data_a = {
        CASE_ID_KEY: ['A1', 'A1', 'A2', 'A2', 'A3', 'A3'],
        ACTIVITY_KEY: ['Start', 'End', 'Start', 'End', 'Start', 'End'],
        TIMESTAMP_KEY: ['2023-01-01 10:00:00', '2023-01-01 12:00:00',
                        '2023-01-02 09:00:00', '2023-01-02 11:30:00',
                      '2023-01-03 15:00:00', '2023-01-03 16:00:00'],
        RESOURCE_KEY: ['R1', 'R1', 'R2', 'R2', 'R3', 'R3']
    }

    data_b = {
        CASE_ID_KEY: ['B1', 'B1', 'B2', 'B2', 'B3', 'B3'],
        ACTIVITY_KEY: ['Start', 'End', 'Start', 'End', 'Start', 'End'],
        TIMESTAMP_KEY: ['2023-01-01 11:00:00', '2023-01-01 13:30:00',
                      '2023-01-02 10:00:00', '2023-01-02 12:00:00',
                      '2023-01-03 16:00:00', '2023-01-03 18:00:00'],
        RESOURCE_KEY: ['R1', 'R1', 'R1', 'R2', 'R2', 'R2']
    }
    log_a = pd.DataFrame(data_a)
    log_b = pd.DataFrame(data_b)

    # SEPSIS_LOG: pd.DataFrame = pd.read_feather(SEPSIS_FEATHER_FILE_PATH)
    # # Group the event log by 'CaseID' to get separate logs for each process
    # midpoint = len(SEPSIS_LOG) // 2  # Integer division to find the midpoint

    # log_a: pd.DataFrame = SEPSIS_LOG.iloc[:midpoint].copy()
    # log_b: pd.DataFrame = SEPSIS_LOG.iloc[midpoint:midpoint + len(log_a)].copy()

    # Calculate interaction strength
    is_a_to_b, is_b_to_a = calculate_interaction_strength_from_logs(log_a, log_b)
    print(f"Interaction Strength (A -> B): {is_a_to_b:.4f}")
    print(f"Interaction Strength (B -> A): {is_b_to_a:.4f}")

    # Calculate niche overlap
    niche_overlap = calculate_niche_overlap_from_logs(log_a, log_b)
    print(f"Niche Overlap: {niche_overlap:.4f}")
