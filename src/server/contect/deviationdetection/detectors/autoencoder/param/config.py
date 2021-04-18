from dataclasses import dataclass, field, InitVar
from typing import List, Dict

from contect.available.available import AvailableSelections
from contect.parsedata.objects.oclog import Trace
from tensorflow.keras.optimizers import Adam


@dataclass
class AutoencParameters:
    deviating_perc: float
    acts: List[str]
    ress: List[str]
    max_trace_len: int = field(init=False)
    vmap_params: Dict[AvailableSelections, str]
    traces: InitVar[Dict[int, Trace]]
    test_size: int = field(default_factory=lambda: 0.2)
    batch_size: int = field(default_factory=lambda: 50)
    epochs: int = field(default_factory=lambda: 200)
    optimizer: Adam = field(default_factory=lambda: Adam(beta_1=0.9,
                                                         beta_2=0.99,
                                                         epsilon=10**-8,
                                                         learning_rate=0.001))
    dropout: float = field(default_factory=lambda: 0.5)
    noise: float = field(default_factory=lambda: 0.1)
    loss: str = field(default_factory=lambda: 'mae')
    hidden: float = field(default_factory=lambda: 0.5)

    def __post_init__(self, traces):
        self.max_trace_len = len(max(traces.items(), key=lambda item: len(item[1].events))[1].events)
