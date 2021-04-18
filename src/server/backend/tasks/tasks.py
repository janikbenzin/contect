from datetime import datetime
from time import sleep
from typing import Dict, List, Union, Any, Tuple, Optional

import numpy as np
import pandas as pd
import os
import itertools

from contect.postprocessing.postprocessor import ContextPostProcessor, get_true_label
from sklearn.metrics import accuracy_score, balanced_accuracy_score
from backend.guidance.guide import build_dataframes, guide_positive, guide_negative, add_includes
from backend.job.param.userconfig import get_context_parameters
from backend.param.available import AvailableCorrelationsExt, AvailableDetectorsExt, extract_title, extract_extension, \
    AvailableSituationsExt, match_entity, match_situation, detector_shortcut, AvailableTops, \
    match_helper, get_required_contextentity, get_required_situations, get_available_from_name
from backend.param.constants import CSV, AGGREGATOR, CONTEXT_KEY, INCLUDES_KEY, GUIDES_KEY, JOBS_KEY, JOB_TASKS_KEY, \
    METHODS_KEY, negative_context, tid_t, group_t, DEFAULT_TOP, \
    column_names, high_t, bord_ps, bord_ng
from backend.param.settings import CeleryConfig, redis_pwd
from celery import Celery
from celery.result import AsyncResult
from contect.available.available import AvailableSelections, \
    AvailableDetectors, get_available_granularity_from_name, AvailableSituations, get_range_from_name, \
    AvailablePerfToDevRelationships, get_simple_available_from_name, AvailableSituationType, AvailableGranularity, \
    AvailableClassifications, AvailableCorrelations
from contect.available.constants import LOG_KEY, SITUATION_AGG_KEY, ANTI_KEY, SITUATION_KEY, \
    HOURS_IN_DAY, ENTITY_KEY, THRESHOLDS_KEY, DETECTORS_KEY
from contect.context.initeventcontext import init_events_context, init_log_events_context
from contect.context.objects.context.factory import get_context
from contect.context.objects.context.versions.context import Context
from contect.context.objects.timeunits.timeunit import get_timedelta
from contect.deviationdetection.objects.detection import Detection, DetectorParameters
from contect.parsedata.objects.ocdata import ObjectCentricData, sort_events
from contect.parsedata.objects.oclog import ObjectCentricLog, Trace
from contect.parsedata.parse import parse_csv, parse_json
import pickle
import redis
from sklearn_extra.cluster import KMedoids

CELERY_TIMEOUT = 21600  # The time in seconds a callback waits for a celery task to get ready


def user_log_key(user, log_hash):
    return f'{user}-{log_hash}'


def results_key(task_id):
    return f'result-{task_id}'


def store_redis(data, task):
    key = results_key(task.id)
    pickled_object = pickle.dumps(data)
    db.set(key, pickled_object)


redis_host = os.getenv('REDIS_LOCALHOST_OR_DOCKER')
db = redis.StrictRedis(host=redis_host, port=6379, password=redis_pwd, db=0)

db.keys()
celery = Celery('contect.worker',
                )
celery.config_from_object(CeleryConfig)

localhost_or_docker = os.getenv('LOCALHOST_OR_DOCKER')


# celery.conf.update({'CELERY_ACCEPT_CONTENT': ['pickle']})


@celery.task(bind=True, serializer='pickle')
def store_redis_backend(self, data: Any) -> Any:
    store_redis(data, self.request)


@celery.task(bind=True, serializer='pickle')
def parse_data(self, data, data_type, parse_param, resource, location) -> ObjectCentricData:
    # Dirty fix for serialization of parse_param to celery seem to change the values always to False
    if resource:
        parse_param.vmap_availables[AvailableSelections.RESOURCE] = True
    if location:
        parse_param.vmap_availables[AvailableSelections.LOCATION] = True
    if data_type == CSV:
        store_redis(parse_csv(data, parse_param), self.request)
    else:
        store_redis(parse_json(data, parse_param), self.request)


@celery.task(bind=True, serializer='pickle')
def compute_context(self,
                    includes_guides: Dict[str, Tuple[str, str]],
                    includes: List[str],
                    guides: List[str],
                    granularity: str,
                    drift: str,
                    methods_bool: List[bool],
                    data: ObjectCentricData,
                    log: ObjectCentricLog) -> Dict[str, Union[Context, List[AvailableSituations]]]:
    granularity = get_available_granularity_from_name(granularity)

    situations = [get_available_from_name(situation,
                                          AvailableSituationsExt.UNIT_PERFORMANCE,
                                          AvailableSituationsExt)
                  for situation in includes_guides]
    includes = [get_available_from_name(situation,
                                        AvailableSituations.UNIT_PERFORMANCE,
                                        AvailableSituations)
                for situation in includes]
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
                    **{AvailableSelections.RESOURCE:
                           AvailableSelections.RESOURCE in log.vmap_param.vmap_params,
                       AvailableSelections.LOCATION:
                           AvailableSelections.LOCATION in log.vmap_param.vmap_params}
                }[selection]
                },
             **get_range_from_name(drift),
             **{AvailablePerfToDevRelationships.PROP: 1},
             **{get_simple_available_from_name(includes_guides[extract_title(situation)],
                                               AvailableSituationType.POSITIVE,
                                               AvailableSituationType): 1}}
        for situation in situations
    }
    context_param = get_context_parameters(granularity,
                                           AGGREGATOR,
                                           situation_selections_weight,
                                           get_range_from_name(drift),
                                           get_required_contextentity,
                                           get_required_situations)
    sort_events(data)
    context = get_context(context_param=context_param,
                          data=data,
                          log=log,
                          call_contextentity=match_entity,
                          call_situation=match_situation,
                          call_helper=match_helper
                          )
    store_redis({CONTEXT_KEY: context,
                 INCLUDES_KEY: includes,
                 GUIDES_KEY: guides,
                 METHODS_KEY: methods_bool},
                self.request)


