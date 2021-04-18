from dataclasses import dataclass, field
from typing import Any
from numpy import arange


@dataclass
class DirectlyParameters:
    excess_days: Any = field(default_factory=lambda: range(5, 31))
    hour_delay: Any = field(default_factory=lambda: arange(2, 8.01, 0.01))
    max_time: int = field(default_factory=lambda: 23)
    alternative_hour: int = field(default_factory=lambda: 22)
    alternative_minute: int = field(default_factory=lambda: 59)



