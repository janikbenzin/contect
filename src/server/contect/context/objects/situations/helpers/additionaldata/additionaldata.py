from dataclasses import dataclass, field
from typing import Dict, Optional

import contect.available.available as av


@dataclass
class AdditionalDataHelper:
    single_granular_additional_data: Optional[Dict[int, Dict[str, float]]] = field(default_factory=lambda: None)
    double_granular_additional_data: Optional[Dict[int, Dict[str,
                                                             Dict[str, float]]]] = field(default_factory=lambda: None)
    single_global_additional_data: Optional[Dict[str, float]] = field(default_factory=lambda: None)
    double_global_additional_data: Optional[Dict[str, Dict[str, float]]] = field(default_factory=lambda: None)


@dataclass
class AdditionalDataSituation:
    add_data_helpers: Dict[av.AvailableSelections, AdditionalDataHelper]


@dataclass
class AdditionalDataContainer:
    add_data_of_situations: Dict[av.AvailableSituations, AdditionalDataSituation]
