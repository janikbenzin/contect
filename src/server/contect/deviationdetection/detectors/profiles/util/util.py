from typing import Dict, List, Tuple, Union

from contect.deviationdetection.detectors.profiles.param.config import DependencyProfileParameters
from numpy.random import choice

from contect.available.available import AvailableProfiles, AvailableClassifications
from contect.parsedata.objects.oclog import ObjectCentricLog, get_tid_filtered_log
from contect.deviationdetection.detectors.profiles.profiles.factory import get_profiling

def get_next_norm(normal_cases: List[int],
                  deviating_cases: List[int],
                  previous_norm: Dict[int, float],
                  normal_adj: float,
                  deviating_adj: float) -> Dict[int, float]:
    next_normal_norm = {tid: normal_adj * previous_norm[tid] for tid in normal_cases}
    next_deviating_norm = {tid: deviating_adj * previous_norm[tid] for tid in deviating_cases}
    unsorted_next_norm = {**next_normal_norm, **next_deviating_norm}
    return {tid: unsorted_next_norm[tid] for tid in sorted(unsorted_next_norm)}


def get_normal_sample(log: ObjectCentricLog,
                      norm: Dict[int, float],
                      sample_size: int) -> List[int]:
    tids = list(log.traces.keys())
    norm_values = list(norm.values())
    norm_normalized = [norm_value / sum(norm_values) for norm_value in norm_values]
    return choice(tids, size=sample_size, p=norm_normalized)


def get_next_classification(log: ObjectCentricLog,
                            normal_sample: List[int],
                            profiles_param: Dict[AvailableProfiles, Union[DependencyProfileParameters]],
                            normal_adj: float,
                            deviating_adj: float,
                            n_deviating: int,
                            norm: Dict[int, float],
                            weights: Dict[AvailableProfiles, float],
                            log_size: int) -> Tuple[float, Dict[int, float], Dict[int, float],
                                                    Dict[AvailableClassifications, List[int]]]:
    profiling = get_profiling(weights=weights,
                              log=get_tid_filtered_log(log, normal_sample),
                              profiles_param=profiles_param)
    profilings = {tid: profiling(log.traces[tid]) for tid in range(log_size)}
    profilings = {tid: profilings[tid] for tid, value in sorted(profilings.items(), key=lambda item: item[1])}
    tids = list(profilings.keys())
    deviating_tids = tids[:n_deviating]
    normal_tids = tids[n_deviating:]
    threshold_score = profilings[deviating_tids[-1]]
    new_norm = get_next_norm(normal_cases=normal_tids,
                             deviating_cases=deviating_tids,
                             previous_norm=norm,
                             normal_adj=normal_adj,
                             deviating_adj=deviating_adj)
    return threshold_score, profilings, new_norm, {AvailableClassifications.N: normal_tids,
                                                   AvailableClassifications.D: deviating_tids}
