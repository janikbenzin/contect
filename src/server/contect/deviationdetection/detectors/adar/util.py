from typing import List, Dict, Tuple, Union, Optional

from contect.available.available import AvailableADAREventMiners, AvailableSelections, AvailableADARResults, \
    AvailableADARTypes
from contect.deviationdetection.detectors.adar.conditiontypes.factory import get_condition_type
from contect.deviationdetection.detectors.adar.conditiontypes.versions.types import ConditionControlFlow
from contect.deviationdetection.detectors.adar.objects.adar import ADAR
from contect.deviationdetection.detectors.adar.objects.result import ADARResult
from contect.deviationdetection.detectors.adar.mapping.factory import get_matcher
from contect.deviationdetection.util.tracesimilarities import score_jaccard
from contect.parsedata.objects.oclog import Trace, ObjectCentricLog


def support_condition(rule: ADAR,
                      log: ObjectCentricLog,
                      vmap_params: Dict[AvailableSelections, str]) -> Dict[AvailableADAREventMiners, float]:
    return {perspective:
                sum([1 for tid, trace in log.traces.items() if
                     get_matcher(perspective, rule, vmap_params, True)(trace)])
                / len(log.traces)
            for perspective in rule.rule_types}


def match_trace(rule: ADAR,
                trace: Trace,
                vmap_params: Dict[AvailableSelections,
                                  str]) -> Dict[
    AvailableADARResults, Union[List[AvailableADAREventMiners],
                                Dict[AvailableADAREventMiners, ADARResult]]]:
    temp_results = {perspective: get_matcher(perspective, rule, vmap_params, False)(trace)
                    for perspective in rule.rule_types}
    matched = AvailableADARResults.MATCHED
    violating = AvailableADARResults.VIOLATED
    # Merge temp_results / perspective into a single dict keyed by result type
    results = {matched: [],
               violating: {}}
    for perspective in temp_results:
        if matched in temp_results[perspective]:
            # Matched key contains list of matched rules
            results[matched] += [perspective]
        if violating in temp_results[perspective]:
            # Violating key contains dict of perspective to ADARResult for root cause analysis
            results[violating][perspective] = temp_results[perspective][violating]
    return results


def assign_matching(match, rule, trace_matching_sups):
    matching = AvailableADARResults.MATCHED
    if len(match[matching]) > 0:
        for rule_type in match[matching]:
            trace_matching_sups.append(rule.supports[rule_type])


def detect_adar(log: ObjectCentricLog,
                rules: Dict[Tuple[int, int], ADAR],
                trace: Trace,
                vmap_params: Dict[AvailableSelections, str],
                sim_traces: Dict[int, List[
                               Dict[AvailableADARResults,
                                    Union[List[AvailableADAREventMiners], Dict[AvailableADAREventMiners,
                                                                               ADARResult]]]]]
                ) -> Tuple[float,
                           float,
                           Dict[Tuple[int, int],
                                Dict[AvailableADAREventMiners,
                                     ADARResult]],
                           Trace,
                           Dict[int, List[
                               Dict[AvailableADARResults,
                                    Union[List[AvailableADAREventMiners], Dict[AvailableADAREventMiners,
                                                                               ADARResult]]]]]]:
    # Compute all scores for similarity and max is the most similar
    similarities = {tid: score_jaccard(trace, log.traces[tid]) for tid in log.traces if tid != trace.id}
    optimal_sim = max(similarities.items(), key=lambda item: item[1])
    sim_trace = log.traces[optimal_sim[0]]

    trace_matching_sups = []
    sim_trace_matching_sups = []
    trace_violating = {}
    sim_matches = {sim_trace.id: []}

    # Traverse all rules and gather supports of matched rules and ADARResults for violating rules
    for idx, (key, rule) in enumerate(rules.items()):
        match = match_trace(rule, trace, vmap_params)
        if sim_trace.id not in sim_traces:
            sim_match = match_trace(rule, sim_trace, vmap_params)
            sim_matches[sim_trace.id] += [sim_match]
        else:
            sim_match = sim_traces[sim_trace.id][idx]
        assign_matching(match, rule, trace_matching_sups)
        assign_matching(sim_match, rule, sim_trace_matching_sups)
        assign_violating(match, sim_match, trace_violating, key)
    trace_sum = sum(trace_matching_sups)
    sim_trace_sum = sum(sim_trace_matching_sups)
    return trace_sum, sim_trace_sum, trace_violating, sim_trace, sim_matches


