from copy import deepcopy
from datetime import datetime
from time import sleep

import dash
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
import dash_interactive_graphviz
from backend.app import app
from backend.callbacks.callbacks import modal_callback, collapse_switch_callback
from backend.components.graphs import generate_causal_graph
from backend.components.misc import container, global_signal_id_maker, temp_jobs_store_id_maker, button, \
    return_title_maker, return_button_id, form_persistence_id_maker, single_row, \
    modal_id, modal_close_button_id, viz_id, checklist_id_maker, tooltip_button, compute_title_maker, compute_button_id, \
    goto_title_maker, goto_button_id, input_id, \
    global_form_load_signal_id_maker, global_url_signal_id_maker
from backend.components.userforms import generate_deviation_form, generate_deviation_param_form, \
    generate_context_form_row, dropdown_id_maker
from backend.param.available import AvailableDetectorsExt, extract_title, extract_helps, extract_inputs, \
    AvailableSituationsExt, extract_extension
from backend.param.constants import CORR_OUT_TITLE, DEV_CTX_TITLE, \
    CORR_TITLE, CORR_OUT_URL, RESULT_URL, RESULT_TITLE, SEP, GLOBAL_FORM_SIGNAL, NA, GUIDANCE_TITLE, CORR_METHOD
from backend.param.helps import GUIDANCE_HELP, TYPE_HELP, STABILITY_HELP, INTRINSIC_HELP, EXTERNAL_HELP, TIME_UNIT_HELP
from backend.param.styles import MODAL_HEADER_STYLE, MODAL_BODY_STYLE, BUTTON_TOOLTIP_HD_STYLE, BUTTON_LEFT_STYLE
from backend.tasks.tasks import compute_detection, compute_context, get_remote_data, get_task, compute_guidance, \
    celery
from backend.util import read_global_signal_value, get_job_id, no_update, get_dev_ctx_form_dict, \
    read_dev_ctx_form_dict, read_corrout_form_dict, \
    run_task, write_global_signal_value, assign_task_id, remove_redis
from contect.available.available import AvailableSituationType, AvailableTasks, AvailableGranularity, \
    extract_options, AvailableNormRanges
from dash.dependencies import Input, Output, State
from flask import request

# Navigation & computation

page_title = "Deviation Detection & Context for Job ID "
return_log = "return-log"
next_title = "next"
goto_title = "Results"
compute_title = "Compute"
guidance_title = 'guidance'

# Form titles
detector_title = "Detection Method"
context_title = "Context"
context_include = "Include"
context_guided = "Guided"
context_exclude = "Disabled"
context_type = "Type"
context_range = "Context Dynamics"
context_granularity = "Time Unit Size"
titles = [context_include, context_guided, context_exclude, context_type, context_range]
causal_1 = "Causal Model of Process Deviations "
causal_2 = " & Context Deviations"
modal_ids = [context_guided, context_type, context_range, context_granularity, causal_1, causal_2]

# Dynamic help texts
detector_helps = extract_helps(AvailableDetectorsExt)
detector_inputs = extract_inputs(AvailableDetectorsExt)
context_helps = extract_helps(AvailableSituationsExt)

# Buttons
return_button = button(return_log, return_title_maker, return_button_id, href=CORR_OUT_URL)
goto_button = button(goto_title, goto_title_maker, goto_button_id, href=RESULT_URL, style=BUTTON_LEFT_STYLE)
buttons_context = [button(compute_title, compute_title_maker, compute_button_id),
                   goto_button]

# DEVIATION
# Dynamic creation of user form for detection methods
detector_group = [
    html.Div(
        [
            dbc.Form(
                [
                    generate_deviation_form(detector, detector_helps),
                    generate_deviation_param_form(detector)
                ]),
            html.Hr()
        ] +
        [
            dbc.Modal(
                [
                    dbc.ModalHeader("Correlation Method Help", style=MODAL_HEADER_STYLE),
                    dbc.ModalBody(dcc.Markdown(detector.value[extract_title(detector)].help_text,
                                               style=MODAL_BODY_STYLE)),
                    dbc.ModalFooter(
                        dbc.Button("Close",
                                   id=modal_close_button_id(extract_title(detector)),
                                   className="ml-auto")
                    ),
                ],
                id=modal_id(extract_title(detector)),
                size="lg"
            ) if detector_helps[detector] else html.Div('')]
    )
    for detector in AvailableDetectorsExt
]

