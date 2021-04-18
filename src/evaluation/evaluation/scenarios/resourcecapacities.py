from typing import Dict, Any, Tuple
from dataclasses import dataclass, field

from contect.available.constants import HOURS_IN_DAY
from evaluation.scenarios.util import sample_n_any, sample_days, sample_any
from numpy import arange
from math import floor

from contect.available.available import AvailableGranularity
import contect.context.objects.timeunits.timeunit as tu


@dataclass
class CapacityParameters:
    capacity_range: Any
    capacity_days: Any
    department: str
    absolute_capacity_per_activity: Any


SYN_ACTS = ['confirm order', 'pay order', 'payment reminder', 'pick item', 'item out of stock',
            'reorder item', 'create package', 'send package', 'failed delivery', 'package delivered',
            'place order']


# Used the 80% percentile of the actual activity counts per resource from the data per day and divided this by 24
# and always rounded up to next integer
@dataclass
class SyntheticCapacityParameters:
    params: Dict[str, CapacityParameters] = field(default_factory=lambda: {
        'Finance': CapacityParameters(
            capacity_range=arange(0.25, 0.76, 0.01),
            capacity_days=range(30, 38),
            department='Finance',
            absolute_capacity_per_activity={
                activity: capacity for activity, capacity in list(zip(SYN_ACTS, [1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0]))
            }
        ),
        'Fullfillment': CapacityParameters(
            capacity_range=arange(0.25, 0.76, 0.01),
            capacity_days=range(30, 38),
            department='Fullfillment',
            absolute_capacity_per_activity={
                activity: capacity for activity, capacity in list(zip(SYN_ACTS, [0, 0, 0, 2, 1, 1, 1, 1, 0, 0, 0]))
            }
        ),
        'Delivery': CapacityParameters(
            capacity_range=arange(0.5, 0.96, 0.01),
            capacity_days=range(0, 7),
            department='Delivery',
            absolute_capacity_per_activity={
                activity: capacity for activity, capacity in list(zip(SYN_ACTS, [0, 0, 0, 0, 0, 0, 0, 0, 42, 1, 0]))
            }
        ),
        'Unassigned': CapacityParameters(
            capacity_range=None,
            capacity_days=None,
            department='None',
            absolute_capacity_per_activity={
                activity: capacity for activity, capacity in list(zip(SYN_ACTS, [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1000]))
            }
        )
    })


def generate_resource_capacities(data,
                                 timespan_d,
                                 year_adjustment,
                                 random,
                                 param: SyntheticCapacityParameters = SyntheticCapacityParameters()) \
        -> Tuple[Dict[str, Dict[str, Any]], Dict[int, Dict[str, Dict[str, float]]]]:
    params = param.params
    # Compute the timespan with granularity day, as the definition of the scenario is based on days

    context_aware_days = {department:
                              {'number_of_days':
                                   sample_n_any(params[department].capacity_days, year_adjustment, random)}
                              if department != 'Unassigned'
                              else {}  # Unassigned does not get any decreased capacities
                          for department in params}
    for department in context_aware_days:
        current = context_aware_days[department]
        if department != 'Unassigned':  # For the number of decreased capacity days, sample the respective capacities
            current['capacities'] = sample_any(params[department].capacity_range, current['number_of_days'], random)
            # On what actual days are capacities decreased
            current['days'] = sample_days(current['number_of_days'], timespan_d, random)
        else:
            current['capacities'] = []
            current['days'] = []

    # Need to recompute the timespan for actual granularity hour
    granularity = AvailableGranularity.HR
    start_time, end_time = tu.get_start_end_time(data.raw.events)
    start_time = tu.round_start_to_granularity(start_time, granularity)
    t, u, timespan = tu.get_timespan(tu.get_timedelta(granularity, 1), start_time, end_time, granularity)
    capacities = {
        time:
            {department: get_capacity_for_hour(floor(time / HOURS_IN_DAY), context_aware_days, department,
                                               params[department])
             for department in context_aware_days}
        for time in timespan.units[granularity]
    }
    return context_aware_days, {time:
                                    {activity:
                                         {resource: capacities[time][resource][activity] for resource in
                                          capacities[time]}
                                     for activity in capacities[time][list(param.params.keys())[0]]}
                                for time in capacities
                                }


def get_capacity_for_hour(time, context_aware_days, department, param) -> Dict[str, float]:
    if time not in context_aware_days[department]['days']:
        return {activity: param.absolute_capacity_per_activity[activity]
                for activity in param.absolute_capacity_per_activity}
    else:
        return {activity: param.absolute_capacity_per_activity[activity] *
                          context_aware_days[department]['capacities']
                          [context_aware_days[department]['days'].index(time)]
                for activity in param.absolute_capacity_per_activity}
