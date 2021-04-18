from datetime import datetime, date
from math import ceil, floor

import dash
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
import numpy as np
from backend.param.interpretations import single_trace_interpretation, aggregate_interpretation
from backend.tasks.tasks import get_remote_data
from flask import request

# https://dash.plotly.com/layout
from subprocess import check_call
from backend.app import app
import dash_table
import pandas as pd
from backend.components.graphs import generate_causal_graph, generate_post_graph
from backend.components.misc import inspect_trace_button, log_header, use_log_button, tab_id, \
    interpretation_trace_button
from backend.param.available import AvailableDetectorsExt, extract_title, detector_shortcut, get_available_from_name, \
    extract_extension, AvailableSituationsExt
from backend.param.colors import SECONDARY_VERY_LIGHT, SECONDARY, INTRINSIC_COLOR_LIGHT, INTRINSIC_COLOR_VERY_LIGHT, \
    NORMAL_COLOR_VERY_LIGHT, NORMAL_COLOR_LIGHT
from backend.param.constants import RESULT_TITLE, TOP_KEY, DP, SUMMARY_KEY, NA, CONTEXT_KEY
from backend.param.styles import act_style, TABLE_ROW_STYLE, HTML_TABLE_CELL_STYLE, NO_DISPLAY
from backend.util import write_global_signal_value, display_time
from contect.available.available import AvailableClassifications, AvailableDetectors, AvailableSituationType, \
    AvailableTasks, AvailableSelections, AvailableGranularity
from contect.available.constants import SITUATION_KEY, ANTI_KEY, ENTITY_KEY, HOURS_IN_DAY, SITUATION_AGG_KEY
from contect.parsedata.objects.exporter.exporter import export_to_pm4py, TID_KEY, EVENTS_KEY, COLOR_KEY, ACT_KEY, \
    export_log_to_dict, export_logs_to_dict, TIMESTAMP_KEY, export_trace_to_dataframe, \
    export_oc_data_events_to_dataframe, export_trace_to_dict, POSITIVE_KEY, NEGATIVE_KEY, SCORE_KEY, VALUES_KEY, \
    OBJECTS_KEY, CA_SCORE_KEY, PS_ALPHA_KEY, NG_ALPHA_KEY, get_required_ps, get_required_ng
from contect.parsedata.objects.oclog import Trace, ObjectCentricLog


def generate_table_from_df(dataframe, max_rows=10):
    return html.Table([
        html.Thead(
            html.Tr([html.Th(col) for col in dataframe.columns])
        ),
        html.Tbody([
            html.Tr([
                html.Td(dataframe.iloc[i][col]) for col in dataframe.columns
            ]) for i in range(min(len(dataframe), max_rows))
        ])
    ])


def generate_log_statistics(log):
    from pm4py.statistics.traces.log import case_statistics
    from pm4py.statistics.traces.log import case_arrival
    from pm4py.statistics.start_activities.log.get import get_start_activities
    from pm4py.statistics.end_activities.log.get import get_end_activities
    from pm4py.algo.filtering.log.attributes import attributes_filter as log_attributes_filter
    import pandas as pd
    pm4py_log = export_to_pm4py(log)
    # Time
    median_case_duration = case_statistics.get_median_caseduration(pm4py_log, parameters={
        case_statistics.Parameters.TIMESTAMP_KEY: TIMESTAMP_KEY.title()
    })
    case_dispersion_ratio = case_arrival.get_case_dispersion_avg(pm4py_log, parameters={
        case_arrival.Parameters.TIMESTAMP_KEY: TIMESTAMP_KEY.title()})
    case_number = len(log.traces)
    case_metrics = {'Log Size': case_number,
                    '# Events': len(log.event_to_traces),
                    'Median Trace Duration': display_time(median_case_duration, 4),
                    'Average Trace Arrival': display_time(case_dispersion_ratio, 4)}
    df_case_metrics = pd.DataFrame(case_metrics, index=[0])
    table_case_metrics = create_data_table(None, df_case_metrics, None, len(df_case_metrics))

    # Determine statistics for variants counts
    variants_count = case_statistics.get_variant_statistics(pm4py_log)
    variants_count = sorted(variants_count, key=lambda x: x['count'], reverse=True)
    average_trace_len = sum(
        [len(trace['variant'].split(',')) * trace['count'] for trace in variants_count]) / case_number
    df_variants_count = pd.DataFrame(variants_count)
    variants_table = create_data_table(None, df_variants_count, None, 10)

    # Start and end
    start_activities = get_start_activities(pm4py_log)
    start_activities = {k: v for k, v in sorted(start_activities.items(), key=lambda item: item[1], reverse=True)}
    df_start_activities = pd.DataFrame(start_activities, index=[0])
    table_start_activities = create_data_table(None, df_start_activities, None, len(df_start_activities))
    end_activities = get_end_activities(pm4py_log)
    end_activities = {k: v for k, v in sorted(end_activities.items(), key=lambda item: item[1], reverse=True)}
    df_end_activities = pd.DataFrame(end_activities, index=[0])
    table_end_activities = create_data_table(None, df_end_activities, None, len(df_end_activities))

    # Activity frequencies
    act_freq = log_attributes_filter.get_attribute_values(pm4py_log, "concept:name")
    act_freq = {k: v for k, v in sorted(act_freq.items(), key=lambda item: item[1], reverse=True)}
    df_act_freq = pd.DataFrame(act_freq, index=[0])
    act_freq_table = create_data_table(None, df_act_freq, None, len(df_act_freq))
    return [
        html.H3('Log Statistics'),
        html.H4('Top 10 Most Frequent Trace Variants'),
        variants_table,
        html.Br(),
        html.H4('Trace Metrics'),
        table_case_metrics,
        html.Br(),
        html.H4('Activity Statistics'),
        html.H5('Activity Frequencies'),
        act_freq_table,
        html.Br(),
        html.H5('Start Activities'),
        table_start_activities,
        html.Br(),
        html.H5('End Activities'),
        table_end_activities,
        html.Br()
    ]


