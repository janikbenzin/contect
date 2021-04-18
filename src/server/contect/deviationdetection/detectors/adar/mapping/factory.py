from functools import partial
from typing import Callable, Dict

from contect.available.available import AvailableADAREventMiners, AvailableSelections
from contect.deviationdetection.detectors.adar.objects.adar import ADAR
from contect.deviationdetection.detectors.adar.mapping.versions.matchers import match_control_condition_support, \
    match_resource_condition_support, match_control_condition_rule, match_resource_condition_rule


def get_matcher(perspective: AvailableADAREventMiners,
                rule: ADAR,
                vmap_params: Dict[AvailableSelections, str],
                variant: bool) -> Callable:
    # The variant determines whether we match support for the item set, or we match the rule with IF and THEN parts
    if variant:
        # Item sets
        if perspective is AvailableADAREventMiners.CONTROL:
            return partial(match_control_condition_support, rule)
        elif perspective is AvailableADAREventMiners.RESOURCE_BOD:
            return partial(match_resource_condition_support, rule, True, vmap_params)
        elif perspective is AvailableADAREventMiners.RESOURCE_SOD:
            return partial(match_resource_condition_support, rule, False, vmap_params)
    else:
        # IF THEN rule
        if perspective is AvailableADAREventMiners.CONTROL:
            return partial(match_control_condition_rule, rule)
        else:
            return partial(match_resource_condition_rule, rule, perspective, vmap_params)



