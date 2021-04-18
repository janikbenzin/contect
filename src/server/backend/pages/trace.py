import os
from datetime import datetime

import dash
import dash_html_components as html
from backend.app import app
from backend.components.misc import container, card, global_signal_id_maker, temp_jobs_store_id_maker, button, \
    return_title_maker, return_button_id, global_url_signal_id_maker
from backend.components.tables import generate_trace_output
from backend.param.constants import CORR_OUT_TITLE, TRACE_SIGNAL, CORR_OUT_URL, TRACE_TITLE, \
    TRACE_RESULT_SIGNAL, RESULT_TITLE, RESULT_URL, RESULT_POST, TRACE_RETURN, RESULT_INIT
from backend.param.styles import NO_DISPLAY
from backend.tasks.tasks import get_remote_data
from backend.util import read_global_signal_value, write_global_signal_value, get_job_id, no_update, \
    check_most_recent_task
from contect.available.available import AvailableTasks
from dash.dependencies import Input, Output, State
from flask import request

page_title = "Trace ID "
return_generic = "return"

page_layout = container(page_title,
                        [
                            card(
                                [
                                    button(return_generic,
                                           return_title_maker,
                                           return_button_id
                                           ),
                                    html.Br(),
                                    html.Div(id=TRACE_TITLE),
                                    html.Div(id='return-url', style=NO_DISPLAY)
                                ]),
                        ], TRACE_TITLE + 'title')


@app.callback(
    Output(global_url_signal_id_maker(TRACE_RETURN), 'children'),
    Input(return_button_id(return_generic), 'n_clicks'),
    State('return-url', 'children')
)
def return_to_callee(n, url):
    if n is None:
        return dash.no_update
    else:
        username = request.authorization['username']
        directory = './assets'
        for file_name in os.listdir(directory):
            if file_name.endswith(f'.{username}.png') or file_name.endswith(f'.{username}.dot'):
                os.remove(f'{directory}/{file_name}')
        return write_global_signal_value([url, str(datetime.now())])


@app.callback(
    Output(TRACE_TITLE, 'children'),
    Output(TRACE_TITLE + 'title', 'children'),
    Output('return-url', 'children'),
    Input(global_signal_id_maker(TRACE_SIGNAL), 'children'),
    Input(global_signal_id_maker(TRACE_RESULT_SIGNAL), 'children'),
    State(temp_jobs_store_id_maker(CORR_OUT_TITLE), 'data'),
    State(temp_jobs_store_id_maker(RESULT_TITLE), 'data'),
    State(temp_jobs_store_id_maker(RESULT_POST), 'data'),
    State(temp_jobs_store_id_maker(RESULT_INIT), 'data')
)
def update_trace_output(value, result_value, jobs, jobs_dev_ctx, jobs_post, jobs_context):
    user = request.authorization['username']
    if value is not None and result_value is not None:
        log_name, log_hash_log, task_id, tid_log, date_log = read_global_signal_value(value)
        dummy, log_hash_res, tid_res, date_res = read_global_signal_value(result_value)
        date_log = datetime.strptime(date_log, '%Y-%m-%d %H:%M:%S.%f')
        date_res = datetime.strptime(date_res, '%Y-%m-%d %H:%M:%S.%f')
        if date_log < date_res:
            result = True
            log_hash = log_hash_res
            if check_most_recent_task(jobs_dev_ctx, jobs_post, log_hash):
                log = get_remote_data(user, log_hash, jobs_post, AvailableTasks.POST.value)
            else:
                log = get_remote_data(user, log_hash, jobs_dev_ctx, AvailableTasks.GUIDE.value)
            if log is None:
                return no_update(3)
            tid = int(tid_res)
            url = RESULT_URL
        else:
            result = False
            log_hash = log_hash_log
            log = get_remote_data(user, log_hash, jobs, AvailableTasks.CORR.value)
            if log is None:
                return no_update(3)
            tid = int(tid_log)
            url = CORR_OUT_URL
            if len(log_name) > 0:
                log = log[log_name]
        trace = log.traces[tid]
        return generate_trace_output(trace, log, result, jobs_context, log_hash), \
               page_title + str(tid) + ' of Job ID ' + str(get_job_id(jobs, log_hash)), \
               url
    elif value is not None:
        log_name, log_hash, task_id, tid, date = read_global_signal_value(value)
        log = get_remote_data(user, log_hash, jobs, AvailableTasks.CORR.value)
        if log is None:
            return no_update(3)
        tid = int(tid)
        if len(log_name) > 0:
            log = log[log_name]
        trace = log.traces[tid]
        return generate_trace_output(trace, log), \
               page_title + str(tid) + ' of Job ID ' + str(get_job_id(jobs, log_hash)), \
               CORR_OUT_URL
    elif result_value is not None:
        dummy, log_hash_res, tid_res, date_res = read_global_signal_value(result_value)
        log_hash = log_hash_res
        if check_most_recent_task(jobs_dev_ctx, jobs_post, log_hash):
            log = get_remote_data(user, log_hash, jobs_post, AvailableTasks.POST.value)
        else:
            log = get_remote_data(user, log_hash, jobs_dev_ctx, AvailableTasks.GUIDE.value)
        if log is None:
            return no_update(3)
        tid = int(tid_res)
        trace = log.traces[tid]
        return generate_trace_output(trace, log, True, jobs_context, log_hash), \
               page_title + str(tid) + ' of Job ID ' + str(get_job_id(jobs, log_hash)), \
               RESULT_URL
    else:
        return no_update(3)
