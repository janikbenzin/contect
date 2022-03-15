import numpy as np
import pandas as pd
from backend.param.available import extract_extension, AvailableSituationsExt, get_situation, get_available_from_name
from backend.param.constants import SEP, AGGREGATOR
from contect.available.available import AvailableSelections, AvailableSituationType
from contect.available.constants import GUIDANCE_SKEW, GUIDANCE_P, GUIDANCE_STD, GUIDANCE_PEARSON
from contect.context.initeventcontext import init_events_context, init_log_events_context
from backend.guidance.util import compute_regression_statistics
from scipy import stats
from sklearn.linear_model import LinearRegression


def add_includes(all_sit, context, includes):
    all_sit = all_sit + [(extract_extension(get_available_from_name(sit.value,
                                                                    AvailableSituationsExt.UNIT_PERFORMANCE,
                                                                    AvailableSituationsExt)).available_entity,
                          sit,
                          sel,
                          None)
                         for sit in includes
                         for sel in set(
            context.params[0].selections[
                extract_extension(
                    get_available_from_name(sit.value,
                                            AvailableSituationsExt.UNIT_PERFORMANCE,
                                            AvailableSituationsExt)).available_entity
            ]
        ).intersection(
            set(extract_extension(get_available_from_name(sit.value,
                                                          AvailableSituationsExt.UNIT_PERFORMANCE,
                                                          AvailableSituationsExt)).selections))
                         ]
    return all_sit


def guide_negative(all_sit, antis, df_neg, situation_entity_selection):
    for sit in df_neg.columns:
        situation, selection = sit.split(SEP)[0], sit.split(SEP)[1]
        situation = get_situation(situation)
        selection = get_available_from_name(selection, AvailableSelections.GLOBAL, AvailableSelections)
        entity, selections = situation_entity_selection[situation]
        skewness = stats.skew(df_neg[sit])
        if not abs(skewness) < GUIDANCE_SKEW:
            # Not skewed enough to justify detection of deviations
            if skewness > 0:
                anti = False
            else:
                anti = True
            all_sit.append((entity,
                            situation,
                            selection,
                            None))
            if situation not in antis:
                antis[situation] = {entity: {selection: anti}}
            else:
                antis[situation][entity][selection] = anti


def guide_positive(all_sit, antis, classifiers, descriptive_features, detector, df_pos, log, results,
                   situation_entity_selection):
    # Positive Guidance
    df_pos[detector.value] = [log.traces[tid].score[detector] for tid in log.traces]
    try:
        classifiers[detector.value] = LinearRegression().fit(df_pos[descriptive_features], df_pos[detector.value])
    except ValueError:
        try:
            classifiers[detector.value] = LinearRegression().fit(df_pos[descriptive_features].interpolate(),
                                                                 df_pos[detector.value].interpolate())
        except ValueError:
            return
    results[detector.value] = compute_regression_statistics(classifiers[detector.value],
                                                            df_pos,
                                                            descriptive_features,
                                                            detector.value)
    for index, sit in enumerate(descriptive_features):
        res = results[detector.value]
        situation, selection = sit.split(SEP)[0], sit.split(SEP)[1]
        situation = get_situation(situation)
        selection = get_available_from_name(selection, AvailableSelections.GLOBAL, AvailableSelections)
        entity, selections = situation_entity_selection[situation]
        i = index + 1
        if res.loc[(res['Descriptive feature'] == sit)]['p values'].get(i) <= GUIDANCE_P:
            # significant
            anti = False
            coefficient = res.loc[(res['Descriptive feature'] == sit)]['Coefficients'].get(i)
            if coefficient < 0:
                # Reversed
                anti = True
                coefficient = abs(coefficient)
            all_sit.append((entity,
                            situation,
                            selection,
                            coefficient))
            if situation not in antis:
                antis[situation] = {entity: {selection: anti}}
            else:
                antis[situation][entity][selection] = anti


def build_dataframes(context, guides, log, oc_data, local=False):
    df_pos = pd.DataFrame()
    df_neg = pd.DataFrame()
    typ = AvailableSituationType.POSITIVE
    situation_entity_selection = {}
    for sit in guides:
        entity = extract_extension(
            get_available_from_name(sit.value, AvailableSituationsExt.UNIT_PERFORMANCE,
                                    AvailableSituationsExt)).available_entity
        situation_entity_selection[sit] = (entity, [selection for selection in context.params[0].selections[entity]])
        if sit in context.params[0].situation_param:
            for selection in context.params[0].situation_param[sit].weights:
                init_events_context(oc_data, context, 0,
                                    include_entity=lambda x: x is entity,
                                    include_sit=lambda x: x is sit,
                                    include_sel=lambda x: x is selection)
                init_log_events_context(oc_data, log, AGGREGATOR, 0, local)
                if sit in context.situation[list(context.situation.keys())[0]].typing[typ]:
                    context_values = [log.traces[tid].context[0][typ] for tid in log.traces]
                    if np.std(context_values) > GUIDANCE_STD:
                        # Only context values with sufficient variation are admissible
                        if len(df_pos) == 0:
                            df_pos[sit.value + SEP + selection.value] = [log.traces[tid].context[0][typ] for tid in
                                                                         log.traces]
                        else:
                            admissible = True
                            for feature in df_pos.columns:
                                feature_values = df_pos[feature]
                                if not abs(np.corrcoef(context_values, feature_values)[0, 1]) < GUIDANCE_PEARSON:
                                    # Too correlated with an existing feature
                                    admissible = False
                            if admissible:
                                df_pos[sit.value + SEP + selection.value] = [log.traces[tid].context[0][typ] for tid in
                                                                             log.traces]
                else:
                    df_neg[sit.value + SEP + selection.value] = [log.traces[tid].context[0][AvailableSituationType.NEGATIVE]
                                                                 for tid in log.traces]
    return df_neg, df_pos, situation_entity_selection
