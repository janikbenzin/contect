from typing import Dict, Set, List, Union
from datetime import datetime
from numpy import mean, isnan

from contect.available.available import AvailableSelections
from contect.parsedata.config.param import CsvParseParameters, JsonParseParameters
from contect.parsedata.objects.ocdata import Event, MetaObjectCentricData, Obj
from contect.parsedata.objects.oclog import ObjectCentricLog
from contect.parsedata.correlate import get_obj_ids


def extract_capacity(selection: AvailableSelections,
                     meta: MetaObjectCentricData,
                     vmap_param: Union[CsvParseParameters, JsonParseParameters],
                     chunk: Dict[str, Event]
                     ) \
        -> Dict[AvailableSelections, Dict[AvailableSelections, int]]:
    events = [event for index, event in chunk.items()]
    activities = meta.acts
    if selection is AvailableSelections.RESOURCE:
        return get_capacities_nested_value(events,
                                           activities,
                                           meta.ress,
                                           vmap_param.vmap_params[AvailableSelections.RESOURCE])
    else:
        return get_capacities_nested_value(events,
                                           activities,
                                           meta.locs,
                                           vmap_param.vmap_params[AvailableSelections.LOCATION])


def get_capacities_nested_value(events: List[Event],
                                activities: Set[str],
                                selected_data: Set[str],
                                vmap_key: str) \
        -> Dict[AvailableSelections, Dict[AvailableSelections, int]]:
    return {
        selection2: {
            selection1:
                count_events_for_selections(events, selection1, selection2, vmap_key)
            for selection1 in selected_data
        }
        for selection2 in activities
    }


def count_events_for_selections(events, selection1, selection2, vmap_key):
    return sum([1 for event in events
                if event.act == str(selection2) and
                str(selection1) in event.vmap[vmap_key] and str(event.vmap[vmap_key]) == str(selection1)])


def count_events_for_selection(events, selection1, vmap_key):
    return sum([1 for event in events
                if str(selection1) in event.vmap[vmap_key] and str(event.vmap[vmap_key]) == str(selection1)])


def extract_timeunit(selection: AvailableSelections,
                     meta: MetaObjectCentricData,
                     vmap_param: Union[CsvParseParameters, JsonParseParameters],
                     objects: Dict[str, Obj],
                     chunk: Dict[str, Event]) \
        -> Dict[AvailableSelections, Dict[AvailableSelections, int]]:
    if selection is AvailableSelections.GLOBAL:
        return {AvailableSelections.GLOBAL.value: len(chunk)}
    else:
        events = [event for index, event in chunk.items()]
        if selection is AvailableSelections.RESOURCE:
            return {selection1: count_events_for_selection(events,
                                                           selection1,
                                                           vmap_param.vmap_params[AvailableSelections.RESOURCE])
                    for selection1 in meta.ress}
        elif selection is AvailableSelections.LOCATION:
            return {selection1: count_events_for_selection(events,
                                                           selection1,
                                                           vmap_param.vmap_params[AvailableSelections.LOCATION])
                    for selection1 in meta.locs}
        elif selection is AvailableSelections.OBJECTTYPE:
            return {selection1: sum([1 for event in events if len(get_obj_ids(event, objects, {selection1})) != 0])
                    for selection1 in meta.obj_types}
        elif selection is AvailableSelections.ACTIVITY:
            return {selection1: sum([1 for event in events if event.act == str(selection1)])
                    for selection1 in meta.acts}


def extract_directly_follows(meta: MetaObjectCentricData,
                             log: ObjectCentricLog,
                             chunk: Dict[str, Event]) -> Dict[AvailableSelections, Dict[AvailableSelections, int]]:
    activities = meta.acts
    return {act: mean(get_time_difference_for_events(act, chunk, log))
            if not isnan(mean(get_time_difference_for_events(act, chunk, log))) else 0
            for act in activities}


def get_time_difference_for_events(act: str,
                                   chunk: Dict[str, Event],
                                   log: ObjectCentricLog) -> List[float]:
    return [get_time_difference_for_event(event, log) for index, event in chunk.items() if event.act == act]


def get_time_difference_for_event(event: Event,
                                  log: ObjectCentricLog) -> float:
    if event.id in log.event_to_traces:
        trace = log.traces[log.event_to_traces[event.id]]
        pos = 0
        for event2 in trace.events:
            if event2.id == event.id:
                if pos == 0:
                    return 0
                else:
                    waiting_time = event2.time - trace.events[pos - 1].time
                    return waiting_time.total_seconds()
            pos += 1
        return 0
    else:
        return 0
