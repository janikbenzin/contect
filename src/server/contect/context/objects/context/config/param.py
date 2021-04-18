from typing import Dict, List, Optional
from dataclasses import dataclass, field

import contect.available.available as av


@dataclass
class HelperParameters:
    norm_range: av.AvailableNormRanges
    granularity: av.AvailableGranularity


@dataclass
class IdentificatorParameters:
    relation: av.AvailablePerfToDevRelationships = field(default_factory=lambda: av.AvailablePerfToDevRelationships.PROP)


@dataclass
class SituationParameters:
    helper: HelperParameters  # they will all be the same in the first version of the framework
    identificator: IdentificatorParameters  # they will all be the same in the first version of the framework
    typing: av.AvailableSituationType
    weights: Dict[av.AvailableSelections, float]


class ContextParameters:
    # explicit
    selected_situations: Dict[av.AvailableEntities, List[av.AvailableSituations]]
    selections: Dict[av.AvailableEntities, List[av.AvailableSelections]]
    granularity: av.AvailableGranularity
    norm_range: av.AvailableNormRanges
    situation_param: Dict[av.AvailableSituations, SituationParameters]
    aggregator: av.AvailableAggregators
    past_granularities: Optional[List[av.AvailableGranularity]] = field(default_factory=lambda: None)
