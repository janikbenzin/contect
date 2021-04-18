from dataclasses import dataclass, field
from typing import Dict, List, Union

from contect.available.available import AvailableADARTypes, AvailableADAREventMiners
from contect.deviationdetection.detectors.adar.conditiontypes.versions.types import ConditionControlFlow


@dataclass
class ADAR:
    tid: Union[int, List[int]] = field(compare=False)
    conditions: Dict[AvailableADARTypes, List[Union[ConditionControlFlow]]]
    rule_types: List[AvailableADAREventMiners]  # Contains verified rule types for the conditions
    supports: Dict[AvailableADAREventMiners, float] = field(default_factory=lambda: {}, compare=False)
