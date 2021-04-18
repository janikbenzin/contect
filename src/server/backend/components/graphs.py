import datetime
from math import floor

import plotly.graph_objs as go
import numpy as np
import dash
from backend.param.available import detector_shortcut, AvailableDetectorsExt, sit_shortcut, AvailableSituationsExt, \
    extract_extension
from backend.param.colors import SECONDARY_LIGHT, INTRINSIC_COLOR, PRIMARY, DETECTION_COLOR, \
    PRIMARY_VERY_LIGHT
from backend.param.constants import INTRINSIC_DEVIATION, EXTERNAL_DEVIATION, NEGATIVE_CONTEXT, DETECTION, FONTSIZE_VIZ, \
    UNKNOWN_CAUSE, EDGE_LBL_CAUSE, EDGE_LBL_DETECT, EDGE_LBL_CONTAIN, COLORSCALE, POSITIVE_CONTEXT, DP
from contect.available.available import AvailableGranularity
import pygraphviz as pgv
from contect.available.constants import HOURS_IN_DAY, SITUATION_AGG_KEY
from plotly.subplots import make_subplots

deviation_pos = 4
sum_nodes = 8


def make_pos_string(pos):
    return str(pos[0]) + "," + str(pos[1]) + "!"


def check_title_len(title):
    if len(title) > 20:
        words = title.split(" ")
        words = [word if index % 3 != 2 else word + "\n" for index, word in enumerate(words)]
        return " ".join(words)
    else:
        return title


def generate_post_graph(positive, detector, negative, score, ca_score, class_title,
                        threshold, old_label, ps, ng, pos, neg):
    """ Creates a visualization of context-aware post-processing

    :param neg: The negative context value
    :param pos: The positive context value
    :param ng: The degree of context-awareness for negative context
    :param ps: The degree of context-awareness for positive context
    :param old_label: The context-unaware classification
    :param threshold: The detector's deviation score threshold
    :param score: The deviation score
    :param ca_score: The context-aware deviation score
    :param class_title: A string for the classification
    :param positive: A list of positive context situations
    :param detector: The detector for this detection
    :param negative: A list of negative context situations
    :return: A graphviz graph
    """
    y_external, y_externals, y_intrinsic, y_intrinsics = generate_node_positions([1,2,3], negative, positive)
    pos_len = len(positive)
    neg_len = len(negative)
    positive_positions = [(0, y_intrinsics[index]) for index in range(pos_len)]
    negative_positions = [(0, y_externals[index]) for index in range(neg_len)]
    negative_pos = (deviation_pos, y_external)
    score_sum_pos = (sum_nodes, y_intrinsic + 2)
    ps_sum_pos = (sum_nodes, y_intrinsic)
    ng_sum_pos = (sum_nodes, y_external)
    ca_pos = (12, y_intrinsic)
    class_pos = (16, y_intrinsic)
    positive_pos = (deviation_pos, y_intrinsic)
    score_pos = (deviation_pos, y_intrinsic + 2)
    score_title = f'The {detector.value} has detected a score of {score}'
    ca_title = f'CA Score: {ca_score}'
    ps_sum_title = f'= {round(pos * score * ps, DP)}'
    ng_sum_title = f'= {round(neg * (1 - score) * ng, DP)}'
    score_sum_title = f'= {score}'
    positive_title = f'{POSITIVE_CONTEXT.title()} has average value of {pos}'
    negative_title = f'{NEGATIVE_CONTEXT.title()} has average value of {neg}'
    G = pgv.AGraph(directed=True)
    G.add_node(positive_title,
                pos=make_pos_string(positive_pos),
                fontsize=FONTSIZE_VIZ,
                color=SECONDARY_LIGHT)
    G.add_node(ps_sum_title,
               pos=make_pos_string(ps_sum_pos),
               fontsize=FONTSIZE_VIZ,
               color=SECONDARY_LIGHT)
    G.add_node(negative_title,
               pos=make_pos_string(negative_pos),
               fontsize=FONTSIZE_VIZ,
               color=INTRINSIC_COLOR)
    G.add_node(ng_sum_title,
               pos=make_pos_string(ng_sum_pos),
               fontsize=FONTSIZE_VIZ,
               color=INTRINSIC_COLOR)
    G.add_node(score_title,
               pos=make_pos_string(score_pos),
               fontsize=FONTSIZE_VIZ)
    G.add_node(score_sum_title,
               pos=make_pos_string(score_sum_pos),
               fontsize=FONTSIZE_VIZ)
    G.add_node(ca_title,
               pos=make_pos_string(ca_pos),
               fontsize=FONTSIZE_VIZ)
    G.add_node(class_title,
               pos=make_pos_string(class_pos),
               fontsize=FONTSIZE_VIZ)
    G.add_edge(positive_title, ps_sum_title,
                label=f'* {round(ps, 2)} * {round(score, 2)}')
    G.add_edge(negative_title, ng_sum_title,
               label=f'* {round(ng, 2)} * (1 - {round(score, 2)})')
    G.add_edge(score_title, score_sum_title,
               label=f'')
    G.add_edge(ps_sum_title, ca_title,
               label=f'-')
    G.add_edge(ng_sum_title, ca_title,
               label=f'+')
    G.add_edge(score_sum_title, ca_title,
               label=f'+')
    decision_label = check_title_len(f'CA score <= threshold ({ca_score} <= {threshold}) and deviation detection label ({old_label}) ?')
    G.add_edge(ca_title, class_title,
               label=decision_label)

    for index, negative_sit in enumerate(negative):
        negative_sit = check_title_len(f'{negative_sit} ')
        G.add_node(negative_sit,
                   pos=make_pos_string(negative_positions[index]),
                   fontsize=FONTSIZE_VIZ)
        G.add_edge(negative_sit, negative_title,
                    label=f'* 1 / {neg_len}')

    for index, positive_sit in enumerate(positive):
        positive_sit = check_title_len(f'{positive_sit} ')
        G.add_node(positive_sit,
                   pos=make_pos_string(positive_positions[index]),
                   fontsize=FONTSIZE_VIZ)
        G.add_edge(positive_sit, positive_title,
                    label=f'* 1 / {pos_len}')
    return G


