from enum import Enum
from functools import partial
from typing import List

from backend.param.constants import PLACEHOLDER_KEY, FORMTEXT_KEY
from backend.param.interpretations import unit_performance_interpretation, schedule_pattern_interpretation, \
    capacity_interpretation, single_unit_performance_interpretation, single_pattern_interpretation, \
    single_capacity_interpretation
from contect.available.constants import TRANSFORMATION_KEY
from contect.available.available import AvailableCorrelations, AvailableDetectors, AvailableSituations, \
    AvailableSelections, AvailableEntities
from contect.available.ext import ContectExtension, ContectExtensible
from contect.context.extractors.versions.extract import extract_capacity, extract_timeunit, extract_directly_follows
from contect.context.identificators.versions.identify import identify_performance, identify_schedule, identify_capacity
from contect.context.objects.contextentities.versions.entities import UnitTimeContextEntity, DirectlyTimeContextEntity, \
    CapacitySystemContextEntity
from contect.context.objects.situations.helpers.versions.extract import extract_double_global, extract_double_granular, \
    extract_single_global, extract_single_granular
from contect.context.objects.situations.helpers.versions.helpers import SingleGlobalHelper, SingleGranularHelper, \
    DoubleGlobalHelper, DoubleGranularHelper
from contect.context.objects.situations.versions.situations import SelectableFunctionalSituation, \
    DoubleSelectionFunctionalSituation
from contect.deviationdetection.detectors.adar.detector import ADARDetector
from contect.deviationdetection.detectors.adar.param.config import ADARParameters
from contect.deviationdetection.detectors.alignments.detector import AlignmentsDetector
from contect.deviationdetection.detectors.alignments.param.config import AlignmentsParameters
from contect.deviationdetection.detectors.autoencoder.detector import AutoencDetector
from contect.deviationdetection.detectors.autoencoder.param.config import AutoencParameters
from contect.deviationdetection.detectors.profiles.detector import ProfilesDetector
from contect.deviationdetection.detectors.profiles.param.config import ProfilesParameters
from contect.parsedata.correlate import correlate_shared_objs, correlate_obj_path


class AvailableEntitiesExt(Enum):
    TIMEUNIT = {AvailableEntities.TIMEUNIT.value:
                    ContectExtension(name='timeunit',
                                     param={},
                                     typ=ContectExtensible.CE,
                                     call=extract_timeunit,
                                     entity=UnitTimeContextEntity,
                                     extractor_target='value',
                                     arguments=['selection', 'meta', 'vmap_param', 'objects', 'chunk']
                                     )}
    DIRECTLYFOLLOWS = {AvailableEntities.DIRECTLYFOLLOWS.value:
                           ContectExtension(name='directlyfollows',
                                            param={},
                                            typ=ContectExtensible.CE,
                                            call=extract_directly_follows,
                                            entity=DirectlyTimeContextEntity,
                                            extractor_target='value',
                                            arguments=['meta', 'log', 'chunk'])}
    CAPACITYUTIL = {AvailableEntities.CAPACITYUTIL.value:
                        ContectExtension(name='capacityutil',
                                         param=dict(value=None),
                                         typ=ContectExtensible.CE,
                                         call=extract_capacity,
                                         entity=CapacitySystemContextEntity,
                                         extractor_target='nested_value',
                                         arguments=['selection', 'meta', 'vmap_param', 'chunk'])}


def get_available_from_name(method, default, available):
    if 'Ext' in str(default.__class__):
        return AVAILABLE_TO_EXT_AVAILABLE[method]
    else:
        return EXT_AVAILABLE_TO_AVAILABLE[method]


def match_entity(entity, **kwargs):
    version = get_available_from_name(entity.value, AvailableEntitiesExt.TIMEUNIT, AvailableEntitiesExt)
    return extract_extension(version).build_entity(**kwargs)


def match_helper(timespan, param, data, entity, situation, step_width, additional_data, **kwargs):
    version = get_available_from_name(situation.value, AvailableSituationsExt.UNIT_PERFORMANCE, AvailableSituationsExt)
    return extract_extension(version).build_helper(timespan,
                                                   param,
                                                   data,
                                                   entity,
                                                   situation,
                                                   step_width,
                                                   additional_data,
                                                   **kwargs)


def get_situation_from_available(method, default, available):
    for candidate in available:
        if method is extract_extension(candidate).available:
            return candidate
    return default


def match_situation(**kwargs):
    version = get_situation_from_available(kwargs['situation'],
                                           AvailableSituationsExt.UNIT_PERFORMANCE,
                                           AvailableSituationsExt)
    return extract_extension(version).build_situation(**kwargs)


def get_required_contextentity(situation):
    version = get_available_from_name(situation.value, AvailableSituationsExt.UNIT_PERFORMANCE, AvailableSituationsExt)
    return extract_extension(version).available_entity


