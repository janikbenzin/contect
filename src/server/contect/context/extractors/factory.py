from functools import partial
from typing import Union, Dict

from contect.parsedata.objects.ocdata import MetaObjectCentricData, Obj
from contect.parsedata.objects.oclog import ObjectCentricLog
from contect.available.available import AvailableEntities, AvailableSelections
from contect.context.extractors.versions.extract import extract_capacity, extract_timeunit, extract_directly_follows
from contect.parsedata.config.param import CsvParseParameters, JsonParseParameters


def get_extractor(variant: AvailableEntities,
                  selection: AvailableSelections,
                  meta: MetaObjectCentricData,
                  vmap_param: Union[CsvParseParameters, JsonParseParameters],
                  objects: Dict[str, Obj],
                  log: ObjectCentricLog):
    if variant is AvailableEntities.CAPACITYUTIL:
        return partial(extract_capacity, selection, meta, vmap_param)
    elif variant is AvailableEntities.TIMEUNIT:
        return partial(extract_timeunit, selection, meta, vmap_param, objects)
    elif variant is AvailableEntities.DIRECTLYFOLLOWS:
        return partial(extract_directly_follows, meta, log)
    else:
        return lambda x: 0
