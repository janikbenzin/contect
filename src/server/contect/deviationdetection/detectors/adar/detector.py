from sklearn.preprocessing import MinMaxScaler
from numpy import array, nextafter

from contect.available.available import AvailableDetectors
from contect.deviationdetection.detectors.adar.arminer.miner import mine_adar_rules
from contect.deviationdetection.detectors.adar.param.config import ADARParameters
from contect.deviationdetection.detectors.adar.util import detect_adar, merge_similar_rules
from contect.deviationdetection.util.util import classify_trace, assign_trace_classification_to_log
from contect.parsedata.objects.oclog import ObjectCentricLog, TraceADAR


class ADARDetector:
    param: ADARParameters

    def __init__(self, param: ADARParameters):
        self.param = param

    def detect(self, log: ObjectCentricLog) -> float:
        detector = AvailableDetectors.ADAR
        rules = mine_adar_rules(self.param, log)

        rules = merge_similar_rules(rules)

        scores = []
        # The threshold is not exactly 0, but a bit larger, since - after suited transformations see score -
        # ADAR uses <= 0 for normal class in contrast to
        # the contect framework, which uses <0 for normal class. Hence, the next representable positive number after 0
        # is used as a threshold
        threshold = nextafter(0, 1)
        sim_traces = {}
        for tid in log.traces:
            trace_sum, sim_trace_sum, trace_violating, sim_trace, sim_matches = detect_adar(log,
                                                                                            rules,
                                                                                            log.traces[tid],
                                                                                            self.param.vmap_param.vmap_params,
                                                                                            sim_traces)
            if not len(sim_matches[sim_trace.id]) == 0:
                sim_traces.update(sim_matches)
            # Here, the ADAR classification of adec function is transformed to a suitable range in the framework
            # Positive differences (except 0 see above) are classified as anomalous
            score = sim_trace_sum - trace_sum
            scores.append(score)
            classify_trace(condition=score < threshold,
                           score=score,  # non-normalized score -> need to correct that after all are computed
                           detector=detector,
                           log=log,
                           tid=tid)
            log.traces[tid].dev_inf[detector] = TraceADAR(sim_trace=sim_trace,
                                                          violating=trace_violating,
                                                          sup=trace_sum,
                                                          sim_sup=sim_trace_sum)
        # The last value is always the threshold
        scores.append(threshold)
        # Need to normalize scores and extract threshold
        scaler = MinMaxScaler()
        score_array = array(scores)
        score_array = score_array.reshape(-1, 1)
        normalized_scores = [score[0] for score in scaler.fit_transform(score_array)]
        normalized_threshold = normalized_scores[-1]
        normalized_scores = normalized_scores[:-1]
        # Assign the normalized scores to each trace
        for tid, score in zip(list(log.traces.keys()), normalized_scores):
            log.traces[tid].score[detector] = score
        assign_trace_classification_to_log(detector, log)
        log.models[detector] = rules  # Keyed in the same way as trace_violating per trace
        return normalized_threshold
