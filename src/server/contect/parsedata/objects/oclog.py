import sys
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Tuple, Union

from contect.available.available import AvailableSituationType, AvailableDetectors, AvailableSituations, \
    AvailableSelections, AvailableGranularity, AvailableNormRanges, AvailableClassifications
from contect.parsedata.config.param import CsvParseParameters, JsonParseParameters
from contect.parsedata.objects.ocdata import Event, EventId, EventClassic, EventClassicResource, Obj, \
    MetaObjectCentricData


@dataclass
class TraceAlignment:
    alignment: List[Tuple[str, Union[str, None]]]


@dataclass
class TraceADAR:
    sim_trace: Any
    violating: Dict[Tuple[int, int], Dict[Any, Any]]
    sup: float
    sim_sup: float


@dataclass
class TraceAutoenc:
    true: List[float]
    pred: List[float]


@dataclass
class Trace:
    events: List[Event]
    id: int = field(compare=False)
    dev_inf: Dict[AvailableDetectors, Union[TraceAlignment, TraceADAR, TraceAutoenc]] = field(
        default_factory=lambda: {})
    # Context only used for intermediate values of guidance
    context: Dict[int, Dict[AvailableSituationType, float]] = field(default_factory=lambda: {})
    complex_context: Dict[AvailableDetectors, Dict[AvailableSituationType, float]] = field(default_factory=lambda: {})
    rich_context: Dict[AvailableDetectors,
                       Dict[AvailableSituationType,
                            Dict[AvailableSituations,
                                 Dict[AvailableSelections,
                                      Dict[str, Union[float, bool]]]]]] = field(default_factory=lambda: {})
    normal: Dict[AvailableDetectors, bool] = field(default_factory=lambda: {})
    deviating: Dict[AvailableDetectors, bool] = field(default_factory=lambda: {})
    score: Dict[AvailableDetectors, float] = field(default_factory=lambda: {})
    ca_score: Dict[AvailableDetectors, float] = field(default_factory=lambda: {})
    ca_normal: Dict[AvailableDetectors, bool] = field(default_factory=lambda: {})
    ca_deviating: Dict[AvailableDetectors, bool] = field(default_factory=lambda: {})
    methods_bool: List[bool] = field(default_factory=lambda: [])
    norm_range: Optional[AvailableNormRanges] = field(default_factory=lambda: None)


@dataclass
class TraceLightweight:
    events: List[EventId]
    id: int


@dataclass
class TraceClassic:
    events: List[EventClassic]
    id: int


@dataclass
class TraceClassicResource:
    events: List[EventClassicResource]
    id: int


@dataclass
class ObjectCentricLog:
    traces: Dict[int, Trace]
    event_to_traces: Dict[str, int]
    objects: Dict[str, Obj]
    meta: MetaObjectCentricData
    vmap_param: Union[CsvParseParameters, JsonParseParameters]
    models: Dict[AvailableDetectors, Any] = field(default_factory=lambda: {})
    deviating: Dict[AvailableDetectors, Dict[int, Trace]] = field(default_factory=lambda: {})
    normal: Dict[AvailableDetectors, Dict[int, Trace]] = field(default_factory=lambda: {})
    ca_deviating: Dict[AvailableDetectors, Dict[int, Trace]] = field(default_factory=lambda: {})
    ca_normal: Dict[AvailableDetectors, Dict[int, Trace]] = field(default_factory=lambda: {})
    timespan: Optional[Any] = field(default_factory=lambda: None)
    granularity: Optional[AvailableGranularity] = field(default_factory=lambda: None)
    events_timeunits: Dict[AvailableGranularity, Dict[str, int]] = field(default_factory=lambda: {})
    detector_thresholds: Dict[AvailableDetectors, float] = field(default_factory=lambda: {})
    labels: Dict[AvailableDetectors, List[AvailableClassifications]] = field(default_factory=lambda: {})
    ca_degrees: Dict[AvailableDetectors, Dict[AvailableSituationType, float]] = field(default_factory=lambda: {})


@dataclass
class LightweightLog:
    traces: Dict[int, TraceLightweight]


@dataclass
class ClassicLog:
    traces: Dict[int, TraceClassic]


@dataclass
class ClassicResourceLog:
    traces: Dict[int, TraceClassicResource]


def get_tid_filtered_log(log: ObjectCentricLog,
                         tids: List[int]) -> ObjectCentricLog:
    new_traces = {tid: log.traces[tid] for tid in log.traces if tid in tids}
    return ObjectCentricLog(traces=new_traces, event_to_traces=log.event_to_traces, objects=log.objects,
                            meta=log.meta, vmap_param=log.vmap_param)


def get_ca_score(score: float,
                 ca_post_param: Dict[AvailableSituationType, float],
                 context: Dict[AvailableSituationType, float]) -> float:
    pos_factor = (- score) * ca_post_param[AvailableSituationType.POSITIVE] * context[AvailableSituationType.POSITIVE]
    neg_factor = (1 - score) * ca_post_param[AvailableSituationType.NEGATIVE] * context[AvailableSituationType.NEGATIVE]
    return score + pos_factor + neg_factor


def get_ps_alpha(score: float,
                 context: Dict[AvailableSituationType, float],
                 threshold: float) -> Union[float, str]:
    ps_term = score - threshold + sys.float_info.min
    context_ps = context[AvailableSituationType.POSITIVE]
    if score != 0 and context_ps != 0:
        alpha = ps_term / (score * context_ps)
        if 0 <= alpha <= 1:
            return alpha
        else:
            return 'na'
    else:
        return 0


def get_ng_alpha(score: float,
                 context: Dict[AvailableSituationType, float],
                 threshold: float) -> Union[float, str]:
    ng_term = threshold - score
    context_ng = context[AvailableSituationType.NEGATIVE]
    if (1 - score) != 0 and context_ng != 0:
        alpha = ng_term / ((1 - score) * context_ng)
        if 0 <= alpha <= 1:
            return alpha
        else:
            return 'na'
    else:
        return 0