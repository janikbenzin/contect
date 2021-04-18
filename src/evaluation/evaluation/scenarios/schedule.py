from dataclasses import dataclass, field
from typing import Any
from numpy import arange


@dataclass
class ScheduleParameters:
    unusual_weekends: Any = field(default_factory=lambda: range(0, 11))
    shifted: Any = field(default_factory=lambda: arange(0.05, 0.51, 0.01))
    fr_or_mon: Any = field(default_factory=lambda: range(0, 2))
