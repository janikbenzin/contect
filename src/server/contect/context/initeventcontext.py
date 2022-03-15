from typing import Dict, List, Union, Callable
from functools import partial

from contect.available.constants import SITUATION_KEY, ANTI_KEY, ENTITY_KEY, MAX_KEY, MIN_KEY, AVG_KEY, MED_KEY
from contect.available.available import AvailableEntities, AvailableSituations, AvailableSelections, \
    AvailableAggregators, AvailableSituationType
from contect.context.objects.context.config.param import SituationParameters
from contect.context.objects.contextentities.versions.entities import ContextEntity
from contect.parsedata.config.param import CsvParseParameters, JsonParseParameters
from contect.parsedata.objects.ocdata import Event, ObjectCentricData, Obj
from contect.context.objects.context.versions.context import SituationHelperConfig, Context
from contect.context.objects.situations.versions.situations import Situation, DoubleSelectionFunctionalSituation
from contect.context.objects.situations.helpers.versions.extract import get_aggregator
from contect.parsedata.objects.oclog import ObjectCentricLog


# if run locally, the data and log both point to the same events, so this function does only work with deeply copied
# data that has the initialized contexts for events
def init_log_events_context(data: ObjectCentricData,
                            log: ObjectCentricLog,
                            aggregator: AvailableAggregators,
                            current_param: int,
                            local: bool = False,
                            backend: bool = True,
                            detector=None) -> None:
    # local == True means that data and log both point to the same events
    if not backend:
        for tid in log.traces:
            if not local:
                for event in log.traces[tid].events:
                    event.complex_context[detector] = data.raw.events[event.id].complex_context[detector]
                    event.rich_context[detector] = data.raw.events[event.id].rich_context[detector]
            log.traces[tid].complex_context[detector] = {
                typ:
                    get_aggregator(aggregator)([event.complex_context[detector][typ]
                                                for event in log.traces[tid].events])
                for typ in AvailableSituationType}
            log.traces[tid].rich_context[detector] = {
                typ:
                    {sit:
                        {selection:
                            {SITUATION_KEY: get_aggregator(aggregator)(
                                [event.rich_context[detector][typ][sit][selection][SITUATION_KEY]
                                 for event in log.traces[tid].events]),
                                ANTI_KEY: log.traces[tid].events[0].rich_context[detector][typ][sit][selection][
                                    ANTI_KEY]}
                            for selection in log.traces[tid].events[0].rich_context[detector][typ][sit]}
                        for sit in log.traces[tid].events[0].rich_context[detector][typ]}
                for typ in AvailableSituationType}
    else:
        for tid in log.traces:
            if not local:
                for event in log.traces[tid].events:
                    if current_param == 0:
                        event.context = {0: {}}
                    event.context[current_param] = data.raw.events[event.id].context[current_param]
            if current_param == 0:
                log.traces[tid].context = {0: {
                    typ: get_aggregator(aggregator)(
                        [event.context[current_param][typ] for event in log.traces[tid].events])
                    for typ in AvailableSituationType}
                }
            else:
                log.traces[tid].context[current_param] = {
                    typ: get_aggregator(aggregator)([event.context[0][typ] for event in log.traces[tid].events])
                    for typ in AvailableSituationType
                }


def init_events_context(data: ObjectCentricData,
                        context: Context,
                        current_param: int,
                        include_entity=lambda x: True,
                        include_sit=lambda x: True,
                        include_sel=lambda x: True,
                        include_sit_sel=lambda sit, sel: True,
                        backend=True,
                        anti=None,
                        weight=lambda sit, sel: None,
                        detector=None) -> None:
    context_param = context.params[current_param]
    granularity = context_param.granularity
    entities = context.context[granularity].entities
    aggregator = context_param.aggregator
    events_timeunit = context.events_timeunits[granularity]
    vmap_param = data.vmap_param
    objects = data.raw.objects
    selections = context_param.selections
    situation_param = context_param.situation_param
    situations = context.situation[granularity].situations
    events = data.raw.events
    for eid in events:
        init_event_context(event=events[eid],
                           events_timeunit=events_timeunit,
                           aggregator=aggregator,
                           vmap_param=vmap_param,
                           selections=selections,
                           current_param=current_param,
                           situations=situations,
                           situation_param=situation_param,
                           objects=objects,
                           include_entity=include_entity,
                           include_sit=include_sit,
                           include_sel=include_sel,
                           include_sit_sel=include_sit_sel,
                           backend=backend,
                           anti=anti,
                           weight=weight,
                           detector=detector,
                           entities=entities)