# Deviation Tab
deviation_tab_content = [
                            html.Br(),
                            return_button,
                            html.Br(),
                            html.Div("Please select deviation detection methods:"),
                            html.Hr()
                        ] + detector_group + [
                            html.Br()
                        ]

# CONTEXT
# Dynamic creation of context user forms
context_group = [
    html.Div(
        [
            dbc.Form(
                generate_context_form_row(context,
                                          titles,
                                          context_helps)
            ),
            html.Hr()
        ] +
        [
            dbc.Modal(
                [
                    dbc.ModalHeader("Correlation Method Help", style=MODAL_HEADER_STYLE),
                    dbc.ModalBody(dcc.Markdown(context.value[extract_title(context)].help_text,
                                               style=MODAL_BODY_STYLE)),
                    dbc.ModalFooter(
                        dbc.Button("Close",
                                   id=modal_close_button_id(extract_title(context)),
                                   className="ml-auto")
                    ),
                ],
                id=modal_id(extract_title(context)),
                size="lg"
            ) if context_helps[context] else html.Div('')]
    )
    for context in AvailableSituationsExt
]

# Context tab
context_tab_content = [
                          html.Br(),
                          return_button,
                          html.Br(),
                          html.Div("Please specify the context in the following:"),
                          html.Hr(),
                          dbc.Row(
                              [
                                  dbc.Col(
                                      html.H2(context_title)
                                  ),
                                  dbc.Col(
                                      html.H2(context_include)
                                  ),
                                  dbc.Col(
                                      html.H2(
                                          [
                                              context_guided
                                          ] + [
                                              tooltip_button(context_guided,
                                                             style=BUTTON_TOOLTIP_HD_STYLE
                                                             )
                                          ]
                                      )
                                  ),
                                  dbc.Col(
                                      html.H2(context_exclude)
                                  ),
                                  dbc.Col(
                                      html.H2(
                                          [
                                              context_type
                                          ] + [
                                              tooltip_button(context_type,
                                                             style=BUTTON_TOOLTIP_HD_STYLE
                                                             )
                                          ]
                                      )
                                  )
                              ]
                          ),
                          html.Hr(),
                      ] + context_group + [
                          html.Br(),
                          html.Div("Please specify the context dynamics of your specified context in the following:"),
                          html.Br(),
                          html.H2(
                              [
                                  context_range
                              ] + [
                                  tooltip_button(context_range,
                                                 style=BUTTON_TOOLTIP_HD_STYLE
                                                 )
                              ]
                          ),
                          dbc.Row(dbc.Col(
                              [
                                  dcc.Dropdown(
                                      id=dropdown_id_maker(context_range),
                                      options=[
                                          dict(label=option.title(), value=option)
                                          for option in extract_options(AvailableNormRanges)
                                      ],
                                      persistence=True,
                                      persistence_type='memory'
                                  )
                              ],
                              width=3
                          )),
                          html.Hr(),
                          html.Div(
                              "Please specify the size of time units that should be used for building the time span"),
                          html.Br(),
                          html.H2(
                              [
                                  context_granularity
                              ] + [
                                  tooltip_button(context_granularity,
                                                 style=BUTTON_TOOLTIP_HD_STYLE
                                                 )
                              ]
                          ),
                          dbc.Row(dbc.Col(
                              [
                                  dcc.Dropdown(
                                      id=dropdown_id_maker(context_granularity),
                                      options=[
                                          {'label': option.title(), 'value': option.title()}
                                          for option in [AvailableGranularity.HR.value, AvailableGranularity.DAY.value]
                                      ],
                                      persistence=True,
                                      persistence_type='memory'
                                  )
                              ],
                              width=3
                          )),
                          html.Br(),
                          single_row(html.Div(buttons_context), 'end'),
                          html.Div(
                              [
                                  html.Br(),
                                  html.H2(
                                      [
                                          causal_1
                                      ] + [
                                          tooltip_button(causal_1,
                                                         style=BUTTON_TOOLTIP_HD_STYLE
                                                         )
                                      ] + [
                                          causal_2
                                      ] + [
                                          tooltip_button(causal_2,
                                                         style=BUTTON_TOOLTIP_HD_STYLE
                                                         ),
                                      ]
                                  ),
                                  html.Hr(),
                                  dbc.Row(dbc.Col(html.Div(
                                      dash_interactive_graphviz.DashInteractiveGraphviz(id=viz_id(causal_1),
                                                                                        engine='neato'),
                                      style=dict(position="relative", display='inline-block', width='100%',
                                                 height='100%'),
                                  )), style={'height': '1000px'})
                              ],
                              # style=dict(position="relative", height="100%", width="100%", display="flex"),
                          )] + [
                          dbc.Modal(
                              [
                                  dbc.ModalHeader(header, style=MODAL_HEADER_STYLE),
                                  dbc.ModalBody(dcc.Markdown(text,
                                                             style=MODAL_BODY_STYLE)),
                                  dbc.ModalFooter(
                                      dbc.Button("Close",
                                                 id=modal_close_button_id(title),
                                                 className="ml-auto")
                                  ),
                              ],
                              id=modal_id(title),
                              size="lg"
                          ) for header, title, text in zip(["Guidance Help",
                                                            "Context Type Help",
                                                            "Context Stability Help",
                                                            "Time Unit Help",
                                                            "Process Deviation Help",
                                                            "Context Deviation Help"],
                                                           modal_ids,
                                                           [GUIDANCE_HELP,
                                                            TYPE_HELP,
                                                            STABILITY_HELP,
                                                            TIME_UNIT_HELP,
                                                            INTRINSIC_HELP,
                                                            EXTERNAL_HELP])]

