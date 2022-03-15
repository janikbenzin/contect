from collections import Counter
from copy import deepcopy
from datetime import datetime

import dash
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from backend.app import app
from backend.callbacks.callbacks import toast_context_help_callback, toast_summary_graph_callback, \
    toast_summary_list_callback
from backend.components.graphs import create_context_graphs
from backend.components.misc import container, global_signal_id_maker, temp_jobs_store_id_maker, \
    form_persistence_id_maker, tab_id, \
    global_form_load_signal_id_maker, toast_id, single_row, global_url_signal_id_maker, ps_context_tab_id, \
    ng_context_tab_id, container_id, graph_id, placeholder_id, tooltip_button, tooltip_button_id, modal_id, \
    global_refresh_signal_id_maker, result_details_toast_id
from backend.components.tables import create_data_table, generate_trace_summary_table, get_background_color
from backend.param.available import AvailableDetectorsExt, extract_title, AvailableSituationsExt, extract_extension, \
    sit_shortcut, detector_shortcut, AvailableTops
from backend.param.constants import CORR_TITLE, RESULT_TITLE, JOBS_KEY, GLOBAL_FORM_SIGNAL, RESULT_INIT, \
    TRACE_RESULT_SIGNAL, CB_TYPE_INSPECT, TRACE_URL, COLORSCALE, deviation_score, \
    positive_context, negative_context, deviating, tid_t, start_ts, end_ts, n_events, group_t, DEFAULT_TOP, \
    RESULT_POST, RESULT_URL, RESULT_INIT_SUMMARY
from backend.param.styles import NO_DISPLAY, toast_style
from backend.tasks.tasks import get_remote_data, generate_context_details, post_process, generate_summary_data
from backend.util import read_global_signal_value, get_job_id, no_update, run_task, write_global_signal_value, \
    read_result_form_dict, get_result_form_dict, check_task_type_in_jobs, check_most_recent_task, remove_tasks_in_jobs
from contect.available.available import AvailableSituationType, AvailableTasks, AvailableClassifications, \
    AvailableDetectors
from dash.dependencies import Input, Output, State, ALL
from flask import request

# Navigation & computation
page_title = "Results for Job ID "
return_dev_ctx = "return-detect-and-context"
# next_title = "next"
# goto_title = "Results"
# compute_title = "Compute"
context_title = 'Context Summary'
aggregate_title = 'Aggregate'
toast_header = 'Details for Selection'
ps_context_placeholder = 'typ-context-summary'
ng_context_placeholder = 'ng-context-summary'
icon = 'primary'


def context_tab_layout(title):
    return [
               html.Hr(),
               html.H2('Calendar View of Context'),
               html.Br(),
               html.H3('Positive Context'),
               html.Hr(),
               html.Div(id=ps_context_tab_id(title))] + [
               html.Div(
                   [
                       html.H4(aggregate_title),
                       dcc.Graph(id=ps_context_tab_id(aggregate_title + '-' + title)),
                       html.Br(),
                       single_row(
                           dbc.Toast(
                               id=toast_id(ps_context_tab_id(aggregate_title + '-' + title)),
                               header=toast_header,
                               icon=icon,
                               is_open=False,
                               dismissable=True,
                               style=toast_style
                           )
                       ),
                       html.Br(),
                   ],
                   id=ps_context_tab_id(container_id(aggregate_title + '-' + title)),
                   style=NO_DISPLAY
               ),
               html.Div(
                   [
                       html.Div(
                           [html.H4(extract_title(sit) + ' using Selection ' + sel.value),
                            dcc.Graph(
                                id=ps_context_tab_id(graph_id(title + '-' + extract_title(sit) + '-' + sel.value))),
                            html.Br(),
                            single_row(
                                dbc.Toast(
                                    id=toast_id(ps_context_tab_id(graph_id(
                                        title + '-' + extract_title(sit) + '-' + sel.value))),
                                    header=toast_header,
                                    icon=icon,
                                    is_open=False,
                                    dismissable=True,
                                    style=toast_style
                                )
                            ),
                            html.Br(),
                            ],
                           id=ps_context_tab_id(container_id(title + '-' + extract_title(sit) + '-' + sel.value)),
                           style=NO_DISPLAY
                       )
                       for sit in AvailableSituationsExt
                       for sel in extract_extension(sit).selections
                   ]
               )

           ] + [
               html.H3('Negative Context'),
               html.Hr(),
               html.Div(id=ng_context_tab_id(title))] + [
               html.Div(
                   [
                       html.H4(aggregate_title),
                       dcc.Graph(id=ng_context_tab_id(aggregate_title + '-' + title)),
                       html.Br(),
                       single_row(
                           dbc.Toast(
                               id=toast_id(ng_context_tab_id(aggregate_title + '-' + title)),
                               header=toast_header,
                               icon=icon,
                               is_open=False,
                               dismissable=True,
                               style=toast_style
                           )
                       ),
                       html.Br(),
                   ],
                   id=ng_context_tab_id(container_id(aggregate_title + '-' + title)),
                   style=NO_DISPLAY
               ),
               html.Div(
                   [
                       html.Div(
                           [html.H4(extract_title(sit) + ' using Selection ' + sel.value),
                            dcc.Graph(
                                id=ng_context_tab_id(graph_id(title + '-' + extract_title(sit) + '-' + sel.value))),
                            html.Br(),
                            single_row(
                                dbc.Toast(
                                    id=toast_id(ng_context_tab_id(graph_id(
                                        title + '-' + extract_title(sit) + '-' + sel.value))),
                                    header=toast_header,
                                    icon=icon,
                                    is_open=False,
                                    dismissable=True,
                                    style=toast_style
                                )
                            ),
                            html.Br()
                            ],
                           id=ng_context_tab_id(container_id(title + '-' + extract_title(sit) + '-' + sel.value)),
                           style=NO_DISPLAY
                       )
                       for sit in AvailableSituationsExt
                       for sel in extract_extension(sit).selections
                   ]
               )

           ]


statistics_title = 'statistics'
alpha = 'Degree of Context-Awareness'
positive = 'Positive Context'
negative = 'Negative Context'
medium_awareness = '0.5 -\n Medium Context-Awareness'
no_awareness = ' 0 -\n No Context-Awareness'
full_awareness = '1 -\n Full Context-Awareness'
cluster_t = 'Cluster'
SLIDER = 'slider'


