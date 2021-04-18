from dataclasses import dataclass
from typing import Optional, Dict

from contect.available.available import AvailableSelections
from contect.context.objects.contextentities.versions.fixedselections import get_capacities_fixed_first_selection

@dataclass
class _DiscreteEntity:
    value: Optional[Dict[str, int]]


@dataclass
class ContextEntity:
    pass


@dataclass
class _ContextEntity(ContextEntity):
    time: int


@dataclass
class _SelectableContextEntity(ContextEntity):
    selection: AvailableSelections


@dataclass
class _DiscreteNestedEntity(ContextEntity):
    nested_value: Dict[str, Dict[str, int]]


@dataclass
class DoubleSelectionEntity(_DiscreteNestedEntity, _SelectableContextEntity):
    selection2: AvailableSelections


@dataclass
class TimeContextEntity(_ContextEntity, _DiscreteEntity):
    pass


@dataclass
class UnitTimeContextEntity(_SelectableContextEntity, TimeContextEntity):
    pass


@dataclass
class FollowTimeContextEntity(_SelectableContextEntity, TimeContextEntity):
    pass


@dataclass
class DirectlyTimeContextEntity(FollowTimeContextEntity):
    pass


@dataclass
class SystemContextEntity(_ContextEntity, _DiscreteEntity):
    pass


@dataclass
class CapacitySystemContextEntity(DoubleSelectionEntity, SystemContextEntity):
    selection2: AvailableSelections = get_capacities_fixed_first_selection()


