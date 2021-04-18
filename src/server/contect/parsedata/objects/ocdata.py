from dataclasses import dataclass, field
from typing import List, Dict, Set, Any, Optional, Union, Tuple
from datetime import datetime

from contect.available.available import AvailableSelections, AvailableSituationType, AvailableDetectors, \
    AvailableSituations
from contect.parsedata.config.param import CsvParseParameters, JsonParseParameters


@dataclass
class EventId:
    id: str


@dataclass
class EventClassic(EventId):
    act: str
    time: datetime


@dataclass
class EventClassicResource(EventClassic):
    vmap: Dict[str, Any]


@dataclass
class Event(EventClassic):
    omap: List[str]
    vmap: Dict[str, Any]
    # Kept for backward compatibility with the evaluation
    context: Optional[Dict[int, Dict[AvailableSituationType, float]]] = field(default_factory=lambda: None)
    complex_context: Dict[AvailableDetectors, Dict[AvailableSituationType, float]] = field(default_factory=lambda: {})
    rich_context: Dict[AvailableDetectors,
                       Dict[AvailableSituationType,
                            Dict[AvailableSituations,
                                 Dict[AvailableSelections,
                                      Dict[str, Union[float, bool]]]]]] = field(default_factory=lambda: {})
    deviating: Optional[Dict[AvailableDetectors, bool]] = field(default_factory=lambda: None)
    score: Optional[Dict[AvailableDetectors, float]] = field(default_factory=lambda: None)
    ca_score: Optional[Dict[AvailableDetectors, float]] = field(default_factory=lambda: None)
    corr: bool = field(default_factory=lambda: False)


@dataclass
class Obj:
    id: str
    type: str
    ovmap: Dict


@dataclass
class MetaObjectCentricData:
    attr_names: List[str]  # AN
    attr_types: List[str]  # AT
    attr_typ: Dict  # pi_typ

    obj_types: List[str]  # OT

    act_attr: Dict[str, List[str]]  # allowed attr per act
    # act_obj: Dict[str, List[str]]  # allowed ot per act

    acts: Set[str] = field(init=False)
    ress: Set[str] = field(init=False)
    locs: Set[str] = field(init=False)
    attr_events: List[str] = field(default_factory=lambda: [])  # Used for OCEL json data to simplify UI on homepage

    def __post_init__(self):
        self.acts = {act for act in self.act_attr}


@dataclass
class RawObjectCentricData:
    events: Dict[str, Event]
    objects: Dict[str, Obj]

    @property
    def obj_ids(self) -> List[str]:
        return list(self.objects.keys())


@dataclass
class ObjectCentricData:
    meta: MetaObjectCentricData
    raw: RawObjectCentricData
    vmap_param: Union[CsvParseParameters, JsonParseParameters]

    def __post_init__(self):
        if self.vmap_param.vmap_availables[AvailableSelections.RESOURCE]:
            self.meta.ress = {event.vmap[self.vmap_param.vmap_params[AvailableSelections.RESOURCE]]
                              for index, event in self.raw.events.items()}
        else:
            self.meta.ress = {}

        if self.vmap_param.vmap_availables[AvailableSelections.LOCATION]:
            self.meta.locs = {event.vmap[self.vmap_param.vmap_params[AvailableSelections.LOCATION]]
                              for index, event in self.raw.events.items()}
        else:
            self.meta.locs = {}


def sort_events(data: ObjectCentricData) -> None:
    events = data.raw.events
    data.raw.events = {k: event for k, event in sorted(events.items(), key=lambda item: item[1].time)}
