from datetime import datetime

import dash
import dash_core_components as dcc
import dash_html_components as html
from backend.app import app
from backend.components.misc import container, card, global_signal_id_maker, temp_jobs_store_id_maker, button, \
    return_title_maker, return_button_id, form_persistence_id_maker, global_url_signal_id_maker, \
    global_form_load_signal_id_maker, single_row, goto_title_maker, goto_button_id, global_refresh_signal_id_maker
from backend.components.tables import generate_log_output
from backend.param.available import AvailableCorrelationsExt
from backend.param.constants import CORR_OUT_TITLE, TRACE_SIGNAL, CB_TYPE_INSPECT, DEV_CTX_TITLE, \
    CB_TYPE_LOG, CORR_URL, DEV_CTX_URL, TRACE_URL, SEP, NA, \
    GLOBAL_FORM_SIGNAL, CORR_OUT_URL, CORR_METHOD
from backend.param.styles import BUTTON_LEFT_STYLE
from backend.tasks.tasks import get_remote_data, get_task_id
from backend.util import read_global_signal_value, get_job_id, no_update, \
    get_corrout_form_dict, read_corrout_form_dict
from contect.available.available import AvailableTasks
from dash.dependencies import Input, Output, State, ALL
from flask import request

page_title = "Correlated Event Log for Job ID "
return_correlate = "return-correlate"
goto_title = "Deviation & Context"

buttons = [button(return_correlate, return_title_maker, return_button_id, href=CORR_URL),
           button(goto_title, goto_title_maker, goto_button_id, href=DEV_CTX_URL, style=BUTTON_LEFT_STYLE)]

page_layout = container(page_title,
                        [
                            dcc.Loading(
                                id=f"loading-1",
                                type="default",
                                children=card(
                                    [
                                        single_row(html.Div(buttons), 'end'),
                                        html.Br(),
                                        html.Div(id=CORR_OUT_TITLE)
                                    ])),
                        ], CORR_OUT_TITLE + 'title')


@app.callback(
    Output(CORR_OUT_TITLE, 'children'),
    Output(CORR_OUT_TITLE + 'title', 'children'),
    Input(global_refresh_signal_id_maker(CORR_OUT_URL), 'children'),
    Input(global_form_load_signal_id_maker(GLOBAL_FORM_SIGNAL), 'children'),
    Input(global_signal_id_maker(CORR_OUT_TITLE), 'children'),
    State(temp_jobs_store_id_maker(CORR_OUT_TITLE), 'data'),
    State(form_persistence_id_maker(CORR_OUT_TITLE), 'data')
)
def update_log_output(date, form_value, value, jobs, form):
    if value is None and form_value is None:
        return no_update(2)
    else:
        if value is not None and form_value is not None:
            log_hash_global, date_global = read_global_signal_value(form_value)
            log_hash_local, task_id, method, date_local = read_global_signal_value(value)
            date_global = datetime.strptime(date_global, '%Y-%m-%d %H:%M:%S.%f')
            date_local = datetime.strptime(date_local, '%Y-%m-%d %H:%M:%S.%f')
            if date_global < date_local:
                log_hash = log_hash_local
            else:
                log_hash = log_hash_global
                method = NA
        elif value is not None:
            log_hash, task_id, method, date = read_global_signal_value(value)
        elif form_value is not None:
            log_hash, date = read_global_signal_value(form_value)
            method = NA
        else:
            return no_update(2)
        if method == NA:
            if form is not None and log_hash in form and CORR_METHOD in form[log_hash]:
                method, log_name = read_corrout_form_dict(form[log_hash])
        user = request.authorization['username']
        log = get_remote_data(user, log_hash, jobs, AvailableTasks.CORR.value)
        if log is None:
            return no_update(2)
        task_id = str(datetime.now())
        return generate_log_output(log, log_hash, task_id, method, isinstance(log, dict)), \
               page_title + str(get_job_id(jobs, log_hash))


@app.callback(
    [
        Output(global_url_signal_id_maker(CORR_OUT_TITLE), 'children')
    ] +
    [
        Output(global_signal_id_maker(TRACE_SIGNAL), 'children'),
        Output(global_signal_id_maker(DEV_CTX_TITLE), 'children'),
        Output(form_persistence_id_maker(CORR_OUT_TITLE), 'data')
    ],
    [
        Input({'type': CB_TYPE_INSPECT, 'index': ALL}, 'n_clicks'),
        Input({'type': CB_TYPE_LOG, 'index': ALL}, 'n_clicks')
    ],
    [
        State({'type': CB_TYPE_INSPECT, 'index': ALL}, 'id'),
        State({'type': CB_TYPE_LOG, 'index': ALL}, 'id')
    ] + [
        State(form_persistence_id_maker(CORR_OUT_TITLE), 'data')
    ]
)
def return_use_inspect(inspect_n, use_n, inspect_index, use_index, form):
    if all([len(n) == 0 for n in [inspect_n, use_n]]) or (all([n is None for n in inspect_n])
                                                          and all([n is None for n in use_n])):
        return no_update(4)
    else:
        triggered = [t["prop_id"] for t in dash.callback_context.triggered]
        if CB_TYPE_LOG in triggered[0]:
            # Use Log triggered
            if form is None:
                form = {}
            if not list(AvailableCorrelationsExt.OBJ_PATH_CORRELATION.value.keys())[0] in triggered[0]:
                # Single log
                log_hash, task_id, method = read_global_signal_value(use_index[0]['index'])
                form[log_hash] = get_corrout_form_dict(NA, method)
                return DEV_CTX_URL + SEP + str(datetime.now()), dash.no_update, use_index[0]['index'] + SEP + str(
                    datetime.now()), form
            else:
                # Multiple logs
                log_name = triggered[0].split(SEP)[0].split('"')[3]
                for use_log in use_index:
                    if log_name == use_log['index'].split(SEP)[0]:
                        log_name, log_hash, task_id, method = read_global_signal_value(use_log['index'])
                        form[log_hash] = get_corrout_form_dict(log_name, method)
                        return DEV_CTX_URL + SEP + str(datetime.now()), dash.no_update, use_log['index'] + SEP + str(
                            datetime.now()), form
                log_name, log_hash, task_id, method = read_global_signal_value(use_index[0]['index'])
                form[log_hash] = get_corrout_form_dict(log_name, method)
                return DEV_CTX_URL + SEP + str(datetime.now()), dash.no_update, use_index[0]['index'] + SEP + str(
                    datetime.now()), form
        else:
            # Inspect trace triggered
            tid = int(triggered[0].split(SEP)[3].split('"')[0])
            return TRACE_URL + SEP + str(datetime.now()), inspect_index[tid]['index'] + SEP + str(
                datetime.now()), dash.no_update, dash.no_update
