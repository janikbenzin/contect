from dataclasses import dataclass, field
from typing import List, Union, Optional

from contect.deviationdetection.detectors.adar.conditiontypes.versions.types import ConditionControlFlow


@dataclass
class ADARResult:
    tid: int
    rule: List[Union[ConditionControlFlow]]
    violating_eid: str
    violating_trace_pos: int  # -1 -> the THEN part is missing in the trace
    sim_violating: Optional[bool] = field(default_factory=lambda: None)
    # True -> also the similar trace violates this rule