@celery.task(bind=True, serializer='pickle')
def post_process(self,
                 alpha_ps: float,
                 alpha_ng: float,
                 threshold: float,
                 log: ObjectCentricLog,
                 detector: AvailableDetectors,
                 variant=False) -> ObjectCentricLog:
    processor = ContextPostProcessor(ps=alpha_ps,
                                     ng=alpha_ng,
                                     threshold=threshold,
                                     detector=detector)
    if variant:
        return processor.predict(log)
    else:
        store_redis(processor.predict(log), self.request)


@celery.task(bind=True, serializer='pickle')
def generate_summary_data(self,
                          cluster_sizes,
                          detectors,
                          log,
                          ng,
                          ps,
                          variant):
    clustering, clustering_dfs, cluster_sizes_l = apply_clustering_on_deviating(cluster_sizes, detectors, log, ng,
                                                                                ps, variant)
    cluster_sizes = {detector_shortcut(detector):
                         {str(top):
                              cluster_sizes[index]
                              if cluster_sizes_l[index] == cluster_sizes[index]
                              else cluster_sizes[index] if top is AvailableTops.POT or top is AvailableTops.BORD_NG
                              else cluster_sizes_l[index]
                          for top in AvailableTops
                          }
                     for index, detector in enumerate(AvailableDetectorsExt)
                     }
    normal_data = create_normal_dfs(clustering_dfs, detectors, log, ng, ps, variant)
    all_data = {}
    for detector in AvailableDetectorsExt:
        detector = detector_shortcut(detector)
        if detector in detectors:
            all_data[detector] = pd.concat([clustering_dfs[detector], normal_data[detector]])
    top_traces = get_top_traces(detectors, cluster_sizes, all_data)
    store_redis(tuple([all_data, top_traces, cluster_sizes, clustering]), self.request)


