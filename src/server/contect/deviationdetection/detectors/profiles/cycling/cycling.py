from typing import Tuple, Dict, List, Union

from contect.available.available import AvailableClassifications, AvailableProfiles
from contect.deviationdetection.detectors.profiles.param.config import DependencyProfileParameters
from contect.deviationdetection.detectors.profiles.util.util import get_normal_sample, get_next_classification
from contect.parsedata.objects.oclog import ObjectCentricLog


def cycle_cyclic_sc(log: ObjectCentricLog,
                    norm: Dict[int, float],
                    sample_size: int,
                    loop_threshold: int,
                    n_deviating: int,
                    profiles_param: Dict[AvailableProfiles, Union[DependencyProfileParameters]],
                    normal_adj: float,
                    deviating_adj: float,
                    log_size: int,
                    weights: Dict[AvailableProfiles, float],
                    loop_iterator: int = 0) -> Tuple[float, Dict[int, float],
                                                     Dict[AvailableClassifications, List[int]]]:
    normal_sample = get_normal_sample(log=log,
                                      norm=norm,
                                      sample_size=sample_size)
    threshold_score, profilings, new_norm, classification = get_next_classification(log=log,
                                                                                    normal_sample=normal_sample,
                                                                                    profiles_param=profiles_param,
                                                                                    normal_adj=normal_adj,
                                                                                    deviating_adj=deviating_adj,
                                                                                    n_deviating=n_deviating,
                                                                                    norm=norm,
                                                                                    weights=weights,
                                                                                    log_size=log_size)
    if loop_iterator <= loop_threshold:
        loop_iterator += 1
        return cycle_cyclic_sc(log=log,
                               norm=new_norm,
                               sample_size=sample_size,
                               loop_threshold=loop_threshold,
                               n_deviating=n_deviating,
                               profiles_param=profiles_param,
                               normal_adj=normal_adj,
                               deviating_adj=deviating_adj,
                               log_size=log_size,
                               weights=weights,
                               loop_iterator=loop_iterator)
    else:
        return threshold_score, profilings, classification