def generate_log_output(log, log_hash, task_id, method, multiple):
    if multiple:
        log_exports = export_logs_to_dict(log)
        return [
            html.Div(

                log_header('Log from Object Path Combination ' + log_name) +
                use_log_button(write_global_signal_value([log_name, log_hash, task_id, method])) +
                generate_log_statistics(log[log_name]) +
                [html.H3('Log Preview'),
                 html.Br()] +
                generate_table_from_log(log_exports[log_name], log_hash, task_id, log_name) +
                [html.Br()]
            )
            for log_name in log_exports]
    else:
        log_export = export_log_to_dict(log)
        return log_header('Log from Event Correlation ' + method) + \
               use_log_button(write_global_signal_value([log_hash, task_id, method])) + \
               generate_log_statistics(log) + \
               [html.H3('Log Preview'),
                html.Br()] + \
               generate_table_from_log(log_export, log_hash, task_id)


def causal_graph_name(detector, version):
    username = request.authorization['username']
    return f'{extract_title(detector)}_causal.{username}.{version}'


def post_graph_name(detector, version):
    username = request.authorization['username']
    return f'{extract_title(detector)}_post.{username}.{version}'


def trace_detector_summary(det, trace, log, post):
    detector = get_available_from_name(extract_title(det), AvailableDetectors.PROF, AvailableDetectors)
    old_label = AvailableClassifications.N.value if trace.id in log.normal[
        detector] else AvailableClassifications.D.value
    asset_dir = './assets/'
    ng = AvailableSituationType.NEGATIVE
    ps = AvailableSituationType.POSITIVE
    if post:
        classical, negative, positive = generate_post_variables(detector, log, old_label, post, trace)
        dp = DP
        causal_graph = generate_causal_graph(positive,
                                             classical,
                                             negative,
                                             True,
                                             post)
        post_graph = generate_post_graph(positive,
                                         detector,
                                         negative,
                                         round(trace.score[detector], dp),
                                         round(trace.ca_score[detector], dp),
                                         log.labels[detector][trace.id],
                                         round(log.detector_thresholds[detector], dp),
                                         old_label,
                                         round(log.ca_degrees[detector][
                                                   ps], dp),
                                         round(log.ca_degrees[detector][
                                                   ng], dp),
                                         round(trace.complex_context[detector][ps], dp),
                                         round(trace.complex_context[detector][ng], dp))

        causal_dot = f'{asset_dir}{causal_graph_name(det, "dot")}'
        post_dot = f'{asset_dir}{post_graph_name(det, "dot")}'
        causal_graph.write(causal_dot)
        post_graph.write(post_dot)
        causal_name = causal_graph_name(det, "png")
        post_name = post_graph_name(det, "png")
        check_call(['neato', '-Tpng', causal_dot, '-o', f'{asset_dir}{causal_name}'])
        check_call(['neato', '-Tpng', post_dot, '-o', f'{asset_dir}{post_name}'])
        return [
                   html.Br(),
                   html.H2('Causal Model'),
                   dbc.Row(
                       dbc.Col(
                           html.Img(src=app.get_asset_url(causal_name))
                       )),
                   html.Br(),
                   html.H2('Post-Processing Visualization'),
                   dbc.Row(
                       dbc.Col(
                           html.Img(src=app.get_asset_url(post_name))
                       )),
                   html.Br(),
                   html.H2('General Interpretations'),
                   html.Br()
               ] + add_interpretations(det, trace, log) + [
                   html.Br(),
                   html.H2('Detailed Interpretations for Trace Context'),
                   html.Br()
               ] + generate_interpretation_for_trace(end=str(trace.events[0].time),
                                                     jobs=None,
                                                     log_hash=None,
                                                     ng_ctx_val=round(trace.complex_context[detector][ng], DP),
                                                     ps_ctx_val=round(trace.complex_context[detector][ps], DP),
                                                     start=str(trace.events[-1].time),
                                                     tid=trace.id,
                                                     det=det,
                                                     log=log)
    else:
        positive = []
        negative = []
        classical = [
            f'{detector.value} detected a score of {round(trace.score[detector], DP)} resulting in class {old_label}'
            if not post else
            f'{detector.value} detected a score of {round(trace.score[detector], DP)} and is post-processed by context-awareness to a CA score of {round(trace.ca_score[detector], DP)} resulting in class {log.labels[detector][trace.id].value}'
        ]
        causal_graph = generate_causal_graph(positive,
                                             classical,
                                             negative,
                                             True,
                                             post)
        causal_dot = f'{asset_dir}{causal_graph_name(det, "dot")}'
        causal_graph.write(causal_dot)
        causal_name = causal_graph_name(det, "png")
        check_call(['neato', '-Tpng', causal_dot, '-o', f'{asset_dir}{causal_name}'])
        return [
                   html.Br(),
                   html.H2('Causal Model'),
                   dbc.Row(
                       dbc.Col(
                           html.Img(src=app.get_asset_url(causal_name))
                       )),
                   html.Br(),
                   html.H2('General Interpretations'),
                   html.Br()
               ] + add_interpretations(det, trace, log) + [
                   html.Br(),
                   html.H2('Detailed Interpretations for Trace Context'),
                   html.Br()
               ] + generate_interpretation_for_trace(end=str(trace.events[0].time),
                                                     jobs=None,
                                                     log_hash=None,
                                                     ng_ctx_val=round(trace.complex_context[detector][ng], DP),
                                                     ps_ctx_val=round(trace.complex_context[detector][ps], DP),
                                                     start=str(trace.events[-1].time),
                                                     tid=trace.id,
                                                     det=det,
                                                     log=log)


