from typing import Dict, List

import contect.available.available as av
from contect.available.available import AvailableSituations, AvailableEntities
from contect.context.objects.context.config.param import ContextParameters, SituationParameters, HelperParameters, \
    IdentificatorParameters


def get_required_contextentity(situation: AvailableSituations) -> AvailableEntities:
    if situation is AvailableSituations.CAPACITY:
        return AvailableEntities.CAPACITYUTIL
    elif situation is AvailableSituations.SCHEDULE or situation is AvailableSituations.UNIT_PERFORMANCE:
        return AvailableEntities.TIMEUNIT
    else:
        return AvailableEntities.DIRECTLYFOLLOWS


def get_selections(desired_selections: Dict[av.AvailableSituations, Dict[av.AvailableSelections, float]],
                   get_associated_contextentity=get_required_contextentity):
    selections = {}
    for situation in desired_selections:
        entity = get_associated_contextentity(situation)
        if entity not in selections:
            selections[entity] = [selection
                                  for selection in desired_selections[situation]
                                  if isinstance(selection, av.AvailableSelections)
                                  ]
        else:
            new_selections = set(selections[entity] + [selection
                                                       for selection in desired_selections[situation]
                                                       if isinstance(selection, av.AvailableSelections)]
                                 )
            selections[entity] = list(new_selections)
    return selections


def get_required_situations(entity: AvailableEntities,
                            selected_situations: List[AvailableSituations]) -> List[AvailableSituations]:
    if entity is AvailableEntities.CAPACITYUTIL:
        return [AvailableSituations.CAPACITY]
    elif entity is AvailableEntities.DIRECTLYFOLLOWS:
        return [AvailableSituations.WAIT_PERFORMANCE]
    else:
        return [situation for situation in selected_situations if situation is
                AvailableSituations.SCHEDULE or situation is AvailableSituations.UNIT_PERFORMANCE]


def get_selected_situations(desired_selections, selections, get_associated_situation=get_required_situations):
    return {
        entity: get_associated_situation(entity, list(desired_selections.keys())) for entity in selections
    }


def default_context_parameters(desired_selections) -> ContextParameters:
    selections = get_selections(desired_selections)

    selected_situations = get_selected_situations(desired_selections, selections)
    context_param = ContextParameters()
    context_param.selected_situations = selected_situations
    context_param.selections = selections
    context_param.granularity = av.AvailableGranularity.HR
    context_param.norm_range = av.AvailableNormRanges.BINS
    context_param.situation_param = {
        situation: SituationParameters(
            helper=HelperParameters(
                norm_range=context_param.norm_range,
                granularity=context_param.granularity,
            ),
            identificator=IdentificatorParameters(
                relation=av.AvailablePerfToDevRelationships.PROP
            ),
            typing=av.AvailableSituationType.POSITIVE,
            weights=desired_selections[situation]
        )
        for situation in desired_selections
    }
    context_param.aggregator = av.AvailableAggregators.MAX
    return context_param


def get_required_contextentities(situations: List[AvailableSituations]) -> List[AvailableEntities]:
    return [get_required_contextentity(situation) for situation in situations]