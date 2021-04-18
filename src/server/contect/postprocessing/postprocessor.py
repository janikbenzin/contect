# https://scikit-learn.org/stable/developers/develop.html
from typing import List

from contect.parsedata.objects.oclog import get_ca_score, ObjectCentricLog
from sklearn.base import BaseEstimator, ClassifierMixin
from contect.available.available import AvailableSituationType, AvailableDetectors, AvailableClassifications

# Change this to your desired post-processing function
DEFAULT_POST_FUNCTION = get_ca_score


def get_label_for_score(old_label: AvailableClassifications, score: float, threshold: float):
    if old_label is AvailableClassifications.N and score >= threshold:
        return AvailableClassifications.CAD
    elif old_label is AvailableClassifications.D and score < threshold:
        return AvailableClassifications.CAN
    elif old_label is AvailableClassifications.D and score >= threshold:
        return AvailableClassifications.D
    else:
        return AvailableClassifications.N


class ContextPostProcessor(BaseEstimator, ClassifierMixin):
    ps: float
    ng: float
    threshold: float
    detector: AvailableDetectors

    def __init__(self,
                 ps: float = 0,
                 ng: float = 0,
                 threshold: float = 0,
                 detector: AvailableDetectors = AvailableDetectors.PROF):
        self.ps = ps
        self.ng = ng
        self.threshold = threshold
        self.detector = detector

    def predict(self, log: ObjectCentricLog) -> ObjectCentricLog:
        threshold = self.threshold
        detector = self.detector
        ca_post_param = {AvailableSituationType.POSITIVE: self.ps,
                         AvailableSituationType.NEGATIVE: self.ng}
        for tid, trace in log.traces.items():
            trace.ca_score[detector] = DEFAULT_POST_FUNCTION(score=trace.score[detector],
                                                             ca_post_param=ca_post_param,
                                                             context=trace.complex_context[detector])
        log.labels[detector] = [get_label_for_score(old_label=log.labels[detector][index],
                                                    score=log.traces[index].ca_score[detector],
                                                    threshold=threshold)
                                if log.traces[index].ca_score[detector] != log.traces[index].score[detector]
                                else log.labels[detector][index]
                                for index in log.traces]
        log.ca_degrees[detector] = ca_post_param
        for tid, trace in log.traces.items():
            if log.labels[detector] is AvailableClassifications.CAD:
                trace.ca_deviating[detector] = True
            elif log.labels[detector] is AvailableClassifications.CAN:
                trace.ca_normal[detector] = True
        return log


def get_true_label(trace, detector):
    if trace.ca_deviating[detector]:
        return AvailableClassifications.CAD.value
    elif trace.ca_normal[detector]:
        return AvailableClassifications.CAN.value
    elif trace.deviating[detector]:
        return AvailableClassifications.D.value
    else:
        return AvailableClassifications.N.value


def get_true_dn_label(trace, detector):
    if trace.ca_deviating[detector]:
        return AvailableClassifications.N.value
    elif trace.ca_normal[detector]:
        return AvailableClassifications.D.value
    elif trace.deviating[detector]:
        return AvailableClassifications.D.value
    else:
        return AvailableClassifications.N.value


def get_true_dn_label_from_label(label):
    if label is AvailableClassifications.CAD:
        return AvailableClassifications.N.value
    elif label is AvailableClassifications.CAN:
        return AvailableClassifications.D.value
    else:
        return label.value