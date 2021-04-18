from datetime import datetime

import dash

from backend.components.misc import collapse_button_id, tooltip_button_id, modal_id, modal_close_button_id, \
    checklist_id_maker, collapse_id, toast_id, temp_jobs_store_id_maker, global_signal_id_maker, \
    global_form_load_signal_id_maker
from backend.components.tables import generate_interpretation_for_trace, get_context_data, \
    generate_agg_context_interpretations, generate_detailed_interpreter
from backend.param.available import extract_title, sit_shortcut
from backend.param.interpretations import aggregate_interpretation, out_of_range_interpretation
from backend.param.constants import RESULT_TITLE, GLOBAL_FORM_SIGNAL, RESULT_INIT, CB_TYPE_INTERPRETATION
from contect.available.constants import ANTI_KEY
from backend.util import read_global_signal_value, no_update
from contect.available.available import AvailableSituationType, AvailableSelections, AvailableSituations
from dash.dependencies import Output, Input, State, ALL


def collapse_switch_callback(app, detector):
    @app.callback(
        Output(collapse_id(extract_title(detector)), "is_open"),
        Input(checklist_id_maker(extract_title(detector)), "on")
    )
    def toggle_collapse(val):
        return val


def collapse_button_callback(app, title):
    @app.callback(
        Output(title, "is_open"),
        Input(collapse_button_id(title), "n_clicks"),
        State(title, "is_open"),
    )
    def toggle_collapse(n, is_open):
        if n:
            return not is_open
        return is_open


def tab_callback(app, idx, ids, output, output_val):
    @app.callback(
        output,
        [Input(idx, "active_tab")]
    )
    def on_switch_tab(at):
        if at == ids[0]:
            return output_val
        else:
            return output_val


def modal_callback(app, title):
    @app.callback(
        Output(modal_id(title), 'is_open'),
        Input(tooltip_button_id(title), "n_clicks"),
        Input(modal_close_button_id(title), "n_clicks"),
        State(modal_id(title), "is_open")
    )
    def toggle_modal(n1, n2, is_open):
        if n1 or n2:
            return not is_open
        return is_open


def toast_summary_list_callback(app, title, det, target):
    @app.callback(
        Output(toast_id(title), 'is_open'),
        Output(toast_id(title), 'children'),
        Input({'type': CB_TYPE_INTERPRETATION, 'index': ALL, 'target': target}, 'n_clicks'),
        State(temp_jobs_store_id_maker(RESULT_TITLE), 'data')
    )
    def init_toggle_toast(*args):
        jobs = args[-1]
        ns = args[:-1]
        if len(ns[0]) == 0 or all([i is None for i in ns[0]]):
            return no_update(2)
        else:
            triggered = [t["prop_id"] for t in dash.callback_context.triggered]
            value = triggered[0].split('"')[3]
            result, log_hash, tid, ps_ctx_val, ng_ctx_val, start, end = read_global_signal_value(value)
            tid = int(tid)
            ps_ctx_val = float(ps_ctx_val)
            ng_ctx_val = float(ng_ctx_val)
            interpretation = generate_interpretation_for_trace(end, jobs, log_hash, ng_ctx_val, ps_ctx_val, start, tid, det)
            return True, interpretation


def toast_summary_graph_callback(app, title, det):
    @app.callback(
        Output(toast_id(title), 'is_open'),
        Output(toast_id(title), 'children'),
        Input(title, 'clickData'),
        State(global_signal_id_maker(RESULT_TITLE), 'children'),
        State(global_form_load_signal_id_maker(GLOBAL_FORM_SIGNAL), 'children'),
        State(temp_jobs_store_id_maker(RESULT_TITLE), 'data')
    )
    def init_toggle_toast(click, value, form_value, jobs):
        if click is None:
            return no_update(2)
        log_hash = read_values(form_value, value)
        # if log_hash is None: return no_update(2)
        hover = 'hovertext'
        if hover not in click['points'][0]:
            # No trace selected
            return no_update(2)
        tid = click['points'][0]['hovertext']
        ps_ctx_val = float(click['points'][0]['x'])
        ng_ctx_val = float(click['points'][0]['y'])
        start = click['points'][0]['customdata'][2]
        end = click['points'][0]['customdata'][3]
        interpretation = generate_interpretation_for_trace(end, jobs, log_hash, ng_ctx_val, ps_ctx_val, start, tid, det)
        return True, interpretation


def read_values(form_value, value):
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
        log_hash = None
    return log_hash


def toast_context_help_callback(app, title, det,
                                sit=AvailableSituations.UNIT_PERFORMANCE,
                                selection=AvailableSelections.GLOBAL,
                                agg=False,
                                variant=AvailableSituationType.POSITIVE):
    @app.callback(
        Output(toast_id(title), 'is_open'),
        Output(toast_id(title), 'children'),
        Input(title, 'clickData'),
        State(global_signal_id_maker(RESULT_TITLE), 'children'),
        State(global_form_load_signal_id_maker(GLOBAL_FORM_SIGNAL), 'children'),
        State(temp_jobs_store_id_maker(RESULT_INIT), 'data')
    )
    def init_toggle_toast(click, value, form_value, jobs):
        if click is None:
            return no_update(2)
        log_hash = read_values(form_value, value)
        daily_contexts, detector, event_to_traces, granularity, ng, ng_agg_daily_contexts, objects, ps, ps_agg_daily_contexts, rng, vmap_params = get_context_data(
            jobs, log_hash, det)
        if not agg:
            simple_sit = sit_shortcut(sit)
            if simple_sit in daily_contexts[detector][ps] and selection in daily_contexts[detector][ps][simple_sit]:
                typ = ps
            elif simple_sit in daily_contexts[detector][ng] and selection in daily_contexts[detector][ng][simple_sit]:
                typ = ng
            else:
                return no_update(2)
            shift = min(daily_contexts[detector][typ][simple_sit][selection])
            if 'nan' in click['points'][0]['text']:
                tu = int(click['points'][0]['pointNumber'] + shift)
            else:
                tu = int(click['points'][0]['pointNumber'])
            anti = daily_contexts[detector][typ][simple_sit][selection][tu][ANTI_KEY]
            text = click['points'][0]['text']
            if tu < 0:
                return out_of_range_interpretation(text)
            date = text.split(' ')[2]
            ctx_value, entity_table, event_table, inspect_trace_buttons, interpreter = generate_detailed_interpreter(
                anti, daily_contexts, detector, event_to_traces, log_hash, objects, simple_sit, tu, typ, vmap_params,
                sit, selection)
            return True, interpreter(rng,
                                     date,
                                     selection.value,
                                     granularity.value,
                                     ctx_value,
                                     event_table,
                                     inspect_trace_buttons,
                                     entity_table)
        else:
            if variant is AvailableSituationType.POSITIVE:
                shift = min(ps_agg_daily_contexts[detector])
                contexts = ps_agg_daily_contexts
            else:
                shift = min(ng_agg_daily_contexts[detector])
                contexts = ng_agg_daily_contexts
            tu = int(click['points'][0]['pointNumber'] + shift)
            text = click['points'][0]['text']
            if tu < 0:
                return out_of_range_interpretation(text)
            else:
                date = text.split(' ')[2]
            ctx_val, event_table, inspect_trace_buttons = generate_agg_context_interpretations(contexts, detector,
                                                                                               event_to_traces,
                                                                                               log_hash, objects, tu,
                                                                                               vmap_params)
            return True, aggregate_interpretation(ctx_val, date, event_table, inspect_trace_buttons)


