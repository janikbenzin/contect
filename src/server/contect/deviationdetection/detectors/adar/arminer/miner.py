from typing import List, Tuple, Dict

from contect.available.available import AvailableADARTypes, AvailableADAREventMiners, AvailableADARStates, \
    AvailableSelections
from contect.deviationdetection.detectors.adar.conditiontypes.factory import get_condition_type
from contect.deviationdetection.detectors.adar.objects.adar import ADAR
from contect.deviationdetection.detectors.adar.param.config import ADARParameters
from contect.deviationdetection.detectors.adar.util import support_condition
from contect.parsedata.objects.oclog import ObjectCentricLog


# The key of the ADAR dict corresponds to trace ids and the respective pos in the events list for that event
def initiate_singleton_rules(log: ObjectCentricLog,
                             mins: Dict[AvailableADAREventMiners,
                                        float],
                             vmap_params: Dict[AvailableSelections,
                                               str]) -> Dict[AvailableADARStates, Dict[Tuple[int, int, int], ADAR]]:
    return verify_rules({AvailableADARStates.NEW:
                             {(tid, pos, 1): ADAR(tid=tid,
                                                  conditions={typ:
                                                                  [get_condition_type(typ, log.traces[tid].events[pos])]
                                                              for typ in AvailableADARTypes},
                                                  rule_types=[typ for typ in AvailableADAREventMiners])
                              for tid in log.traces for pos in range(len(log.traces[tid].events))}},
                        log,
                        mins,
                        vmap_params)


def extend_rules(current_rules: Dict[AvailableADARStates, Dict[Tuple[int, int, int], ADAR]],
                 log: ObjectCentricLog,
                 typs: List[AvailableADARTypes]) -> Dict[AvailableADARStates, Dict[Tuple[int, int, int], ADAR]]:
    # Since we generate all rules of old_length + 1 in one step, we do not need to do this step again for
    # shorter, already verified rules, as this would be redundant. Thus, newly generated rules are separated
    # by the AvailableADARState from earlier generated and verified shorter rules
    new_rules = {AvailableADARStates.NEW: {(tid, new_pos, cur_rl + 1):  # Store the new position as part of the key
                                               ADAR(tid=tid,
                                                    # Add the new condition to conditions
                                                    conditions={typ:
                                                                    current_rules[AvailableADARStates.NEW][
                                                                        (tid, cur_pos, cur_rl)].conditions[typ] + [
                                                                        get_condition_type(typ, event)]
                                                                for typ in typs},
                                                    # Only use rule types, if they were previously verified + possible
                                                    # given the ADARTypes typs
                                                    rule_types=[typ for typ in current_rules[AvailableADARStates.NEW][
                                                        (tid, cur_pos, cur_rl)].rule_types if typ.value[0] in typs])
                                           # Traverse all existing ADARs
                                           for tid, cur_pos, cur_rl in current_rules[AvailableADARStates.NEW] if
                                           # Only use traces that have at least one event left at end
                                           cur_pos + 1 < len(log.traces[tid].events) and
                                           # Only use existing ADARs whose rule types correspond to chosen typs
                                           len([typ for typ in current_rules[AvailableADARStates.NEW][
                                               (tid, cur_pos, cur_rl)].rule_types if typ.value[0] in typs]) != 0
                                           # Traverse events from cur pos + 1 in associated trace
                                           for event, new_pos in
                                           [(log.traces[tid].events[pos], pos) for pos in
                                            # Traverse the subtrace at pos
                                            range(cur_pos + 1, len(log.traces[tid].events))]},
                 AvailableADARStates.OLD: current_rules[AvailableADARStates.NEW]}
    if AvailableADARStates.OLD in current_rules:
        # First run has only NEW
        new_rules[AvailableADARStates.OLD].update(current_rules[AvailableADARStates.OLD])
    return new_rules


def verify_rules(current_rules: Dict[AvailableADARStates, Dict[Tuple[int, int, int], ADAR]],
                 log: ObjectCentricLog,
                 mins: Dict[AvailableADAREventMiners, float],
                 vmap_params: Dict[AvailableSelections, str]) -> Dict[AvailableADARStates, Dict[Tuple[int, int, int],
                                                                                                ADAR]]:
    # Check all rules
    verified_rules = {AvailableADARStates.NEW: {}}
    for (tid, pos, cur_rl), rule in current_rules[AvailableADARStates.NEW].items():
        # Check all different perspectives of a rule
        sup_perspectives = support_condition(rule, log, vmap_params)
        verified = {perspective: sup_perspectives[perspective] < mins[perspective] for perspective in sup_perspectives}
        # Only add a rule to the verified rules, if there is at least one supported perspective
        if not all(list(verified.values())):
            valid_rule_types = [typ for typ in rule.rule_types if not verified[typ]]
            verified_rules[AvailableADARStates.NEW][(tid, pos, cur_rl)] = ADAR(tid,
                                                                               # that removes unnecessary conditions
                                                                               rule.conditions,
                                                                               valid_rule_types,
                                                                               supports={typ: sup_perspectives[typ]
                                                                                         for typ in valid_rule_types})
    if AvailableADARStates.OLD in current_rules:
        verified_rules[AvailableADARStates.OLD] = current_rules[AvailableADARStates.OLD]
    return verified_rules


def mine_adar_rules(param: ADARParameters, log: ObjectCentricLog) -> Dict[Tuple[int, int, int], ADAR]:
    rules = initiate_singleton_rules(log=log,
                                     mins=param.mins,
                                     vmap_params=param.vmap_param.vmap_params)
    # Subtract one for singleton rules
    sorted_rl = {typ: rl - 1 for typ, rl in sorted(param.rl.items(), key=lambda item: item[1])}
    list_rl = list(sorted_rl.items())
    # Get differences of rule lengths of sorted list
    diff_rl = iter([rl2 - rl1 for (typ1, rl1), (typ2, rl2) in zip(list_rl[:-1], list_rl[1:])])
    rl_counter = 0
    for length in range(list_rl[rl_counter][1]):
        # Smallest rl is valid for all ADARTypes
        rules = extend_rules(current_rules=rules,
                             log=log,
                             typs=list(sorted_rl.keys()))
        rules = verify_rules(rules, log, param.mins, param.vmap_param.vmap_params)
    # Look for longer than minimal length ADARTypes
    rl_counter += 1
    for i in range(rl_counter, len(list_rl)):
        remaining_length = next(diff_rl)
        if not remaining_length == 0:  # Only strictly larger rule lengths per type need to be extended further
            # The rules need to be extended for the remaining ADARTypes in list_rl
            for length in range(remaining_length):
                rules = extend_rules(current_rules=rules,
                                     log=log,
                                     typs=[list_rl[j][0] for j in range(i, len(list_rl))])
                rules = verify_rules(rules, log, param.mins, param.vmap_param.vmap_params)
        rl_counter += 1
    # Currently, the rules contain frequent item sets
    # These are now transformed to actual ADAR rules by removing the singleton rules. According to the paper,
    # the whole sequence of conditions per typ is the IF part except for the last condition, which is the THEN
    rules_merged = rules[AvailableADARStates.OLD]
    rules_merged.update(rules[AvailableADARStates.NEW])
    rules = {(tid, pos, rl): adar for (tid, pos, rl), adar in rules_merged.items() if rl > 1}
    return rules