@celery.task(bind=True, serializer='pickle')
def generate_context_details(self,
                             detectors,
                             events_timeunits,
                             granularity,
                             log,
                             ng,
                             ps,
                             rng,
                             event_to_traces,
                             vmap_params,
                             objects):
    ps_agg_daily_contexts = {detector: {} for detector in detectors}
    ng_agg_daily_contexts = {detector: {} for detector in detectors}
    daily_contexts = {detector:
                          {typ:
                               {sit:
                                    {sel:
                                         {}
                                     for sel in log.traces[0].rich_context[detector][typ][sit]
                                     }
                                for sit in log.traces[0].rich_context[detector][typ]
                                }
                           for typ in log.traces[0].rich_context[detector]
                           }
                      for detector in detectors}
    for tid, trace in log.traces.items():
        for event in trace.events:
            tu = events_timeunits[granularity][event.id]
            for detector in detectors:
                # Aggregates
                if tu not in ps_agg_daily_contexts[detector]:
                    ps_agg_daily_contexts[detector][tu] = [(event.complex_context[detector][ps],
                                                            event)
                                                           ]
                else:
                    ps_agg_daily_contexts[detector][tu].append((event.complex_context[detector][ps],
                                                                event))
                if tu not in ng_agg_daily_contexts[detector]:
                    ng_agg_daily_contexts[detector][tu] = [(event.complex_context[detector][ng],
                                                            event)]
                else:
                    ng_agg_daily_contexts[detector][tu].append((event.complex_context[detector][ng],
                                                                event))
                    # Details
                for typ in event.rich_context[detector]:
                    for sit in event.rich_context[detector][typ]:
                        for sel in event.rich_context[detector][typ][sit]:
                            if tu not in daily_contexts[detector][typ][sit][sel]:
                                daily_contexts[detector][typ][sit][sel][tu] = [
                                    (event.rich_context[detector][typ][sit][sel], event)
                                ]
                            else:
                                daily_contexts[detector][typ][sit][sel][tu].append(
                                    (event.rich_context[detector][typ][sit][sel], event)
                                )
    daily_contexts = {detector:
                          {typ:
                               {sit:
                                    {sel:
                                         {tu:
                                              {SITUATION_AGG_KEY:
                                                   np.average([d[0][SITUATION_KEY]
                                                               for d in daily_contexts[detector][typ][sit][sel][tu]]),
                                               SITUATION_KEY:
                                                   [(t[0][SITUATION_KEY], t[1])
                                                    for t in daily_contexts[detector][typ][sit][sel][tu]],
                                               ANTI_KEY:
                                                   daily_contexts[detector][typ][sit][sel][tu][0][0][ANTI_KEY],
                                               ENTITY_KEY:
                                                   daily_contexts[detector][typ][sit][sel][tu][0][0][ENTITY_KEY]
                                               }
                                          for tu in daily_contexts[detector][typ][sit][sel]
                                          }
                                     for sel in daily_contexts[detector][typ][sit]
                                     }
                                for sit in daily_contexts[detector][typ]
                                }
                           for typ in daily_contexts[detector]
                           }
                      for detector in daily_contexts}
    ps_agg_daily_contexts = {detector:
        {tu:
            (
                np.average(
                    [val[0] for val in ps_agg_daily_contexts[detector][tu]
                     ]
                ),
                ps_agg_daily_contexts[detector][tu]
            )
            for tu in ps_agg_daily_contexts[detector]}
        for detector in ps_agg_daily_contexts}
    ng_agg_daily_contexts = {detector:
        {tu:
            (np.average(
                [val[0] for val in ng_agg_daily_contexts[detector][tu]
                 ]
            ),
             ng_agg_daily_contexts[detector][tu]
            )
            for tu in ng_agg_daily_contexts[detector]}
        for detector in ng_agg_daily_contexts}
    timespan = log.timespan
    start_year = timespan.start.year
    end_year = timespan.end.year
    years = tuple([year for year in range(start_year, end_year + 1)])
    next_time = datetime(start_year, 1, 1)
    delta = get_timedelta(granularity, 1)
    tus = []
    while next_time < timespan.start:
        tus.append(1)
        next_time += delta
    added = - len(tus)
    tu_before = [i for i in range(added, 0)]
    tu_at = [tu for tu in log.timespan.units[granularity]]
    for tu in tu_before:
        for detector in detectors:
            if tu not in ps_agg_daily_contexts[detector]:
                ps_agg_daily_contexts[detector][tu] = (np.nan, [])
            if tu not in ng_agg_daily_contexts[detector]:
                ng_agg_daily_contexts[detector][tu] = (np.nan, [])
            for typ in daily_contexts[detector]:
                for sit in daily_contexts[detector][typ]:
                    for sel in daily_contexts[detector][typ][sit]:
                        if tu not in daily_contexts[detector][typ][sit][sel]:
                            daily_contexts[detector][typ][sit][sel][tu] = {}
                            daily_contexts[detector][typ][sit][sel][tu][SITUATION_AGG_KEY] = np.nan
                            daily_contexts[detector][typ][sit][sel][tu][SITUATION_KEY] = []
                            daily_contexts[detector][typ][sit][sel][tu][ANTI_KEY] = None
                            daily_contexts[detector][typ][sit][sel][tu][ENTITY_KEY] = None
    for tu in tu_at:
        for detector in detectors:
            if tu not in ps_agg_daily_contexts[detector]:
                ps_agg_daily_contexts[detector][tu] = (0, [])
            if tu not in ng_agg_daily_contexts[detector]:
                ng_agg_daily_contexts[detector][tu] = (0, [])
            for typ in daily_contexts[detector]:
                for sit in daily_contexts[detector][typ]:
                    for sel in daily_contexts[detector][typ][sit]:
                        if tu not in daily_contexts[detector][typ][sit][sel]:
                            daily_contexts[detector][typ][sit][sel][tu] = {}
                            daily_contexts[detector][typ][sit][sel][tu][SITUATION_AGG_KEY] = 0
                            daily_contexts[detector][typ][sit][sel][tu][SITUATION_KEY] = []
                            daily_contexts[detector][typ][sit][sel][tu][ANTI_KEY] = None
                            daily_contexts[detector][typ][sit][sel][tu][ENTITY_KEY] = None
    if granularity is AvailableGranularity.HR:
        # Need to aggregate to days
        daily_contexts = {detector:
            {typ:
                {sit:
                    {sel:
                        {int(tu / HOURS_IN_DAY):
                            {SITUATION_AGG_KEY:
                                np.average([
                                    daily_contexts[detector][typ][sit][sel][tud][SITUATION_AGG_KEY]
                                    if tud in daily_contexts[detector][typ][sit][sel]
                                    else 0
                                    for tud in range(tu, tu + HOURS_IN_DAY)
                                ]),
                                SITUATION_KEY:
                                    [
                                        item for sublist in
                                        [
                                            daily_contexts[detector][typ][sit][sel][tud][SITUATION_KEY]
                                            if tud in daily_contexts[detector][typ][sit][sel]
                                            else []
                                            for tud in range(tu, tu + HOURS_IN_DAY)
                                        ]
                                        for item in sublist
                                    ],
                                ANTI_KEY:
                                    daily_contexts[detector][typ][sit][sel][tu][ANTI_KEY],
                                ENTITY_KEY:
                                    [
                                        daily_contexts[detector][typ][sit][sel][tud][ENTITY_KEY]
                                        if tud in daily_contexts[detector][typ][sit][sel]
                                        else None
                                        for tud in range(tu, tu + HOURS_IN_DAY)
                                    ]

                            }
                            for tu in range(added, len(log.timespan.units[granularity]), HOURS_IN_DAY)
                        }
                        for sel in daily_contexts[detector][typ][sit]
                    }
                    for sit in daily_contexts[detector][typ]
                }
                for typ in daily_contexts[detector]
            }
            for detector in daily_contexts}
        ps_agg_daily_contexts = {detector:
            {int(tu / HOURS_IN_DAY):
                (
                    np.average(
                        [
                            ps_agg_daily_contexts[detector][tud][0]
                            if tud in ps_agg_daily_contexts[detector]
                            else 0
                            for tud in range(tu, tu + HOURS_IN_DAY)
                        ]
                    ),
                    [
                        item for sublist in
                        [
                            ps_agg_daily_contexts[detector][tud][1]
                            if tud in ps_agg_daily_contexts[detector]
                            else []
                            for tud in range(tu, tu + HOURS_IN_DAY)
                        ]
                        for item in sublist
                    ]
                )
                for tu in range(added, len(log.timespan.units[granularity]), HOURS_IN_DAY)}
            for detector in ps_agg_daily_contexts}
        ng_agg_daily_contexts = {detector:
            {int(tu / HOURS_IN_DAY):
                (
                    np.average(
                        [
                            ng_agg_daily_contexts[detector][tud][0]
                            if tud in ng_agg_daily_contexts[detector]
                            else 0
                            for tud in range(tu, tu + HOURS_IN_DAY)
                        ]
                    ),
                    [
                        item for sublist in
                        [
                            ng_agg_daily_contexts[detector][tud][1]
                            if tud in ng_agg_daily_contexts[detector]
                            else []
                            for tud in range(tu, tu + HOURS_IN_DAY)
                        ]
                        for item in sublist
                    ]
                )
                for tu in range(added, len(log.timespan.units[granularity]), HOURS_IN_DAY)}
            for detector in ng_agg_daily_contexts}
    t = tuple(
        [added, daily_contexts, ng_agg_daily_contexts, ps_agg_daily_contexts, years, granularity, rng, event_to_traces,
         vmap_params, objects])
    store_redis(t, self.request)