def generate_post_variables(detector, log, old_label, post, trace):
    ps = AvailableSituationType.POSITIVE
    positive = [
        f'{situation.value} has value {round(np.average([trace.rich_context[detector][ps][situation][selection][SITUATION_KEY] for selection in trace.rich_context[detector][ps][situation]]), DP)}'
        for situation in trace.rich_context[detector][ps]]
    ng = AvailableSituationType.NEGATIVE
    negative = [
        f'{situation.value} has value {round(np.average([trace.rich_context[detector][ng][situation][selection][SITUATION_KEY] for selection in trace.rich_context[detector][ng][situation]]), DP)}'
        for situation in trace.rich_context[detector][ng]]
    classical = [
        f'{detector.value} detected a score of {round(trace.score[detector], DP)} resulting in class {old_label}'
        if not post else
        f'{detector.value} detected a score of {round(trace.score[detector], DP)} and is post-processed by context-awareness to a CA score of {round(trace.ca_score[detector], DP)} resulting in class {log.labels[detector][trace.id].value}'
    ]
    return classical, negative, positive


def add_interpretations(det, trace, log):
    detector = get_available_from_name(extract_title(det), AvailableDetectors.PROF, AvailableDetectors)
    situations = [(sit, typ, sel) for typ in trace.rich_context[detector]
                  for sit in trace.rich_context[detector][typ]
                  for sel in trace.rich_context[detector][typ][sit]]
    return [
        html.Div(
            [
                html.H3(f'{sit.value.title()} {sel.value.title()} - Interpretation'),
                html.Br(),
                dcc.Markdown(extract_extension(get_available_from_name(sit.value,
                                                                       AvailableSituationsExt.UNIT_PERFORMANCE,
                                                                       AvailableSituationsExt)).interpretation_single(
                    anti=trace.rich_context[detector][typ][sit][sel][ANTI_KEY],
                    unit=log.granularity.value,
                    val='x',
                    rng=log.norm_range,
                    sel=sel.value.lower()
                ))
            ]
        )
        for sit, typ, sel in situations
    ]


def add_daily_interpretations(det, trace, log, jobs, log_hash):
    daily_contexts, detector, event_to_traces, granularity, ng, ng_agg_daily_contexts, objects, ps, ps_agg_daily_contexts, rng, vmap_params = get_context_data(
        jobs, log_hash, det)
    # Positive Aggregate
    events_timeunits = log.events_timeunits
    interpretations = []
    tus = {events_timeunits[granularity][event.id]
           if granularity is AvailableGranularity.DAY
           else floor(events_timeunits[granularity][event.id] / HOURS_IN_DAY): event.time
           for event in trace.events}
    for tu in tus:
        dt = tus[tu]
        d = str(date(dt.year, dt.month, dt.day))
        # tu -= 1
        interpretations += [
            html.H3(f'Aggregate Context Details & Interpretations for {d}'),
            html.Br()
        ]
        interpretations += [
            html.H4(f'Positive'),
            html.Br()
        ]
        ctx_val, event_table, inspect_trace_buttons = generate_agg_context_interpretations(ps_agg_daily_contexts,
                                                                                           detector,
                                                                                           event_to_traces,
                                                                                           log_hash,
                                                                                           objects,
                                                                                           tu,
                                                                                           vmap_params)
        interpretations += aggregate_interpretation(ctx_val, d, event_table, inspect_trace_buttons) + [html.Br()]
        interpretations += [html.H4(f'Negative'),
                            html.Br()]
        ctx_val, event_table, inspect_trace_buttons = generate_agg_context_interpretations(ng_agg_daily_contexts,
                                                                                           detector,
                                                                                           event_to_traces,
                                                                                           log_hash,
                                                                                           objects,
                                                                                           tu,
                                                                                           vmap_params)
        interpretations += aggregate_interpretation(ctx_val, d, event_table, inspect_trace_buttons) + [html.Br()]
        interpretations += [
            html.H4(f'Context Details & Interpretations for {d}'),
            html.Br(),
            html.H3('Positive'),
            html.Br()
        ]
        for sit in trace.rich_context[detector][ps]:
            complex_sit = get_available_from_name(sit.value,
                                                  AvailableSituationsExt.UNIT_PERFORMANCE,
                                                  AvailableSituationsExt)
            for sel in trace.rich_context[detector][ps][sit]:
                anti = daily_contexts[detector][ps][sit][sel][tu][ANTI_KEY]
                ctx_value, entity_table, event_table, inspect_trace_buttons, interpreter = generate_detailed_interpreter(
                    anti, daily_contexts, detector, event_to_traces, log_hash, objects, sit, tu, ps,
                    vmap_params,
                    complex_sit, sel)
                interpretations += [
                    html.H4(f'{sit.value} {sel.value}'),
                    html.Br()
                ]
                interpretations += interpreter(rng,
                                               d,
                                               sel.value,
                                               granularity.value,
                                               ctx_value,
                                               event_table,
                                               inspect_trace_buttons,
                                               entity_table)
        for sit in trace.rich_context[detector][ng]:
            complex_sit = get_available_from_name(sit.value,
                                                      AvailableSituationsExt.UNIT_PERFORMANCE,
                                                      AvailableSituationsExt)
            for sel in trace.rich_context[detector][ng][sit]:
                anti = daily_contexts[detector][ng][sit][sel][tu][ANTI_KEY]
                ctx_value, entity_table, event_table, inspect_trace_buttons, interpreter = generate_detailed_interpreter(
                    anti, daily_contexts, detector, event_to_traces, log_hash, objects, sit, tu, ng,
                    vmap_params,
                    complex_sit, sel)
                interpretations += [
                    html.H4(f'{sit.value} {sel.value}'),
                    html.Br()
                ]
                interpretations += interpreter(rng,
                                               d,
                                               sel.value,
                                               granularity.value,
                                               ctx_value,
                                               event_table,
                                               inspect_trace_buttons,
                                               entity_table)
    return interpretations


