from functools import partial
from typing import Dict, Callable, Union
from pm4py.algo.discovery.dfg import algorithm as dfg_discovery

from contect.available.available import AvailableProfiles
from contect.parsedata.objects.oclog import ObjectCentricLog
from contect.parsedata.objects.exporter.exporter import export_to_pm4py
from contect.deviationdetection.detectors.profiles.profiles.versions.util import get_dependency_relation, RegexDict
from contect.deviationdetection.detectors.profiles.profiles.versions.profiles import apply_df_profile, apply_dr_profile
from contect.deviationdetection.detectors.profiles.param.config import DependencyProfileParameters


def get_profiling(weights: Dict[AvailableProfiles, float],
                  log: ObjectCentricLog,
                  profiles_param: Dict[AvailableProfiles, Union[DependencyProfileParameters]]) -> Callable:
    if AvailableProfiles.DF in weights and AvailableProfiles.DR in weights:
        dfg = dfg_discovery.apply(export_to_pm4py(log))
        max_freq = max(dfg.values())
        if AvailableProfiles.DR in weights:
            dep_rel = RegexDict(get_dependency_relation(log=log,
                                                        profiles_param=profiles_param))
            return lambda trace: (weights[AvailableProfiles.DF] * apply_dr_profile(dfg, max_freq, trace) +
                                  weights[AvailableProfiles.DR] * apply_df_profile(dep_rel, trace)) / sum(
                weights.values())
        else:
            return partial(apply_df_profile, dfg, max_freq)
    else:
        dep_rel = RegexDict(get_dependency_relation(log=log,
                                                    profiles_param=profiles_param))
        return partial(apply_dr_profile, dep_rel)
