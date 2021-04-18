from typing import Dict, Union

from contect.parsedata.objects.ocdata import Event, MetaObjectCentricData, Obj
from contect.parsedata.objects.oclog import ObjectCentricLog
from contect.available.available import AvailableEntities, AvailableSelections
from contect.context.objects.contextentities.config.mappings import SUPPORTED_SELECTIONS, AVAILABLE_CE
from contect.context.objects.contextentities.versions.entities import ContextEntity, DoubleSelectionEntity
from contect.context.extractors.factory import get_extractor
from contect.parsedata.config.param import CsvParseParameters, JsonParseParameters


def get_contextentity(entity: AvailableEntities,
                      selection: AvailableSelections,
                      chunk: Dict[str, Event],
                      time: int,
                      meta: MetaObjectCentricData,
                      vmap_param: Union[CsvParseParameters, JsonParseParameters],
                      objects: Dict[str, Obj],
                      log: ObjectCentricLog) -> ContextEntity:
    if selection in SUPPORTED_SELECTIONS[entity]:
        if isinstance(AVAILABLE_CE[entity]['type'], DoubleSelectionEntity):
            return AVAILABLE_CE[entity]['constructor'](
                value=None,
                time=time,
                selection=selection,
                nested_value=get_extractor(entity, selection, meta, vmap_param, objects, log)(chunk)
            )
        else:
            return AVAILABLE_CE[entity]['constructor'](
                value=get_extractor(entity, selection, meta, vmap_param, objects, log)(chunk),
                time=time,
                selection=selection
            )