def trace_details_tab_layout(det, trace, log, jobs, log_hash):
    detector = get_available_from_name(extract_title(det), AvailableDetectors.PROF, AvailableDetectors)
    ps = AvailableSituationType.POSITIVE
    ng = AvailableSituationType.NEGATIVE
    threshold = log.detector_thresholds[detector]
    round_n = 4
    if trace.id in log.labels:
        label = log.labels[trace.id]
    else:
        label = AvailableClassifications.N if trace.id in log.normal[
            detector] else AvailableClassifications.D
    df = export_trace_to_dataframe(trace, log, True, detector)
    # cols = [EID_KEY, ACT_KEY, TIMESTAMP_KEY, POSITIVE_KEY, NEGATIVE_KEY, ]
    return [
               html.Br(),
               html.H2('Trace Results'),
               html.Table(
                   [
                       html.Thead(
                           html.Tr(
                               [
                                   html.Th(col) for col in
                                   ['TraceID', 'Class', 'Score', 'Threshold', 'CA Score', 'Positive Context',
                                    'Required Degree Ps',
                                    'Negative Context', 'Required Degree Ng']
                               ])
                       ),
                       html.Tbody(
                           [
                               html.Tr(
                                   [html.Td(trace.id,
                                            style=dict(width=10))] +
                                   [html.Td(label.value,
                                            style=dict(width=10))] +
                                   [html.Td(round(trace.score[detector], DP),
                                            style=dict(width=12))] +
                                   [html.Td(round(threshold, DP),
                                            style=dict(width=12))] +
                                   [html.Td(round(trace.ca_score[detector], DP) if detector in trace.ca_score else 'na',
                                            style=dict(width=12))] +
                                   [html.Td(round(trace.complex_context[detector][ps], DP),
                                            style=dict(width=12))] +
                                   [html.Td(get_required_ps(detector, label, round_n, threshold, trace),
                                            style=dict(width=12))] +
                                   [html.Td(round(trace.complex_context[detector][ng], DP),
                                            style=dict(width=12))] +
                                   [html.Td(get_required_ng(detector, label, round_n, threshold, trace),
                                            style=dict(width=12))]
                               )
                           ]
                       )
                   ]),
               html.Br(),
               html.H2('Events'),
               create_data_table(None, df, None, len(df)),
               html.Br(),
               html.H2('General Interpretations'),
               html.Br()
           ] + add_interpretations(det, trace, log) + [
               html.Br(),
               html.H2('Daily Context Details & Interpretations'),
               html.Br()
           ] + add_daily_interpretations(det, trace, log, jobs, log_hash)


def trace_prefix(trace):
    return f'{trace.id}-trace-'


def trace_detector_tab_layout(detector, trace, log, post=False, generate=False, jobs=None, log_hash=None):
    detector_title = extract_title(detector)
    if generate:
        return [
            dbc.Tabs([
                dbc.Tab(trace_detector_summary(detector, trace, log, post),
                        label=detector_title + ' - ' + 'Overview',
                        tab_id=tab_id(trace_prefix(trace) + detector_title + '-overview')),
                dbc.Tab(trace_details_tab_layout(detector, trace, log, jobs, log_hash),
                        label=detector_title + ' - ' + 'Details',
                        tab_id=tab_id(trace_prefix(trace) + detector_title + '-details')),
            ],
                id=tab_id(trace_prefix(trace) + detector_title))
        ]
    else:
        return []


