from typing import Dict, List, Tuple, Optional, Union, Any, Set
from dataclasses import dataclass, field, InitVar
import copy
import pandas as pd
from evaluation.constants import DEVS, PERCS
from numpy import median

import contect.available.available
import contect.available.available as av
from backend.param.available import get_available_from_name, AvailableSituationsExt, extract_extension, extract_title, \
    AvailableDetectorsExt, detector_shortcut
from contect.context.objects.situations.helpers.additionaldata.additionaldata import AdditionalDataContainer
from contect.context.objects.timeunits.timeunit import TimeSpan
from contect.deviationdetection.detectors.profiles.param.config import ProfilesParameters
from contect.parsedata.objects.ocdata import ObjectCentricData, Event
from contect.parsedata.parse import parse_csv
from contect.resource.resource import read_csv_from_file, get_resource_filepath
from evaluation.objects.param.config import EvaluationExperiment, EvaluationSituation
from contect.parsedata.config.param import CsvParseParameters, JsonParseParameters
import contect.context.objects.timeunits.timeunit as tu
from contect.deviationdetection.objects.detection import DetectorParameters
from backend.job.param.userconfig import UserConfig
from contect.available.available import AvailableSelections, \
    AvailableDetectors, get_available_granularity_from_name, AvailableSituations, get_range_from_name, \
    AvailablePerfToDevRelationships, get_simple_available_from_name, AvailableSituationType, AvailableGranularity, \
    AvailableClassifications

DRIFT = 'moderate'  # Random selection of parameters for contexts change yearly

@dataclass
class DefaultEvaluation:
    detectors: List[AvailableDetectors] = field(default_factory=lambda: [
        detector for detector in AvailableDetectors])
    percs_deviating: List[float] = field(default_factory=lambda: DEVS)
    percs_attributable: List[float] = field(default_factory=lambda: PERCS)
    # Use only hour, as the generated data has timestamp precision is seconds --> more precise and schedule needs this
    granularities: List[av.AvailableGranularity] = field(default_factory=lambda: [av.AvailableGranularity.HR])
    user_configs: Dict[str, Dict[av.AvailableGranularity, UserConfig]] = field(init=False)


@dataclass
class Evaluation:
    params: Dict[str, EvaluationExperiment] = field(init=False)  # key is the dataset
    data_names: List[str]
    datasets: Dict[str, ObjectCentricData] = field(init=False)
    weekly_demands: Dict[str, int] = field(init=False)
    weeks: Dict[str, Set[int]] = field(init=False)
    sep: InitVar[str]
    additional_data: Dict[str, AdditionalDataContainer] = field(default_factory=lambda: {})


@dataclass
class _SyntheticEvaluation:
    parse_param: CsvParseParameters = field(default_factory=lambda: default_csv_parameters())


@dataclass
class SyntheticEvaluation(DefaultEvaluation, _SyntheticEvaluation, Evaluation):

    def __post_init__(self,
                      sep: str):
        self.datasets = {data_name: parse_evaluation(data_name, sep, self.parse_param)
                         for data_name in self.data_names}
        weekly_demands = {data_name: 0
                          for data_name in self.data_names}
        self.weeks = {}
        for data_name in self.data_names:
            self.weeks[data_name] = set()
            events = self.datasets[data_name].raw.events
            n_place_order = {}
            for index, eid in enumerate(events):
                event = events[eid]
                week = event.time.isocalendar()[1]
                if event.act == 'place order':
                    # Only place order weeks are relevant
                    self.weeks[data_name].add(week)
                    if week in n_place_order:
                        n_place_order[week].append(1)
                    else:
                        n_place_order[week] = [1]
            n_place_order = {
                w: sum(n_place_order[w])
                for w in n_place_order
            }
            weekly_demands[data_name] = median([n_place_order[w] for w in n_place_order])
        self.weekly_demands = weekly_demands
        self.user_configs = {data_name: {granularity:
            UserConfig(
                situation_selections_weight=default_situation_selections_weight(),
                parse_param=self.parse_param,
                detector_params={
                    detector: default_profiles_parameters(detector, 0.2)  # this is only a dummy
                    for detector in self.detectors
                },
                granularity=self.granularities[0],
                aggregator=av.AvailableAggregators.MAX,
                drift=DRIFT)
            for granularity in self.granularities} for data_name in self.datasets}
        self.params = {f'{data_name}-m{detector.value}-pD{perc_deviating}'
                       f'-pA{perc_pos_attributable1}-{perc_pos_attributable2}':
                           EvaluationExperiment(perc_deviating=perc_deviating,
                                                detector=detector,
                                                data_name=data_name,
                                                granularity=granularity,
                                                dataset=self.datasets[data_name],
                                                timespan=get_timespan_for_dataset(self.datasets[data_name],
                                                                                  granularity),
                                                context_param=self.user_configs[data_name][granularity].context_param,
                                                perc_pos_attributables=(perc_pos_attributable1,
                                                                        perc_pos_attributable2))
                       for data_name in self.data_names
                       for perc_deviating in self.percs_deviating
                       for perc_pos_attributable1 in self.percs_attributable
                       for perc_pos_attributable2 in self.percs_attributable
                       for detector in self.detectors
                       for granularity in self.granularities}
        # self.datasets = None