class AvailableSituationsExt(Enum):
    UNIT_PERFORMANCE = {AvailableSituations.UNIT_PERFORMANCE.value:
                            ContectExtension(name='time unit performance',
                                             param={},
                                             param_helper={},
                                             typ=ContectExtensible.SIT,
                                             call=identify_performance,
                                             global_helper_call=extract_single_global,
                                             granular_helper_call=extract_single_granular,
                                             help_text='''The time unit performance context detects periods of unusally large demand or workload in your process.''',
                                             available_entity=AvailableEntities.TIMEUNIT,
                                             available=AvailableSituations.UNIT_PERFORMANCE,
                                             situation=SelectableFunctionalSituation,
                                             helper_global=SingleGlobalHelper,
                                             helper_granular=SingleGranularHelper,
                                             selections=[AvailableSelections.GLOBAL,
                                                         AvailableSelections.RESOURCE,
                                                         AvailableSelections.LOCATION,
                                                         AvailableSelections.OBJECTTYPE,
                                                         AvailableSelections.ACTIVITY],
                                             extractor_target='value',
                                             interpretation=partial(unit_performance_interpretation,
                                                                    'time unit',
                                                                    'count',
                                                                    ''),
                                             interpretation_anti=partial(unit_performance_interpretation,
                                                                         'time unit',
                                                                         'count',
                                                                         '1 subtracted by'),
                                             interpretation_single=partial(single_unit_performance_interpretation,
                                                                           'count'))}
    WAIT_PERFORMANCE = {AvailableSituations.WAIT_PERFORMANCE.value:
                            ContectExtension(name='waiting time performance',
                                             param={},
                                             param_helper={},
                                             typ=ContectExtensible.SIT,
                                             call=identify_performance,
                                             global_helper_call=extract_single_global,
                                             granular_helper_call=extract_single_granular,
                                             situation=SelectableFunctionalSituation,
                                             help_text='''The waiting time performance context detects periods of unusually long waiting times for activities.''',
                                             helper_global=SingleGlobalHelper,
                                             helper_granular=SingleGranularHelper,
                                             available_entity=AvailableEntities.DIRECTLYFOLLOWS,
                                             available=AvailableSituations.WAIT_PERFORMANCE,
                                             selections=[AvailableSelections.ACTIVITY],
                                             extractor_target='value',
                                             interpretation=partial(unit_performance_interpretation,
                                                                    'waiting time',
                                                                    'waiting time in seconds',
                                                                    ''),
                                             interpretation_anti=partial(unit_performance_interpretation,
                                                                         'waiting time',
                                                                         'waiting time in seconds',
                                                                         '1 subtracted by'),
                                             interpretation_single=partial(single_unit_performance_interpretation,
                                                                           'waiting time'))}
    SCHEDULE = {AvailableSituations.SCHEDULE.value:
                    ContectExtension(name='schedule pattern',
                                     param={},
                                     param_helper={},
                                     typ=ContectExtensible.SIT,
                                     call=identify_schedule,
                                     global_helper_call=extract_single_global,
                                     granular_helper_call=extract_single_granular,
                                     situation=SelectableFunctionalSituation,
                                     help_text='''The schedule pattern breach context detects unusually high workloads of a given weekly schedule hour compared to the preceding month or year, e.g. if there is usually no work on weekends, but on one Sunday an employee works a lot, the working hours of that Sunday are detected.''',
                                     helper_global=SingleGlobalHelper,
                                     helper_granular=SingleGranularHelper,
                                     available_entity=AvailableEntities.TIMEUNIT,
                                     available=AvailableSituations.SCHEDULE,
                                     selections=[AvailableSelections.GLOBAL],
                                     extractor_target='value',
                                     interpretation=partial(schedule_pattern_interpretation,
                                                            ''),
                                     interpretation_anti=partial(schedule_pattern_interpretation,
                                                                 '1 subtracted by'),
                                     interpretation_single=single_pattern_interpretation)}
    CAPACITY = {AvailableSituations.CAPACITY.value:
                    ContectExtension(name='capacity',
                                     param=dict(value=None,  # Used for parametrization of situation call
                                                selection2=AvailableSelections.ACTIVITY),
                                     param_helper=dict(selection2=AvailableSelections.ACTIVITY),
                                     typ=ContectExtensible.SIT,
                                     call=identify_capacity,
                                     global_helper_call=extract_double_global,
                                     granular_helper_call=extract_double_granular,
                                     situation=DoubleSelectionFunctionalSituation,
                                     helper_global=DoubleGlobalHelper,
                                     helper_granular=DoubleGranularHelper,
                                     help_text='''The capacity utilization performance detects unusually high capacity utilizations of the resources or locations in your process.''',
                                     available_entity=AvailableEntities.CAPACITYUTIL,
                                     available=AvailableSituations.CAPACITY,
                                     selections=[AvailableSelections.RESOURCE,
                                                 AvailableSelections.LOCATION],
                                     extractor_target='nested_value',
                                     interpretation=partial(capacity_interpretation,
                                                            ''),
                                     interpretation_anti=partial(capacity_interpretation,
                                                                 '1 subtracted by'),
                                     interpretation_single=single_capacity_interpretation)}