@celery.task(bind=True, serializer='pickle')
def correlate_events(self,
                     data: ObjectCentricData,
                     user_ot_selection: List[str],
                     version: str):
    version_ext = get_available_from_name(version,
                                          AvailableCorrelationsExt.INITIAL_PAIR_CORRELATION,
                                          AvailableCorrelationsExt)
    selection = set(user_ot_selection)
    sort_events(data)
    store_redis(version_ext.value[version].call_with_param(selection=selection, data=data), self.request)


@celery.task(bind=True, serializer='pickle')
def compute_detection(self,
                      versions: List[str],
                      inputs: Dict[str, Dict[str, str]],
                      log: ObjectCentricLog,
                      variant=False) -> Dict[str, Union[Detection, ObjectCentricLog]]:
    detectors = [get_available_from_name(version,
                                         AvailableDetectorsExt.ADAR,
                                         AvailableDetectorsExt)
                 for version in versions]
    detector_params = {extract_extension(detector).available:
                           extract_extension(detector).build_param_obj(log, **inputs[extract_title(detector)])
                       for detector in detectors}

    detection = Detection(detector_params={detector: DetectorParameters(detector=detector,
                                                                        param=detector_params[detector])
                                           for detector in detector_params},
                          detectors={
                              extract_extension(detector).available:
                                  extract_extension(detector).call_wo_param(param=
                                                                            detector_params[
                                                                                extract_extension(detector).available])
                              for detector in detectors
                          })
    detection.detector_thresholds = {detector:
                                         detection.detectors[detector].detect(log=log)
                                     for detector in detector_params}
    if variant:
        return {DETECTORS_KEY: list(detection.detectors.keys()),
                THRESHOLDS_KEY: detection.detector_thresholds,
                LOG_KEY: log}
    else:
        store_redis({DETECTORS_KEY: list(detection.detectors.keys()),
                     THRESHOLDS_KEY: detection.detector_thresholds,
                     LOG_KEY: log}, self.request)


