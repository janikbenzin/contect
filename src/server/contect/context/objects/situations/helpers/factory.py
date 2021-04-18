from typing import Dict, Any, Union

from contect.available.available import AvailableNormRanges, AvailableSelections, AvailableSituations, AvailableEntities
import contect.context.objects.situations.helpers.versions.helpers as h
from contect.context.objects.contextentities.versions.entities import DoubleSelectionEntity, TimeContextEntity
from contect.context.objects.situations.helpers.additionaldata.additionaldata import AdditionalDataSituation, \
    AdditionalDataHelper
from contect.context.objects.context.config.param import HelperParameters
from contect.context.objects.situations.helpers.versions.extract import extract_double_global, \
    extract_single_granular, extract_single_global, extract_double_granular
from contect.context.objects.timeunits.timeunit import TimeSpan
from contect.parsedata.objects.ocdata import MetaObjectCentricData


def get_helper(timespan: TimeSpan,
               param: HelperParameters,
               data: Dict[AvailableSelections, Dict[int, Union[TimeContextEntity, DoubleSelectionEntity]]],
               entity: AvailableEntities,
               situation: AvailableSituations,
               step_width: int,
               additional_data: AdditionalDataSituation = None) -> h.Helper:
    return h.Helper(
        helpers={
            selection:
                get_functional_helper(timespan,
                                      param,
                                      data[selection],
                                      entity,
                                      situation,
                                      selection,
                                      step_width,
                                      additional_data.add_data_helpers[selection] if
                                      additional_data is not None else None)
            for selection in {sel if situation is not AvailableSituations.SCHEDULE else AvailableSelections.GLOBAL
                              for sel in data}
        },
        associated_ce=entity,
        associated_sit=situation
    )


def get_functional_helper(timespan: TimeSpan,
                          param: HelperParameters,
                          data: Dict[int, Union[TimeContextEntity, DoubleSelectionEntity]],
                          entity: AvailableEntities,
                          situation: AvailableSituations,
                          selection: AvailableSelections,
                          step_width: int,
                          additional_data: AdditionalDataHelper = None) -> h.FunctionalHelper:
    if param.norm_range is AvailableNormRanges.GLOBAL:
        if situation is AvailableSituations.CAPACITY:
            return get_double_global(constructor=h.DoubleGlobalHelper,
                                     timespan=timespan,
                                     param=param,
                                     data=data,
                                     entity=entity,
                                     situation=situation,
                                     selection=selection,
                                     additional_data=additional_data)
        else:
            return h.SingleGlobalHelper(selection=selection,
                                        aggregator=extract_single_global(timespan=timespan,
                                                                         param=param,
                                                                         data=data,
                                                                         entity=entity,
                                                                         situation=situation,
                                                                         selection=selection,
                                                                         additional_data=additional_data
                                                                         )
                                        )
    else:
        if situation is AvailableSituations.CAPACITY:
            return get_double_granular(constructor=h.DoubleGranularHelper,
                                       timespan=timespan,
                                       param=param,
                                       data=data,
                                       entity=entity,
                                       situation=situation,
                                       selection=selection,
                                       step_width=step_width,
                                       additional_data=additional_data)
        else:
            return h.SingleGranularHelper(selection=selection,
                                          granularity=param.granularity,
                                          aggregator=extract_single_granular(timespan=timespan,
                                                                             param=param,
                                                                             data=data,
                                                                             entity=entity,
                                                                             situation=situation,
                                                                             selection=selection,
                                                                             step_width=step_width,
                                                                             additional_data=additional_data),
                                          )


def get_double_granular(constructor: Any,
                        timespan: TimeSpan,
                        param: HelperParameters,
                        data: Dict[int, Union[TimeContextEntity, DoubleSelectionEntity]],
                        entity: AvailableEntities,
                        situation: AvailableSituations,
                        selection: AvailableSelections,
                        step_width: int,
                        additional_data: AdditionalDataHelper = None) -> h.DoubleGranularHelper:
    return constructor(selection=AvailableSelections.ACTIVITY,
                       selection2=selection,
                       granularity=param.granularity,
                       aggregator=extract_double_granular(data=data,
                                                          step_width=step_width,
                                                          additional_data=additional_data,
                                                          timespan=timespan,
                                                          param=param,
                                                          entity=entity,
                                                          situation=situation,
                                                          selection=selection))


def get_double_global(constructor: Any,
                      timespan: TimeSpan,
                      param: HelperParameters,
                      data: Dict[int, Union[TimeContextEntity, DoubleSelectionEntity]],
                      entity: AvailableEntities,
                      situation: AvailableSituations,
                      selection: AvailableSelections,
                      additional_data: AdditionalDataHelper = None) -> h.DoubleGlobalHelper:
    return constructor(
        selection=AvailableSelections.ACTIVITY,
        selection2=selection,
        aggregator=extract_double_global(timespan=timespan,
                                         param=param,
                                         data=data,
                                         entity=entity,
                                         situation=situation,
                                         selection=selection,
                                         additional_data=additional_data)
    )