def trace_summary(trace: Trace, log: ObjectCentricLog):
    if len(log.labels) == 0:
        detectors_deviating = ', '.join([detector.value
                                         for detector in AvailableDetectors
                                         if detector in log.deviating and
                                         trace.id in log.deviating[detector]
                                         ])
        detectors_all_deviating = detectors_deviating
        detectors_ca_deviating = ''
        detectors_normal = ', '.join([detector.value
                                      for detector in AvailableDetectors
                                      if detector in log.normal and
                                      trace.id in log.normal[detector]])
        detectors_all_normal = detectors_normal
        detectors_ca_normal = ''
    else:
        detectors_deviating = ', '.join([detector.value
                                         for detector in AvailableDetectors
                                         if detector in log.labels and
                                         log.labels[detector][trace.id] is AvailableClassifications.D
                                         ])
        detectors_ca_deviating = ', '.join([detector.value
                                            for detector in AvailableDetectors
                                            if detector in log.labels and
                                            log.labels[detector][trace.id] is AvailableClassifications.CAD
                                            ])
        detectors_all_deviating = f'{detectors_deviating}, {detectors_ca_deviating}'

        detectors_normal = ', '.join([detector.value
                                      for detector in AvailableDetectors
                                      if detector in log.labels and
                                      log.labels[detector][trace.id] is AvailableClassifications.N
                                      ])
        detectors_ca_normal = ', '.join([detector.value
                                         for detector in AvailableDetectors
                                         if detector in log.labels and
                                         log.labels[detector][trace.id] is AvailableClassifications.CAN
                                         ])
        detectors_all_normal = f'{detectors_normal}, {detectors_ca_normal}'
    events_n = len(trace.events)
    start = trace.events[0].time
    end = trace.events[-1].time
    period = display_time((end - start).seconds, 4)
    return html.Div(
        [
            html.H2('Summary'),
            html.Br(),
            create_data_table(None,
                              pd.DataFrame(
                                  {'# Events': [events_n],
                                   '# Start': [start],
                                   '# End': [end],
                                   '# Time Period': [period],
                                   'Detectors All Deviating': [detectors_all_deviating],
                                   'Detectors Deviating': [detectors_deviating],
                                   'Detectors CA-Deviating': [detectors_ca_deviating],
                                   'Detectors All Normal': [detectors_all_normal],
                                   'Detectors Normal': [detectors_normal],
                                   'Detectors CA-Normal': [detectors_ca_normal]
                                   },
                                  index=[0]),
                              None,
                              1)
        ]
    )


def generate_trace_output(trace, log, result=False, jobs=None, log_hash=None):
    if not result:
        df = export_trace_to_dataframe(trace, log, result)
        table_trace = create_data_table(None, df, None, len(df))
        return [
            html.H2("Events"),
            table_trace
        ]
    else:
        return [
            trace_summary(trace, log),
            html.Br(),
            dbc.Tabs(
                [
                    dbc.Tab(trace_detector_tab_layout(detector,
                                                      trace,
                                                      log,
                                                      True if detector_shortcut(detector) in log.traces[0].ca_score
                                                      else False,
                                                      True if detector_shortcut(detector) in log.detector_thresholds
                                                      else False,
                                                      jobs,
                                                      log_hash) if detector_shortcut(
                        detector) in log.detector_thresholds else html.Div(style=NO_DISPLAY),
                            label=extract_title(detector),
                            tab_id=extract_title(detector),
                            id=trace_prefix(trace) + 'extract_title(detector)',
                            disabled=True if detector_shortcut(detector) not in log.detector_thresholds else False)
                    for detector in AvailableDetectorsExt
                ],
                id=trace_prefix(trace) + '-results-tabs'
            )
        ]


def generate_table_from_log(log_export, log_hash, task_id, log_name=''):
    return [html.Table([
        html.Thead(
            html.Tr([html.Th(col) for col in ['TraceID', 'Events', '']], style=TABLE_ROW_STYLE)
        ),
        html.Tbody([
            html.Tr(
                [html.Td(log_export[tid][TID_KEY])] +
                [html.Td(
                    html.Div([html.Div([html.Div(style=act_style(event[COLOR_KEY])),
                                        event[ACT_KEY]], style=HTML_TABLE_CELL_STYLE) if index != 7 else
                              html.Div("...", style=HTML_TABLE_CELL_STYLE) if len(log_export[tid][EVENTS_KEY]) > 7 else
                              html.Div([html.Div(style=act_style(event[COLOR_KEY])),
                                        event[ACT_KEY]], style=HTML_TABLE_CELL_STYLE)
                              for index, event in enumerate(log_export[tid][EVENTS_KEY]) if index <= 7],
                             style={'overflow': 'hidden'})
                )] +
                [html.Td(inspect_trace_button(write_global_signal_value([log_name, log_hash, task_id, str(tid)])))]
                , style=TABLE_ROW_STYLE)
            for tid in range(len(log_export)) if tid <= 20]
        )
    ], style=TABLE_ROW_STYLE)]


def get_background_color(label):
    if label is AvailableClassifications.D:
        return INTRINSIC_COLOR_VERY_LIGHT
    elif label is AvailableClassifications.CAD:
        return INTRINSIC_COLOR_LIGHT
    elif label is AvailableClassifications.N:
        return NORMAL_COLOR_VERY_LIGHT
    else:
        return NORMAL_COLOR_LIGHT


