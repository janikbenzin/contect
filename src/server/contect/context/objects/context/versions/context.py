from dataclasses import dataclass
from typing import Dict, List

from contect.available.available import AvailableEntities, AvailableSelections, AvailableSituationType, \
    AvailableSituations, AvailableGranularity
from contect.context.objects.context.config.param import ContextParameters
from contect.context.objects.timeunits.timeunit import TimeSpan
from contect.context.objects.contextentities.versions.entities import ContextEntity
from contect.context.objects.situations.versions.situations import Situation
from contect.context.objects.situations.helpers.versions.helpers import Helper


@dataclass
class ContextEntityConfig:
    selected_entities: List[AvailableEntities]
    selections: Dict[AvailableEntities, List[AvailableSelections]]
    entities: Dict[AvailableEntities, Dict[AvailableSelections, Dict[int, ContextEntity]]]


@dataclass
class SituationHelperConfig:
    situation: Situation
    helper: Helper


@dataclass
class SituationConfig:
    selected_situations: Dict[AvailableEntities, List[AvailableSituations]]
    situations: Dict[AvailableEntities, Dict[AvailableSituations, SituationHelperConfig]]
    typing: Dict[AvailableSituationType, List[AvailableSituations]]
    weights: Dict[AvailableSituations, Dict[AvailableSelections, float]]


@dataclass
class Context:
    timespan: TimeSpan
    time_to_time_bin: Dict[AvailableSituations, Dict[int, int]]
    events_timeunits: Dict[AvailableGranularity, Dict[str, int]]
    context: Dict[AvailableGranularity, ContextEntityConfig]
    situation: Dict[AvailableGranularity, SituationConfig]
    params: Dict[int, ContextParameters]
