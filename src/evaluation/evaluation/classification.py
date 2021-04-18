from random import Random
from typing import List, Dict, Union, Any, Set

from contect.available.available import AvailableDeviationTypes, AvailableClassifications, AvailableClassificationValues
from contect.context.objects.timeunits.timeunit import assign_events_to_unit, get_timedelta, TimeSpan
from contect.parsedata.config.param import CsvParseParameters, JsonParseParameters
from contect.parsedata.objects.ocdata import sort_events, ObjectCentricData, Event
from contect.parsedata.objects.oclog import Trace, ObjectCentricLog
from evaluation.deviations.contextunaware.factory import get_deviation_injector
from evaluation.objects.param.config import EvaluationExperiment
from evaluation.deviations.contextaware.factory import get_contextaware_classifier


def add_deviations(eval_param: EvaluationExperiment,
                   random: Random) -> None:
    data = eval_param.dataset
    start = eval_param.timespan.start
    end = eval_param.timespan.end
    deviation_types = eval_param.deviation_types
    perc_deviating = eval_param.perc_deviating
    n_deviation_types = len(deviation_types)
    # Generate random event ids that will be deviating
    if AvailableDeviationTypes.REPL in deviation_types:
        needed_percentage = perc_deviating * (n_deviation_types + 1) / n_deviation_types
        denominator = n_deviation_types + 1
    else:
        needed_percentage = perc_deviating
        denominator = n_deviation_types
    deviation_ids = random.sample(list(data.raw.events.keys()),
                                  int(float(len(data.raw.events)) * needed_percentage))
    chunk_size = int(len(deviation_ids) / denominator)
    gen_ids = chunks(deviation_ids, chunk_size)
    # Inject the deviation for generated eids
    for typ in eval_param.deviation_types:
        if typ is AvailableDeviationTypes.REPL:
            ids = list(zip(next(gen_ids), next(gen_ids)))
        else:
            ids = next(gen_ids)
        [get_deviation_injector(typ, data, start, end)(eid) for eid in ids]


def classify_context_aware_events(eval_param: EvaluationExperiment,
                                  parse_param: Union[CsvParseParameters, JsonParseParameters],
                                  context_aware_days: Dict[str, Dict[str, Any]],
                                  random: Random,
                                  timespan_d: TimeSpan,
                                  year_adjustment: float,
                                  excess_log: ObjectCentricLog,
                                  weekly_demand: int,
                                  weeks: Set[int],
                                  weeks_to_events: Dict[int, Dict[str, Event]],
                                  data: ObjectCentricData,
                                  weekends: Dict[int, Dict[str, Dict[str, Event]]],
                                  context_aware_weeks: List[int]) -> None:
    combinations = eval_param.situation_combinations
    sort_events(eval_param.dataset)
    granularity = eval_param.granularity
    units = eval_param.timespan.units[granularity]
    events_timeunit, events_split = assign_events_to_unit(add_timedelta=get_timedelta(granularity, 1),
                                                          events=eval_param.dataset.raw.events,
                                                          time_units=eval_param.timespan.units,
                                                          granularity=granularity,
                                                          start_time=units[0].start,
                                                          time_unit=list(units.keys())[-2],
                                                          sort=True)
    [get_contextaware_classifier(entity=combination.entity,
                                 situation=combination.situation,
                                 selection=combination.selection,
                                 parse_param=parse_param,
                                 perc_pos_attributable=eval_param.perc_pos_attributable,
                                 random=random,
                                 events_split=events_split,
                                 timespan=eval_param.timespan,
                                 timespan_d=timespan_d,
                                 year_adjustment=year_adjustment,
                                 context_aware_days=context_aware_days,
                                 granularity=eval_param.granularity,
                                 excess_log=excess_log,
                                 weekly_demand=weekly_demand,
                                 weeks=weeks,
                                 weeks_to_events=weeks_to_events,
                                 data=data,
                                 weekends=weekends,
                                 context_aware_weeks=context_aware_weeks)
        for combination in combinations]


# https://stackoverflow.com/questions/312443/how-do-you-split-a-list-into-evenly-sized-chunks
def chunks(lst: List, n: int) -> List:
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        if i + n >= len(lst) - n:
            yield lst[i:len(lst)]  # the last chunk gets the remaining elements
        else:
            yield lst[i:i + n]


def is_ca_deviating(trace: Trace) -> bool:
    return any([event.vmap[AvailableClassifications.CAD.value] == AvailableClassificationValues.TRUE.value for event in
                trace.events])


def is_deviating(trace: Trace) -> bool:
    if is_ca_normal(trace) or is_ca_deviating(trace):
        return False
    else:
        return any(
            [event.vmap[AvailableClassifications.D.value] == AvailableClassificationValues.TRUE.value for event in
             trace.events])


def is_normal(trace: Trace) -> bool:
    if is_ca_deviating(trace) or is_ca_normal(trace) or is_deviating(trace):
        return False
    else:
        return True


def is_ca_normal(trace: Trace) -> bool:
    if is_ca_deviating(trace):
        return False
    else:
        return any(
            [event.vmap[AvailableClassifications.CAN.value] == AvailableClassificationValues.TRUE.value for event in
             trace.events])
