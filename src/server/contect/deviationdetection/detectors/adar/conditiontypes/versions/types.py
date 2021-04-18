from dataclasses import dataclass, field
from typing import Union, List


@dataclass
class ConditionControlFlow:
    val: str
    eid: Union[str, List[str]] = field(compare=False)