@celery.task(bind=True, serializer='pickle')
def compute_guidance(self, oc_data, detection_dict, context_dict):
    detectors = detection_dict[DETECTORS_KEY]
    detector_thresholds = detection_dict[THRESHOLDS_KEY]
    log = detection_dict[LOG_KEY]
    context = context_dict[CONTEXT_KEY]
    includes = context_dict[INCLUDES_KEY]
    guides = context_dict[GUIDES_KEY]
    methods = context_dict[METHODS_KEY]
    # Guide > Include
    includes = [sit for sit in includes if sit not in guides]
    if AvailableSituations.UNIT_PERFORMANCE.value in includes:
        context.params[0].situation_param[AvailableSituations.UNIT_PERFORMANCE].weights = {
            sel: 1 / len(context.params[0].situation_param[AvailableSituations.UNIT_PERFORMANCE].weights)
            for sel in context.params[0].situation_param[AvailableSituations.UNIT_PERFORMANCE].weights
        }
    extended_guides = {}
    df_neg, df_pos, situation_entity_selection = build_dataframes(context, guides, log, oc_data)
    descriptive_features = df_pos.columns.to_list()
    classifiers = {}
    results = {}
    for detector in detectors:
        all_sit = []
        antis = {}
        if len(df_pos) > 0:
            guide_positive(all_sit, antis, classifiers, descriptive_features, detector, df_pos, log, results,
                           situation_entity_selection)

        # Negative Guidance
        if len(df_neg) > 0:
            guide_negative(all_sit, antis, df_neg, situation_entity_selection)
        all_sit = add_includes(all_sit, context, includes)
        entities = set()
        situations = set()
        sit_sel = {}
        for entity, sit, sel, c in all_sit:
            entities.add(entity)
            if sit not in situations:
                sit_sel[sit] = [sel]
            else:
                sit_sel[sit].append(sel)
            situations.add(sit)
        init_events_context(oc_data, context, 0,
                            include_entity=lambda x: any([x is ent for ent in list(entities)]),
                            include_sit=lambda x: any([x is sit for sit in list(situations)]),
                            include_sit_sel=lambda sit, selection: selection in sit_sel[sit],
                            anti=antis,
                            backend=False,
                            detector=detector)
        init_log_events_context(oc_data, log, AGGREGATOR, 0, False, False, detector)
    log.timespan = context.timespan
    log.events_timeunits = context.events_timeunits
    log.granularity = list(context.context.keys())[0]
    log.methods_bool = methods
    log.norm_range = context.params[0].norm_range
    log.detector_thresholds = detector_thresholds
    for detector in AvailableDetectorsExt:
        if detector_shortcut(detector) in detectors:
            log.labels[detector_shortcut(detector)] = [
                AvailableClassifications.N if tid in log.normal[detector_shortcut(detector)]
                else AvailableClassifications.D for tid in log.traces]
    store_redis(log, self.request)


def get_remote_data(user, log_hash, jobs, task_type, length=None):
    if jobs is not None and log_hash in jobs[JOBS_KEY] and task_type in jobs[JOBS_KEY][log_hash][JOB_TASKS_KEY]:
        task = get_task(jobs, log_hash, task_type)
        task.forget()
        timeout = 0
        key = results_key(get_task_id(jobs, log_hash, task_type))
        while not db.exists(key):
            sleep(1)
            timeout += 1
            if timeout > CELERY_TIMEOUT:
                return None
            if task.failed():
                return None
        return pickle.loads(db.get(key))
    else:
        if length is not None:
            return tuple([None] * length)
        else:
            return None


def get_task(jobs, log_hash, task_type):
    task = AsyncResult(id=get_task_id(jobs, log_hash, task_type), app=celery)
    return task


def get_task_id(jobs, log_hash, task_type):
    return jobs[JOBS_KEY][log_hash][JOB_TASKS_KEY][task_type]


def get_top_traces(detectors, cluster_sizes, all_data):
    top_traces = {str(top): {} for top in AvailableTops}
    for index, detector in enumerate(AvailableDetectorsExt):
        detector = detector_shortcut(detector)
        if detector in detectors:
            n_clusters = cluster_sizes[detector]
            high_traces = sorted([(all_data[detector][high_t][i],
                                   all_data[detector][tid_t][i],
                                   i) for i in range(len(all_data[detector]))],
                                 key=lambda item: item[0],
                                 reverse=True)[:n_clusters[str(AvailableTops.HIGH)]]
            top_traces[str(AvailableTops.HIGH)][detector] = high_traces
            for t in high_traces:
                all_data[detector].at[t[2], group_t] = 'Most Critical'
            pot_traces = sorted([(all_data[detector][negative_context][i],
                                  all_data[detector][tid_t][i],
                                  i) for i in range(len(all_data[detector]))],
                                key=lambda item: item[0],
                                reverse=True)[:n_clusters[str(AvailableTops.POT)]]
            top_traces[str(AvailableTops.POT)][detector] = pot_traces
            for t in pot_traces:
                all_data[detector].at[t[2], group_t] = 'Potentially Critical'
            ps_traces = sorted([(all_data[detector][bord_ps][i],
                                 all_data[detector][tid_t][i],
                                 i) for i in range(len(all_data[detector]))],
                               key=lambda item: item[0],
                               reverse=True)[:n_clusters[str(AvailableTops.BORD_PS)]]
            top_traces[str(AvailableTops.BORD_PS)][detector] = ps_traces
            for t in ps_traces:
                all_data[detector].at[t[2], group_t] = 'Border Cases Positive'
            ng_traces = sorted([(all_data[detector][bord_ng][i],
                                 all_data[detector][tid_t][i],
                                 i) for i in
                                range(len(all_data[detector]))],
                               key=lambda item: item[0],
                               reverse=True)[:n_clusters[str(AvailableTops.BORD_NG)]]
            top_traces[str(AvailableTops.BORD_NG)][detector] = ng_traces
            for t in ng_traces:
                all_data[detector].at[t[2], group_t] = 'Border Cases Negative'
    return top_traces