def slider_id(title):
    return f'range-{SLIDER}-{title}'


def post_slider(title, variant):
    return dcc.Slider(
        id=slider_id(title + variant),
        min=0, max=1, step=0.0001,
        marks={0: no_awareness,
               0.5: medium_awareness,
               1: full_awareness},
        value=0
    )


def cluster_id(title):
    return f'{cluster_t}-{title}'


def controls_sliders(detector_title):
    return dbc.Card(
        [
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.P(f'{alpha} for {positive}:'),
                            post_slider(detector_title, positive),
                        ],
                        width={'size': 10, 'offset': 1}
                    )
                ]
            ),
            html.Div(id=f'{detector_title}-pos-slider-output-container'),
            html.Br(),
            dbc.Row(
                dbc.Col(
                    [
                        html.P(f'{alpha} for {negative}:'),
                        post_slider(detector_title, negative),
                    ],
                    width={'size': 10, 'offset': 1}
                )
            ),
            html.Div(id=f'{detector_title}-neg-slider-output-container'),
            html.Br()
        ],
        body=True
    )


def top_ids(title, variant):
    if variant is AvailableTops.POT:
        return title + AvailableTops.POT.value(DEFAULT_TOP)
    elif variant is AvailableTops.HIGH:
        return title + AvailableTops.HIGH.value(DEFAULT_TOP)
    elif variant is AvailableTops.REP:
        return title + AvailableTops.REP.value(DEFAULT_TOP)
    elif variant is AvailableTops.BORD_PS:
        return title + AvailableTops.BORD_PS.value(DEFAULT_TOP)
    else:
        return title + AvailableTops.BORD_NG.value(DEFAULT_TOP)


detector_tooltip = [
    dcc.Markdown(''' Next to displaying the actual summary of the deviation detection result, it offers a complete
    visual analytics suite. This suite allows you to gain deeper insights into the **interaction** of context-unaware 
    detection results in terms of the (deviation) **score** of a trace and of the **context** that the trace had during the 
    time units containing the events of a trace. The higher the score of a trace, the more deviating the detection method classified this 
    trace. As the scale of positive and negative context of a trace (the average of maximum contexts per context type) 
    is built with the same semantics (higher means more exceptional), the interaction can be 
    formalized by means of post-processing the context-unaware score. From the causal model you specified during 
    the deviation & context specification step, we can deduce that a high positive context is the root-cause for a 
    deviating trace, but we do not know to what extent it is the only root-cause. Hence, the degree of context-awareness
    for positive contexts determines how much of the positive context should be deducted from the score, i.e. 
    the deductible is 
    ```python
    score * degree_ps * positive_context
    ```
    . The result is called the **CA score**, which 
    is an abbreviation for context-aware score. If the CA score is below the deviating threshold, then 
    the deviating trace is reclassified as context-aware normal, which is subsumed under *All Normal* in the statistics.
    From the causal model you specified during the deviation & context specification step, we can also deduce that 
    a high negative context indicates a contextual deviation, a type of deviation that classical, context-unaware 
    deviation methods cannot detect. Hence, the post-processing also considers the negative context of a trace by 
    allowing you to add 
    ```python
    (1 - score) * degree_ng * negative_context
    ```
    to the score, yielding the CA score, again. 
    As for the positive context, we do not know to what extent a negative context should be causing a trace to be detected
    as context-aware deviating, you can control this extent by the degree of context-awareness for negative contexts. 
    If you specify both degrees simultaneously, the CA score equals 
    ```python
    score - score * degree_ps * positive_context + (1 - score) * degree_ng * negative_context
    ```
    . 
    To facilitate your analysis, the following top traces for certain properties of traces have a column 
    for required degrees that will cause the respective trace to fall below or above the deviating threshold. 
    All results are visualized in a 3D scatter plot under *Visual Exploration of Context-aware Detection*. 
    The labels of traces - *deviating*, *context-aware deviating*, *normal* and *context-aware normal* - are 
    visualized in the following lists and in the overall list under the tab *Details* by the following color code:
''',
                 style={"font-size": "medium",
                        "text-align": "justify",
                        "text-justify": "inter-word"}),
    html.Br(),
    html.Div(AvailableClassifications.D.value,
             style={'background-color': get_background_color(AvailableClassifications.D),
                    'height': '50px'}),
    html.Br(),
    html.Div(AvailableClassifications.CAD.value,
             style={'background-color': get_background_color(AvailableClassifications.CAD),
                    'height': '50px'}),
    html.Br(),
    html.Div(AvailableClassifications.N.value,
             style={'background-color': get_background_color(AvailableClassifications.N),
                    'height': '50px'}),
    html.Br(),
    html.Div(AvailableClassifications.CAN.value,
             style={'background-color': get_background_color(AvailableClassifications.CAN),
                    'height': '50px'}),
    html.Br(),
]


