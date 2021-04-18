from typing import List
from dataclasses import dataclass, field


@dataclass
class AlignmentsParameters:
    thresholds: List[float] = field(default_factory=
                                    lambda: [t for t in map(lambda i: i / 100, range(0, 11))] +
                                    [0.15, 0.20, 0.25, 0.30])

