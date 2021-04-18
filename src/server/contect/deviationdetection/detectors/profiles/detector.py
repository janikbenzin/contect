from math import ceil

from contect.available.available import AvailableClassifications, AvailableDetectors
from contect.deviationdetection.detectors.profiles.param.config import ProfilesParameters
from contect.deviationdetection.detectors.profiles.cycling.cycling import cycle_cyclic_sc
from contect.parsedata.objects.oclog import ObjectCentricLog
from contect.deviationdetection.util.util import assign_trace_classification_to_log, classify_trace


class ProfilesDetector:
    param: ProfilesParameters

    def __init__(self, param: ProfilesParameters):
        self.param = param

    def detect(self, log: ObjectCentricLog) -> float:
        log_size = len(log.traces)
        self.param.log_size = log_size
        if isinstance(self.param.init_initial_norm, int):
            self.param.initial_norm = {tid: self.param.init_initial_norm for tid in range(log_size)}
        else:
            self.param.initial_norm = {tid: self.param.init_initial_norm[tid] for tid in range(log_size)}
        self.param.sample_size = int((1 - self.param.deviating_perc) * log_size)
        self.param.n_deviating = int(ceil(self.param.deviating_perc * log_size))
        param = self.param
        threshold_score, profilings, classification = cycle_cyclic_sc(log=log,
                                                                      norm=param.initial_norm,
                                                                      sample_size=param.sample_size,
                                                                      loop_threshold=param.loop_threshold,
                                                                      n_deviating=param.n_deviating,
                                                                      profiles_param=param.profiles_param,
                                                                      normal_adj=param.normal_adj,
                                                                      deviating_adj=param.deviating_adj,
                                                                      log_size=param.log_size,
                                                                      weights=param.weights)
        detector = AvailableDetectors.PROF
        for tid in log.traces:
            classify_trace(tid in classification[AvailableClassifications.N], 1 - profilings[tid], detector, log, tid)

        assign_trace_classification_to_log(detector, log)
        return 1 - threshold_score


