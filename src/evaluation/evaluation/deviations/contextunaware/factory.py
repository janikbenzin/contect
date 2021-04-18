from typing import Callable
from datetime import datetime
from functools import partial

from contect.parsedata.objects.ocdata import ObjectCentricData
from evaluation.deviations.contextunaware.versions.deviations import inject_add_deviation, inject_remove_deviation, \
    inject_replace_deviation, inject_replace_res_deviation
from contect.available.available import AvailableDeviationTypes


def get_deviation_injector(typ: AvailableDeviationTypes,
                           data: ObjectCentricData,
                           start: datetime,
                           end: datetime) -> Callable:
    if typ is AvailableDeviationTypes.ADD:
        return partial(inject_add_deviation, data, start, end)
    if typ is AvailableDeviationTypes.REM:
        return partial(inject_remove_deviation, data)
    if typ is AvailableDeviationTypes.REPL:
        return partial(inject_replace_deviation, data)
    else:
        return partial(inject_replace_res_deviation, data)