# PAGE
page_layout = container(page_title,
                        [
                            dbc.Tabs(
                                [
                                    dbc.Tab(deviation_tab_content, label="Deviation Detection", tab_id='deviation'),
                                    dbc.Tab(context_tab_content, label="Context", tab_id='context')
                                ], id='dev-ctx-tabs'
                            )
                        ], DEV_CTX_TITLE + 'title')

offset = len(AvailableSituationsExt)


@app.callback(
    Output(viz_id(causal_1), "dot_source"),
    [
        Input(checklist_id_maker(extract_title(context) + '-' + titles[0]), 'value') for context in
        AvailableSituationsExt
    ] +
    [
        Input(checklist_id_maker(extract_title(context) + '-' + titles[1]), 'value') for context in
        AvailableSituationsExt
    ] +
    [
        Input(checklist_id_maker(extract_title(context) + '-' + titles[2]), 'value') for context in
        AvailableSituationsExt
    ] +
    [
        Input(dropdown_id_maker(extract_title(context) + '-' + titles[3]), 'value') for context in
        AvailableSituationsExt
    ],
    [
        State(checklist_id_maker(extract_title(detector)), 'on') for detector in AvailableDetectorsExt
    ]

)
def display_causal_model(*args):
    # triggered = [t["prop_id"] for t in dash.callback_context.triggered]
    # Create list of positive contexts and negative contexts from user form
    if not all(
            [len(args[i]) == 0 for i in range(offset * 3)] + [args[i] is None for i in range(offset * 3, offset * 4)]):
        positive = []
        negative = []
        for index_c, context in enumerate(AvailableSituationsExt):
            assigned = False
            for index_t, title in enumerate(titles[:3]):
                if index_t == 0:
                    # Include
                    if check_checklist(args, index_c, index_t):
                        pass
                    else:
                        assigned = True
                        assign_pos_or_neg(args, context, index_c, negative, positive)
                elif index_t == 1:
                    # Guided
                    if check_checklist(args, index_c, index_t):
                        pass
                    elif not assigned:
                        assigned = True
                        assign_pos_or_neg(args, context, index_c, negative, positive)
                elif index_t == 2:
                    # Disabled
                    if check_checklist(args, index_c, index_t):
                        pass
                    elif assigned:
                        # Disabled overrules previously assigned membership
                        negative, positive = delete_pos_or_neg(args, index_c, negative, positive)
        classical = []
        for index_d, detector in enumerate(AvailableDetectorsExt):
            if args[offset * 4 + index_d]:
                classical.append(extract_title(detector))
        return generate_causal_graph(positive, classical, negative)
    else:
        return dash.no_update