class AvailableCorrelationsExt(Enum):
    MAXIMUM_CORRELATION = {AvailableCorrelations.MAXIMUM_CORRELATION.value:
                               ContectExtension(name='shared object id (maximum)',
                                                param={'version': AvailableCorrelations.MAXIMUM_CORRELATION},
                                                typ=ContectExtensible.CORR,
                                                call=correlate_shared_objs)
                           }
    INITIAL_PAIR_CORRELATION = {AvailableCorrelations.INITIAL_PAIR_CORRELATION.value:
                                    ContectExtension(name='shared object id (partition, minimum)',
                                                     param={'version': AvailableCorrelations.INITIAL_PAIR_CORRELATION},
                                                     typ=ContectExtensible.CORR,
                                                     call=correlate_shared_objs)}
    OBJ_PATH_CORRELATION = {AvailableCorrelations.OBJ_PATH_CORRELATION.value:
                                ContectExtension(name='object path correlation',
                                                 param={},
                                                 typ=ContectExtensible.CORR,
                                                 call=correlate_obj_path)}
    INITIAL_PAIR_CORRELATION_NON = {AvailableCorrelations.INITIAL_PAIR_CORRELATION_NON.value:
                                    ContectExtension(name='shared object id (minimum)',
                                                     param={'version': AvailableCorrelations.INITIAL_PAIR_CORRELATION,
                                                            'partition': False},
                                                     typ=ContectExtensible.CORR,
                                                     call=correlate_shared_objs)}


def transform_deviating_perc(input_string):
    return dict(deviating_perc=float(input_string) / 100)


class AvailableDetectorsExt(Enum):
    # To extend contect with a detector, please implement a class YourDetector according
    # to the structure of the existing detectors. Important: The detector constructor will be called
    # with the corresponding parameters object, which receives user-dependent input variables from the
    # output of the function referenced at TRANSFORMATION_KEY. Then, the detector's detect function
    # will be called to return the detector's threshold and as a side effect the new log
    PROF = {AvailableDetectors.PROF.value:
                ContectExtension(name='profiles',
                                 param=None,
                                 param_constructor=ProfilesParameters,
                                 typ=ContectExtensible.DET,
                                 call=ProfilesDetector,
                                 input_display={'% Deviating Traces':
                                                    {PLACEHOLDER_KEY: '0 < x <= 100',
                                                     FORMTEXT_KEY: "Please specify what percentage of your log's "
                                                                   "overall traces shall be detected as deviating",
                                                     TRANSFORMATION_KEY: transform_deviating_perc}

                                                },
                                 help_text='''Profiles iteratively samples more normal sets of traces and profiles each trace against this more normal set of traces. 
The result is a sorting of traces according to their profiles in the last iteration, which is used to partition the event data into a set of normal traces and a set of deviating traces using the *% deviating traces*.''',
                                 available=AvailableDetectors.PROF
                                 )
            }
    ALIGN = {AvailableDetectors.ALIGN.value:
                 ContectExtension(name='alignments',
                                  param=None,
                                  param_constructor=AlignmentsParameters,
                                  typ=ContectExtensible.DET,
                                  call=AlignmentsDetector,
                                  help_text='''Inductive applies the IMf with various filtering parameter values to mine a process model that has the maximum sum of fitness, precision, generalization and simplicity. Then, alignments are applied to detect traces that deviate from the mined process model.''',
                                  available=AvailableDetectors.ALIGN)}
    ADAR = {AvailableDetectors.ADAR.value:
                ContectExtension(name='anomaly detection association rules',
                                 param=None,
                                 param_constructor=ADARParameters,
                                 typ=ContectExtensible.DET,
                                 call=ADARDetector,
                                 help_text='''ADAR applies the idea of association rules to event data. 
A set of anomaly detection association rules specifying normal behavior is mined from the event data. 
A trace is detected as deviating if its aggregate support is below the the aggregate support of its most similar trace in the event data with respect to the set of anomaly detection association rules.''',
                                 log_param=['vmap_param'],
                                 available=AvailableDetectors.ADAR,
                                 resource=True)}
    AUTOENC = {AvailableDetectors.AUTOENC.value:
                   ContectExtension(name='autoencoder',
                                    param=None,
                                    param_constructor=AutoencParameters,
                                    typ=ContectExtensible.DET,
                                    call=AutoencDetector,
                                    input_display={'% Deviating Traces':
                                                       {PLACEHOLDER_KEY: '0 < x <= 100',
                                                        FORMTEXT_KEY: "Please specify what percentage of your log's "
                                                                      "overall traces shall be detected as deviating",
                                                        TRANSFORMATION_KEY: transform_deviating_perc

                                                        }
                                                   },
                                    help_text='''Autoencoder one-hot encodes a trace in the event data and use it as input (and output) to an autoencoder **neural network**.
After the autoencoder has been trained, the deviation of a trace can be determined by means of the error the autoencoder makes in predicting the trace.''',
                                    log_param=['meta.acts', 'meta.ress', 'vmap_param.vmap_params', 'traces'],
                                    available=AvailableDetectors.AUTOENC,
                                    resource=True
                                    )
               }