def generate_trace_summary_table(traces, detector, log_hash, vmap_params, details=False, objects=None, threshold=None,
                                 labels=None, target=None):
    trace_export = [export_trace_to_dict(trace, False, detector, vmap_params, objects, threshold, labels) for trace in
                    traces]

    def details_simple(event):
        return dcc.Markdown(f'**Act**: {event[ACT_KEY]} \n'
                            f'**Pos Ctx**: {event[POSITIVE_KEY]} \n'
                            f'**Neg Ctx**: {event[NEGATIVE_KEY]}\n'
                            f'**Time**: {event[TIMESTAMP_KEY]}',
                            style={"white-space": "pre"})

    def details_all(event):
        return dcc.Markdown(f'**Act**: {event[ACT_KEY]} \n'
                            f'**Pos Ctx**: {event[POSITIVE_KEY]} \n'
                            f'**Neg Ctx**: {event[NEGATIVE_KEY]}\n'
                            f'**Time**: {event[TIMESTAMP_KEY]}\n'
                            f'**Object Types**: {event[OBJECTS_KEY]}\n'
                            f'{event[VALUES_KEY]}',
                            style={"white-space": "pre"})

    display_n = 3
    return [html.Table([
        html.Thead(
            html.Tr([html.Th(col) for col in
                     ['Top', 'TraceID', 'Score', 'CA Score', 'Positive Context', 'Required Degree Ps',
                      'Negative Context', 'Required Degree Ng', 'Events', '']],
                    style=TABLE_ROW_STYLE)
        ),
        html.Tbody([
            html.Tr(
                [html.Td(i + 1,
                         style=dict(width=10))] +
                [html.Td(
                    html.Div(
                        [
                            trace[TID_KEY],
                            interpretation_trace_button(write_global_signal_value([RESULT_TITLE,
                                                                                   log_hash,
                                                                                   str(trace[TID_KEY]),
                                                                                   str(trace[POSITIVE_KEY]),
                                                                                   str(trace[NEGATIVE_KEY]),
                                                                                   str(trace[EVENTS_KEY][0][
                                                                                           TIMESTAMP_KEY]),
                                                                                   str(trace[EVENTS_KEY][-1][
                                                                                           TIMESTAMP_KEY])
                                                                                   ]),
                                                        target)
                        ]
                    ),
                    style=dict(width=8))] +
                [html.Td(trace[SCORE_KEY],
                         style=dict(width=12))] +
                [html.Td(trace[CA_SCORE_KEY],
                         style=dict(width=12))] +
                [html.Td(trace[POSITIVE_KEY],
                         style=dict(width=12))] +
                [html.Td(trace[PS_ALPHA_KEY],
                         style=dict(width=12))] +
                [html.Td(trace[NEGATIVE_KEY],
                         style=dict(width=12))] +
                [html.Td(trace[NG_ALPHA_KEY],
                         style=dict(width=12))] +
                [html.Td(
                    html.Div([html.Div([html.Div(style=act_style(event[COLOR_KEY])),
                                        details_simple(event) if not details else details_all(event)],
                                       style=HTML_TABLE_CELL_STYLE) if index != display_n else
                              html.Div("...", style=HTML_TABLE_CELL_STYLE) if len(trace[EVENTS_KEY]) > display_n else
                              html.Div([html.Div(style=act_style(event[COLOR_KEY])),
                                        details_simple(event) if not details else details_all(event)],
                                       style=HTML_TABLE_CELL_STYLE)
                              for index, event in enumerate(trace[EVENTS_KEY]) if index <= display_n],
                             style={'overflow': 'hidden'})
                )] +
                [html.Td(inspect_trace_button(write_global_signal_value([RESULT_TITLE,
                                                                         log_hash,
                                                                         str(trace[TID_KEY]),
                                                                         str(datetime.now())
                                                                         ]),
                                              version=False,
                                              result=TOP_KEY
                                              )
                         )

                 ]
                , style={**TABLE_ROW_STYLE,
                         **{'background-color': get_background_color(labels[trace[TID_KEY]])}})
            for i, trace in enumerate(trace_export)]
        )
    ], style=TABLE_ROW_STYLE)]


def create_data_table(date, df, name, rows, header_color=SECONDARY, header_weight='bold', minWidth='180px',
                      maxWidth='180px',
                      width='180px'):
    if name is not None:
        header = [html.H5(name),
                  html.H6(date)]
    else:
        header = []
    return html.Div(header + [
        dash_table.DataTable(
            style_table={'overflowX': 'auto'},
            style_cell={
                'height': 'auto',
                # all three widths are needed
                'minWidth': minWidth, 'width': width, 'maxWidth': maxWidth,
                'whiteSpace': 'normal',
                'textAlign': 'left',
                'textOverflow': 'ellipsis'
            },
            data=df[:rows].to_dict('records'),
            columns=[{'name': i, 'id': i} for i in df.columns],
            css=[{
                'selector': '.dash-spreadsheet td div',
                'rule': '''
                            line-height: 15px;
                            max-height: 30px; min-height: 30px; height: 30px;
                            display: block;
                            overflow-y: hidden;
                        '''
            }],
            tooltip_data=[
                {
                    column: {'value': str(value), 'type': 'markdown'}
                    for column, value in row.items()
                } for row in df.to_dict('records')
            ],
            tooltip_duration=None,
            style_as_list_view=True,
            style_data_conditional=[
                {
                    'if': {'row_index': 'odd'},
                    'backgroundColor': SECONDARY_VERY_LIGHT
                }
            ],
            style_header={
                'backgroundColor': header_color,
                'fontWeight': header_weight,
                'color': 'white' if header_color == SECONDARY else 'black'
            }
        ),
    ])


def create_oc_data_dfs(oc_data):
    meta = oc_data.meta
    # Unfortunately, need to fix it this way, since in Celery only
    df_acts = pd.DataFrame(columns=list(meta.acts))
    df_ots = pd.DataFrame(columns=meta.obj_types)
    # df_act_ot = pd.DataFrame(meta.act_obj)
    df_vals = pd.DataFrame(columns=meta.attr_names)
    df_valt = pd.DataFrame(columns=meta.attr_types)
    df_valtt = pd.DataFrame(meta.attr_typ, index=[0])
    df_act_val = pd.DataFrame(meta.act_attr)
    df_events = export_oc_data_events_to_dataframe(oc_data.raw.events, oc_data.raw.objects, rows=20)
    if len(meta.ress) > 0:
        df_res = pd.DataFrame(columns=list(meta.ress))
        res_out = [html.H3('Resources'),
                   create_data_table(None, df_res, None, len(df_res), SECONDARY_VERY_LIGHT, 'medium')]
    else:
        res_out = dash.no_update
    if len(meta.locs) > 0:
        df_loc = pd.DataFrame(columns=list(meta.locs))
        loc_out = [html.H3('Locations'),
                   create_data_table(None, df_loc, None, len(df_loc), SECONDARY_VERY_LIGHT, 'medium')]
    else:
        loc_out = dash.no_update
    return df_act_val, df_acts, df_ots, df_vals, df_valt, df_valtt, loc_out, meta, res_out, df_events


