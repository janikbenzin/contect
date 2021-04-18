from typing import Dict, Any, List, Set
from math import ceil, floor
from random import Random
from datetime import timedelta, date
from datetime import datetime

from evaluation.deviations.contextunaware.param.config import AddParameters
from evaluation.objects.param.config import FRIDAY, MONDAY, SATURDAY, SUNDAY
from evaluation.scenarios.schedule import ScheduleParameters

from contect.available.available import AvailableClassifications, AvailableClassificationValues, AvailableGranularity
from contect.available.constants import HOURS_IN_DAY
from contect.context.objects.situations.helpers.versions.extract import get_start_hour_shift
from contect.parsedata.objects.ocdata import ObjectCentricData, Event, sort_events
import contect.context.objects.timeunits.timeunit as tu

# seed(20201120)
from contect.parsedata.objects.oclog import ObjectCentricLog
from evaluation.scenarios.directlyfollows import DirectlyParameters
from evaluation.scenarios.timeunit import TimeUnitParameters
from evaluation.scenarios.util import sample_n_any, sample_days, sample_any


def classify_resource_capacity_util(resource_key: str,
                                    random: Random,
                                    perc_pos_attributable: float,
                                    events_split: Dict[AvailableGranularity, Dict[int, Dict[str, Event]]],
                                    context_aware_days: Dict[str, Dict[str, Any]],
                                    granularity: AvailableGranularity) -> None:
    events_split = events_split[granularity]
    attributable_event_counts = {time: [event for event in list(events_split[time].values())
                                        if any_attributable_res(time, event, resource_key, context_aware_days)]
                                 for time in events_split}
    [mark_as_context_aware_normal(event)
     for time in events_split
     for event in random.sample(attributable_event_counts[time],  # Randomly sampled keys
                                get_number_of_attributable_events(attributable_event_counts[time],
                                                                  perc_pos_attributable))]


def get_number_of_attributable_events(events: List[Event],
                                      perc_pos_attributable: float):
    return ceil(len(events) * perc_pos_attributable)


def any_attributable_res(time: int,
                         event: Event,
                         resource_key: str,
                         context_aware_days: Dict[str, Dict[str, Any]]) -> bool:
    return floor(time / HOURS_IN_DAY) in context_aware_days[event.vmap[resource_key]]['days'] and \
           event.vmap[AvailableClassifications.D.value] == AvailableClassificationValues.TRUE.value


def any_attributable_tu(week, event, context_aware_weeks):
    return week in context_aware_weeks and event.vmap[
        AvailableClassifications.D.value] == AvailableClassificationValues.TRUE.value


def classify_global_tu_performance(timespan: tu.TimeSpan,
                                   timespan_d: tu.TimeSpan,
                                   year_adjustment: float,
                                   random: Random,
                                   perc_pos_attributable: float,
                                   events_split: Dict[AvailableGranularity, Dict[int, Dict[str, Event]]],
                                   granularity: AvailableGranularity,
                                   excess_log: ObjectCentricLog,
                                   weekly_demand: int,
                                   weeks: Set[int],
                                   weeks_to_events: Dict[int, Dict[str, Event]],
                                   data: ObjectCentricData,
                                   context_aware_weeks: List[int],
                                   parameters: TimeUnitParameters = TimeUnitParameters(),
                                   add_param: AddParameters = AddParameters()) -> None:
    attributable_event_counts = {week: [event for eid, event in weeks_to_events[week].items()
                                        if any_attributable_tu(week, event, context_aware_weeks)]
                                 for week in weeks_to_events}
    [mark_as_context_aware_normal(event)
     for week in weeks_to_events
     for event in random.sample(attributable_event_counts[week],  # Randomly sampled keys
                                get_number_of_attributable_events(attributable_event_counts[week],
                                                                  perc_pos_attributable))]