def detector_summary(detector):
    detector_title = extract_title(detector)
    return [
        html.Br(),
        html.H2('Summary'),
        html.Hr(),
        html.H3(['Result Statistic', tooltip_button(detector_title + 'help')]),
        html.Br(),
        dbc.Modal(
            [
                dbc.ModalHeader("Correlation Method Help", style={"font-size": "x-large",
                                                                  "font-weight": "bolder"}),
                dbc.ModalBody(detector_tooltip),
                dbc.ModalFooter(
                    dbc.Button("Close", id=f'{detector_title}-close-help', className="ml-auto")
                ),
            ],
            id=modal_id(detector_title + 'help'),
            size="lg"
        ),
        html.Div(id=placeholder_id(detector_title + statistics_title)),
        html.Br(),
        html.H3(AvailableTops.HIGH.value(DEFAULT_TOP), id=top_ids(detector_title, AvailableTops.HIGH)),
        html.Br(),
        html.P('The following traces exhibit a high severity of deviation while at the '
               'same time very low positive context values that could explain the deviation:'),
        html.Div(id=placeholder_id(top_ids(detector_title, AvailableTops.HIGH))),
        html.Br(),
        single_row(
            dbc.Toast(
                id=toast_id(top_ids(detector_title, AvailableTops.HIGH)),
                header=toast_header,
                icon=icon,
                is_open=False,
                dismissable=True,
                style=toast_style
            )
        ),
        # html.H3(AvailableTops.REP.value(DEFAULT_TOP), id=top_ids(detector_title, AvailableTops.REP)),
        # html.Br(),
        # html.P('The following traces are the mediods of k-mediods clustering for the deviating traces, i.e. they '
        #       'are representative for deviating traces overall:'),
        # html.Div(id=placeholder_id(top_ids(detector_title, AvailableTops.REP))),
        # html.Br(),
        html.H3(AvailableTops.POT.value(DEFAULT_TOP), id=top_ids(detector_title, AvailableTops.POT)),
        html.Br(),
        html.P('The following traces have the highest values for negative context, i.e. they '
               'potentially indicate a deviation that is not detectable by context-unaware detection methods:'),
        html.Div(id=placeholder_id(top_ids(detector_title, AvailableTops.POT))),
        html.Br(),
        single_row(
            dbc.Toast(
                id=toast_id(top_ids(detector_title, AvailableTops.POT)),
                header=toast_header,
                icon=icon,
                is_open=False,
                dismissable=True,
                style=toast_style
            )
        ),
        html.P('If you would like to view more or fewer traces in the summary and visual '
               'exploration (for clusters and for border case traces), you can specify it in the following:'),
        dbc.Row(
            dbc.Col(
                dbc.Card(
                    dbc.Row(
                        [
                            dbc.Col(),
                            dbc.Col(
                                [
                                    html.P(f'Count:'),
                                    dbc.Input(id=cluster_id(detector_title), type='number', value=5),
                                ]
                            ),
                            dbc.Col()
                        ]
                    ),
                    body=True
                ),
                md=2
            )
        ),
        html.Br(),
        html.H2('Visual Exploration of Context-aware Detection'),
        html.Hr(),
        html.H3('Visualization of Results'),
        html.Br(),
        dbc.Row(
            [
                dbc.Col(
                    html.Div(
                        dcc.Graph(graph_id(detector_title), style={'height': '1000px'}),
                        style={'height': '800px'}),
                )
            ]),
        html.Br(),
        html.Br(),
        single_row(
            dbc.Toast(
                id=toast_id(graph_id(detector_title)),
                header=toast_header,
                icon=icon,
                is_open=False,
                dismissable=True,
                style=toast_style
            )
        ),
        single_row(
            controls_sliders(detector_title)
        ),
        html.Br(),
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.H4(AvailableTops.BORD_NG.value(DEFAULT_TOP),
                                id=top_ids(detector_title, AvailableTops.BORD_NG)),
                        html.Br(),
                        html.P(
                            'The following traces have a deviation score that is slightly above the threshold and at the same time  '
                            'a positive context that is maximal compared to similar border cases. Hence, these traces '
                            'will be the first that are reclassified as normal, if you start adjusting the degree of context-awareness'
                            ' for the positive context above 0:'),
                        html.Div(id=placeholder_id(top_ids(detector_title, AvailableTops.BORD_NG))),
                        html.Br(),
                        single_row(
                            dbc.Toast(
                                id=toast_id(top_ids(detector_title, AvailableTops.BORD_NG)),
                                header=toast_header,
                                icon=icon,
                                is_open=False,
                                dismissable=True,
                                style=toast_style
                            )
                        ),
                    ]
                )
            ]
        ),
        dbc.Row(
            dbc.Col(
                [
                    html.H4(AvailableTops.BORD_PS.value(DEFAULT_TOP),
                            id=top_ids(detector_title, AvailableTops.BORD_PS)),
                    html.Br(),
                    html.P(
                        'The following traces have a deviation score that is slightly below to the threshold and at the same time  '
                        'a negative context that is maximal compared to similar border cases. Hence, these traces '
                        'will be the first that are reclassified as deviating, if you start adjusting the degree of context-awareness'
                        ' for the negative context above 0:'),
                    html.Div(id=placeholder_id(top_ids(detector_title, AvailableTops.BORD_PS))),
                    html.Br(),
                    single_row(
                        dbc.Toast(
                            id=toast_id(top_ids(detector_title, AvailableTops.BORD_PS)),
                            header=toast_header,
                            icon=icon,
                            is_open=False,
                            dismissable=True,
                            style=toast_style
                        )
                    ),
                ]
            )
        ),
        html.Br(),
        html.Div(dbc.Input(id=f'dummy-input-{detector_title}', type='number', value=5), style=NO_DISPLAY)
    ]


def details_tab_layout(detector):
    detector_title = extract_title(detector)
    return [
        html.Br(),
        html.H3('Detailed Results'),
        html.Br(),
        single_row(
            dbc.Toast(
                id=toast_id(result_details_toast_id(detector_title)),
                header=toast_header,
                icon=icon,
                is_open=False,
                dismissable=True,
                style=toast_style
            )
        ),
        html.Div(id=placeholder_id(detector_title + 'details'))
    ]


def detector_tab_layout(detector):
    detector_title = extract_title(detector)
    return [
        dbc.Tabs([
            dbc.Tab(detector_summary(detector), label=detector_title + ' - ' + 'Overview',
                    tab_id=tab_id(detector_title + '-overview')),
            dbc.Tab(context_tab_layout(detector_title), label=detector_title + ' - ' + 'Context',
                    tab_id=tab_id(detector_title + '-context')),
            dbc.Tab(details_tab_layout(detector), label=detector_title + ' - ' + 'Details',
                    tab_id=tab_id(detector_title + '-details')),
        ],
            id=tab_id(detector_title),
            persistence=True,
            persistence_type='local')
    ]


page_layout = container(page_title,
                        [
                            dbc.Tabs(
                                [
                                    dbc.Tab(detector_tab_layout(detector),
                                            label=extract_title(detector),
                                            tab_id=extract_title(detector),
                                            id=extract_title(detector))
                                    for detector in AvailableDetectorsExt
                                ],
                                id='results-tabs',
                                persistence=True,
                                persistence_type='local'
                            )
                        ], idx=RESULT_TITLE + 'title')

offset = len(AvailableDetectorsExt)


