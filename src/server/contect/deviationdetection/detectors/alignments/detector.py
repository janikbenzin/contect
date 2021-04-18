import contect.deviationdetection.detectors.alignments.util as util
from contect.available.available import AvailableDetectors
from contect.deviationdetection.detectors.alignments.param.config import AlignmentsParameters
from contect.deviationdetection.util.util import assign_trace_classification_to_log, classify_trace
from contect.parsedata.objects.exporter.exporter import export_to_pm4py
from contect.parsedata.objects.oclog import ObjectCentricLog, TraceAlignment


class AlignmentsDetector:
    param: AlignmentsParameters

    def __init__(self, param: AlignmentsParameters):
        self.param = param

    def detect(self, log: ObjectCentricLog) -> float:
        pm4py_log = export_to_pm4py(log)
        # For each dfg filter threshold, IM discovers a process model and the sum of evaluation metrics is computed
        models = [{'model': model,
                   'metric': util.evaluate_quality(pm4py_log, *model)} for model in
                  [util.discover_process_model(pm4py_log, threshold) for threshold in self.param.thresholds]]
        # The model with the maximum sum of evaluation metrics is selected as optimal
        optimal = max(models, key=lambda result: result['metric'])
        # Alignments are computed
        aligned = util.align(pm4py_log, *optimal['model'])
        # The alignment results are transformed into the internal representation of normal / deviating
        detector = AvailableDetectors.ALIGN
        for tid in log.traces:
            classify_trace(aligned[tid]['cost'] == 0,
                           1 - aligned[tid]['fitness'],  # Reverse to match general classification
                           detector, log, tid)
            log.traces[tid].dev_inf[detector] = TraceAlignment(alignment=aligned[tid]['alignment'])

        assign_trace_classification_to_log(detector, log)
        log.models[detector] = optimal['model']
        return 0  # The reverse of non-deviating trace fitness is 0, i.e. anything above 0 is deviating -> threshold = 0




