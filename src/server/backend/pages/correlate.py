from datetime import datetime
from time import sleep

import dash
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
from backend.app import app
from backend.components.misc import container, card, single_row, button, tooltip_button, tooltip_button_id, \
    global_signal_id_maker, temp_jobs_store_id_maker, compute_title_maker, compute_button_id, form_persistence_id_maker, \
    return_title_maker, return_button_id, global_form_load_signal_id_maker, goto_button_id, goto_title_maker
from backend.components.tables import create_data_table, create_oc_data_dfs
from backend.components.userforms import dropdown, dropdown_id_maker
from backend.param.available import AvailableCorrelationsExt, get_available_from_name
from backend.param.colors import SECONDARY_VERY_LIGHT
from backend.param.constants import CORR_TITLE, CORR_OUT_TITLE, CORR_OUT_URL, GLOBAL_FORM_SIGNAL, DEFAULT_FORM, \
    CORR_METHOD
from backend.param.styles import BUTTON_LEFT_STYLE
from backend.tasks.tasks import correlate_events, get_remote_data, celery
from backend.util import read_global_signal_value, run_task, \
    guarantee_list_input, get_corr_form_dict, write_global_signal_value, get_job_id, read_corr_form_dict, no_update
from contect.available.available import AvailableTasks
from dash.dependencies import Input, Output, State
from flask import request

goto_title = "Log"
return_upload = "return-upload"
page_title = "Uncorrelated Event Log for Job ID "
activities = 'activities'
object_types = 'object-types'
activity_object_type = 'activity-to-object-types'
value_names = 'value-names'
value_types = 'value-types'
value_type = 'value-to-type'
activity_values = 'activity-to-values'
resources = 'resources'
locations = 'locations'
events = 'events'

cids = [activities, object_types, value_names, value_types, value_type, activity_values,
        resources, locations]

correlation_method = 'correlation-method'
correlation_objects = 'correlation-objects'

correlation_dropdown = dropdown([list(method.value.keys())[0].title() for method in AvailableCorrelationsExt],
                                correlation_method,
                                False)

buttons = [button(CORR_TITLE, compute_title_maker, compute_button_id, href=CORR_OUT_URL),
           button(goto_title, goto_title_maker, goto_button_id, href=CORR_OUT_URL, style=BUTTON_LEFT_STYLE)]

correlate_layout = [
    single_row(["Please specify your desired event correlation approach", tooltip_button('correlate'), " :"]
               ),
    single_row(correlation_dropdown),
    html.Br(),
    single_row("Select a set of object types to use for the event correlation approach:"),
    single_row(html.Div(dropdown(['NA'], correlation_objects), id=correlation_objects)),
    html.Br(),
    single_row(html.Div(buttons), 'end')

]

correlate_tooltip = '''
 The **shared object id (minimum)** event correlation works best for customer-facing business processes that have a single or multiple object identifiers of a single or multiple object types shared in each event to be correlated. The result are traces with events that share object identifiers of your specified object type(s). 
 The **shared object id (partition, minimum)** event correlation always partitions the set of events, whereas the aforementioned method correlates batch events (events with multiple object identifiers of your specified object type) into each trace whose events share one of the multiple object identifiers of the batch event. 
                     The **shared object id maximum** event correlation is best suited for production processes where batch events are recording activities of combining multiple components and all the preceding as well as succeeding activities of one of the involved components shall be correlated into one trace. 
                     '''

summary_layout = [html.H3('Activities'),
                  html.Div(id=activities),
                  html.Br(),
                  html.H3('Object Types'),
                  html.Div(id=object_types),
                  html.Br(),
                  html.H3('Value Names'),
                  html.Div(id=value_names),
                  html.Br(),
                  html.H3('Value Types'),
                  html.Div(id=value_types),
                  html.Br(),
                  html.H3('Value-Name-to-Type Map'),
                  html.Div(id=value_type),
                  html.Br(),
                  html.H3('Activity-to-Values Map'),
                  html.Div(id=activity_values),
                  html.Br(),
                  html.Div(id=resources),
                  html.Br(),
                  html.Div(id=locations)]

summary_tab = dcc.Loading(
    id=f"loading-3",
    type="default",
    children=card(
        [
            button(return_upload,
                   return_title_maker,
                   return_button_id,
                   href='/home'),
            single_row(html.H2("Correlation Approach")),
            dbc.Modal(
                [
                    dbc.ModalHeader("Correlation Method Help", style={"font-size": "x-large",
                                                                      "font-weight": "bolder"}),
                    dbc.ModalBody(dcc.Markdown(correlate_tooltip,
                                               style={"font-size": "medium",
                                                      "text-align": "justify",
                                                      "text-justify": "inter-word"})),
                    dbc.ModalFooter(
                        dbc.Button("Close", id="correlate-close", className="ml-auto")
                    ),
                ],
                id="modal",
                size="lg"
            ),
            html.Br(),
            single_row(correlate_layout),
            html.Hr(),
            single_row(html.H2("Object-centric Event Data - Summary"))
        ] + summary_layout
    )
)

event_tab = dcc.Loading(
    id=f"loading-2",
    type="default",
    children=card(
        [
            button(return_upload,
                   return_title_maker,
                   return_button_id,
                   href='/home'),
            single_row(html.H2("Events")),
            html.Div(id=events)
        ]
    )
)