def create_normal_dfs(clustering_dfs, detectors, log, ng, ps, variant=True):
    normal_data = {detector_shortcut(detector):
                       pd.DataFrame(
                           [
                               [score_variant(log, tid, detector_shortcut(detector), variant),
                                log.traces[tid].complex_context[detector_shortcut(detector)][
                                    ps],
                                log.traces[tid].complex_context[detector_shortcut(detector)][
                                    ng],
                                log.labels[detector_shortcut(detector)][tid].value,
                                tid,
                                log.traces[tid].events[0].time,
                                log.traces[tid].events[-1].time,
                                len(log.traces[tid].events),
                                0,
                                -2,
                                score_variant(log, tid, detector_shortcut(detector), variant) +
                                log.traces[tid].complex_context[detector_shortcut(detector)][
                                    ng],
                                'Normal',
                                ]
                               for tid in log.traces if
                               log.labels[detector_shortcut(detector)][tid] is AvailableClassifications.N
                               or log.labels[detector_shortcut(detector)][
                                   tid] is AvailableClassifications.CAN
                           ],
                           columns=column_names + [group_t],
                           index=range(len(clustering_dfs[detector_shortcut(detector)])
                                       if clustering_dfs[detector_shortcut(detector)] is not None
                                       else 0, len(log.traces))
                       ) if detector_shortcut(detector) in detectors else None
                   for detector in AvailableDetectorsExt}
    return normal_data


def apply_clustering_on_deviating(cluster_sizes, detectors, log, ng, ps, variant=True):
    clustering_data = {detector_shortcut(detector):
                           np.asarray(
                               [
                                   [score_variant(log, tid, detector_shortcut(detector), variant),
                                    log.traces[tid].complex_context[
                                        detector_shortcut(detector)][
                                        ps],
                                    log.traces[tid].complex_context[
                                        detector_shortcut(detector)][
                                        ng],
                                    log.labels[detector_shortcut(detector)][tid].value,
                                    tid,
                                    log.traces[tid].events[0].time,
                                    log.traces[tid].events[-1].time,
                                    len(log.traces[tid].events),

                                    score_variant(log, tid, detector_shortcut(detector), variant) + (1 -
                                                                                                     log.traces[
                                                                                                         tid].complex_context[
                                                                                                         detector_shortcut(
                                                                                                             detector)][
                                                                                                         ps]),
                                    log.traces[tid].complex_context[
                                        detector_shortcut(detector)][
                                        ps] - score_variant(log, tid, detector_shortcut(detector), variant),
                                    0
                                    ]
                                   for tid in range(len(log.traces))
                                   if log.labels[detector_shortcut(detector)][tid] is AvailableClassifications.D
                                      or log.labels[detector_shortcut(detector)][
                                          tid] is AvailableClassifications.CAD
                               ]
                           ) if detector_shortcut(detector) in detectors else None
                       for detector in AvailableDetectorsExt}
    cluster_size_l = []
    for index, detector in enumerate(AvailableDetectorsExt):
        detector = detector_shortcut(detector)
        if detector in detectors:
            d_n = len(clustering_data[detector])
            if d_n < cluster_sizes[index]:
                cluster_size_l.append(d_n)
            else:
                cluster_size_l.append(cluster_sizes[index])
        else:
            cluster_size_l.append(DEFAULT_TOP)
    cluster_sizes = cluster_size_l
    clustering = {detector_shortcut(detector):
                      KMedoids(n_clusters=cluster_sizes[index],
                               random_state=0).fit(clustering_data[detector_shortcut(detector)][:, 0:3])
                      if detector_shortcut(detector) in detectors and
                         len(clustering_data[detector_shortcut(detector)].shape) > 1 else
                      None
                  for index, detector in enumerate(AvailableDetectorsExt)}
    clustering_dfs = {detector_shortcut(detector):
                          pd.DataFrame(clustering_data[detector_shortcut(detector)],
                                       columns=column_names,
                                       index=range(len(clustering_data[detector_shortcut(detector)])))
                          if detector_shortcut(detector) in detectors and
                             len(clustering_data[detector_shortcut(detector)].shape) > 1 else None
                      for detector in AvailableDetectorsExt}
    for detector in AvailableDetectorsExt:
        detector = detector_shortcut(detector)
        if detector in detectors and len(clustering_data[detector].shape) > 1:
            clustering_dfs[detector][group_t] = [f'Cluster {label}' for label in clustering[detector].labels_]
    return clustering, clustering_dfs, cluster_sizes


def score_variant(log, tid, detector, variant=None):
    if variant is None:
        return log.traces[tid].score[detector]
    elif variant[detector]:
        return log.traces[tid].score[detector]
    else:
        return log.traces[tid].ca_score[detector]


