from typing import List

from contect.available.available import AvailableDetectors
from contect.parsedata.objects.oclog import ObjectCentricLog


def classify_trace(condition: bool, score: float, detector: AvailableDetectors, log: ObjectCentricLog, tid: int):
    if condition:
        log.traces[tid].normal[detector] = True
    else:
        log.traces[tid].deviating[detector] = True
    log.traces[tid].score[detector] = score


def assign_trace_classification_to_log(detector: AvailableDetectors, log: ObjectCentricLog):
    log.deviating[detector] = {
        tid: trace for tid, trace in log.traces.items() if detector in trace.deviating and trace.deviating[detector]
    }
    log.normal[detector] = {
        tid: trace for tid, trace in log.traces.items() if detector in trace.normal and trace.normal[detector]
    }


# https://stackoverflow.com/questions/3438756/some-built-in-to-pad-a-list-in-python
def pad_list(x: List, n, pad_val='') -> List:
    return x + [pad_val] * (n - len(x))
