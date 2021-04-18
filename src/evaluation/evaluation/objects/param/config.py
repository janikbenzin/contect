from typing import List, Optional, Dict, Union, Tuple, Any
from dataclasses import dataclass, field, InitVar

import contect.available.available
import contect.available.available as av
from contect.context.objects.context.config.param import ContextParameters
from contect.context.objects.context.versions.context import Context
from contect.context.objects.situations.helpers.additionaldata.additionaldata import AdditionalDataContainer
from contect.context.objects.timeunits.timeunit import TimeSpan
from contect.parsedata.objects.ocdata import ObjectCentricData, Event, sort_events
from contect.deviationdetection.objects.detection import Detection
from contect.parsedata.objects.oclog import ObjectCentricLog, Trace

FRIDAY = 'friday'
SATURDAY = 'saturday'
SUNDAY = 'sunday'
MONDAY = 'monday'


@dataclass
class EvaluationSituation:
    entity: av.AvailableEntities
    situation: av.AvailableSituations
    selection: av.AvailableSelections


def default_situation_combinations():
    return [
        EvaluationSituation(av.AvailableEntities.TIMEUNIT,
                            av.AvailableSituations.UNIT_PERFORMANCE,
                            av.AvailableSelections.GLOBAL),
        EvaluationSituation(av.AvailableEntities.CAPACITYUTIL,
                            av.AvailableSituations.CAPACITY,
                            av.AvailableSelections.RESOURCE),
        EvaluationSituation(av.AvailableEntities.DIRECTLYFOLLOWS,
                            av.AvailableSituations.WAIT_PERFORMANCE,
                            av.AvailableSelections.ACTIVITY),
        EvaluationSituation(av.AvailableEntities.TIMEUNIT,
                            av.AvailableSituations.SCHEDULE,
                            av.AvailableSelections.GLOBAL)
    ]


@dataclass
class EvaluationExperiment:
    perc_deviating: float
    perc_pos_attributable: Dict[av.AvailableSituations, float] = field(init=False)
    perc_pos_attributables: InitVar[Tuple[float, float]]
    detector: av.AvailableDetectors
    data_name: str
    granularity: av.AvailableGranularity
    dataset: ObjectCentricData
    timespan: TimeSpan
    context_param: ContextParameters
    real_perc_deviating: float = field(default_factory=lambda: 0)
    real_perc_ca_deviating: float = field(default_factory=lambda: 0)
    real_perc_deviating_ca: float = field(default_factory=lambda: 0)
    real_perc_ca_normal: float = field(default_factory=lambda: 0)
    real_perc_normal: float = field(default_factory=lambda: 0)
    log: Optional[ObjectCentricLog] = field(default_factory=lambda: None)
    log_with_classification: Optional[Dict[int, Trace]] = field(default_factory=lambda: None)
    detection: Optional[Detection] = field(default_factory=lambda: None)
    context: Optional[Context] = field(default_factory=lambda: None)
    additional_data: Optional[Dict[av.AvailableGranularity,
                                   AdditionalDataContainer]] = field(default_factory=lambda: None)
    situation_combinations: List[EvaluationSituation] = field(default_factory=lambda: default_situation_combinations())
    deviation_types: List[av.AvailableDeviationTypes] = field(init=False)
    weeks_to_events: Dict[int, Dict[str, Event]] = field(default_factory=lambda: {})
    weekends: Dict[int, Dict[str, Dict[str, Event]]] = field(default_factory=lambda: {})
    context_dict: Any = field(default_factory=lambda: None)
    detection_dict: Any = field(default_factory=lambda: None)

    def __post_init__(self, perc_pos_attributables):
        self.deviation_types = get_method_associated_types(self.detector)
        self.perc_pos_attributable = {av.AvailableSituations.CAPACITY: perc_pos_attributables[0],
                                      av.AvailableSituations.UNIT_PERFORMANCE: perc_pos_attributables[1]}

    def init_weeks(self):
        weekend_n = 0
        # sort_events(self.dataset)
        events = self.dataset.raw.events
        for index, eid in enumerate(events):
            event = events[eid]
            week = event.time.isocalendar()[1]
            if week in self.weeks_to_events:
                self.weeks_to_events[week][event.id] = event
            else:
                self.weeks_to_events[week] = {event.id: event}

    def init_weekends(self):
        weekend_n = 0
        sort_events(self.dataset)
        events = self.dataset.raw.events
        for index, eid in enumerate(events):
            event = events[eid]
            weekday = event.time.weekday()
            if weekday == 4:
                if weekend_n not in self.weekends:
                    self.weekends[weekend_n] = {}
                self.assign_to_weekends(event, weekend_n, FRIDAY)
            if weekday == 5:
                if weekend_n not in self.weekends:
                    self.weekends[weekend_n] = {}
                self.assign_to_weekends(event, weekend_n, SATURDAY)
            if weekday == 6:
                if weekend_n not in self.weekends:
                    self.weekends[weekend_n] = {}
                self.assign_to_weekends(event, weekend_n, SUNDAY)
            if weekday == 0:
                if weekend_n > 0 and weekend_n not in self.weekends:
                    self.weekends[weekend_n] = {}
                if weekend_n in self.weekends:
                    self.assign_to_weekends(event, weekend_n, MONDAY)
            if weekday == 1:
                if weekend_n in self.weekends:
                    weekend_n += 1

    def assign_to_weekends(self, event, weekend_n, key):
        if key in self.weekends[weekend_n]:
            self.weekends[weekend_n][key][event.id] = event
        else:
            self.weekends[weekend_n][key] = {}
            self.weekends[weekend_n][key][event.id] = event


def get_method_associated_types(method: contect.available.available.AvailableDetectors) -> List[
    av.AvailableDeviationTypes]:
    return [av.AvailableDeviationTypes.REM,
                av.AvailableDeviationTypes.REPL,  # replace is swapping to events
                av.AvailableDeviationTypes.ADD,  # Add = rework = repeat
                av.AvailableDeviationTypes.REPLR]
