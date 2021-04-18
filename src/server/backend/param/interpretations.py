import dash_html_components as html
import dash_core_components as dcc
from contect.available.available import AvailableNormRanges
from contect.available.constants import HOURS_IN_YEAR, HOURS_IN_MONTH


def get_rng_interpretation(rng):
    if AvailableNormRanges.GLOBAL in rng:
        rng = 'complete timespan'
    else:
        if rng[AvailableNormRanges.BINS] == HOURS_IN_YEAR:
            rng = 'year'
        elif rng[AvailableNormRanges.BINS] == HOURS_IN_MONTH:
            rng = 'month'
        else:
            rng = 'week'
    return rng


def aggregate_interpretation(ctx_val, date, event_table, inspect_trace_buttons):
    return [
        html.Div(f'On {date} the average aggregate context for events were\n: '
                 f'{ctx_val}. This is an average over aggregate contexts of all events, '
                 f'presented below: \n:'),
        html.Br(),
        event_table,
        html.Br(),
        html.Div(
            'You can inspect each event by looking at its associated trace after clicking on the respective '
            'inspect trace button\n:'),
        html.Br(),
        html.Div(inspect_trace_buttons),
        html.Br(),
        html.Div(f'An aggregate context is the average over '
                 f' different contexts and their respective selections, which you can see in the graphs below'
                 f' (with the exception '
                 f'that if you have used mode include \'Time Unit Performance\' their overall weight equals '
                 f'the weights of the other context\'s weights).')
    ]


def single_trace_interpretation(ps_ctx_val, ng_ctx_val, start, end, tid, ps_context_table, ng_context_table,
                                inspect_trace_button):
    return [
        dcc.Markdown(f'Over the period from *{start}* to *{end}* the average positive context for **trace {tid}** was '
                     f'**{ps_ctx_val}** and the average negative context was **{ng_ctx_val}**. '
                     f'These are weighted averages over **maximum** positive / negative contexts of '
                     f'all the trace\'s events '
                     f'with equal weights for all respective contexts'
                     f' except for the case '
                     f'that if you have used mode include for \'Time Unit Performance\'. Then, '
                     f'its selections\' overall weights equal '
                     f'the weights of the other context\'s weights in order to avoid overemphasis. '
                     f'The respective events and their interpretation of individual contexts is presented below:'),
        html.Br(),
        dcc.Markdown('**Positive Context**'),
        ps_context_table,
        html.Br(),
        dcc.Markdown('**Negative Context**'),
        ng_context_table,
        html.Br(),
        html.Div(inspect_trace_button),
    ]


def out_of_range_interpretation(text):
    return [html.Div(f'The data point {text} falls outside of the time range of your uploaded data.')]


def single_unit_performance_interpretation(metric, anti, unit, val, rng, sel):
    rng = get_rng_interpretation(rng)
    if anti:
        return f'During this {unit} the difference of matching {sel} event\'s last {rng}\' maximal {unit} {metric} and this {unit}\'s' \
               f' {metric} was {round(100 * val, 0) if isinstance(val, float) else "100 * x"} ' \
               f'% of the last {rng}\'s maximal {unit} {metric}.'
    else:
        return f'During this {unit} {round(100*val, 0) if isinstance(val, float) else "100 * x"} % of the matching {sel} event\'s last {rng}\'s maximal {unit} {metric} occurred.'


def unit_performance_interpretation(directly, metric, anti, rng, date, sel, unit, ctx_val, event_table, inspect_traces,
                                    entity_table):
    rng = get_rng_interpretation(rng)
    return [
               html.Div(f'On {date} the {metric} of {sel} events were\n: '),
               html.Br(),
               entity_table,
               html.Br(),
               html.Div(f'As the {directly} performance context identifies the {unit}ly context as '
                        f'{anti} the ratio of the respective date\'s {metric} (figures shown above) '
                        f'and the maximum {metric} of the last {rng}, '
                        f'the following event\'s context values are the respective ratios for each event '
                        f'after association with '
                        f'the corresponding value of the above shown counts. These ratios are shown in the following\n:'),
               html.Br(),
               event_table,
               html.Br(),
               html.Div(
                   'You can inspect each event by looking at its associated trace after clicking on the respective '
                   'inspect trace button\n:')] + inspect_traces + [
               html.Div(
                   f'Finally, the calendar view depicts the average of those actually associated ratios over all events '
                   f'on {date}. This average equals {ctx_val}')
           ]


