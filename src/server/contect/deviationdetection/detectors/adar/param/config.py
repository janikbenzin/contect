from dataclasses import dataclass, field
from typing import Dict, Union

from contect.available.available import AvailableADARTypes, AvailableADAREventMiners, AvailableSelections
from contect.parsedata.config.param import CsvParseParameters, JsonParseParameters


@dataclass
class ADARParameters:
    vmap_param: Union[CsvParseParameters, JsonParseParameters]
    mins: Dict[AvailableADAREventMiners, float] = field(default_factory=lambda:
                                                                    {typ: 0.9 for typ in AvailableADAREventMiners})
    # From evaluation of ADAR: Best result + good column, but low computational effort
    rl: Dict[AvailableADAREventMiners, int] = field(default_factory=lambda: {AvailableADARTypes.CONTROL: 3,
                                                                             AvailableADARTypes.RESOURCE: 2})

