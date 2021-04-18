from dataclasses import dataclass, field
from typing import Dict, List, Union, Optional

from contect.available.available import AvailableProfiles


@dataclass
class DependencyProfileParameters:
    min_conf: float = field(default_factory=lambda: 0.7)
    min_supp: float = field(default_factory=lambda: 0.1)


@dataclass
class ProfilesParameters:
    deviating_perc: float
    init_initial_norm: Union[int, List[int]] = field(default_factory=lambda: 1)
    log_size: Optional[int] = field(default_factory=lambda: None)
    sample_size: Optional[int] = field(default_factory=lambda: None)
    n_deviating: Optional[int] = field(default_factory=lambda: None)
    initial_norm: Dict[int, float] = field(init=False)
    profiles_param: Dict[AvailableProfiles, Union[DependencyProfileParameters]] = field(default_factory=lambda: {
        AvailableProfiles.DF: DependencyProfileParameters()
    })
    normal_adj: float = field(default_factory=lambda: 0.9)
    deviating_adj: float = field(default_factory=lambda: 1.1)
    loop_threshold: int = field(default_factory=lambda: 20)
    threshold: Optional[float] = field(default_factory=lambda: None)
    weights: Dict[AvailableProfiles, float] = field(default_factory=
                                                    lambda: {prof: 1 for prof in AvailableProfiles})

