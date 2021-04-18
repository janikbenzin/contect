from typing import Union, Callable, Optional

from contect.available.available import AvailableADARTypes
from contect.deviationdetection.detectors.adar.conditiontypes.versions.types import ConditionControlFlow
from contect.parsedata.objects.ocdata import Event


def get_condition_type(typ: AvailableADARTypes,
                       event: Optional[Event] = None) -> Union[ConditionControlFlow, Callable]:
    if typ is AvailableADARTypes.CONTROL or typ is AvailableADARTypes.RESOURCE:
        # Event given in the extend_rules function
        if event is not None:
            return ConditionControlFlow(val=event.act,
                                        eid=event.id)
        else:
            # No event given during the merge_conditions function after rules have been mined
            return ConditionControlFlow