@app.callback(
    [
        Output(placeholder_id(extract_title(detector) + statistics_title), 'children')
        for detector in AvailableDetectorsExt
    ] + [
        Output(top_ids(extract_title(detector), AvailableTops.HIGH), 'children')
        for detector in AvailableDetectorsExt
    ] + [
        Output(placeholder_id(top_ids(extract_title(detector), AvailableTops.HIGH)), 'children')
        for detector in AvailableDetectorsExt
    ] + [
        Output(top_ids(extract_title(detector), AvailableTops.POT), 'children')
        for detector in AvailableDetectorsExt
    ] + [
        Output(placeholder_id(top_ids(extract_title(detector), AvailableTops.POT)), 'children')
        for detector in AvailableDetectorsExt
    ] + [
        Output(top_ids(extract_title(detector), AvailableTops.BORD_PS), 'children')
        for detector in AvailableDetectorsExt
    ] + [
        Output(placeholder_id(top_ids(extract_title(detector), AvailableTops.BORD_PS)), 'children')
        for detector in AvailableDetectorsExt
    ] + [
        Output(top_ids(extract_title(detector), AvailableTops.BORD_NG), 'children')
        for detector in AvailableDetectorsExt
    ] + [
        Output(placeholder_id(top_ids(extract_title(detector), AvailableTops.BORD_NG)), 'children')
        for detector in AvailableDetectorsExt
    ] + [
        Output(graph_id(extract_title(detector)), 'figure')
        for detector in AvailableDetectorsExt
    ] + [
        Output(placeholder_id(extract_title(detector) + 'details'), 'children')
        for detector in AvailableDetectorsExt
    ] + [
        Output(temp_jobs_store_id_maker(RESULT_POST), 'data')
    ] + [
        Output(cluster_id(extract_title(detector)), 'value')
        for detector in AvailableDetectorsExt
    ] + [
        Output(slider_id(extract_title(detector) + positive), 'value')
        for detector in AvailableDetectorsExt
    ] + [
        Output(slider_id(extract_title(detector) + negative), 'value')
        for detector in AvailableDetectorsExt
    ] + [
        Output(form_persistence_id_maker(RESULT_TITLE), 'data'),
        Output(temp_jobs_store_id_maker(RESULT_INIT_SUMMARY), 'data')
    ], [
        Input(cluster_id(extract_title(detector)), 'value')
        for detector in AvailableDetectorsExt
    ] + [
        Input(slider_id(extract_title(detector) + positive), 'value')
        for detector in AvailableDetectorsExt
    ] + [
        Input(slider_id(extract_title(detector) + negative), 'value')
        for detector in AvailableDetectorsExt
    ] + [
        Input(global_refresh_signal_id_maker(RESULT_URL), 'children')
    ], [
        State(global_signal_id_maker(RESULT_TITLE), 'children'),
        State(global_form_load_signal_id_maker(GLOBAL_FORM_SIGNAL), 'children'),
        State(temp_jobs_store_id_maker(RESULT_TITLE), 'data'),
        State(form_persistence_id_maker(RESULT_TITLE), 'data'),
        State(temp_jobs_store_id_maker(RESULT_POST), 'data'),
        State(temp_jobs_store_id_maker(RESULT_INIT_SUMMARY), 'data')
    ]
)
def update_summary_output(*args):
    jobs_summary = args[-1]
    temp_jobs = args[-2]
    form = args[-3]
    jobs_dev_ctx = args[-4]
    form_value = args[-5]
    value = args[-6]
    date = args[-7]
    jobs_post = temp_jobs
    if value is None and form_value is None:
        return no_update(14 * len(AvailableDetectorsExt) + 3)
    else:
        if value is not None and form_value is not None:
            log_hash_global, date_global = read_global_signal_value(form_value)
            log_hash_local, task_id, date_local = read_global_signal_value(value)
            date_global = datetime.strptime(date_global, '%Y-%m-%d %H:%M:%S.%f')
            date_local = datetime.strptime(date_local, '%Y-%m-%d %H:%M:%S.%f')
            if date_global < date_local:
                log_hash = log_hash_local
            else:
                log_hash = log_hash_global
        elif value is not None:
            log_hash, task_id, date = read_global_signal_value(value)
        elif form_value is not None:
            log_hash, date = read_global_signal_value(form_value)
        else:
            return no_update(14 * len(AvailableDetectorsExt) + 3)
        ctx = dash.callback_context
        trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
        user = request.authorization['username']
        if check_most_recent_task(jobs_dev_ctx, jobs_summary, log_hash):
            # The dev ctx job is older -> no update of everything necessary
            if trigger_id == '' or len(ctx.triggered) > 1:
                # No post oder cluster could have been triggered (first page load or simple page load)
                init = True
                set_from_form = True
                post = False
                compute_summary = False
                if check_task_type_in_jobs(jobs_post, log_hash, AvailableTasks.POST.value):
                    # Post job is the most recent one
                    log = get_remote_data(user, log_hash, jobs_post, AvailableTasks.POST.value)
                    if log is None:
                        return no_update(14 * len(AvailableDetectorsExt) + 3)
                else:
                    # No post job yet
                    log = get_remote_data(user, log_hash, jobs_dev_ctx, AvailableTasks.GUIDE.value)
                    if log is None:
                        return no_update(14 * len(AvailableDetectorsExt) + 3)
            elif cluster_t in trigger_id:
                # Clusters triggered
                set_from_form = False
                post = False
                compute_summary = True
                if check_task_type_in_jobs(jobs_post, log_hash, AvailableTasks.POST.value):
                    # Post job is the most recent one
                    init = False
                    log = get_remote_data(user, log_hash, jobs_post, AvailableTasks.POST.value)
                    if log is None:
                        return no_update(14 * len(AvailableDetectorsExt) + 3)
                else:
                    # No post job yet
                    init = True
                    log = get_remote_data(user, log_hash, jobs_dev_ctx, AvailableTasks.GUIDE.value)
                    if log is None:
                        return no_update(14 * len(AvailableDetectorsExt) + 3)

            else:
                # Post sliders triggered
                init = False
                set_from_form = False
                post = True
                log = get_remote_data(user, log_hash, jobs_dev_ctx, AvailableTasks.GUIDE.value)
                if log is None:
                    return no_update(14 * len(AvailableDetectorsExt) + 3)
                compute_summary = True
        else:
            # Need to recompute everything
            init = True
            set_from_form = False
            post = False
            compute_summary = True
            log = get_remote_data(user, log_hash, jobs_dev_ctx, AvailableTasks.GUIDE.value)
            if log is None:
                return no_update(14 * len(AvailableDetectorsExt) + 3)
            # Need to clean jobs
            remove_tasks_in_jobs(jobs_summary, log_hash, True, AvailableTasks.POST_DATA.value)
            remove_tasks_in_jobs(jobs_post, log_hash, True, AvailableTasks.POST.value)
        # Check whether there exist persisted form values for that job and we need to set it
        current_offset = 3 * len(AvailableDetectorsExt)
        if set_from_form and form is not None and log_hash in form and len(form[log_hash]) == current_offset:
            persisted_form_values = read_result_form_dict(form, log_hash)
        else:
            if form is None:
                form = {}
            form[log_hash] = get_result_form_dict(args, current_offset)
            persisted_form_values = args[0:3 * len(AvailableDetectorsExt)]
        detectors = [detector for detector in log.traces[0].complex_context]
        ps = AvailableSituationType.POSITIVE
        ng = AvailableSituationType.NEGATIVE
        cluster_sizes = args[0: offset]
        alphas_positive = args[offset:2 * offset]
        alphas_negative = args[2 * offset:3 * offset]
        if not init:
            found = False
            for index, det in enumerate(AvailableDetectorsExt):
                if extract_title(det) in trigger_id:
                    detector = detector_shortcut(det)
                    det_id = index
                    if detector not in detectors:
                        return no_update(14 * len(AvailableDetectorsExt) + 3)
                    found = True
                    break
            if not found:
                return no_update(14 * len(AvailableDetectorsExt) + 3)
            if post:
                alpha_ps = alphas_positive[det_id]
                alpha_ng = alphas_negative[det_id]
                threshold = log.detector_thresholds[detector]
                task_id = run_task(jobs_post, log_hash, AvailableTasks.POST.value,
                                   post_process, jobs_post,
                                   alpha_ps=alpha_ps,
                                   alpha_ng=alpha_ng,
                                   threshold=threshold,
                                   log=log,
                                   detector=detector)
                log = get_remote_data(user, log_hash, jobs_post, AvailableTasks.POST.value)
                if log is None:
                    return no_update(14 * len(AvailableDetectorsExt) + 3)
        if jobs_post is None or len(jobs_post[JOBS_KEY]) == 0:
            jobs_post = deepcopy(jobs_dev_ctx)
        if log_hash not in jobs_post[JOBS_KEY]:
            jobs_post[JOBS_KEY][log_hash] = deepcopy(jobs_dev_ctx[JOBS_KEY][log_hash])
        # Check whether there exist celery results for this job and form values already
        variant = {detector: True if detector not in log.traces[0].ca_score else False
                   for detector in AvailableDetectors}
        if compute_summary:
            if jobs_summary is None or len(jobs_summary[JOBS_KEY]) == 0:
                jobs_summary = deepcopy(jobs_dev_ctx)
            if log_hash not in jobs_summary[JOBS_KEY]:
                jobs_summary[JOBS_KEY][log_hash] = deepcopy(jobs_dev_ctx[JOBS_KEY][log_hash])
            task_id = run_task(jobs_summary, log_hash, AvailableTasks.POST_DATA.value,
                               generate_summary_data, jobs_summary,
                               cluster_sizes=cluster_sizes,
                               detectors=detectors,
                               log=log,
                               ng=ng,
                               ps=ps,
                               variant=variant)
            all_data, top_traces, cluster_sizes, clustering = get_remote_data(user, log_hash, jobs_summary,
                                                                              AvailableTasks.POST_DATA.value,
                                                                              4)
            if all_data is None:
                return no_update(14 * len(AvailableDetectorsExt) + 3)
        else:
            all_data, top_traces, cluster_sizes, clustering = get_remote_data(user, log_hash, jobs_summary,
                                                                              AvailableTasks.POST_DATA.value,
                                                                              4)
            if all_data is None:
                return no_update(14 * len(AvailableDetectorsExt) + 3)
        all_figures = []
        for index, detector in enumerate(AvailableDetectorsExt):
            detector = detector_shortcut(detector)
            if detector in detectors:
                threshold = log.detector_thresholds[detector]
                point_shape = 50
                z = np.array(
                    [
                        [threshold] * point_shape
                    ] * point_shape
                )
                x, y = np.linspace(0, 1, point_shape), np.linspace(0, 1, point_shape)
                surface = go.Surface(x=x,
                                     y=y,
                                     z=z,
                                     name='Deviation Threshold',
                                     showlegend=False,
                                     showscale=False,
                                     colorscale=COLORSCALE
                                     )
                fig = px.scatter_3d(all_data[detector],
                                    x=positive_context,
                                    y=negative_context,
                                    z=deviation_score,
                                    range_y=[0, 1],
                                    range_x=[0, 1],
                                    range_z=[0, 1],
                                    symbol=deviating,
                                    hover_name=tid_t,
                                    hover_data={deviating: False,
                                                n_events: True,
                                                start_ts: True,
                                                end_ts: True},
                                    color=group_t,
                                    height=800
                                    )
                fig.add_trace(surface)
                # fig.add_trace(center_figures[detector])
                if clustering[detector] is not None:
                    layout = dict(scene=dict(annotations=[{
                        'x': 0.25,
                        'y': 0.25,
                        'z': threshold,
                        'text': 'Deviation Threshold',
                        'showarrow': True,
                        'arrowhead': 7,
                        'ax': 0,
                        'ay': -30,
                    }] + [{
                        'x': p[0],
                        'y': p[1],
                        'z': p[2],
                        'text': f'Cluster center {i}',
                        'showarrow': True,
                        'arrowhead': 7,
                        'ax': 0,
                        'ay': -30,
                    }
                                                             for i, p in
                                                             enumerate(
                                                                 zip(clustering[detector].cluster_centers_[:, 1],
                                                                     clustering[detector].cluster_centers_[:, 2],
                                                                     clustering[detector].cluster_centers_[:, 0]))
                                                         ],
                                             aspectmode='manual',
                                             aspectratio=go.layout.scene.Aspectratio(
                                                 x=1, y=1, z=1
                                             )
                                             )
                                  )
                else:
                    layout = dict(scene=dict(annotations=[{
                        'x': 0.25,
                        'y': 0.25,
                        'z': threshold,
                        'text': 'Deviation Threshold',
                        'showarrow': True,
                        'arrowhead': 7,
                        'ax': 0,
                        'ay': -30,
                    }],
                        aspectmode='manual',
                        aspectratio=go.layout.scene.Aspectratio(
                            x=1, y=1, z=1
                        )
                    )
                    )
                fig.update_layout(layout)
                fig.update_layout(showlegend=True,
                                  autosize=False,
                                  height=800)
                all_figures.append(fig)
            else:
                all_figures.append(dash.no_update)
        all_figures = tuple(
            all_figures
        )
        counters = {detector:
                        Counter(log.labels[detector_shortcut(detector)])
                        if detector_shortcut(detector) in detectors else dash.no_update
                    for detector in AvailableDetectorsExt
                    }
        statistics = tuple(
            [
                create_data_table(None,
                                  pd.DataFrame(
                                      {'# All Deviating Traces': [counters[detector][AvailableClassifications.D] +
                                                                  counters[detector][AvailableClassifications.CAD]],
                                       '# Context-unaware Deviating Traces': [
                                           counters[detector][AvailableClassifications.D]],
                                       '# Context-aware Deviating Traces': [
                                           counters[detector][AvailableClassifications.CAD]],
                                       '# All Normal Traces': [counters[detector][AvailableClassifications.N] +
                                                               counters[detector][
                                                                   AvailableClassifications.CAN]],
                                       '# Context-unaware Normal Traces': [
                                           counters[detector][AvailableClassifications.N]],
                                       '# Context-aware Normal Traces': [
                                           counters[detector][AvailableClassifications.CAN]],
                                       'Deviating Threshold': [
                                           round(log.detector_thresholds[detector_shortcut(detector)], 4)]},
                                      index=[0]),
                                  None,
                                  1)
                if detector_shortcut(detector) in detectors else dash.no_update
                for detector in AvailableDetectorsExt
            ]
        )
        titles_high = tuple(
            [
                AvailableTops.HIGH.value(cluster_sizes[detector_shortcut(detector)][str(AvailableTops.HIGH)])
                if detector_shortcut(detector) in detectors else dash.no_update
                for index, detector in enumerate(AvailableDetectorsExt)
            ]
        )
        titles_pot = tuple(
            [
                AvailableTops.POT.value(cluster_sizes[detector_shortcut(detector)][str(AvailableTops.POT)])
                if detector_shortcut(detector) in detectors else dash.no_update
                for index, detector in enumerate(AvailableDetectorsExt)
            ]
        )
        titles_bord_ps = tuple(
            [
                AvailableTops.BORD_PS.value(cluster_sizes[detector_shortcut(detector)][str(AvailableTops.BORD_PS)])
                if detector_shortcut(detector) in detectors else dash.no_update
                for index, detector in enumerate(AvailableDetectorsExt)
            ]
        )
        titles_bord_ng = tuple(
            [
                AvailableTops.BORD_NG.value(cluster_sizes[detector_shortcut(detector)][str(AvailableTops.BORD_NG)])
                if detector_shortcut(detector) in detectors else dash.no_update
                for index, detector in enumerate(AvailableDetectorsExt)
            ]
        )
        high_traces = tuple(
            [
                generate_trace_summary_table(
                    [
                        log.traces[int(i[1])]
                        for i in top_traces[str(AvailableTops.HIGH)][detector_shortcut(detector)]
                    ],
                    detector_shortcut(detector),
                    log_hash,
                    log.vmap_param.vmap_params,
                    threshold=log.detector_thresholds[detector_shortcut(detector)],
                    labels=log.labels[detector_shortcut(detector)],
                    target=top_ids(extract_title(detector), AvailableTops.HIGH)
                )
                if detector_shortcut(detector) in detectors else dash.no_update
                for detector in AvailableDetectorsExt
            ]
        )
        pot_traces = tuple(
            [
                generate_trace_summary_table(
                    [
                        log.traces[int(i[1])]
                        for i in top_traces[str(AvailableTops.POT)][detector_shortcut(detector)]
                    ],
                    detector_shortcut(detector),
                    log_hash,
                    log.vmap_param.vmap_params,
                    threshold=log.detector_thresholds[detector_shortcut(detector)],
                    labels=log.labels[detector_shortcut(detector)],
                    target=top_ids(extract_title(detector), AvailableTops.POT)

                )
                if detector_shortcut(detector) in detectors else dash.no_update
                for detector in AvailableDetectorsExt
            ]
        )
        bord_ps_traces = tuple(
            [
                generate_trace_summary_table(
                    [
                        log.traces[int(i[1])]
                        for i in top_traces[str(AvailableTops.BORD_PS)][detector_shortcut(detector)]
                    ],
                    detector_shortcut(detector),
                    log_hash,
                    log.vmap_param.vmap_params,
                    threshold=log.detector_thresholds[detector_shortcut(detector)],
                    labels=log.labels[detector_shortcut(detector)],
                    target=top_ids(extract_title(detector), AvailableTops.BORD_PS)
                )
                if detector_shortcut(detector) in detectors else dash.no_update
                for detector in AvailableDetectorsExt
            ]
        )
        bord_ng_traces = tuple(
            [
                generate_trace_summary_table(
                    [
                        log.traces[int(i[1])]
                        for i in top_traces[str(AvailableTops.BORD_NG)][detector_shortcut(detector)]
                    ],
                    detector_shortcut(detector),
                    log_hash,
                    log.vmap_param.vmap_params,
                    threshold=log.detector_thresholds[detector_shortcut(detector)],
                    labels=log.labels[detector_shortcut(detector)],
                    target=top_ids(extract_title(detector), AvailableTops.BORD_NG)
                )
                if detector_shortcut(detector) in detectors else dash.no_update
                for detector in AvailableDetectorsExt
            ]
        )
        details = tuple(
            [
                generate_trace_summary_table(
                    traces=[
                        trace
                        for tid, trace in
                        sorted(log.traces.items(), key=lambda item: item[1].score[detector_shortcut(detector)]
                        if variant else item[1].ca_score[detector_shortcut(detector)], reverse=True)
                    ],
                    detector=detector_shortcut(detector),
                    log_hash=log_hash,
                    vmap_params=log.vmap_param.vmap_params,
                    details=True,
                    objects=log.objects,
                    threshold=log.detector_thresholds[detector_shortcut(detector)],
                    labels=log.labels[detector_shortcut(detector)],
                    target=result_details_toast_id(extract_title(detector))
                )
                if detector_shortcut(detector) in detectors else dash.no_update
                for detector in AvailableDetectorsExt
            ]
        )
        return statistics + \
               titles_high + high_traces + \
               titles_pot + pot_traces + \
               titles_bord_ps + bord_ps_traces + \
               titles_bord_ng + bord_ng_traces + \
               all_figures + details + tuple([jobs_post]) + persisted_form_values + tuple([form, jobs_summary])