def classify_schedule(year_adjustment: float,
                      random: Random,
                      events_split: Dict[AvailableGranularity, Dict[int, Dict[str, Event]]],
                      granularity: AvailableGranularity,
                      data: ObjectCentricData,
                      weekends: Dict[int, Dict[str, Dict[str, Event]]],
                      parameters: ScheduleParameters = ScheduleParameters()) -> None:
    n_weekends = sample_n_any(parameters.unusual_weekends, year_adjustment, random)
    context_aware_weekends = sample_any(list(weekends.keys()), n_weekends, random)
    shifted = [sample_any(list(parameters.shifted), 1, random)[0] for i in range(n_weekends)]
    fr_or_mons = [sample_any(list(parameters.fr_or_mon), 1, random)[0] for i in range(n_weekends)]
    d_delta = timedelta(days=1)
    for index, weekend in enumerate(context_aware_weekends):
        fr_or_mon = fr_or_mons[index]
        if FRIDAY in weekends[weekend]:
            friday_events = weekends[weekend][FRIDAY]
        else:
            friday_events = None
        if SATURDAY in weekends[weekend]:
            saturday_events = weekends[weekend][SATURDAY]
        else:
            saturday_events = None
        if SUNDAY in weekends[weekend]:
            sunday_events = weekends[weekend][SUNDAY]
        else:
            sunday_events = None
        if MONDAY in weekends[weekend]:
            monday_events = weekends[weekend][MONDAY]
        else:
            monday_events = None
        if fr_or_mon == 0:
            # Take from Friday night
            if friday_events is not None:
                shift_n = int(len(friday_events) * shifted[index])
                if shift_n > 0:
                    shift_keys = list(friday_events.keys())[-shift_n:]
                    if saturday_events is not None:
                        first_time = saturday_events[list(saturday_events.keys())[0]].time
                    else:
                        # Saturday night 23:59:00
                        first_time = tu.round_start_to_granularity(friday_events[shift_keys[0]].time,
                                                                   AvailableGranularity.DAY) + 2 * d_delta - timedelta(minutes=1)
                    year = first_time.year
                    month = first_time.month
                    day = first_time.day
                    night_time = datetime(year, month, day)
                    morning_step_width = (first_time - night_time) / shift_n
                    # Simply shift to Saturday morning before the first existing event on Saturday
                    for i, key in enumerate(shift_keys):
                        friday_events[key].time = night_time + i * morning_step_width
                        mark_as_context_aware_deviating(friday_events[key])
        else:
            # Take from Monday morning
            if monday_events is not None:
                shift_n = int(len(monday_events) * shifted[index])
                if shift_n > 0:
                    shift_keys = list(monday_events.keys())[:shift_n]
                    if sunday_events is not None:
                        last_time = sunday_events[list(sunday_events.keys())[0]].time
                    else:
                        # Sunday morning 00:01:00
                        last_time = tu.round_start_to_granularity(monday_events[shift_keys[0]].time,
                                                                  AvailableGranularity.DAY) - d_delta + timedelta(minutes=1)
                    year = last_time.year
                    month = last_time.month
                    day = last_time.day
                    night_time = datetime(year, month, day) + d_delta
                    night_step_width = (night_time - last_time) / shift_n
                    # Simply shift to Saturday morning before the first existing event on Saturday
                    for i, key in enumerate(shift_keys):
                        monday_events[key].time = last_time + i * night_step_width
                        mark_as_context_aware_deviating(monday_events[key])


def classify_df_performance(timespan: tu.TimeSpan,
                            timespan_d: tu.TimeSpan,
                            year_adjustment: float,
                            random: Random,
                            events_split: Dict[AvailableGranularity, Dict[int, Dict[str, Event]]],
                            granularity: AvailableGranularity,
                            parameters: DirectlyParameters = DirectlyParameters()) -> None:
    n_days = sample_n_any(parameters.excess_days, year_adjustment, random)
    context_aware_days = sample_days(n_days, timespan_d, random)
    delays = sample_any(parameters.hour_delay, n_days, random)
    # We compute the actual numbering of hours for the start day, ie we shift the hourly numbering by this shift
    # This reduces the number of to be limited delay events due to having earlier events in the daily scope
    start_time = timespan_d.start
    start_hour_shift = int(get_start_hour_shift(start_time, timespan))
    events_split = events_split[granularity]
    for index, day in enumerate(context_aware_days):
        time_units = [day * HOURS_IN_DAY + h for h in range(HOURS_IN_DAY)]
        events_temp = {}
        for t in time_units:
            if t - start_hour_shift in events_split:
                events_temp = {**events_temp, **events_split[t - start_hour_shift]}
        hour_delay = timedelta(hours=delays[index])
        # We keep the limited events, so we can distribute them over the remaining time period from
        # the last event's normally delayed time to the maximal time of the parameters
        limited_events = []
        last_time = None
        for eid, event in events_temp.items():
            delayed_time = hour_delay + event.time
            if delayed_time.hour == parameters.max_time or delayed_time.hour < event.time.hour:
                limited_events.append(event)
            else:
                event.time = delayed_time
                mark_as_context_aware_deviating(event)
                last_time = delayed_time
        if last_time is None:
            if len(events_temp) == 0:
                continue
            else:
                last_time = events_temp[list(events_temp.keys())[-1]].time
        n_limited = len(limited_events)
        if n_limited > 0:
            limited_time = tu.round_start_to_granularity(last_time,
                                                         AvailableGranularity.DAY) + timedelta(
                hours=parameters.alternative_hour,
                minutes=parameters.alternative_minute)
            alternative_range_step_width = (limited_time - last_time) / n_limited
            start = last_time + alternative_range_step_width
            for event in limited_events:
                event.time = start
                mark_as_context_aware_deviating(event)
                start += alternative_range_step_width


def mark_as_context_aware_normal(event: Event) -> None:
    event.vmap[AvailableClassifications.D.value] = AvailableClassificationValues.FALSE.value
    event.vmap[AvailableClassifications.CAN.value] = AvailableClassificationValues.TRUE.value


def mark_as_context_aware_deviating(event: Event) -> None:
    if event.vmap[AvailableClassifications.D.value] == AvailableClassificationValues.TRUE.value:
        return
    else:
        event.vmap[AvailableClassifications.N.value] = AvailableClassificationValues.FALSE.value
        event.vmap[AvailableClassifications.CAD.value] = AvailableClassificationValues.TRUE.value
