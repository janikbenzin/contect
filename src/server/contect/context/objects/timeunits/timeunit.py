from typing import Dict, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta

from contect.available.available import AvailableGranularity
from contect.parsedata.objects.ocdata import ObjectCentricData
from contect.context.objects.timeunits.container import ContainerSplitObjectCentricData


@dataclass
class TimeUnit:
    start: datetime
    end: datetime


@dataclass
class _TimeSpan:
    start: datetime
    end: datetime
    min_granularity: AvailableGranularity


@dataclass
class TimeSpan(_TimeSpan):
    units: Dict[AvailableGranularity, Dict[
        int, TimeUnit]]



def split_log(data: ObjectCentricData,
              granularity: AvailableGranularity) -> Tuple[ContainerSplitObjectCentricData,
                                                          TimeSpan, Dict[str, int]]:
    events = data.raw.events
    start_time, end_time = get_start_end_time(events)
    start_time = round_start_to_granularity(start_time, granularity)
    add_timedelta = get_timedelta(granularity, 1)

    # Build the units dict for the TimeSpan object
    time_unit, time_units, timespan = get_timespan(add_timedelta, start_time, end_time, granularity)

    # Initialize the dict from time unit to contained events dict

    events_timeunit, events_split = assign_events_to_unit(add_timedelta,
                                                          events,
                                                          time_units,
                                                          granularity,
                                                          start_time,
                                                          time_unit)

    return ContainerSplitObjectCentricData(
        meta=data.meta,
        objects=data.raw.objects,
        events_split=events_split), timespan, events_timeunit


def assign_events_to_unit(add_timedelta, events, time_units, granularity, start_time, time_unit, sort=False):
    # Initialize the dict from time unit to contained events dict
    if sort:
        events = {k: event for k, event in sorted(events.items(), key=lambda item: item[1].time)}
    events_split = {granularity: {
        time_unit: {}
        for time_unit in time_units[granularity]
    }
    }
    # Fill it with correct events
    last_time_unit = time_unit
    time_unit = 0
    next_time = start_time + add_timedelta
    events_timeunit = {}
    for index, event in events.items():
        # As long as an event is not contained in current time unit increment time unit
        while not time_in_range(start_time, next_time, event.time) and time_unit <= last_time_unit:
            time_unit += 1
            start_time = next_time
            next_time += add_timedelta

        events_split[granularity][time_unit][event.id] = event
        events_timeunit[event.id] = time_unit
    return events_timeunit, events_split


def get_start_end_time(events):
    start_time = events[list(events.keys())[0]].time
    end_time = events[list(events.keys())[-1]].time
    return start_time, end_time


def get_timespan(add_timedelta, start_time, end_time, granularity):
    time_unit = 0
    time_units = {granularity: {}}
    next_time = start_time
    while next_time <= end_time:
        time_units[granularity][time_unit] = TimeUnit(
            start=next_time,
            end=next_time + add_timedelta
        )
        next_time += add_timedelta
        time_unit += 1
    timespan = TimeSpan(
        units=time_units,
        start=start_time,
        end=end_time,
        min_granularity=AvailableGranularity.SEC
    )
    return time_unit, time_units, timespan


def get_timedelta(granularity: AvailableGranularity, index):
    if granularity is AvailableGranularity.HR:
        return timedelta(hours=index)
    elif granularity is AvailableGranularity.MIN:
        return timedelta(minutes=index)
    elif granularity is AvailableGranularity.DAY:
        return timedelta(days=index)
    elif granularity is AvailableGranularity.WK:
        return timedelta(weeks=index)
    elif granularity is AvailableGranularity.MON:
        return timedelta(weeks=index * 4)
    else:
        return timedelta(weeks=index * 48)


# from https://stackoverflow.com/questions/10747974/how-to-check-if-the-current-time-is-in-range-in-python
def time_in_range(start: datetime, end: datetime, x: datetime) -> bool:
    """Return true if x is in the range [start, end]"""
    if start <= end:
        return start <= x <= end
    else:
        return start <= x or x <= end


def round_start_to_granularity(start_time: datetime, granularity: AvailableGranularity) -> datetime:
    if granularity is AvailableGranularity.HR:
        return start_time - timedelta(minutes=start_time.minute, seconds=start_time.second)
    elif granularity is AvailableGranularity.MIN:
        return start_time - timedelta(seconds=start_time.second)
    elif granularity is AvailableGranularity.DAY:
        return start_time - timedelta(hours=start_time.hour, minutes=start_time.minute,
                                      seconds=start_time.second)
    else:
        return start_time - timedelta(days=start_time.weekday(), hours=start_time.hour,
                                      minutes=start_time.minute, seconds=start_time.second)