if localhost_or_docker == 'localhost':
    from evaluation.scenarios.timeunit import add_excess_demand_events
    from evaluation.classification import add_deviations
    from evaluation.classification import classify_context_aware_events
    from contect.parsedata.correlate import correlate_shared_objs
    from evaluation.classification import is_deviating, is_ca_deviating, is_ca_normal, is_normal


    @celery.task(serializer='pickle')
    def compute_evaluation_experiment(random_r,
                                      eval_param_r,
                                      weeks_r,
                                      weekly_demand_r,
                                      day_timespans_r,
                                      excess_log_r,
                                      parse_param_r,
                                      data_to_resource_r):
        eval_param_r.init_weeks()
        context_aware_weeks_r = add_excess_demand_events(year_adjustment=day_timespans_r[eval_param_r.data_name][1],
                                                         random=random_r,
                                                         excess_log=excess_log_r,
                                                         weekly_demand=weekly_demand_r,
                                                         weeks=weeks_r,
                                                         weeks_to_events=eval_param_r.weeks_to_events,
                                                         data=eval_param_r.dataset)

        add_deviations(eval_param=eval_param_r,
                       random=random_r)
        eval_param_r.init_weekends()
        classify_context_aware_events(eval_param=eval_param_r,
                                      parse_param=parse_param_r,
                                      context_aware_days=data_to_resource_r[eval_param_r.data_name][0],
                                      random=random_r,
                                      timespan_d=day_timespans_r[eval_param_r.data_name][0],
                                      year_adjustment=day_timespans_r[eval_param_r.data_name][1],
                                      excess_log=excess_log_r,
                                      weekly_demand=weekly_demand_r,
                                      weeks=weeks_r,
                                      weeks_to_events=eval_param_r.weeks_to_events,
                                      data=eval_param_r.dataset,
                                      weekends=eval_param_r.weekends,
                                      context_aware_weeks=context_aware_weeks_r)
        sort_events(eval_param_r.dataset)

        eval_param_r.log = correlate_shared_objs(eval_param_r.dataset,
                                                 {'orders'},
                                                 AvailableCorrelations.INITIAL_PAIR_CORRELATION,
                                                 partition=False)
        eval_param_r.context = get_context(context_param=eval_param_r.context_param,
                                           data=eval_param_r.dataset,
                                           log=eval_param_r.log,
                                           additional_data=eval_param_r.additional_data[eval_param_r.granularity],
                                           call_contextentity=match_entity,
                                           call_situation=match_situation,
                                           call_helper=match_helper
                                           )
        # The ground truth
        eval_param_r.log_with_classification = {
            tid: Trace(events=[],
                       context={},
                       deviating={eval_param_r.detector: is_deviating(trace)},
                       ca_deviating={eval_param_r.detector: is_ca_deviating(trace)},
                       ca_normal={eval_param_r.detector: is_ca_normal(trace)},
                       normal={eval_param_r.detector: is_normal(trace)},
                       id=trace.id) for tid, trace in eval_param_r.log.traces.items()
        }
        # Need to adjust the deviating percentage to reflect the actual percentage of deviating traces not events
        adjusted_deviating_perc = 1 - (sum([1 for tid, trace in eval_param_r.log_with_classification.items()
                                            if trace.normal[eval_param_r.detector]
                                            or trace.ca_deviating[eval_param_r.detector]]) / len(
            eval_param_r.log_with_classification))
        eval_param_r.real_perc_deviating = adjusted_deviating_perc
        eval_param_r.real_perc_ca_deviating = sum([1 for tid, trace in eval_param_r.log_with_classification.items()
                                                   if trace.ca_deviating[eval_param_r.detector]]) / len(
            eval_param_r.log_with_classification)
        eval_param_r.real_perc_deviating_ca = sum([1 for tid, trace in eval_param_r.log_with_classification.items()
                                                   if trace.deviating[eval_param_r.detector]]) / len(
            eval_param_r.log_with_classification)
        eval_param_r.real_perc_ca_normal = sum([1 for tid, trace in eval_param_r.log_with_classification.items()
                                                if trace.ca_normal[eval_param_r.detector]]) / len(
            eval_param_r.log_with_classification)
        eval_param_r.real_perc_normal = sum([1 for tid, trace in eval_param_r.log_with_classification.items()
                                             if trace.normal[eval_param_r.detector]]) / len(
            eval_param_r.log_with_classification)
        if eval_param_r.detector is AvailableDetectors.PROF or eval_param_r.detector is AvailableDetectors.AUTOENC:
            inputs = {eval_param_r.detector.value: {'% Deviating Traces': eval_param_r.real_perc_deviating * 100}}
        else:
            inputs = {eval_param_r.detector.value: {}}
        detection_dict = compute_detection([eval_param_r.detector.value],
                                           inputs,
                                           eval_param_r.log,
                                           variant=True)
        eval_param_r.detection = detection_dict
        methods_bool = [True, True, True, True]
        includes = []
        guides = [context.value for context in AvailableSituations]
        guides = [get_available_from_name(situation,
                                          AvailableSituations.UNIT_PERFORMANCE,
                                          AvailableSituations)
                  for situation in guides]
        context_dict = {CONTEXT_KEY: eval_param_r.context,
                        INCLUDES_KEY: includes,
                        GUIDES_KEY: guides,
                        METHODS_KEY: methods_bool}
        eval_param_r.log = compute_evaluation_guidance(eval_param_r.dataset, detection_dict, context_dict)
        # eval_param_r.context_dict = context_dict
        # eval_param_r.detection_dict = detection_dict
        return eval_param_r


    def compute_evaluation_guidance(oc_data, detection_dict, context_dict):
        detectors = detection_dict[DETECTORS_KEY]
        detector_thresholds = detection_dict[THRESHOLDS_KEY]
        log = detection_dict[LOG_KEY]
        context = context_dict[CONTEXT_KEY]
        includes = context_dict[INCLUDES_KEY]
        guides = context_dict[GUIDES_KEY]
        methods = context_dict[METHODS_KEY]
        # Guide > Include
        includes = [sit for sit in includes if sit not in guides]
        if AvailableSituations.UNIT_PERFORMANCE.value in includes:
            context.params[0].situation_param[AvailableSituations.UNIT_PERFORMANCE].weights = {
                sel: 1 / len(context.params[0].situation_param[AvailableSituations.UNIT_PERFORMANCE].weights)
                for sel in context.params[0].situation_param[AvailableSituations.UNIT_PERFORMANCE].weights
            }
        extended_guides = {}
        df_neg, df_pos, situation_entity_selection = build_dataframes(context, guides, log, oc_data, local=True)
        descriptive_features = df_pos.columns.to_list()
        classifiers = {}
        results = {}
        for detector in detectors:
            all_sit = []
            antis = {}
            if len(df_pos) > 0:
                guide_positive(all_sit, antis, classifiers, descriptive_features, detector, df_pos, log, results,
                               situation_entity_selection)

            # Negative Guidance
            if len(df_neg) > 0:
                guide_negative(all_sit, antis, df_neg, situation_entity_selection)
            all_sit = add_includes(all_sit, context, includes)
            entities = set()
            situations = set()
            sit_sel = {}
            for entity, sit, sel, c in all_sit:
                entities.add(entity)
                if sit not in situations:
                    sit_sel[sit] = [sel]
                else:
                    sit_sel[sit].append(sel)
                situations.add(sit)
            init_events_context(oc_data, context, 0,
                                include_entity=lambda x: any([x is ent for ent in list(entities)]),
                                include_sit=lambda x: any([x is sit for sit in list(situations)]),
                                include_sit_sel=lambda sit, selection: selection in sit_sel[sit],
                                anti=antis,
                                backend=False,
                                detector=detector)
            init_log_events_context(oc_data, log, AGGREGATOR, 0, True, False, detector)
        log.timespan = context.timespan
        log.events_timeunits = context.events_timeunits
        log.granularity = list(context.context.keys())[0]
        log.methods_bool = methods
        log.norm_range = context.params[0].norm_range
        log.detector_thresholds = detector_thresholds
        for detector in AvailableDetectorsExt:
            if detector_shortcut(detector) in detectors:
                log.labels[detector_shortcut(detector)] = [
                    AvailableClassifications.N if tid in log.normal[detector_shortcut(detector)]
                    else AvailableClassifications.D for tid in log.traces]
        return log


    def assign_optimal_processor(clfs,
                                 params,
                                 new_acc_candidate,
                                 balanced_acc,
                                 variant):
        clfs[variant] = {'params': params,
                         'acc': new_acc_candidate,
                         'balanced_acc': balanced_acc}


    @celery.task(serializer='pickle')
    def compute_post_evaluation_experiment(detector_r, experiment_data_r, parameters_r):
        parameters = itertools.product(parameters_r, parameters_r)
        clfs = {'optimized': {},
                'balanced': {},
                'old_accuracy': {},
                'old_balanced': {},
                'all': {}}
        ca_y_true = [get_true_label(trace, detector_r)
                     for tid, trace in experiment_data_r.log_with_classification.items()]
        ca_y_pred = [label.value for label in experiment_data_r.log.labels[detector_r]]
        clfs['old_accuracy'] = accuracy_score(ca_y_true,
                                              ca_y_pred)
        clfs['old_balanced'] = balanced_accuracy_score(ca_y_true,
                                                       ca_y_pred)
        clfs['all'] = {'acc': {}, 'balanced_acc': {},
                       'precision': {}, 'recall': {}}
        for params in parameters:
            new_log = post_process(alpha_ps=params[0],
                                   alpha_ng=params[1],
                                   threshold=experiment_data_r.log.detector_thresholds[detector_r],
                                   log=experiment_data_r.log,
                                   detector=detector_r,
                                   variant=True)
            ca_y_pred = [label.value for label in new_log.labels[detector_r]]
            new_acc = accuracy_score(ca_y_true, ca_y_pred)
            new_bal_acc = balanced_accuracy_score(ca_y_true, ca_y_pred)
            clfs['all']['acc'][params] = new_acc
            clfs['all']['balanced_acc'][params] = new_bal_acc
            if new_acc > clfs['old_accuracy']:
                if 'params' not in clfs['optimized']:
                    assign_optimal_processor(clfs=clfs,
                                             params=params,
                                             new_acc_candidate=new_acc,
                                             balanced_acc=new_bal_acc,
                                             variant='optimized')
                else:
                    if new_acc > clfs['optimized']['acc']:
                        assign_optimal_processor(clfs=clfs,
                                                 params=params,
                                                 new_acc_candidate=new_acc,
                                                 balanced_acc=new_bal_acc,
                                                 variant='optimized')
                    else:
                        pass
            if new_bal_acc > clfs['old_balanced']:
                if 'params' not in clfs['balanced']:
                    assign_optimal_processor(clfs=clfs,
                                             params=params,
                                             new_acc_candidate=new_acc,
                                             balanced_acc=new_bal_acc,
                                             variant='balanced')
                else:
                    if new_bal_acc > clfs['balanced']['balanced_acc']:
                        assign_optimal_processor(clfs=clfs,
                                                 params=params,
                                                 new_acc_candidate=new_acc,
                                                 balanced_acc=new_bal_acc,
                                                 variant='balanced')
                    else:
                        pass
        return clfs

if __name__ == '__main__':
    celery.worker_main()
