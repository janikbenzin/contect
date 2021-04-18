from typing import Union, Optional, Dict
from dataclasses import dataclass, field, InitVar

from contect.context.objects.context.config.param import ContextParameters, SituationParameters, HelperParameters, \
    IdentificatorParameters
from contect.context.util.util import get_selections, get_selected_situations, get_required_contextentity, \
    get_required_situations
from contect.parsedata.config.param import CsvParseParameters, JsonParseParameters
from contect.deviationdetection.detectors.profiles.param.config import ProfilesParameters
from contect.deviationdetection.objects.detection import DetectorParameters
import contect.available.available as av
from backend.param.available import AvailableCorrelationsExt, AvailableDetectorsExt, extract_title, extract_extension, \
    AvailableSituationsExt, match_entity, match_situation, detector_shortcut, AvailableTops, \
    match_helper, get_required_contextentity, get_required_situations, get_available_from_name


@dataclass
class UserConfig:
    parse_param: Union[CsvParseParameters, JsonParseParameters]
    detector_params: Dict[av.AvailableDetectors, DetectorParameters]
    context_param: ContextParameters = field(init=False)
    granularity: InitVar[av.AvailableGranularity]
    aggregator: av.AvailableAggregators
    drift: InitVar[str]
    situation_selections_weight: InitVar[Dict[av.AvailableSituations,
                                              Dict[Union[av.AvailableSelections,
                                                         av.AvailableNormRanges,
                                                         av.AvailablePerfToDevRelationships,
                                                         av.AvailableSituationType,
                                                         str], float]]]
    ca_post_params: Dict[av.AvailableDetectors, Dict[av.AvailableSituationType, float]] = field(
        default_factory=lambda: {detector:
                                     {typ: 0
                                      for typ in av.AvailableSituationType}
                                 for detector in av.AvailableDetectors})
    corr_combination: Optional[str] = field(default_factory=lambda: None)

    def __post_init__(self, granularity: av.AvailableGranularity, drift, situation_selections_weight):
        self.context_param = get_context_parameters(granularity, self.aggregator, situation_selections_weight,
                                                    av.get_range_from_name(drift),
                                                    get_required_contextentity,
                                                    get_required_situations)


def get_context_parameters(granularity, aggregator, situation_selections_weight, norm_range,
                           get_associated_contextentity=get_required_contextentity,
                           get_associated_situation=get_required_situations):
    selections = get_selections(situation_selections_weight, get_associated_contextentity)
    selected_situations = get_selected_situations(situation_selections_weight, selections, get_associated_situation)
    context_param = ContextParameters()
    context_param.selected_situations = selected_situations
    context_param.selections = selections
    context_param.granularity = granularity
    context_param.situation_param = {
        situation: SituationParameters(
            helper=HelperParameters(
                norm_range=extract_norm_range(situation_selections_weight, situation),
                granularity=context_param.granularity
            ),
            identificator=IdentificatorParameters(
                relation=extract_perf_dev_rel(situation_selections_weight, situation)
            ),
            typing=extract_situation_type(situation_selections_weight, situation),
            weights=situation_selections_weight[situation]
        )
        for situation in situation_selections_weight
    }
    context_param.aggregator = aggregator
    context_param.norm_range = norm_range
    return context_param


def extract_norm_range(situation_selections_weight: Dict[av.AvailableSituations,
                                                         Dict[Union[av.AvailableSelections,
                                                                    av.AvailableNormRanges,
                                                                    av.AvailablePerfToDevRelationships,
                                                                    av.AvailableSituationType,
                                                                    str], float]],
                       situation: av.AvailableSituations) -> av.AvailableNormRanges:
    norm_range = [norm_range for norm_range in situation_selections_weight[situation]
                  if isinstance(norm_range, av.AvailableNormRanges)][0]
    del situation_selections_weight[situation][norm_range]
    return norm_range


def extract_perf_dev_rel(situation_selections_weight: Dict[av.AvailableSituations,
                                                           Dict[Union[av.AvailableSelections,
                                                                      av.AvailableNormRanges,
                                                                      av.AvailablePerfToDevRelationships,
                                                                      av.AvailableSituationType,
                                                                      str], float]],
                         situation: av.AvailableSituations) -> av.AvailablePerfToDevRelationships:
    rel = [rel for rel in situation_selections_weight[situation]
           if isinstance(rel, av.AvailablePerfToDevRelationships)][0]
    del situation_selections_weight[situation][rel]
    return rel


def extract_situation_type(situation_selections_weight: Dict[av.AvailableSituations,
                                                             Dict[Union[av.AvailableSelections,
                                                                        av.AvailableNormRanges,
                                                                        av.AvailablePerfToDevRelationships,
                                                                        av.AvailableSituationType,
                                                                        str], float]],
                           situation: av.AvailableSituations) -> av.AvailableSituationType:
    typ = [typ for typ in situation_selections_weight[situation]
           if isinstance(typ, av.AvailableSituationType)][0]
    del situation_selections_weight[situation][typ]
    return typ
