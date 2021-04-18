from datetime import timedelta
from typing import Dict

from contect.available.constants import HOURS_IN_MONTH, HOURS_IN_WEEK, SECONDS_IN_HOUR, DAYS_IN_WEEK_DATETIME
from contect.context.objects.context.config.param import HelperParameters
from contect.context.objects.timeunits.timeunit import TimeSpan, round_start_to_granularity
from numpy import mean, median

from contect.available.available import AvailableSelections, AvailableEntities, AvailableNormRanges, \
    AvailableSituations, AvailableGranularity, AvailableAggregators
from contect.context.objects.situations.helpers.additionaldata.additionaldata import AdditionalDataHelper
from contect.context.objects.contextentities.versions.entities import DoubleSelectionEntity, TimeContextEntity
from contect.parsedata.objects.ocdata import MetaObjectCentricData


def extract_double_global(timespan: TimeSpan,
                          param: HelperParameters,
                          data: Dict[int, DoubleSelectionEntity],
                          entity: AvailableEntities,
                          situation: AvailableSituations,
                          selection: AvailableSelections,
                          step_width: int = 0,
                          additional_data: AdditionalDataHelper = None) \
        -> Dict[AvailableAggregators, Dict[str, Dict[str, int]]]:
    if additional_data is not None:
        return {aggregator: additional_data.double_global_additional_data for aggregator in AvailableAggregators}
    else:
        return {aggregator:
                    {selection1:
                         {selection2: get_aggregator(aggregator)([data[time].nested_value[selection1][selection2]
                                                                  for time in data])
                          for selection2 in data[0].nested_value[selection1]}
                     for selection1 in data[0].nested_value}
                for aggregator in AvailableAggregators}


def get_aggregator(variant: AvailableAggregators):
    if variant is AvailableAggregators.MIN:
        return min
    elif variant is AvailableAggregators.MAX:
        return max
    elif variant is AvailableAggregators.MED:
        return median
    else:
        return mean


def extract_single_global(timespan: TimeSpan,
                          param: HelperParameters,
                          data: Dict[int, TimeContextEntity],
                          entity: AvailableEntities,
                          situation: AvailableSituations,
                          selection: AvailableSelections = AvailableSelections.GLOBAL,
                          step_width: int = 0,
                          additional_data: AdditionalDataHelper = None) -> Dict[AvailableAggregators, Dict[str, int]]:
    if additional_data is not None:
        return {aggregator: additional_data.single_global_additional_data for aggregator in AvailableAggregators}
    else:
        return {aggregator:
                    {selection1:
                         get_aggregator(aggregator)([data[time].value[selection1] for time in data])
                     for selection1 in data[0].value
                     }
                for aggregator in AvailableAggregators
                }


def extract_double_granular(timespan: TimeSpan,
                            param: HelperParameters,
                            data: Dict[int, DoubleSelectionEntity],
                            entity: AvailableEntities,
                            situation: AvailableSituations,
                            selection: AvailableSelections,
                            step_width: int,
                            additional_data: AdditionalDataHelper = None) \
        -> Dict[AvailableAggregators, Dict[int, Dict[str, Dict[str, int]]]]:
    if additional_data is not None:
        return {aggregator: additional_data.double_granular_additional_data for aggregator in
                AvailableAggregators}
    else:
        data_len = len(data)
        return {aggregator:
                    {time_bin:
                         {selection1:
                              {selection2:
                                   get_aggregator(aggregator)([data[time].nested_value[selection1][selection2]
                                                               for time in time_of_time_bin_range(data_len,
                                                                                                  step_width,
                                                                                                  time_bin)])
                               for selection2 in data[0].nested_value[selection1]}
                          for selection1 in data[0].nested_value}
                     for time_bin in time_bin_range(data_len, step_width)}
                for aggregator in AvailableAggregators}


def time_bin_range(data_len: int, step_width: int):
    return range(0, data_len, step_width)


def time_of_time_bin_range(data_len: int, step_width: int, time_bin: int):
    return range(time_bin, stop_at_end_of_data(time_bin, step_width, data_len))