def init_event_context(event: Event,
                       events_timeunit: Dict[str, int],
                       aggregator: AvailableAggregators,
                       vmap_param: Union[CsvParseParameters, JsonParseParameters],
                       selections: Dict[AvailableEntities, List[AvailableSelections]],
                       current_param: int,  # relates to the key in the params dict of the global context
                       situations: Dict[AvailableEntities,
                                        Dict[AvailableSituations, SituationHelperConfig]],
                       situation_param: Dict[AvailableSituations, SituationParameters],
                       objects: Dict[str, Obj],
                       entities: Dict[AvailableEntities, Dict[AvailableSelections, Dict[int, ContextEntity]]],
                       include_entity=lambda x: True,
                       include_sit=lambda x: True,
                       include_sel=lambda x: True,
                       include_sit_sel=lambda sit, sel: True,
                       backend=True,
                       anti=None,
                       weight=lambda sit, sel: None,
                       detector=None) -> None:
    timeunit = events_timeunit[event.id]
    vmap_params = vmap_param.vmap_params
    weighted_situations = {entity:
                               {situation:
                                    sum([extract_associated_context_values(event=event,
                                                                           situation=situations[entity][
                                                                               situation].situation,
                                                                           timeunit=timeunit,
                                                                           aggregator=aggregator,
                                                                           selection=selection,
                                                                           vmap_params=vmap_params,
                                                                           objects=objects,
                                                                           anti=(lambda x: x) if anti is None else
                                                                           (lambda x: 1 - x) if check_anti(anti,
                                                                                                           situation,
                                                                                                           entity,
                                                                                                           selection)
                                                                           else (lambda x: x),
                                                                           weight=situation_param[situation].weights[
                                                                               selection]
                                                                           if weight(situation, selection) is None
                                                                           else weight(situation, selection))
                                         for selection in situation_param[situation].weights
                                         if include_sel(selection) and include_sit_sel(situation, selection)])
                                for situation in situations[entity] if include_sit(situation)}
                           for entity in situations if include_entity(entity)}
    summer = partial(sum_weighted_situations_per_type, weighted_situations, situation_param)
    weighted_sums = {typ: summer(typ) for typ in AvailableSituationType}
    summer = partial(sum_weights_per_type, weighted_situations, situation_param)
    weight_sums = {typ: summer(typ) for typ in AvailableSituationType}
    if not backend:
        # For the Frontend we like to keep detailed information on context values for transparency wrt the user
        # Moreover, the Frontend allows for parallel computation of multiple detectors, which are kept separate
        weight_sums = {AvailableSituationType.POSITIVE: sum_weights_per_type(weighted_situations, situation_param, AvailableSituationType.POSITIVE, include_sel, include_sit_sel),
                       AvailableSituationType.NEGATIVE: sum_weights_per_type(weighted_situations, situation_param, AvailableSituationType.NEGATIVE, include_sel, include_sit_sel)}
        event.complex_context[detector] = get_weighted_sums_dict(weight_sums, weighted_sums)
        weighted_situations_wo_entity = {}
        for entity in weighted_situations:
            weighted_situations_wo_entity = {**weighted_situations_wo_entity,
                                             **{(entity, situation):
                                                    weighted_situations[entity][situation]
                                                for situation in weighted_situations[entity]}}
        event.rich_context[detector] = {typ:
            {situation:
                {selection:
                    {SITUATION_KEY:
                        extract_associated_context_values(
                            event=event,
                            situation=situations[entity][
                                situation].situation,
                            timeunit=timeunit,
                            aggregator=aggregator,
                            selection=selection,
                            vmap_params=vmap_params,
                            objects=objects,
                            anti=(lambda x: x) if anti is None else
                            (lambda x: 1 - x) if check_anti(anti,
                                                            situation,
                                                            entity,
                                                            selection)
                            else (lambda x: x),
                            weight=situation_param[situation].weights[selection]
                            if weight(situation, selection) is None
                            else weight(situation, selection)),
                        ANTI_KEY: check_anti(anti, situation, entity, selection),
                        ENTITY_KEY: entities[entity][selection][timeunit]
                    }
                    for selection in selections[entity] if include_sel(selection)
                                                        and include_sit_sel(situation, selection)
                }
                for entity, situation in weighted_situations_wo_entity
                if situation_param[situation].typing is typ}
            for typ in AvailableSituationType
        }
    else:
        if event.context is None:
            event.context = {0: get_weighted_sums_dict(weight_sums, weighted_sums)}
        else:
            event.context[current_param] = get_weighted_sums_dict(weight_sums, weighted_sums)