def extract_title(detector):
    return list(detector.value.keys())[0]


def extract_helps(available):
    return {detector:
                detector.value[extract_title(detector)].help_text is not None
            for detector in available}


def extract_inputs(available):
    return {detector:
                detector.value[extract_title(detector)].input_display is not None
            for detector in available}


def extract_extension(detector):
    return detector.value[extract_title(detector)]


def get_situation(situation):
    return get_available_from_name(situation,
                                   AvailableSituations.UNIT_PERFORMANCE,
                                   AvailableSituations)


def sit_shortcut(sit):
    return get_available_from_name(extract_title(sit),
                                   AvailableSituations.CAPACITY,
                                   AvailableSituations)


def detector_shortcut(detector):
    return get_available_from_name(extract_title(detector),
                                   AvailableDetectors.ADAR,
                                   AvailableDetectors)


def representative_title(representative, n):
    return f'{n} {representative}'


def get_available_from_name_compile_time(method, default, available):
    for candidate in available:
        if method in candidate.value:
            return candidate
    return default


EXT_AVAILABLE_TO_AVAILABLE = {
    **{extract_title(ext): get_available_from_name_compile_time(extract_title(ext), AvailableEntities.TIMEUNIT,
                                                                AvailableEntities)
       for ext in AvailableEntitiesExt},
    **{extract_title(ext): get_available_from_name_compile_time(extract_title(ext),
                                                                AvailableCorrelations.MAXIMUM_CORRELATION,
                                                                AvailableCorrelations)
       for ext in AvailableCorrelationsExt},
    **{extract_title(ext): get_available_from_name_compile_time(extract_title(ext), AvailableDetectors.ADAR,
                                                                AvailableDetectors)
       for ext in AvailableDetectorsExt},
    **{extract_title(ext): get_available_from_name_compile_time(extract_title(ext),
                                                                AvailableSituations.UNIT_PERFORMANCE,
                                                                AvailableSituations)
       for ext in AvailableSituationsExt},
    **{ext.value: ext
       for ext in AvailableSelections}
}

AVAILABLE_TO_EXT_AVAILABLE = {
    **{ext.value: get_available_from_name_compile_time(ext.value, AvailableEntitiesExt.TIMEUNIT,
                                                       AvailableEntitiesExt)
       for ext in AvailableEntities},
    **{ext.value: get_available_from_name_compile_time(ext.value, AvailableSituationsExt.UNIT_PERFORMANCE,
                                                       AvailableSituationsExt)
       for ext in AvailableSituations},
    **{ext.value: get_available_from_name_compile_time(ext.value, AvailableCorrelationsExt.OBJ_PATH_CORRELATION,
                                                       AvailableCorrelationsExt)
       for ext in AvailableCorrelations},
    **{ext.value: get_available_from_name_compile_time(ext.value, AvailableDetectorsExt.ADAR,
                                                       AvailableDetectorsExt)
       for ext in AvailableDetectors},
}

ENTITY_TO_SITUATIONS = {
    entity:
        {
            extract_extension(situation).available
            for situation in AvailableSituationsExt if extract_extension(situation).available_entity is entity
        }
    for entity in AvailableEntities
}


def get_required_situations(entity: AvailableEntities,
                            selected_situations: List[AvailableSituations]) -> List[AvailableSituations]:
    return list(ENTITY_TO_SITUATIONS[entity].intersection(set(selected_situations)))


class AvailableTops(Enum):
    REP = partial(representative_title, 'representative deviating traces')
    HIGH = partial(representative_title, 'most critical deviating traces')
    POT = partial(representative_title, 'potentially critical traces')
    BORD_PS = partial(representative_title, ' about to be reclassified as normal traces (positive context)')
    BORD_NG = partial(representative_title, ' about to be reclassified as deviating traces (negative context)')