def get_lengths_for_context_return():
    detector_len = len(AvailableDetectorsExt)
    detailed_len = 0
    for sit in AvailableSituationsExt:
        detailed_len += detector_len * len(extract_extension(sit).selections)
    return detector_len, detailed_len


@app.callback(
    [
        Output(temp_jobs_store_id_maker(RESULT_INIT), 'data'),
        Output(RESULT_TITLE + 'title', 'children')
    ] + [
        Output(ps_context_tab_id(aggregate_title + '-' + extract_title(detector)), 'figure')
        for detector in AvailableDetectorsExt
    ] + [
        Output(ps_context_tab_id(
            graph_id(
                extract_title(detector) + '-' + extract_title(sit) + '-' + sel.value)), 'figure')
        for detector in AvailableDetectorsExt
        for sit in AvailableSituationsExt
        for sel in extract_extension(sit).selections
    ] + [
        Output(ng_context_tab_id(aggregate_title + '-' + extract_title(detector)), 'figure')
        for detector in AvailableDetectorsExt
    ] + [
        Output(ng_context_tab_id(
            graph_id(
                extract_title(detector) + '-' + extract_title(sit) + '-' + sel.value)), 'figure')
        for detector in AvailableDetectorsExt
        for sit in AvailableSituationsExt
        for sel in extract_extension(sit).selections
    ] + [
        Output(ps_context_tab_id(
            container_id(aggregate_title + '-' + extract_title(detector))), 'style')
        for detector in AvailableDetectorsExt
    ] + [
        Output(ps_context_tab_id(
            container_id(
                extract_title(detector) + '-' + extract_title(sit) + '-' + sel.value)), 'style')
        for detector in AvailableDetectorsExt
        for sit in AvailableSituationsExt
        for sel in extract_extension(sit).selections
    ] + [
        Output(ng_context_tab_id(
            container_id(aggregate_title + '-' + extract_title(detector))), 'style')
        for detector in AvailableDetectorsExt
    ] + [
        Output(ng_context_tab_id(
            container_id(
                extract_title(detector) + '-' + extract_title(sit) + '-' + sel.value)), 'style')
        for detector in AvailableDetectorsExt
        for sit in AvailableSituationsExt
        for sel in extract_extension(sit).selections
    ] + [
        Output(extract_title(detector), 'disabled')
        for detector in AvailableDetectorsExt
    ],
    [
        Input(global_refresh_signal_id_maker(RESULT_URL), 'children')
    ] + [
        Input(f'dummy-input-{extract_title(detector)}', 'value')
        for detector in AvailableDetectorsExt
    ],
    [
        State(global_signal_id_maker(RESULT_TITLE), 'children'),
        State(global_form_load_signal_id_maker(GLOBAL_FORM_SIGNAL), 'children'),
        State(temp_jobs_store_id_maker(RESULT_TITLE), 'data'),
        State(temp_jobs_store_id_maker(CORR_TITLE), 'data'),
        State(form_persistence_id_maker(RESULT_TITLE), 'data'),
        State(temp_jobs_store_id_maker(RESULT_INIT), 'data')
    ]
)
def update_context_output(*args):
    jobs_context_details = args[-1]
    form = args[-2]
    jobs_data = args[-3]
    jobs_dev_ctx = args[-4]
    form_value = args[-5]
    value = args[-6]
    if value is not None and form_value is not None:
        log_hash_global, date_global = read_global_signal_value(form_value)
        log_hash_local, task_id, date_local = read_global_signal_value(value)
        date_global = datetime.strptime(date_global, '%Y-%m-%d %H:%M:%S.%f')
        date_local = datetime.strptime(date_local, '%Y-%m-%d %H:%M:%S.%f')
        if date_global < date_local:
            log_hash = log_hash_local
        else:
            log_hash = log_hash_global
    elif value is not None:
        log_hash, task_id, date = read_global_signal_value(value)
    elif form_value is not None:
        log_hash, date = read_global_signal_value(form_value)
    else:
        detector_len, detailed_len = get_lengths_for_context_return()
        return no_update(2 + 5 * detector_len + 4 * detailed_len)
    if check_most_recent_task(jobs_dev_ctx, jobs_context_details, log_hash):
        # The dev ctx job is older -> no update of everything necessary
        compute_details = False
        user = request.authorization['username']
        data = get_remote_data(user, log_hash,
                               jobs_context_details,
                               AvailableTasks.CONTEXT_RESULT.value)
        if data is None:
            detector_len, detailed_len = get_lengths_for_context_return()
            return no_update(2 + 5 * detector_len + 4 * detailed_len)

    else:
        # Need to recompute everything
        compute_details = True
        # Need to clean jobs
        remove_tasks_in_jobs(jobs_context_details, log_hash, True, AvailableTasks.CONTEXT_RESULT.value)
    # log_hash = list(jobs_dev_ctx[JOBS_KEY].keys())[0]
    user = request.authorization['username']
    log = get_remote_data(user, log_hash, jobs_dev_ctx, AvailableTasks.GUIDE.value)
    if log is None:
        detector_len, detailed_len = get_lengths_for_context_return()
        return no_update(2 + 5 * detector_len + 4 * detailed_len)
    events_timeunits = log.events_timeunits
    detectors = [detector for detector in log.traces[0].complex_context]
    granularity = log.granularity
    ps = AvailableSituationType.POSITIVE
    ng = AvailableSituationType.NEGATIVE
    rng = log.norm_range
    event_to_traces = log.event_to_traces
    if jobs_context_details is None or len(jobs_context_details[JOBS_KEY]) == 0:
        jobs_context_details = jobs_dev_ctx
    if log_hash not in jobs_context_details[JOBS_KEY]:
        jobs_context_details[JOBS_KEY][log_hash] = deepcopy(jobs_dev_ctx[JOBS_KEY][log_hash])
    if compute_details:
        # data = generate_context_details(detectors, events_timeunits, granularity, log, ng, typ, rng, event_to_traces, log.vmap_param.vmap_params, log.objects)
        task_id = run_task(jobs_context_details, log_hash, AvailableTasks.CONTEXT_RESULT.value,
                           generate_context_details,
                           jobs_context_details,
                           detectors=detectors,
                           events_timeunits=events_timeunits,
                           granularity=granularity,
                           log=log,
                           ng=ng,
                           ps=ps,
                           rng=rng,
                           event_to_traces=event_to_traces,
                           vmap_params=log.vmap_param.vmap_params,
                           objects=log.objects)
        data = get_remote_data(user,
                               log_hash,
                               jobs_context_details,
                               AvailableTasks.CONTEXT_RESULT.value)
        if data is None:
            detector_len, detailed_len = get_lengths_for_context_return()
            return no_update(2 + 5 * detector_len + 4 * detailed_len)

    added, daily_contexts, ng_agg_daily_contexts, ps_agg_daily_contexts, years, granularity, rng, event_to_traces, vmap_params, objects = data

    ps_context_graphs = create_context_graphs(added, daily_contexts, granularity, log, ps, ps_agg_daily_contexts,
                                              years)
    ng_context_graphs = create_context_graphs(added, daily_contexts, granularity, log, ng, ng_agg_daily_contexts,
                                              years)
    show_ps_details = show_detailed_graphs(daily_contexts, ps, ps_agg_daily_contexts)
    show_ng_details = show_detailed_graphs(daily_contexts, ng, ng_agg_daily_contexts)
    show_ps = show_agg_graphs(ps_agg_daily_contexts)
    show_ng = show_agg_graphs(ng_agg_daily_contexts)
    title = page_title + str(get_job_id(jobs_dev_ctx, log_hash))
    methods = tuple([not enabled for enabled in log.methods_bool])
    return tuple([jobs_context_details, title]) + ps_context_graphs + ng_context_graphs + \
           show_ps + show_ps_details + show_ng + show_ng_details + methods