def generate_causal_graph(positive, classical, negative, result=False, post=False, g=None):
    """ Creates a causal graph using pygraphviz

    :param g: Contains the post-processing graphviz object
    :param post: Determines whether the user has post-processed the results for context-awareness
    :param result: Determines whether the causal graph will be shown for available results or not
    :param positive: A list of positive context situations
    :param classical: A list of classic deviation detection methods
    :param negative: A list of negative context situations
    :return: A graphviz causal graph
    """
    y_external, y_externals, y_intrinsic, y_intrinsics = generate_node_positions(classical, negative, positive)
    positive_positions = [(0, y_intrinsics[index]) for index in range(len(positive))]
    classical_positions = [(12, y_intrinsics[index]) for index in range(len(classical))]
    negative_positions = [(12, y_externals[index]) for index in range(len(negative))]
    external_pos = (deviation_pos, y_external)
    negative_pos = (sum_nodes, y_external)
    unkown_pos = (0, y_external)
    intrinsic_pos = (deviation_pos, y_intrinsic)
    detection_pos = (sum_nodes, y_intrinsic)


    G = pgv.AGraph(directed=True)
    G.add_subgraph(name='Causal Model for Intrinsic Deviations', color=PRIMARY_VERY_LIGHT, style='filled')
    Gi = G.subgraphs()[0]
    G.add_subgraph(name='Causal Model for External Deviations')
    Ge = G.subgraphs()[1]
    if not result or (result and post):
        Ge.add_node(UNKNOWN_CAUSE.title(),
                    pos=make_pos_string(unkown_pos),
                    fontsize=FONTSIZE_VIZ,
                    color=SECONDARY_LIGHT)
        Ge.add_node(EXTERNAL_DEVIATION.title(),
                    color=INTRINSIC_COLOR,
                    pos=make_pos_string(external_pos),
                    fontsize=FONTSIZE_VIZ)
        Ge.add_edge(UNKNOWN_CAUSE.title(), EXTERNAL_DEVIATION.title(),
                    label=EDGE_LBL_CAUSE)
        Ge.add_node(NEGATIVE_CONTEXT.title(),
                    pos=make_pos_string(negative_pos),
                    fontsize=FONTSIZE_VIZ)
        Ge.add_edge(EXTERNAL_DEVIATION.title(), NEGATIVE_CONTEXT.title(),
                    style='dashed',
                    label=EDGE_LBL_DETECT)
        for index, negative_sit in enumerate(negative):
            negative_sit = check_title_len(negative_sit)
            Ge.add_node(negative_sit,
                        pos=make_pos_string(negative_positions[index]),
                        fontsize=FONTSIZE_VIZ)
            Ge.add_edge(NEGATIVE_CONTEXT.title(), negative_sit,
                        style='dashed',
                        label=EDGE_LBL_CONTAIN)

    Gi.add_node(INTRINSIC_DEVIATION.title(),
                color=INTRINSIC_COLOR,
                pos=make_pos_string(intrinsic_pos),
                fontsize=FONTSIZE_VIZ)
    if not result:
        Gi.add_node(DETECTION.title(),
                    color=DETECTION_COLOR,
                    pos=make_pos_string(detection_pos),
                    fontsize=FONTSIZE_VIZ)
        Gi.add_edge(INTRINSIC_DEVIATION.title(), DETECTION.title(),
                    style='dashed',
                    label=EDGE_LBL_DETECT)
    else:
        classical_title = check_title_len(classical[0])
        Gi.add_node(classical_title,
                    pos=make_pos_string(detection_pos),
                    fontsize=FONTSIZE_VIZ)
        Gi.add_edge(INTRINSIC_DEVIATION.title(), classical_title,
                    style='dashed',
                    label=EDGE_LBL_DETECT)

    if not result or (result and post):
        for index, positive_sit in enumerate(positive):
            positive_sit = check_title_len(positive_sit)
            Gi.add_node(positive_sit,
                        color=SECONDARY_LIGHT,
                        pos=make_pos_string(positive_positions[index]),
                        fontsize=FONTSIZE_VIZ)
            Gi.add_edge(positive_sit, INTRINSIC_DEVIATION.title(),
                        color=PRIMARY,
                        label=EDGE_LBL_CAUSE)

    if not result:
        for index, classical_dev in enumerate(classical):
            classical_dev = check_title_len(classical_dev)
            Gi.add_node(classical_dev,
                        pos=make_pos_string(classical_positions[index]),
                        fontsize=FONTSIZE_VIZ)
            Gi.add_edge(DETECTION.title(), classical_dev,
                        style='dashed',
                        label=EDGE_LBL_CONTAIN)
    if result:
        return G
    else:
        return G.to_string()