def generate_interpretation_for_trace(end, jobs, log_hash, ng_ctx_val, ps_ctx_val, start, tid, det, log=None):
    if log is None:
        user = request.authorization['username']
        log = get_remote_data(user, log_hash, jobs, AvailableTasks.GUIDE.value)
        button = inspect_trace_button(write_global_signal_value([RESULT_TITLE,
                                                                 log_hash,
                                                                 str(tid),
                                                                 str(datetime.now())
                                                                 ]),
                                      suffix=f'trace {tid}',
                                      version=False,
                                      result=SUMMARY_KEY
                                      )
    else:
        button = []
    trace = log.traces[tid]
    detector = detector_shortcut(det)
    ps = AvailableSituationType.POSITIVE
    ng = AvailableSituationType.NEGATIVE
    ps_context_table = generate_trace_context_table(detector,
                                                    ps,
                                                    trace,
                                                    log.granularity.value,
                                                    log.norm_range)
    ng_context_table = generate_trace_context_table(detector,
                                                    ng,
                                                    trace,
                                                    log.granularity.value,
                                                    log.norm_range)
    interpretation = single_trace_interpretation(ps_ctx_val,
                                                 ng_ctx_val,
                                                 start,
                                                 end,
                                                 tid,
                                                 ps_context_table,
                                                 ng_context_table,
                                                 button)
    return interpretation


def generate_trace_context_table(detector, typ, trace, unit, rng):
    context_df = pd.DataFrame()
    ps_rich_context = trace.rich_context[detector][typ]
    single_interpretations = {
        sit: extract_extension(get_available_from_name(sit.value,
                                                       AvailableSituationsExt.UNIT_PERFORMANCE,
                                                       AvailableSituationsExt)).interpretation_single
        for sit in ps_rich_context
    }
    context_df['Maximum event contexts'] = [
        item for sublist in
        [
            [round(ps_rich_context[sit][sel][SITUATION_KEY], 4),
             single_interpretations[sit](
                 ps_rich_context[sit][sel][ANTI_KEY],
                 unit,
                 round(ps_rich_context[sit][sel][SITUATION_KEY], 4),
                 rng,
                 sel.value
             )]
            for sit in ps_rich_context
            for sel in ps_rich_context[sit]
        ]
        for item in sublist
    ]
    for event in trace.events:
        ps_event_rich_context = event.rich_context[detector][typ]
        context_df[f'Event {event.id}'] = [
            item for sublist in
            [
                [round(ps_event_rich_context[sit][sel][SITUATION_KEY], 4),
                 single_interpretations[sit](
                     ps_event_rich_context[sit][sel][ANTI_KEY],
                     unit,
                     round(ps_event_rich_context[sit][sel][SITUATION_KEY], 4),
                     rng,
                     sel.value
                 )]
                for sit in ps_rich_context
                for sel in ps_rich_context[sit]
            ]
            for item in sublist
        ]
    context_df.index = [
        item for sublist in
        [
            [f'{sit.value} {sel.value}',
             f'{sit.value} {sel.value} Help']
            for sit in ps_rich_context
            for sel in ps_rich_context[sit]
        ]
        for item in sublist
    ]
    context_df.reset_index(inplace=True)
    context_df.rename(columns={'index': 'Context'}, inplace=True)
    width = '60px'
    ps_context_table = create_data_table(None, context_df, None, len(context_df),
                                         minWidth=width,
                                         width=width,
                                         maxWidth=width)
    return ps_context_table


def get_context_data(jobs, log_hash, det):
    user = request.authorization['username']
    data = get_remote_data(user,
                           log_hash,
                           jobs,
                           AvailableTasks.CONTEXT_RESULT.value)
    added, daily_contexts, ng_agg_daily_contexts, ps_agg_daily_contexts, years, granularity, rng, event_to_traces, vmap_params, objects = data
    ps = AvailableSituationType.POSITIVE
    ng = AvailableSituationType.NEGATIVE
    detector = detector_shortcut(det)
    return daily_contexts, detector, event_to_traces, granularity, ng, ng_agg_daily_contexts, objects, ps, ps_agg_daily_contexts, rng, vmap_params


def generate_agg_context_interpretations(contexts, detector, event_to_traces, log_hash, objects, tu, vmap_params):
    try:
        values, events = zip(*contexts[detector][tu][1])
        event_table, inspect_trace_buttons = generate_events_table(events,
                                                                   event_to_traces,
                                                                   log_hash,
                                                                   objects,
                                                                   vmap_params,
                                                                   values)
        ctx_val = contexts[detector][tu][0]
        return ctx_val, event_table, inspect_trace_buttons
    except KeyError:
        return 'na', html.Br(), html.Br()