page_layout = container(page_title,
                        [
                            dbc.Tabs(
                                [
                                    dbc.Tab(summary_tab, label="Correlate & Summary", tab_id="data-summary"),
                                    dbc.Tab(event_tab, label="Events", tab_id="data-events")
                                ]
                            )
                        ], CORR_TITLE + 'title')


@app.callback(
    Output(global_signal_id_maker(CORR_OUT_TITLE), 'children'),
    Output(temp_jobs_store_id_maker(CORR_OUT_TITLE), 'data'),
    Output(form_persistence_id_maker(CORR_TITLE), 'data'),
    Input(compute_button_id(CORR_TITLE), 'n_clicks'),
    State(global_form_load_signal_id_maker(GLOBAL_FORM_SIGNAL), 'children'),
    State(global_signal_id_maker(CORR_TITLE), 'children'),
    State(dropdown_id_maker(correlation_method), 'value'),
    State(dropdown_id_maker(correlation_objects), 'value'),
    State(temp_jobs_store_id_maker(CORR_TITLE), 'data'),
    State(temp_jobs_store_id_maker(CORR_OUT_TITLE), 'data'),
    State(form_persistence_id_maker(CORR_TITLE), 'data')
)
def run_correlate_log(n, value, value_old, method, objects, jobs, temp_jobs, form):
    if n is not None:
        objects = guarantee_list_input(objects)
        if value is None:
            value = value_old
        log_hash, dummy = read_global_signal_value(value)
        if form is None:
            form = {}
        form[log_hash] = get_corr_form_dict(method, objects)
        user = user = request.authorization['username']
        oc_data = get_remote_data(user, log_hash, jobs, AvailableTasks.PARSE.value)
        if oc_data is None:
            return no_update(3)
        task_id = run_task(jobs, log_hash, AvailableTasks.CORR.value, correlate_events, temp_jobs,
                           data=oc_data,
                           user_ot_selection=objects,
                           version=method
                           )
        from celery.result import AsyncResult
        res = AsyncResult(task_id, app=celery)
        while not res.ready():
            sleep(1)
        return write_global_signal_value([log_hash, task_id, method, str(datetime.now())]), jobs, form
    else:
        return no_update(3)


@app.callback(
    [
        Output(dropdown_id_maker(correlation_method), 'value'),
        Output(correlation_objects, 'children'),
        Output(CORR_TITLE + 'title', 'children'),
        Output(events, 'children')
    ] +
    [
        Output(cid, 'children') for cid in cids
    ],
    Input(global_form_load_signal_id_maker(GLOBAL_FORM_SIGNAL), 'children'),
    Input(global_signal_id_maker(CORR_TITLE), 'children'),
    State(temp_jobs_store_id_maker(CORR_TITLE), 'data'),
    State(form_persistence_id_maker(CORR_TITLE), 'data')
)
def update_correlate_output(form_value, value, jobs, form):
    if value is None and form_value is None:
        return tuple([dash.no_update] * 12)
    else:
        triggered = [t["prop_id"] for t in dash.callback_context.triggered]
        if CORR_TITLE in triggered[0]:
            set_value = False
            log_hash, task_id = read_global_signal_value(value)
        else:
            log_hash, date = read_global_signal_value(form_value)
            if form is not None and log_hash in form and CORR_METHOD.title() in form[log_hash]:
                set_value = True
                method, objects = read_corr_form_dict(form[log_hash])
            else:
                set_value = False
        user = request.authorization['username']
        oc_data = get_remote_data(user, log_hash, jobs, AvailableTasks.PARSE.value)
        if oc_data is None:
            return no_update(12)
        df_act_val, df_acts, df_ots, df_vals, df_valt, df_valtt, loc_out, meta, res_out, df_events = \
            create_oc_data_dfs(oc_data)
        return dash.no_update if not set_value else method, \
               dropdown(meta.obj_types, correlation_objects,
                        True,
                        set_value=set_value,
                        persisted=None if not set_value else objects), \
               page_title + str(get_job_id(jobs, log_hash)), \
               create_data_table(None, df_events, None, 20), \
               create_data_table(None, df_acts, None, len(df_acts), SECONDARY_VERY_LIGHT, 'medium'), \
               create_data_table(None, df_ots, None, len(df_ots), SECONDARY_VERY_LIGHT, 'medium'), \
               create_data_table(None, df_vals, None, len(df_vals), SECONDARY_VERY_LIGHT, 'medium'), \
               create_data_table(None, df_valt, None, len(df_valt), SECONDARY_VERY_LIGHT, 'medium'), \
               create_data_table(None, df_valtt, None, len(df_valtt)), \
               create_data_table(None, df_act_val, None, len(df_act_val)), \
               res_out, \
               loc_out


@app.callback(
    Output("modal", "is_open"),
    [
        Input(tooltip_button_id('correlate'), "n_clicks"),
        Input("correlate-close", "n_clicks")
    ],
    [
        State("modal", "is_open")
    ],
)
def toggle_modal(n1, n2, is_open):
    if n1 or n2:
        return not is_open
    return is_open