def stop_at_end_of_data(time_bin: int, step_width: int, data_len: int) -> int:
    if time_bin + step_width < data_len:
        return time_bin + step_width
    else:
        return data_len


def extract_single_granular(timespan: TimeSpan,
                            param: HelperParameters,
                            data: Dict[int, TimeContextEntity],
                            entity: AvailableEntities,
                            situation: AvailableSituations,
                            selection: AvailableSelections,
                            step_width: int,
                            additional_data: AdditionalDataHelper = None) \
        -> Dict[AvailableAggregators, Dict[int, Dict[str, int]]]:
    if additional_data is not None:
        return {aggregator: additional_data.single_granular_additional_data for aggregator in AvailableAggregators}
    else:
        if situation is not AvailableSituations.SCHEDULE:
            data_len = len(data)
            return {aggregator:
                        {time_bin:
                             {selection1:
                                  get_aggregator(aggregator)([data[time].value[selection1]
                                                              for time in time_of_time_bin_range(data_len,
                                                                                                 step_width,
                                                                                                 time_bin)])
                              for selection1 in data[0].value
                              }
                         for time_bin in time_bin_range(data_len, step_width)}
                    for aggregator in AvailableAggregators}
        else:
            # Need to enlarge the overall timespan by the preceding and trailing hours for a full weekly schedule
            end_hour_shift, start_hour_shift = enlarge_schedule_hours_to_full_weeks(timespan)

            # We can now enlarge the given data by the preceding and trailing hours and insert zero TimeContextEntities
            selection = AvailableSelections.GLOBAL.value  # The global value is used as a dummy for hours of schedules
            enlarged_data = {}
            for time in range(int(- start_hour_shift), int(len(data) + end_hour_shift)):
                if (time in range(int(- start_hour_shift), 0)
                        or time in range(len(data), len(data) + int(end_hour_shift))):
                    enlarged_data[time] = TimeContextEntity(value={selection: 0},
                                                            time=time)
                else:
                    enlarged_data[time] = data[time]

            data_len = len(enlarged_data)
            # If the norm range is a week, this will be a month for schedules
            if step_width < HOURS_IN_MONTH:
                schedule_step_width = HOURS_IN_MONTH
            else:
                schedule_step_width = step_width

            return {aggregator:
                        {time_bin:
                             {hour:  # The schedule is always hours per week
                                  get_aggregator(aggregator)([enlarged_data[week].value[selection]
                                                              # Week iterates through the time_bins hours in
                                                              # in steps of a week, but taking care of not going
                                                              # beyond the end of data
                                                              for week in range(time_bin + hour,
                                                                                stop_at_end_of_data(time_bin,
                                                                                                    HOURS_IN_WEEK,
                                                                                                    data_len),
                                                                                HOURS_IN_WEEK)])
                              for hour in range(HOURS_IN_WEEK)}
                         for time_bin in range(int(- start_hour_shift), data_len, schedule_step_width)}
                    for aggregator in AvailableAggregators}


def enlarge_schedule_hours_to_full_weeks(timespan):
    start_time = round_start_to_granularity(timespan.start, AvailableGranularity.WK)
    start_hour_shift = get_start_hour_shift(start_time, timespan)
    # From a given weekday, we add the missing days and remove the other time parts
    end_time = timespan.end + timedelta(days=(DAYS_IN_WEEK_DATETIME - timespan.end.weekday()))
    end_time = end_time - timedelta(hours=timespan.end.hour,
                                    minutes=timespan.end.minute,
                                    seconds=timespan.end.second)
    end_hour_shift = (end_time - timespan.end).total_seconds() / SECONDS_IN_HOUR
    return end_hour_shift, start_hour_shift


def get_start_hour_shift(start_time, timespan):
    start_hour_shift = (timespan.start - start_time).total_seconds() / SECONDS_IN_HOUR
    return start_hour_shift


def get_associated_meta(selection: AvailableSelections,
                        meta: MetaObjectCentricData):
    if selection is AvailableSelections.ACTIVITY:
        return meta.acts
    elif selection is AvailableSelections.GLOBAL:
        return
    elif selection is AvailableSelections.RESOURCE:
        return meta.ress
    else:
        return