# Dynamically add help texts and collapses for inputs
detector_with_param = []
for detector in AvailableDetectorsExt:
    if detector_helps[detector]:
        modal_callback(app, extract_title(detector))
    if detector_inputs[detector]:
        collapse_switch_callback(app, detector)
        for input_name in detector.value[extract_title(detector)].input_display:
            detector_with_param.append((extract_title(detector), input_name))

for context in AvailableSituationsExt:
    if context_helps[context]:
        modal_callback(app, extract_title(context))

for modal in modal_ids:
    modal_callback(app, modal)


@app.callback(
    Output(global_signal_id_maker(GUIDANCE_TITLE), 'children'),
    Output(temp_jobs_store_id_maker(GUIDANCE_TITLE), 'data'),
    Output(form_persistence_id_maker(DEV_CTX_TITLE), 'data'),
    Input(compute_button_id(compute_title), 'n_clicks'),
    [
        State(checklist_id_maker(extract_title(context) + '-' + titles[0]), 'value') for context in
        AvailableSituationsExt
    ] +
    [
        State(checklist_id_maker(extract_title(context) + '-' + titles[1]), 'value') for context in
        AvailableSituationsExt
    ] +
    [
        State(checklist_id_maker(extract_title(context) + '-' + titles[2]), 'value') for context in
        AvailableSituationsExt
    ] +
    [
        State(dropdown_id_maker(extract_title(context) + '-' + titles[3]), 'value') for context in
        AvailableSituationsExt
    ] +
    [
        State(dropdown_id_maker(context_range), 'value')
    ] + [
        State(dropdown_id_maker(context_granularity), 'value')
    ],
    [
        State(checklist_id_maker(extract_title(detector)), 'on') for detector in AvailableDetectorsExt
    ] +
    [
        State(input_id(title + SEP + param), 'value') for title, param in detector_with_param
    ] +
    [
        State(global_form_load_signal_id_maker(GLOBAL_FORM_SIGNAL), 'children'),
        State(form_persistence_id_maker(CORR_OUT_TITLE), 'data'),
        State(global_signal_id_maker(DEV_CTX_TITLE), 'children'),
        State(temp_jobs_store_id_maker(CORR_OUT_TITLE), 'data'),
        State(temp_jobs_store_id_maker(CORR_TITLE), 'data'),
        State(temp_jobs_store_id_maker(GUIDANCE_TITLE), 'data'),
        State(form_persistence_id_maker(DEV_CTX_TITLE), 'data')
    ]
)
def run_detect_context(*args):
    if args[0] is not None:
        args = args[1:]
        form_value = args[-7]
        form_corr = args[-6]
        value = args[-5]
        jobs_log = args[-4]
        jobs_data = args[-3]
        temp_jobs = args[-2]
        form = args[-1]

        if value is not None and form_value is not None:
            log_hash_global, date_global = read_global_signal_value(form_value)
            value = read_global_signal_value(value)
            if len(value) == 5:
                log_name, log_hash_local, task_id, method, date_local = value
            else:
                log_hash_local, task_id, method, date_local = value
            date_global = datetime.strptime(date_global, '%Y-%m-%d %H:%M:%S.%f')
            date_local = datetime.strptime(date_local, '%Y-%m-%d %H:%M:%S.%f')
            if date_global < date_local:
                log, log_hash = extract_from_local_value(jobs_log, value)
                if log is None:
                    return no_update(3)
            else:
                log = extract_from_global_value(form, jobs_log, log_hash_global)
                if log is None:
                    return no_update(3)
                log_hash = log_hash_global
        elif value is not None:
            value = read_global_signal_value(value)
            log, log_hash = extract_from_local_value(jobs_log, value)
            if log is None:
                return no_update(3)
        elif form_value is not None:
            log_hash, date = read_global_signal_value(form_value)
            if form_corr is not None and log_hash in form_corr and CORR_METHOD in form_corr[log_hash]:
                log = extract_from_global_value(form_corr, jobs_log, log_hash)
                if log is None:
                    return no_update(3)
            else:
                return no_update(3)
        else:
            return no_update(3)
        user = request.authorization['username']
        oc_data = get_remote_data(user, log_hash, jobs_data, AvailableTasks.PARSE.value)
        if oc_data is None:
            return no_update(3)

        # CONTEXT
        # Include
        includes_bool = [len(arg) == 1 for arg in args[0:offset]]
        includes = [extract_title(context) for context, arg in zip(AvailableSituationsExt, includes_bool) if arg]

        # Guide
        guides_bool = [len(arg) == 1 for arg in args[offset: 2 * offset]]
        guides = [extract_title(context) for context, arg in zip(AvailableSituationsExt, guides_bool) if arg]

        # Disable
        disables_bool = [len(arg) == 1 for arg in args[2 * offset: 3 * offset]]

        # Type
        types = [arg for arg in args[3 * offset: 4 * offset]]

        # Range / Stability
        drift = args[4 * offset]

        # Granularity
        granularity = args[4 * offset + 1]

        if granularity == 'Day':
            # Weekly Schedule Pattern is solely computed on hours per week, so a granularity of days does not permit
            # this
            disables_bool[2] = True

        # Disabled > Guide > Include
        includes_guides = {extract_title(context): typ
                           for inc, gui, dis, context, typ in zip(includes_bool, guides_bool, disables_bool,
                                                                  AvailableSituationsExt, types)
                           if not dis and (inc or gui)}

        # DETECTION
        # Detection methods
        methods_bool = [arg for arg in args[4 * offset + 2: 4 * offset + 2 + len(AvailableDetectorsExt)]]
        methods = [extract_title(method) for arg, method in
                   zip(methods_bool,
                       AvailableDetectorsExt) if arg]

        # Detection methods' inputs
        current_offset = 4 * offset + 2 + len(AvailableDetectorsExt)
        inputs = {extract_title(detector): {} for detector in AvailableDetectorsExt}
        for index_d, detector in enumerate(AvailableDetectorsExt):
            if detector_inputs[detector]:
                for index, name in enumerate(detector.value[extract_title(detector)].input_display):
                    if methods_bool[index_d]:
                        inputs[extract_title(detector)][name] = args[current_offset]
                    current_offset += 1

        # Form persistence
        if form is None:
            form = {}
        form[log_hash] = get_dev_ctx_form_dict(args, current_offset)

        # context = compute_context(includes_guides, includes, guides, granularity, drift, methods_bool, oc_data, log)

        # detection = compute_detection(methods, inputs, log)
        task_context_id = run_task(jobs_log, log_hash, AvailableTasks.CONTEXT.value, compute_context, temp_jobs,
                                   includes_guides=includes_guides,
                                   includes=includes,
                                   guides=guides,
                                   granularity=granularity,
                                   methods_bool=methods_bool,
                                   drift=drift,
                                   data=oc_data,
                                   log=log)

        task_detect_id = run_task(jobs_log, log_hash, AvailableTasks.DETECT.value, compute_detection, temp_jobs,
                                  versions=methods,
                                  inputs=inputs,
                                  log=log
                                  )
        assign_task_id(jobs_log, log_hash, AvailableTasks.CONTEXT.value, task_context_id)
        assign_task_id(jobs_log, log_hash, AvailableTasks.DETECT.value, task_detect_id)
        return write_global_signal_value([log_hash, task_context_id, task_detect_id]), jobs_log, form
        # return dash.no_update, jobs_log, form
    else:
        return no_update(3)


