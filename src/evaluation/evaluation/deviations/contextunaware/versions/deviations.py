from datetime import datetime
from typing import Tuple
import copy
import random

from contect.parsedata.objects.ocdata import ObjectCentricData, Event
from contect.available.available import AvailableClassifications, AvailableClassificationValues, AvailableSelections
from evaluation.deviations.contextunaware.param.config import AddParameters


# Implemented as rework, i.e. the same as repeat
def inject_add_deviation(data: ObjectCentricData,
                         start: datetime,
                         end: datetime,
                         eid: str) -> None:
    param = AddParameters()
    event = data.raw.events[eid]
    event_duplicate = Event(param.key, event.act, event.time, event.omap, event.vmap, event.context)
    potential_new_time = event.time + param.timedelta
    if potential_new_time > end or potential_new_time < start:
        # negating the timedelta always yields a time in the timespan, if it would otherwise lie outside
        event_duplicate.time = event.time - param.timedelta
    else:
        event_duplicate.time = event.time + param.timedelta
    mark_as_deviating(event_duplicate)
    data.raw.events[param.key] = event_duplicate


def inject_remove_deviation(data: ObjectCentricData,
                            eid: str) -> None:
    del data.raw.events[eid]


def inject_replace_deviation(data: ObjectCentricData,
                             eids: Tuple[str, str]) -> None:
    eid1, eid2 = eids
    event1 = data.raw.events[eid1]
    event2 = data.raw.events[eid2]
    timestamp1 = event1.time
    event1.time = event2.time
    event2.time = timestamp1
    mark_as_deviating(event1)
    mark_as_deviating(event2)


def inject_replace_res_deviation(data: ObjectCentricData,
                                 eid: str) -> None:
    event = data.raw.events[eid]
    key = data.vmap_param.vmap_params[AvailableSelections.RESOURCE]
    ress = data.meta.ress.difference({event.vmap[key]})
    res = random.sample(list(ress), 1)
    event.vmap[key] = res[0]
    mark_as_deviating(event)


def mark_as_deviating(event: Event) -> None:
    event.vmap[AvailableClassifications.N.value] = AvailableClassificationValues.FALSE.value
    event.vmap[AvailableClassifications.D.value] = AvailableClassificationValues.TRUE.value
