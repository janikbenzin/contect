from dataclasses import dataclass, field
from typing import Any, Set, Dict
from datetime import datetime
from numpy import cumsum, arange
from random import Random

from contect.parsedata.objects.ocdata import Event, ObjectCentricData
from contect.parsedata.objects.oclog import ObjectCentricLog
from evaluation.deviations.contextunaware.param.config import AddParameters
from evaluation.scenarios.util import sample_n_any, sample_any


@dataclass
class TimeUnitParameters:
    excess_weeks: Any = field(default_factory=lambda: range(2, 5))
    excess_demand: Any = field(default_factory=lambda: arange(0.05, 1.01, 0.01))


def add_excess_demand_events(year_adjustment: float,
                             random: Random,
                             excess_log: ObjectCentricLog,
                             weekly_demand: int,
                             weeks: Set[int],
                             weeks_to_events: Dict[int, Dict[str, Event]],
                             data: ObjectCentricData,
                             parameters: TimeUnitParameters = TimeUnitParameters()):
    n_weeks = sample_n_any(parameters.excess_weeks, year_adjustment, random)
    context_aware_weeks = sample_any(list(weeks), n_weeks, random)
    demands = [sample_any(parameters.excess_demand, 1, random)[0] for i in range(n_weeks)]
    excess_demands = [0] + [int(weekly_demand * demand) for demand in demands]
    excess_demands = cumsum(excess_demands)
    excess_week_traces = [[excess_log.traces[tid] for tid in range(excess_demands[i], excess_demands[i + 1])]
                          for i in range(len(excess_demands) - 1)]
    for index, week in enumerate(context_aware_weeks):
        existing_events = weeks_to_events[week]
        excess_traces = excess_week_traces[index]
        dt = existing_events[list(existing_events.keys())[0]].time
        event = excess_traces[0].events[0]
        start_time_of_old_week = event.time
        # We need to insert the excess demand events in their existing order relative to the new week start
        timedeltas = [event.time - start_time_of_old_week
                      for trace in excess_traces
                      for event in trace.events]
        start_time_of_new_week = datetime(dt.year, dt.month, dt.day,
                                          event.time.hour, event.time.minute, event.time.second,
                                          event.time.microsecond)
        i = 0
        for trace in excess_traces:
            for event in trace.events:
                new_time = start_time_of_new_week + timedeltas[i]
                add_param = AddParameters()
                new_id = add_param.key
                excess_event = Event(new_id,
                                     event.act,
                                     new_time,
                                     event.omap,
                                     event.vmap,
                                     event.context)
                data.raw.events[new_id] = excess_event
                i += 1
    #data.raw.objects = {**data.raw.objects, **excess_log.objects}
    return context_aware_weeks