# Aggregate typ context graphs
for detector in AvailableDetectorsExt:
    title_agg = ps_context_tab_id(aggregate_title + '-' + extract_title(detector))
    toast_context_help_callback(app=app,
                                title=title_agg,
                                det=detector,
                                agg=True,
                                variant=AvailableSituationType.POSITIVE)

# Aggregate ng context graphs
for detector in AvailableDetectorsExt:
    title_agg_ng = ng_context_tab_id(aggregate_title + '-' + extract_title(detector))
    toast_context_help_callback(app=app,
                                title=title_agg_ng,
                                det=detector,
                                agg=True,
                                variant=AvailableSituationType.NEGATIVE)

# Single typ context graphs
for detector in AvailableDetectorsExt:
    for sit in AvailableSituationsExt:
        for sel in extract_extension(sit).selections:
            title_detailed_ps = ps_context_tab_id(graph_id(
                extract_title(detector) + '-' + extract_title(sit) + '-' + sel.value))
            toast_context_help_callback(app=app,
                                        title=title_detailed_ps,
                                        det=detector,
                                        sit=sit,
                                        selection=sel,
                                        agg=False)

# Single ng context graphs
for detector in AvailableDetectorsExt:
    for sit in AvailableSituationsExt:
        for sel in extract_extension(sit).selections:
            title_detailed_ng = ng_context_tab_id(graph_id(
                extract_title(detector) + '-' + extract_title(sit) + '-' + sel.value))
            toast_context_help_callback(app=app,
                                        title=title_detailed_ng,
                                        det=detector,
                                        sit=sit,
                                        selection=sel, agg=False)

