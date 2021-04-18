from dataclasses import dataclass
from typing import Dict, Optional

from contect.available.available import AvailableSelections, AvailableEntities, AvailableSituations


# Create proper class diagram for these
@dataclass
class TimedSituation:
    time: int


@dataclass
class _FunctionalSituation:
    value: Optional[Dict[str, float]]


@dataclass
class FunctionalSituation(TimedSituation, _FunctionalSituation):
    pass


@dataclass
class SelectableSituation:
    selection: AvailableSelections


@dataclass
class SelectableFunctionalSituation(SelectableSituation, FunctionalSituation):
    pass


@dataclass
class DoubleSelectionFunctionalSituation(SelectableSituation, FunctionalSituation):
    nested_value: Dict[str, Dict[str, float]]
    selection2: AvailableSelections


@dataclass
class Situation:
    situations: Dict[AvailableSelections, Dict[int, FunctionalSituation]]
    associated_ce: AvailableEntities
    associated_sit: AvailableSituations