def generate_node_positions(classical, negative, positive, post_offset=None):
    if post_offset is None:
        max_n = max(len(positive) + len(negative), len(classical) + len(negative))
        if len(negative) != 0:
            ys = [2 * i for i in range(max_n)]
            y_externals = [ys[i] for i in range(len(negative))]
            if len(y_externals) % 2 != 0:
                # Odd
                y_external = y_externals[floor(len(y_externals) / 2)]
            else:
                y_external = y_externals[int(len(y_externals) / 2)] - 1
            offset = len(negative)
        else:
            ys = [2 * i for i in range(max_n + 1)]
            y_externals = [ys[0]]
            y_external = ys[0]
            offset = 1
        max_intrinsic = max(len(positive), len(classical))
        y_intrinsics = [ys[i] for i in range(offset, offset + max_intrinsic)]
        if len(y_intrinsics) % 2 != 0:
            # Odd
            y_intrinsic = y_intrinsics[floor(len(y_intrinsics) / 2)]
        else:
            y_intrinsic = y_intrinsics[int(len(y_intrinsics) / 2)] - 1
        return y_external, y_externals, y_intrinsic, y_intrinsics
    else:
        max_n = max(len(positive) + len(negative), len(classical) + len(negative), 2)
        if len(negative) != 0:
            ys = [2 * i for i in range(post_offset, post_offset + max_n)]
            y_externals = [ys[i] for i in range(len(negative))]
            if len(y_externals) % 2 != 0:
                # Odd
                y_external = y_externals[floor(len(y_externals) / 2)]
            else:
                y_external = y_externals[int(len(y_externals) / 2)] - 1
            offset = len(negative)
        else:
            ys = [2 * i for i in range(post_offset + 1, post_offset + max_n + 1)]
            y_externals = [ys[0]]
            y_external = ys[0]
            offset = 1
        max_intrinsic = max(len(positive), len(classical))
        y_intrinsics = [ys[i] for i in range(offset, offset + max_intrinsic)]
        if len(y_intrinsics) % 2 != 0:
            # Odd
            y_intrinsic = y_intrinsics[floor(len(y_intrinsics) / 2)]
        else:
            y_intrinsic = y_intrinsics[int(len(y_intrinsics) / 2)] - 1
        return y_external, y_externals, y_intrinsic, y_intrinsics