def generate_events_table(events, event_to_traces, log_hash, objects,
                          vmap_params, values):
    event_df = pd.DataFrame()
    sit_len = len(events)
    rows = ceil(sit_len / 12)
    row_indices = [r * 12 for r in range(rows + 2)]
    i = 0
    inspect_trace_buttons = []
    for index, event in enumerate(sorted(events,
                                         key=lambda item: item.time)):
        event_df[event.id] = [values[index],
                              event.act,
                              ','.join(list({objects[oid].type for oid in event.omap})),
                              event.vmap[vmap_params[AvailableSelections.RESOURCE]]
                              if AvailableSelections.RESOURCE in vmap_params else NA,
                              event.vmap[vmap_params[AvailableSelections.LOCATION]]
                              if AvailableSelections.LOCATION in vmap_params else NA,
                              event.time]
        if row_indices[i] <= index < row_indices[i + 1]:
            if index % 12 == 0:
                row_buttons = [dbc.Col(inspect_trace_button(write_global_signal_value([RESULT_TITLE,
                                                                                       log_hash,
                                                                                       str(event_to_traces[
                                                                                               event.id]),
                                                                                       str(datetime.now())]),
                                                            suffix=str(event.id),
                                                            version=False,
                                                            result=CONTEXT_KEY))]
            else:
                row_buttons.append(dbc.Col(inspect_trace_button(write_global_signal_value([RESULT_TITLE,
                                                                                           log_hash,
                                                                                           str(event_to_traces[
                                                                                                   event.id]),
                                                                                           str(
                                                                                               datetime.now())]),
                                                                suffix=str(event.id),
                                                                version=False,
                                                                result=CONTEXT_KEY)))
        else:
            i += 1
            inspect_trace_buttons.append(dbc.Row(row_buttons))
            row_buttons = [dbc.Col(inspect_trace_button(write_global_signal_value([RESULT_TITLE,
                                                                                   log_hash,
                                                                                   str(event_to_traces[
                                                                                           event.id]),
                                                                                   str(datetime.now())]),
                                                        suffix=str(event.id),
                                                        version=False,
                                                        result=CONTEXT_KEY))]
    remainder = sit_len % 12
    if remainder != 0:
        for i in range(12 - remainder):
            row_buttons.append(dbc.Col())
        inspect_trace_buttons.append(dbc.Row(row_buttons))
    event_df.index = ['Context', 'Activity', 'Object Types', 'Resource', 'Location', 'Date']
    event_df.reset_index(inplace=True)
    event_df.rename(columns={'index': 'EventID'}, inplace=True)
    width = '100px'
    event_table = create_data_table(None, event_df, None, len(event_df),
                                    minWidth=width,
                                    width=width,
                                    maxWidth=width)
    return event_table, inspect_trace_buttons


def generate_entity_table(daily_contexts, detector, typ, simple_sit, sel, tu):
    entities = daily_contexts[detector][typ][simple_sit][sel][tu][ENTITY_KEY]
    if isinstance(entities, list):
        entity_df = pd.DataFrame()
        subtract = None
        for index, entity in enumerate(entities):
            if entity is not None:
                if subtract is None:
                    subtract = entity.time - index
                    if entity.value is not None:
                        entity_df[str(entity.time - subtract) + ' h'] = [item
                                                                         for val, item in
                                                                         entity.value.items()]
                        entity_df.index = [k for k in entity.value]
                    else:
                        names = [f'{outerKey} / {innerKey}'
                                 for outerKey, innerDict in entity.nested_value.items()
                                 for innerKey, values in innerDict.items()]
                        entity_df[str(entity.time - subtract)] = [val
                                                                  for k, d in entity.nested_value.items()
                                                                  for k2, val in d.items()
                                                                  ]
                        entity_df.index = names
                else:
                    if entity.value is not None:
                        # Single
                        entity_df[str(entity.time - subtract) + ' h'] = [item
                                                                         for val, item in
                                                                         entity.value.items()]
                    else:
                        # Double
                        entity_df[str(entity.time - subtract) + ' h'] = [item
                                                                         for sel1, d in
                                                                         entity.nested_value.items()
                                                                         for sel2, item in
                                                                         entity.nested_value[sel1].items()]
    else:
        if entities.value is not None:
            # Single
            entity_df = pd.DataFrame()
            entity_df['Day'] = [item for val, item in entities.value.items()]
            entity_df.index = [k for k in entities.value]
        else:
            # Double
            reform = {(outerKey, innerKey): values
                      for outerKey, innerDict in entities.nested_value.items()
                      for innerKey, values in innerDict.items()}
            entity_df = pd.DataFrame(reform, index=['Day'])
            # entity_df.index = ['Day']
            entity_df = entity_df.T
    entity_df.reset_index(inplace=True)
    entity_df.rename(columns={'index': f'Selection {sel.value}'}, inplace=True)
    width = '60px'
    return create_data_table(None, entity_df, None, len(entity_df),
                             minWidth=width,
                             width=width,
                             maxWidth=width)


def generate_detailed_interpreter(anti, daily_contexts, detector, event_to_traces, log_hash, objects, simple_sit,
                                  tu, typ, vmap_params, sit, selection):
    if anti:
        interpreter = extract_extension(sit).interpretation_anti
    else:
        interpreter = extract_extension(sit).interpretation
    try:
        entity_table = generate_entity_table(daily_contexts, detector, typ, simple_sit, selection, tu)
        values, events = zip(*daily_contexts[detector][typ][simple_sit][selection][tu][SITUATION_KEY])
        event_table, inspect_trace_buttons = generate_events_table(events, event_to_traces,
                                                                   log_hash,
                                                                   objects, vmap_params,
                                                                   values)
        ctx_value = round(daily_contexts[detector][typ][simple_sit][selection][tu][SITUATION_AGG_KEY], 4)
        return ctx_value, entity_table, event_table, inspect_trace_buttons, interpreter
    except KeyError:
        return 'na', html.Br(), html.Br(), html.Br(), interpreter
