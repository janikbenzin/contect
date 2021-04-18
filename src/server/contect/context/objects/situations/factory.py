from typing import Dict, List

from contect.available.available import AvailableEntities, AvailableSelections, AvailableSituations
from contect.context.objects.context.config.param import SituationParameters
from contect.context.objects.situations.versions.situations import Situation, FunctionalSituation, \
    DoubleSelectionFunctionalSituation
from contect.context.identificators.factory import get_identifcator
from contect.context.objects.situations.config.mappings import AVAILABLE_SIT
from contect.context.objects.contextentities.versions.entities import ContextEntity
from contect.context.objects.situations.helpers.versions.helpers import Helper


def get_situation(entity: AvailableEntities,
                  situation: AvailableSituations,
                  selections: List[AvailableSelections],
                  entities: Dict[AvailableSelections, Dict[int, ContextEntity]],
                  helper: Helper,
                  time_to_time_bin: Dict[int, int],
                  situation_param: SituationParameters) -> Situation:
    if isinstance(AVAILABLE_SIT[entity]['type'], DoubleSelectionFunctionalSituation):
        return Situation({selection:
            {time:
                AVAILABLE_SIT[entity]['constructor'](
                    value=None,
                    time=time,
                    selection=selection,
                    nested_value=get_identifcator(entity=entity,
                                                  situation=situation,
                                                  selection=selection,
                                                  helper=helper,
                                                  time_to_time_bin=time_to_time_bin,
                                                  situation_param=situation_param)(
                        entity=entities[selection][time], time=time),
                    selection2=AvailableSelections.ACTIVITY)
                for time in entities[selection]
            }
            for selection in selections},
            associated_ce=entity,
            associated_sit=situation)
    else:
        return Situation({selection:
            {time:
                AVAILABLE_SIT[entity]['constructor'](
                    value=get_identifcator(entity=entity,
                                           situation=situation,
                                           selection=selection,
                                           helper=helper,
                                           time_to_time_bin=time_to_time_bin,
                                           situation_param=situation_param)(entities[selection][time], time),
                    time=time,
                    selection=selection)
                for time in entities[selection]
            }
            for selection in selections},
            associated_ce=entity,
            associated_sit=situation)
