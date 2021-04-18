from __future__ import division
from typing import Dict, Union

from contect.available.available import AvailableSelections, AvailableNormRanges, AvailablePerfToDevRelationships
from contect.available.constants import HOURS_IN_WEEK
from contect.context.objects.context.config.param import SituationParameters
from contect.context.objects.situations.helpers.versions.helpers import Helper, DoubleGranularHelper, \
    DoubleGlobalHelper, SingleGlobalHelper, SingleGranularHelper
from contect.context.objects.contextentities.versions.entities import CapacitySystemContextEntity, \
    UnitTimeContextEntity, TimeContextEntity, DirectlyTimeContextEntity


def identify_capacity(selection: AvailableSelections,
                      helper: Helper,
                      time_to_time_bin: Dict[int, int],
                      situation_param: SituationParameters,
                      entity: CapacitySystemContextEntity,
                      time: int) -> Dict[str, Dict[str, float]]:
    norm_range = situation_param.helper.norm_range
    selected_helper = helper.helpers[selection]
    try:
        if norm_range is AvailableNormRanges.GLOBAL:
            return identify_capacity_global(selected_helper, entity)
        else:
            return identify_capacity_granular(selected_helper, time_to_time_bin, entity, time)
    except AttributeError:
        test = 0


def identify_capacity_granular(selected_helper: DoubleGranularHelper,
                               time_to_time_bin: Dict[int, int],
                               entity: CapacitySystemContextEntity,
                               time: int) -> Dict[str, Dict[str, float]]:
    # For the case of no additional data and norm range is of type bins, then the time key does not match the
    # keys of the selected_helper, but the time_to_time_bin contains the correct key for the selected helper
    # for that time
    if time_to_time_bin != {}:
        time = time_to_time_bin[time]
    return {selection1:
                {selection2:
                     min(1.0,
                         entity.nested_value[selection1][selection2] / selected_helper.maxs[time][selection1][
                             selection2])
                     if selected_helper.maxs[time][selection1][selection2] != 0 else 0
                     if entity.nested_value[selection1][selection2] == 0 else 1
                 for selection2 in entity.nested_value[selection1]}
            for selection1 in entity.nested_value
            }


def identify_capacity_global(selected_helper: DoubleGlobalHelper,
                             entity: CapacitySystemContextEntity) -> Dict[str, Dict[str, float]]:
    return {selection1:
                {selection2:
                     entity.nested_value[selection1][selection2] / selected_helper.maxs[selection1][selection2]
                     if selected_helper.maxs[selection1][selection2] != 0 else 0
                     if entity.nested_value[selection1][selection2] == 0 else 1
                 for selection2 in entity.nested_value[selection1]}
            for selection1 in entity.nested_value
            }


def identify_performance(selection: AvailableSelections,
                         helper: Helper,
                         time_to_time_bin: Dict[int, int],
                         situation_param: SituationParameters,
                         entity: Union[TimeContextEntity, DirectlyTimeContextEntity],
                         time: int) -> Dict[str, float]:
    norm_range = situation_param.helper.norm_range
    selected_helper = helper.helpers[selection]
    if norm_range is AvailableNormRanges.GLOBAL:
        return identify_performance_global(selected_helper, entity)
    else:
        return identify_performance_granular(selected_helper, time_to_time_bin, entity, time)


def identify_performance_global(selected_helper: SingleGlobalHelper,
                                entity: Union[TimeContextEntity, DirectlyTimeContextEntity]) -> Dict[str, float]:
    return {selection1:
                entity.value[selection1] / selected_helper.maxs[selection1]
                if selected_helper.maxs[selection1] != 0 else 0
                if entity.value[selection1] == 0 else 1
            for selection1 in entity.value}


def identify_performance_granular(selected_helper: SingleGranularHelper,
                                  time_to_time_bin: Dict[int, int],
                                  entity: Union[TimeContextEntity, DirectlyTimeContextEntity],
                                  time: int) -> Dict[str, float]:
    if time_to_time_bin != {}:
        time = time_to_time_bin[time]
    return {selection1:
                min(1.0, entity.value[selection1] / selected_helper.maxs[time][selection1])
                if selected_helper.maxs[time][selection1] != 0 else 0
                if entity.value[selection1] == 0 else 1
            for selection1 in entity.value}


def identify_schedule(selection: AvailableSelections,
                      helper: Helper,
                      time_to_time_bin: Dict[int, int],
                      situation_param: SituationParameters,
                      entity: UnitTimeContextEntity,
                      time: int) -> Dict[AvailableSelections, Dict[AvailableSelections, float]]:
    # Since schedules are limited to hours in the week and only a month or a year for k-tail, which is configured
    # by the frontend, the norm range is not affecting the identificator
    selected_helper = helper.helpers[selection]
    # The selected helper aggregates are keyed by hour of week,
    # so we need to transform the time (in hour) to the hour in week
    hour = (time - next(iter(time_to_time_bin))) % HOURS_IN_WEEK
    time_bin = time_to_time_bin[time]  # Extract the time bin of the time
    if time_bin not in selected_helper.medians:
        median = selected_helper.medians[AvailableSelections.GLOBAL.value]
        maximum = selected_helper.maxs[AvailableSelections.GLOBAL.value]
    else:
        median = selected_helper.medians[time_bin][hour]
        maximum = selected_helper.maxs[time_bin][hour]
    return {selection1:
                max(0, entity.value[selection1] - median)
                 / (maximum - median) if maximum - median != 0 else 0
            for selection1 in entity.value}