def single_pattern_interpretation(anti, unit, val, rng, sel):
    rng = get_rng_interpretation(rng)
    if anti:
        return f'During this hour the difference of the hourly count and the median of the matching {sel} event\'s last {rng} was ' \
               f' {round(100* (1 - val), 0) if isinstance(val, float) else "100 * (1 - x)"} % of the difference of last {rng}\' maximal and median hourly count. ' \
               f'However,' \
               f'the guidance revealed, ' \
               f'that the relationship should be reversed, so it is 1 subtracted by the above value.'
    else:
        return f'During this hour the difference of the hourly count and the median of the matching {sel} event\'s last {rng} was ' \
               f' {round(100*val, 0) if isinstance(val, float) else "100 * val"} % of the difference of last {rng}\' maximal and median hourly count.'


def schedule_pattern_interpretation(anti, rng, date, sel, unit, ctx_val, event_table, inspect_traces, entity_table):
    rng = get_rng_interpretation(rng)
    return [
               html.Div(f'On {date} the counts of {sel} events were\n: '),
               html.Br(),
               entity_table,
               html.Br(),
               html.Div(f'As the schedule pattern context always identifies the {unit}ly context as '
                        f'{anti} the ratio of the respective date\'s hourly count (figures shown above) '
                        f'minus the median of the last {rng} '
                        f'divided by the difference of the maximum and median of the last {rng}, '
                        f'the following event\'s context values are the respective ratios for each event '
                        f'after association with '
                        f'the corresponding value of the above shown counts. These ratios are shown in the following\n:'),
               html.Br(),
               event_table,
               html.Br(),
               html.Div(
                   'You can inspect each event by looking at its associated trace after clicking on the respective '
                   'inspect trace button\n:')] + inspect_traces + [
               html.Div(
                   f'Finally, the calendar view depicts the average of those actually associated ratios over all events '
                   f'on {date}. This average equals {ctx_val}')
           ]


def single_capacity_interpretation(anti, unit, val, rng, sel):
    rng = get_rng_interpretation(rng)
    if anti:
        return f'During this {unit} the difference of matching {sel} event\'s last {rng}\' maximal {unit} load and this {unit}\'s' \
               f' load was {round(100 * val, 0) if isinstance(val, float) else "100 * x"} % of the last {rng}\' maximal {unit} load.'
    else:
        return f'During this {unit} {round(100*val, 0) if isinstance(val, float) else "100 * x"} % of the matching {sel} event\'s last {rng}\' maximal {unit} load occurred.'


def capacity_interpretation(anti, rng, date, sel, unit, ctx_val, event_table, inspect_traces, entity_table):
    rng = get_rng_interpretation(rng)
    return [
               html.Div(f'On {date} the load of {sel} events were\n: '),
               html.Br(),
               entity_table,
               html.Br(),
               html.Div(f'As the capacity performance context identifies the {unit}ly context as '
                        f'{anti} the ratio of the respective date\'s {sel}\'s load (figures shown above) '
                        f'and the maximum {sel}\'s load of the last {rng}, '
                        f'the following event\'s context values are the respective ratios for each event '
                        f'after association with '
                        f'the corresponding value of the above shown counts. These ratios are shown in the following\n:'),
               html.Br(),
               event_table,
               html.Br(),
               html.Div(
                   'You can inspect each event by looking at its associated trace after clicking on the respective '
                   'inspect trace button\n:')] + inspect_traces + [
               html.Div(
                   f'Finally, the calendar view depicts the average of those actually associated ratios over all events '
                   f'on {date}. This average equals {ctx_val}')
           ]
