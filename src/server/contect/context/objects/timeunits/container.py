from dataclasses import dataclass
from typing import Dict

from contect.parsedata.objects.ocdata import MetaObjectCentricData, Event, Obj
from contect.available.available import AvailableGranularity


@dataclass
class ContainerSplitObjectCentricData:
    meta: MetaObjectCentricData
    objects: Dict[str, Obj]
    events_split: Dict[AvailableGranularity, Dict[int, Dict[str, Event]]]