# Summary toasts (graph)
for detector in AvailableDetectorsExt:
    title_summary_graph = graph_id(extract_title(detector))
    toast_summary_graph_callback(app, title_summary_graph, detector)

# Summary toasts (top lists)
for detector in AvailableDetectorsExt:
    for top in AvailableTops:
        title_summary_list = top_ids(extract_title(detector), top)
        toast_summary_list_callback(app, title_summary_list, detector, title_summary_list)

# Summary toasts (details)
for detector in AvailableDetectorsExt:
    title_summary_details = result_details_toast_id(extract_title(detector))
    toast_summary_list_callback(app, title_summary_details, detector, title_summary_details)


@app.callback(
    Output(global_url_signal_id_maker(TRACE_RESULT_SIGNAL), 'children'),
    Output(global_signal_id_maker(TRACE_RESULT_SIGNAL), 'children'),
    Input({'type': CB_TYPE_INSPECT, 'index': ALL, 'result': ALL}, 'n_clicks')
)
def inspect(ns):
    if all([i is None for i in ns]):
        return dash.no_update
    else:
        triggered = [t["prop_id"] for t in dash.callback_context.triggered]
        value = triggered[0].split('"')[3]
        return write_global_signal_value([TRACE_URL, str(datetime.now())]), value


def show_agg_graphs(ng_agg_daily_contexts):
    return tuple([
        {}
        if detector_shortcut(detector) in ng_agg_daily_contexts else dash.no_update
        for detector in AvailableDetectorsExt
    ])