@app.callback(
    Output(global_url_signal_id_maker(RESULT_TITLE), 'children'),
    Output(global_signal_id_maker(RESULT_TITLE), 'children'),
    Output(temp_jobs_store_id_maker(RESULT_TITLE), 'data'),
    Input(global_signal_id_maker(GUIDANCE_TITLE), 'children'),
    State(temp_jobs_store_id_maker(GUIDANCE_TITLE), 'data'),
    State(temp_jobs_store_id_maker(RESULT_TITLE), 'data'),
    State(temp_jobs_store_id_maker(CORR_TITLE), 'data'),
)
def init_guidance(value, jobs_guidance, jobs_result, jobs_data):
    user = request.authorization['username']
    if value is not None:
        log_hash, task_context_id, task_detect_id = read_global_signal_value(value)
        oc_data = get_remote_data(user, log_hash, jobs_data, AvailableTasks.PARSE.value)
        if oc_data is None:
            return no_update(3)
        detection_dict = get_remote_data(user, log_hash, jobs_guidance, AvailableTasks.DETECT.value)
        if detection_dict is None:
            return no_update(3)
        context_dict = get_remote_data(user, log_hash, jobs_guidance, AvailableTasks.CONTEXT.value)
        if context_dict is None:
            return no_update(3)
        jobs_delete = deepcopy(jobs_guidance)
        #guidance = compute_guidance(oc_data, detection_dict, context_dict)
        task_id = run_task(jobs_guidance, log_hash, AvailableTasks.GUIDE.value, compute_guidance, jobs_result,
                           oc_data=oc_data,
                           detection_dict=detection_dict,
                           context_dict=context_dict)
        task_detection = get_task(jobs_delete, log_hash, AvailableTasks.DETECT.value)
        task_context = get_task(jobs_delete, log_hash, AvailableTasks.CONTEXT.value)
        task_detection.forget()
        remove_redis(task_detection.id)
        task_context.forget()
        remove_redis(task_context.id)
        from celery.result import AsyncResult
        res = AsyncResult(task_id, app=celery)
        while not res.ready():
            sleep(2)
        time = str(datetime.now())
        return write_global_signal_value([RESULT_URL,
                                          time]), write_global_signal_value([log_hash,
                                                                             task_id,
                                                                             time]), jobs_guidance
    else:
        return no_update(3)