def check_anti(anti, situation, entity, selection):
    if situation not in anti:
        return False
    if entity not in anti[situation]:
        return False
    if selection not in anti[situation][entity]:
        return False
    return anti[situation][entity][selection]


def get_weighted_sums_dict(weight_sums, weighted_sums):
    return {typ: weighted_sums[typ] / weight_sums[typ] if weight_sums[typ] != 0 else 0
            for typ in AvailableSituationType}


def sum_weighted_situations_per_type(weighted_situations: Dict[AvailableEntities,
                                                               Dict[AvailableSituations, float]],
                                     situation_param: Dict[AvailableSituations, SituationParameters],
                                     typ: AvailableSituationType) -> float:
    return sum(weighted_situations[entity][situation] for entity, situation_dict in weighted_situations.items()
               for situation in situation_dict.keys() if situation_param[situation].typing is typ)


def sum_weights_per_type(weighted_situations: Dict[AvailableEntities,
                                                   Dict[AvailableSituations, float]],
                         situation_param: Dict[AvailableSituations, SituationParameters],
                         typ: AvailableSituationType,
                         include_sel=lambda x: True,
                         include_sit_sel=lambda sit, sel: True) -> float:
    return sum(weight for entity, situation_dict in weighted_situations.items()
               for situation in situation_dict.keys()
               for selection, weight in situation_param[situation].weights.items() if
               situation_param[situation].typing is typ and
               include_sel(selection) and include_sit_sel(situation, selection))


def extract_associated_context_values(event: Event,
                                      situation: Situation,
                                      timeunit: int,
                                      aggregator: AvailableAggregators,
                                      selection: AvailableSelections,
                                      vmap_params: Dict[AvailableSelections, str],
                                      objects: Dict[str, Obj],
                                      anti: Callable,
                                      weight: float,
                                      ) -> float:
    if isinstance(situation.situations[selection][timeunit], DoubleSelectionFunctionalSituation):
        return weight * anti(situation.situations[selection][timeunit].nested_value[event.act][
                                 get_associated_attribute(selection,
                                                          vmap_params,
                                                          event)])
    elif selection is not AvailableSelections.OBJECTTYPE:
        return weight * anti(situation.situations[selection][timeunit].value[get_associated_attribute(selection,
                                                                                                      vmap_params,
                                                                                                      event)])
    else:
        return weight * anti(get_aggregator(aggregator)([situation.situations[selection][timeunit].value[ot]
                                                         for ot in {objects[objid].type for objid in
                                                                    get_associated_attribute(selection, vmap_params,
                                                                                             event)}]))


def get_associated_attribute(selection: AvailableSelections,
                             vmap_params: Dict[AvailableSelections, str],
                             event: Event):
    if selection is AvailableSelections.ACTIVITY:
        return event.act
    elif selection is AvailableSelections.GLOBAL:
        return AvailableSelections.GLOBAL.value
    elif selection is AvailableSelections.RESOURCE or selection is AvailableSelections.LOCATION:
        return event.vmap[vmap_params[selection]]
    else:
        return event.omap
