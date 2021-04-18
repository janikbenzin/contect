from dataclasses import dataclass, field
from typing import List, Any
import random
from itertools import count

from contect.available.available import AvailableGranularity
from contect.context.objects.timeunits.timeunit import get_timedelta

counter = count()


@dataclass
class AddParameters:
    change_range: List = field(default_factory=lambda: list(range(-3, 4)))
    granularity: AvailableGranularity = field(default_factory=lambda: AvailableGranularity.DAY)
    index: int = field(default_factory=lambda: next(counter))
    timedelta: Any = field(init=False)
    key: str = field(init=False)

    def __post_init__(self):
        self.timedelta = get_timedelta(self.granularity, random.sample(self.change_range, 1)[0])
        self.key = 'ADDED' + str(self.index)