def extract_from_global_value(form, jobs_log, log_hash):
    user = request.authorization['username']
    if form is not None and log_hash in form and CORR_METHOD in form[log_hash]:
        method, log_name = read_corrout_form_dict(form[log_hash])
    else:
        return None
    if log_name != NA:
        # Multiple logs
        log = get_remote_data(user, log_hash, jobs_log, AvailableTasks.CORR.value)
        if log is None:
            return None
        else:
            log = log[log_name]
    else:
        log = get_remote_data(user, log_hash, jobs_log, AvailableTasks.CORR.value)
    return log


def extract_from_local_value(jobs_log, value):
    user = request.authorization['username']
    if len(value) == 5:
        # Multiple logs
        log_name, log_hash, task_id, method, date = value
        log = get_remote_data(user, log_hash, jobs_log, AvailableTasks.CORR.value)
        log = log[log_name]
    else:
        log_hash, task_id, method, date = value
        log = get_remote_data(user, log_hash, jobs_log, AvailableTasks.CORR.value)
    return log, log_hash


@app.callback(
    [
        Output(checklist_id_maker(extract_title(context) + '-' + titles[0]), 'value') for context in
        AvailableSituationsExt
    ] +
    [
        Output(checklist_id_maker(extract_title(context) + '-' + titles[1]), 'value') for context in
        AvailableSituationsExt
    ] +
    [
        Output(checklist_id_maker(extract_title(context) + '-' + titles[2]), 'value') for context in
        AvailableSituationsExt
    ] +
    [
        Output(dropdown_id_maker(extract_title(context) + '-' + titles[3]), 'value') for context in
        AvailableSituationsExt
    ] +
    [
        Output(dropdown_id_maker(context_range), 'value')
    ] + [
        Output(dropdown_id_maker(context_granularity), 'value')
    ],
    [
        Output(checklist_id_maker(extract_title(detector)), 'on') for detector in AvailableDetectorsExt
    ] +
    [
        Output(input_id(title + SEP + param), 'value') for title, param in detector_with_param
    ],
    Input(global_form_load_signal_id_maker(GLOBAL_FORM_SIGNAL), 'children'),
    State(form_persistence_id_maker(DEV_CTX_TITLE), 'data')
)
def update_persisted_form(value, form):
    if value is not None:
        log_hash, date = read_global_signal_value(value)
        current_offset = 4 * offset + 2 + len(AvailableDetectorsExt)
        for index_d, detector in enumerate(AvailableDetectorsExt):
            if detector_inputs[detector]:
                for index, name in enumerate(detector.value[extract_title(detector)].input_display):
                    current_offset += 1
        # current_offset -= 1
        if form is not None and log_hash in form and len(form[log_hash]) == current_offset:
            return read_dev_ctx_form_dict(form, log_hash)
        else:
            return no_update(offset * 4 + 2 + len(AvailableDetectorsExt) + len(detector_with_param))
    else:
        return no_update(offset * 4 + 2 + len(AvailableDetectorsExt) + len(detector_with_param))