# https://gist.github.com/bendichter/d7dccacf55c7d95aec05c6e7bcf4e66e
# z = np.random.randint(2, size=(500,))
#
# display_years(z, (2019, 2020))
def display_year(z,
                 year: int = None,
                 month_lines: bool = True,
                 fig=None,
                 row: int = None,
                 color: bool=False):
    if year is None:
        year = datetime.datetime.now().year



    data = np.ones(365) * np.nan
    data[:len(z)] = z

    d1 = datetime.date(year, 1, 1)
    d2 = datetime.date(year, 12, 31)

    delta = d2 - d1

    month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    month_days = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    month_positions = (np.cumsum(month_days) - 15) / 7

    dates_in_year = [d1 + datetime.timedelta(i) for i in
                     range(delta.days + 1)]  # gives me a list with datetimes for each day a year
    weekdays_in_year = [i.weekday() for i in
                        dates_in_year]  # gives [0,1,2,3,4,5,6,0,1,2,3,4,5,6,…] (ticktext in xaxis dict translates this to weekdays

    weeknumber_of_dates = [int(i.strftime("%V")) if not (int(i.strftime("%V")) == 1 and i.month == 12) else 53
                           for i in dates_in_year]  # gives [1,1,1,1,1,1,1,2,2,2,2,2,2,2,…] name is self-explanatory
    text = [str(round(data[i], 4) if i < data.shape[0] and data[i] is not np.nan else 'NA') + ' on ' + str(date)
            for i, date in enumerate(dates_in_year)]  # gives something like list of strings like ‘2018-01-25’ for each date. Used in data trace to make good hovertext.
    # 4cc417 green #347c17 dark green
    colorscale = COLORSCALE

    # handle end of year

    data = [
        go.Heatmap(
            x=weeknumber_of_dates,
            y=weekdays_in_year,
            z=data,
            text=text,
            hoverinfo='text',
            xgap=3,  # this
            ygap=3,  # and this is used to make the grid-like apperance
            showscale=True,
            colorscale='Greens' if not color else colorscale,
            colorbar=dict(title='Anomaly Level',
                          thickness=10),
            zmin=0,
            zmax=max(data) if str(max(data)) != 'nan' else 0
        )
    ]

    if month_lines:
        kwargs = dict(
            mode='lines',
            line=dict(
                color='#9e9e9e',
                width=1
            ),
            hoverinfo='skip'

        )
        for date, dow, wkn in zip(dates_in_year,
                                  weekdays_in_year,
                                  weeknumber_of_dates):
            if date.day == 1:
                data += [
                    go.Scatter(
                        x=[wkn - .5, wkn - .5],
                        y=[dow - .5, 6.5],
                        **kwargs
                    )
                ]
                if dow:
                    data += [
                        go.Scatter(
                            x=[wkn - .5, wkn + .5],
                            y=[dow - .5, dow - .5],
                            **kwargs
                        ),
                        go.Scatter(
                            x=[wkn + .5, wkn + .5],
                            y=[dow - .5, -.5],
                            **kwargs
                        )
                    ]

    layout = go.Layout(
        # title='activity chart',
        height=250,
        yaxis=dict(
            showline=False, showgrid=False, zeroline=False,
            tickmode='array',
            ticktext=['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
            tickvals=[0, 1, 2, 3, 4, 5, 6],
            autorange="reversed"
        ),
        xaxis=dict(
            showline=False, showgrid=False, zeroline=False,
            tickmode='array',
            ticktext=month_names,
            tickvals=month_positions
        ),
        font={'size': 10, 'color': '#9e9e9e'},
        plot_bgcolor=('#fff'),
        margin=dict(t=40),
        showlegend=False
    )

    if fig is None:
        fig = go.Figure(data=data, layout=layout)
    else:
        fig.add_traces(data, rows=[(row + 1)] * len(data), cols=[1] * len(data))
        fig.update_layout(layout)
        fig.update_xaxes(layout['xaxis'])
        fig.update_yaxes(layout['yaxis'])

    return fig


def display_years(z, years, color=False):
    fig = make_subplots(rows=len(years), cols=1, subplot_titles=years)
    for i, year in enumerate(years):
        data = z[i * 365: (i + 1) * 365]
        display_year(data, year=year, fig=fig, row=i, color=color)
        fig.update_layout(height=250 * len(years))
    return fig


def create_context_graphs(added, daily_contexts, granularity, log, ng, ng_agg_daily_contexts, years):
    ng_context_graphs = tuple(
        [
            display_years(
                np.array(
                    [
                        ng_agg_daily_contexts[detector_shortcut(detector)][tu][0]
                        for tu in range(added
                                        if granularity is AvailableGranularity.DAY
                                        else int(added / HOURS_IN_DAY),
                                        len(log.timespan.units[granularity])
                                        if granularity is AvailableGranularity.DAY
                                        else int(len(log.timespan.units[granularity]) / HOURS_IN_DAY))
                    ]
                ),
                years,
                True)

            if detector_shortcut(detector) in ng_agg_daily_contexts else dash.no_update

            for detector in AvailableDetectorsExt
        ] + [
            display_years(
                np.array(
                    [
                        daily_contexts[detector_shortcut(detector)][ng][sit_shortcut(sit)][sel][tu][SITUATION_AGG_KEY]
                        for tu in range(added
                                        if granularity is AvailableGranularity.DAY
                                        else int(added / HOURS_IN_DAY),
                                        len(log.timespan.units[granularity])
                                        if granularity is AvailableGranularity.DAY
                                        else int(len(log.timespan.units[granularity]) / HOURS_IN_DAY))
                    ]
                ),
                years,
                True)

            if detector_shortcut(detector) in ng_agg_daily_contexts and
               sit_shortcut(sit) in daily_contexts[detector_shortcut(detector)][ng] and
               sel in daily_contexts[detector_shortcut(detector)][ng][sit_shortcut(sit)]
            else dash.no_update

            for detector in AvailableDetectorsExt
            for sit in AvailableSituationsExt
            for sel in extract_extension(sit).selections
        ]
    )
    return ng_context_graphs