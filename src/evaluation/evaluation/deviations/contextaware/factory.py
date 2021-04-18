from functools import partial
from typing import Callable, Union, Dict, Any, Set, List
from random import Random

import contect.available.available as av
from contect.context.objects.timeunits.timeunit import TimeSpan
from contect.parsedata.config.param import CsvParseParameters, JsonParseParameters
from contect.parsedata.objects.ocdata import Event, ObjectCentricData
from contect.parsedata.objects.oclog import ObjectCentricLog
from evaluation.deviations.contextaware.versions.classifiers import classify_resource_capacity_util, \
    classify_global_tu_performance, \
    classify_df_performance, classify_schedule


def get_contextaware_classifier(entity: av.AvailableEntities,
                                situation: av.AvailableSituations,
                                selection: av.AvailableSelections,
                                parse_param: Union[CsvParseParameters, JsonParseParameters],
                                perc_pos_attributable: Dict[av.AvailableSituations, float],
                                random: Random,
                                events_split: Dict[av.AvailableGranularity, Dict[int, Dict[str, Event]]],
                                timespan: TimeSpan,
                                timespan_d: TimeSpan,
                                year_adjustment: float,
                                context_aware_days: Dict[str, Dict[str, Any]],
                                granularity: av.AvailableGranularity,
                                excess_log: ObjectCentricLog,
                                weekly_demand: int,
                                weeks: Set[int],
                                weeks_to_events: Dict[int, Dict[str, Event]],
                                data: ObjectCentricData,
                                weekends: Dict[int, Dict[str, Dict[str, Event]]],
                                context_aware_weeks: List[int]):
    if entity is av.AvailableEntities.CAPACITYUTIL and situation is av.AvailableSituations.CAPACITY and \
            selection is av.AvailableSelections.RESOURCE:
        return classify_resource_capacity_util(parse_param.vmap_params[av.AvailableSelections.RESOURCE],
                                               random,
                                               perc_pos_attributable[situation],
                                               events_split,
                                               context_aware_days,
                                               granularity)
    elif entity is av.AvailableEntities.TIMEUNIT and situation is av.AvailableSituations.UNIT_PERFORMANCE and \
            selection is av.AvailableSelections.GLOBAL:
        return classify_global_tu_performance(timespan,
                                              timespan_d,
                                              year_adjustment,
                                              random,
                                              perc_pos_attributable[situation],
                                              events_split,
                                              granularity,
                                              excess_log,
                                              weekly_demand,
                                              weeks,
                                              weeks_to_events,
                                              data,
                                              context_aware_weeks)
    elif entity is av.AvailableEntities.TIMEUNIT and situation is av.AvailableSituations.SCHEDULE and \
            selection is av.AvailableSelections.GLOBAL:
        return classify_schedule(year_adjustment,
                                 random,
                                 events_split,
                                 granularity,
                                 data,
                                 weekends)
    else:
        return classify_df_performance(timespan,
                                       timespan_d,
                                       year_adjustment,
                                       random,
                                       events_split,
                                       granularity)