@app.callback(
    [
        Output(DEV_CTX_TITLE + 'title', 'children')
    ] + [
        Output(checklist_id_maker(extract_title(detector)), 'disabled')
        for detector in AvailableDetectorsExt
    ],
    Input(global_signal_id_maker(DEV_CTX_TITLE), 'children'),
    Input(global_form_load_signal_id_maker(GLOBAL_FORM_SIGNAL), 'children'),
    State(temp_jobs_store_id_maker(CORR_OUT_TITLE), 'data'),
    State(form_persistence_id_maker(CORR_OUT_TITLE), 'data')
)
def update_dev_ctx_output(value, form_value, jobs_log, form_corr):
    if value is not None and form_value is not None:
        log_hash_global, date_global = read_global_signal_value(form_value)
        value = read_global_signal_value(value)
        if len(value) == 5:
            log_name, log_hash_local, task_id, method, date_local = value
        else:
            log_hash_local, task_id, method, date_local = value
        date_global = datetime.strptime(date_global, '%Y-%m-%d %H:%M:%S.%f')
        date_local = datetime.strptime(date_local, '%Y-%m-%d %H:%M:%S.%f')
        if date_global < date_local:
            log, log_hash = extract_from_local_value(jobs_log, value)
            if log is None:
                return no_update(1 + len(AvailableDetectorsExt))
        else:
            log = extract_from_global_value(form_corr, jobs_log, log_hash_global)
            if log is None:
                return no_update(1 + len(AvailableDetectorsExt))
            log_hash = log_hash_global
    elif value is not None:
        value = read_global_signal_value(value)
        log, log_hash = extract_from_local_value(jobs_log, value)
        if log is None:
            return no_update(1 + len(AvailableDetectorsExt))
    elif form_value is not None:
        log_hash, date = read_global_signal_value(form_value)
        log = extract_from_global_value(form_corr, jobs_log, log_hash)
        if log is None:
            return no_update(1 + len(AvailableDetectorsExt))
    else:
        return no_update(1 + len(AvailableDetectorsExt))
    if len(log.meta.ress) > 0:
        set_resource_available = tuple(
                [False] * len(AvailableDetectorsExt)
            )
    else:
        set_resource_available = tuple(
                [
                    extract_extension(detector).resource is not None
                    for detector in AvailableDetectorsExt
                ]
            )
    return tuple([page_title + str(get_job_id(jobs_log, log_hash))]) + set_resource_available



# Util functions for causal model
def delete_pos_or_neg(args, index_c, negative, positive):
    if args[index_c + 3 * offset] == AvailableSituationType.POSITIVE.value:
        positive = positive[:len(positive) - 1]
    elif args[index_c + 3 * offset] == AvailableSituationType.NEGATIVE.value:
        negative = negative[:len(negative) - 1]
    return negative, positive


def check_checklist(args, index_c, index_t):
    return len(args[index_c + index_t * offset]) == 0


def assign_pos_or_neg(args, context, index_c, negative, positive):
    if args[index_c + 3 * offset] == AvailableSituationType.POSITIVE.value:
        positive.append(extract_title(context))
    elif args[index_c + 3 * offset] == AvailableSituationType.NEGATIVE.value:
        negative.append(extract_title(context))
