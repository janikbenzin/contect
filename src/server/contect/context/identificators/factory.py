from functools import partial
from typing import Dict

from contect.context.identificators.versions.identify import identify_capacity, identify_performance, identify_schedule
from contect.available.available import AvailableEntities, AvailableSelections, AvailableSituations
from contect.context.objects.context.config.param import SituationParameters
from contect.context.objects.situations.helpers.versions.helpers import Helper


def get_identifcator(entity: AvailableEntities,
                     situation: AvailableSituations,
                     selection: AvailableSelections,
                     helper: Helper,
                     time_to_time_bin: Dict[int, int],
                     situation_param: SituationParameters):
    if entity is AvailableEntities.CAPACITYUTIL:
        return partial(identify_capacity, selection, helper, time_to_time_bin, situation_param)
    elif situation is AvailableSituations.UNIT_PERFORMANCE or situation is AvailableSituations.WAIT_PERFORMANCE:
        return partial(identify_performance, selection, helper, time_to_time_bin, situation_param)
    elif situation is AvailableSituations.SCHEDULE:
        return partial(identify_schedule, selection, helper, time_to_time_bin, situation_param)
    else:
        return lambda x: 0