def show_detailed_graphs(daily_contexts, ps, ps_agg_daily_contexts):
    return tuple(
        [
            {}
            if detector_shortcut(detector) in ps_agg_daily_contexts and
               sit_shortcut(sit) in daily_contexts[detector_shortcut(detector)][ps] and
               sel in daily_contexts[detector_shortcut(detector)][ps][sit_shortcut(sit)]
            else dash.no_update

            for detector in AvailableDetectorsExt
            for sit in AvailableSituationsExt
            for sel in extract_extension(sit).selections
        ]
    )


for detector in AvailableDetectorsExt:
    @app.callback(
        Output(f'{extract_title(detector)}-pos-slider-output-container', 'children'),
        [Input(slider_id(extract_title(detector) + positive), 'value')])
    def update_output(value):
        return 'You have selected "{}" for the positive degree.'.format(value)

    @app.callback(
        Output(f'{extract_title(detector)}-neg-slider-output-container', 'children'),
        [Input(slider_id(extract_title(detector) + negative), 'value')])
    def update_output(value):
        return 'You have selected "{}" for the negative degree'.format(value)


for detector in AvailableDetectorsExt:
    @app.callback(
        Output(modal_id(extract_title(detector) + 'help'), "is_open"),
        [
            Input(tooltip_button_id(extract_title(detector) + 'help'), "n_clicks"),
            Input(f'{extract_title(detector)}-close-help', "n_clicks")
        ],
        [
            State(modal_id(extract_title(detector) + 'help'), "is_open")
        ],
    )
    def toggle_modal(n1, n2, is_open):
        if n1 or n2:
            return not is_open
        return is_open