def parse_evaluation(data_name, sep, parse_param):
    return parse_csv(
        pd.read_csv(
            get_resource_filepath(data_name),
            sep=sep,
            names=['activity', 'time', 'orders', 'items', 'packages', 'customers', 'products', 'price', 'weight',
                   'resource', 'normal', 'context-aware-normal', 'deviating', 'context-aware-deviating'],
            header=0
        ).rename(columns={'normal': AvailableClassifications.N.value,
                          'context-aware-normal': AvailableClassifications.CAN.value,
                          'deviating': AvailableClassifications.D.value,
                          'context-aware-deviating': AvailableClassifications.CAD.value}),
        parse_param)


def default_profiles_parameters(detector, perc_deviating):
    return DetectorParameters(
        detector=detector,
        param=ProfilesParameters(deviating_perc=perc_deviating,
                                 init_initial_norm=1))


def default_context_settings(situations, desired_selections, vmap_parameters):
    pass


def get_timespan_for_dataset(dataset, granularity) -> TimeSpan:
    start_time, end_time = tu.get_start_end_time(dataset.raw.events)
    start_time = tu.round_start_to_granularity(start_time, granularity)
    t, u, timespan = tu.get_timespan(tu.get_timedelta(granularity, 1), start_time, end_time, granularity)
    return timespan


def default_csv_parameters() -> CsvParseParameters:
    vmap_availables = {}
    vmap_availables[av.AvailableSelections.RESOURCE] = True
    vmap_availables[av.AvailableSelections.LOCATION] = False
    vmap_params = {av.AvailableSelections.RESOURCE: 'resource'}
    csv_param = CsvParseParameters(time_name='time',
                                   act_name='activity',
                                   obj_names=['orders', 'items', 'packages'],
                                   val_names=['price', 'weight', 'customers',
                                              'resource'] + [val.value for val in AvailableClassifications],
                                   vmap_availables=vmap_availables,
                                   vmap_params=vmap_params)

    return csv_param


def default_situations() -> List[Tuple[av.AvailableEntities,
                                       av.AvailableSituations,
                                       av.AvailableSelections]]:
    return [(av.AvailableEntities.CAPACITYUTIL,
             av.AvailableSituations.CAPACITY,
             av.AvailableSelections.RESOURCE)]


def default_situation_selections_weight() -> Dict[av.AvailableSituations,
                                                  Dict[Union[av.AvailableSelections,
                                                             av.AvailableNormRanges,
                                                             av.AvailablePerfToDevRelationships,
                                                             av.AvailableSituationType], float]]:
    granularity = AvailableGranularity.HR.value
    includes_guides = {AvailableSituations.CAPACITY.value: AvailableSituationType.POSITIVE.value,
                       AvailableSituations.UNIT_PERFORMANCE.value: AvailableSituationType.POSITIVE.value,
                       AvailableSituations.SCHEDULE.value: AvailableSituationType.NEGATIVE.value,
                       AvailableSituations.WAIT_PERFORMANCE.value: AvailableSituationType.NEGATIVE.value}
    drift = DRIFT
    guides = [context.value for context in AvailableSituations]

    granularity = get_available_granularity_from_name(granularity)

    situations = [get_available_from_name(situation,
                                          AvailableSituationsExt.UNIT_PERFORMANCE,
                                          AvailableSituationsExt)
                  for situation in includes_guides]

    guides = [get_available_from_name(situation,
                                      AvailableSituations.UNIT_PERFORMANCE,
                                      AvailableSituations)
              for situation in guides]
    situation_selections_weight = {
        extract_extension(situation).available:
            {**{selection: 1 for selection in extract_extension(situation).selections
                if {
                    **{AvailableSelections.GLOBAL: True,
                       AvailableSelections.ACTIVITY: True,
                       AvailableSelections.OBJECTTYPE: True},
                    **{AvailableSelections.RESOURCE: True,
                       AvailableSelections.LOCATION: False}
                }[selection]
                },
             **get_range_from_name(drift),
             **{AvailablePerfToDevRelationships.PROP: 1},
             **{get_simple_available_from_name(includes_guides[extract_title(situation)],
                                               AvailableSituationType.POSITIVE,
                                               AvailableSituationType): 1}}
        for situation in situations
    }
    # situation_selections_weight[AvailableSituations.CAPACITY]['additional_data'] = 1
    return situation_selections_weight