def assign_violating(match: Dict[AvailableADARResults, Union[List[AvailableADAREventMiners],
                                                             Dict[AvailableADAREventMiners, ADARResult]]],
                     sim_match: Dict[AvailableADARResults, Union[List[AvailableADAREventMiners],
                                                                 Dict[AvailableADAREventMiners, ADARResult]]],
                     trace_violating: Dict[Tuple[int, int], Dict[AvailableADAREventMiners, ADARResult]],
                     key: Tuple[int, int]) -> None:
    violating = AvailableADARResults.VIOLATED
    if len(match[violating]) > 0:
        # Only keep ADARResults that only the trace violates, not also the sim trace
        trace_violating[key] = {rule_type: ADARResult(tid=result.tid,
                                                      rule=result.rule,
                                                      violating_eid=result.violating_eid,
                                                      violating_trace_pos=result.violating_trace_pos,
                                                      sim_violating=True if rule_type in sim_match[violating] else False
                                                      )
                                for rule_type, result in match[violating].items()}


def merge_similar_rules(rules: Dict[Tuple[int, int, int], ADAR]) -> Dict[Tuple[int, int], ADAR]:
    """Similar ADAR rules motivated by different traces are merged to a single ADAR rule
    """
    unique_rule_key = 0
    to_be_merged = {}
    assigned = {}
    # The rules dict is ordered with ascending tid and ascending rl. This property is leveraged here
    for (tid, pos, rl), rule in rules.items():
        # Already assigned rules can be passed
        if (tid, pos, rl) in assigned:
            pass
        else:
            # Start new rule in to be merged for unassigned rule
            to_be_merged[(unique_rule_key, rl)] = [(tid, pos, rl)]
            assigned[(tid, pos, rl)] = None
            # Look for similar rules
            for (tid2, pos2, rl2), rule2 in rules.items():
                # Already assigned rules cannot be similar
                if (tid2, pos2, rl2) in assigned:
                    pass
                else:
                    # Only rules of same length can be the same
                    if rl2 == rl:
                        # Are rules similar?
                        if rule == rule2:
                            to_be_merged[(unique_rule_key, rl)] += [(tid2, pos2, rl2)]
                            assigned[(tid2, pos2, rl2)] = None
                    else:
                        break
            unique_rule_key += 1
    return {key: ADAR(tid=[tid for tid, pos, rl in to_be_merged[key]],
                      conditions=merge_conditions(rules, to_be_merged[key]),
                      rule_types=rules[to_be_merged[key][0]].rule_types,
                      supports=rules[to_be_merged[key][0]].supports)
            for key in to_be_merged}


def merge_conditions(rules: Dict[Tuple[int, int, int], ADAR],
                     rule_keys: List[Tuple[int, int, int]]) -> Dict[
    AvailableADARTypes, List[Union[ConditionControlFlow]]]:
    return {typ: [get_condition_type(typ)(condition.val,
                                          # Keep all associated eids of all the merged conditions for the
                                          # respective condition
                                          [all_condition.eid for key in rule_keys
                                           for idy, all_condition in enumerate(rules[key].conditions[typ])
                                           if idx == idy])
                  for idx, condition in enumerate(rules[rule_keys[0]].conditions[typ])]
            for typ in rules[rule_keys[0]].conditions}
