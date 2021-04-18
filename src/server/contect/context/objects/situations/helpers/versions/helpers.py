from dataclasses import dataclass, InitVar, field
from typing import Dict, List, Tuple, Optional

from contect.available.available import AvailableSelections, AvailableGranularity, AvailableEntities, \
    AvailableSituations, AvailableAggregators


@dataclass
class FunctionalHelper:
    pass


@dataclass
class DiscreteHelper(FunctionalHelper):
    pass


@dataclass
class MinMaxHelper(DiscreteHelper):
    pass


@dataclass
class SelectableHelper(FunctionalHelper):
    selection: AvailableSelections


@dataclass
class SingleSelectionHelper(SelectableHelper):
    pass


@dataclass
class DoubleSelectionHelper(SelectableHelper):
    selection2: AvailableSelections


@dataclass
class SingleGlobalHelper(MinMaxHelper, SingleSelectionHelper):
    mins: Dict[str, int] = field(init=False)
    maxs: Dict[str, int] = field(init=False)
    medians: Dict[str, int] = field(init=False)
    averages: Dict[str, int] = field(init=False)
    aggregator: InitVar[Dict[AvailableAggregators, Dict[str, int]]]

    def __post_init__(self, aggregator):
        self.mins = aggregator[AvailableAggregators.MIN]
        self.maxs = aggregator[AvailableAggregators.MAX]
        self.medians = aggregator[AvailableAggregators.MED]
        self.averages = aggregator[AvailableAggregators.AVG]


@dataclass
class DoubleGlobalHelper(MinMaxHelper, DoubleSelectionHelper):
    mins: Dict[str, Dict[str, int]] = field(init=False)
    maxs: Dict[str, Dict[str, int]] = field(init=False)
    medians: Dict[str, Dict[str, int]] = field(init=False)
    averages: Dict[str, Dict[str, int]] = field(init=False)
    aggregator: InitVar[Dict[AvailableAggregators, Dict[str, Dict[str, int]]]]

    def __post_init__(self, aggregator):
        self.mins = aggregator[AvailableAggregators.MIN]
        self.maxs = aggregator[AvailableAggregators.MAX]
        self.medians = aggregator[AvailableAggregators.MED]
        self.averages = aggregator[AvailableAggregators.AVG]


@dataclass
class DoubleGranularHelper(MinMaxHelper, DoubleSelectionHelper):
    mins: Dict[int, Dict[str, Dict[str, int]]] = field(init=False)
    maxs: Dict[int, Dict[str, Dict[str, int]]] = field(init=False)
    medians: Dict[int, Dict[str, Dict[str, int]]] = field(init=False)
    averages: Dict[int, Dict[str, Dict[str, int]]] = field(init=False)
    granularity: AvailableGranularity
    aggregator: InitVar[Dict[AvailableAggregators, Dict[int, Dict[str, Dict[str, int]]]]]

    def __post_init__(self, aggregator):
        self.mins = aggregator[AvailableAggregators.MIN]
        self.maxs = aggregator[AvailableAggregators.MAX]
        self.medians = aggregator[AvailableAggregators.MED]
        self.averages = aggregator[AvailableAggregators.AVG]


@dataclass
class SingleGranularHelper(MinMaxHelper, SingleSelectionHelper):
    mins: Dict[int, Dict[str, int]] = field(init=False)
    maxs: Dict[int, Dict[str, int]] = field(init=False)
    medians: Dict[int, Dict[str, int]] = field(init=False)
    averages: Dict[int, Dict[str, int]] = field(init=False)
    granularity: AvailableGranularity
    aggregator: InitVar[Dict[AvailableAggregators, Dict[int, Dict[str, int]]]]
    start_hour_shift: Optional[int] = field(default_factory=lambda: None)
    end_hour_shift: Optional[int] = field(default_factory=lambda: None)

    def __post_init__(self, aggregator):
        self.mins = aggregator[AvailableAggregators.MIN]
        self.maxs = aggregator[AvailableAggregators.MAX]
        self.medians = aggregator[AvailableAggregators.MED]
        self.averages = aggregator[AvailableAggregators.AVG]




@dataclass
class Helper:
    helpers: Dict[AvailableSelections, FunctionalHelper]
    associated_ce: AvailableEntities
    associated_sit: AvailableSituations
