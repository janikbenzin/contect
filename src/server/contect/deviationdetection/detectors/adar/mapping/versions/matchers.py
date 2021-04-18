from typing import Dict, Union, List

from contect.available.available import AvailableADARTypes, AvailableSelections, AvailableADARResults, \
    AvailableADAREventMiners
from contect.available.constants import MISSING
from contect.deviationdetection.detectors.adar.objects.result import ADARResult
from contect.parsedata.objects.oclog import Trace
from contect.deviationdetection.detectors.adar.objects.adar import ADAR


def match_control_condition_support(rule: ADAR,
                                    trace: Trace) -> bool:
    typ = AvailableADARTypes.CONTROL
    trace_len = len(trace.events)
    rule_len = len(rule.conditions[typ])
    i, j = 0, 0
    if trace_len < rule_len:
        return False
    while True:
        if trace.events[i].act == rule.conditions[typ][j].val:
            # Matching -> both pointers need to be moved
            i += 1
            j += 1
        else:
            # Not matching -> only the trace needs to be traversed further
            i += 1
        # If the trace pointer is beyond the trace length, then we need to stop in any case
        if i + 1 > trace_len:
            if j + 1 >= rule_len:
                # If at the same time the rule is completely matched, then the whole rule was matched
                return True
            else:
                # If not all conditions were matched, the whole rule was not matched
                return False
        else:
            # The rule is completely matched before reaching the end of the trace
            if j + 1 >= rule_len:
                return True


def match_control_condition_rule(rule: ADAR,
                                 trace: Trace) -> Dict[AvailableADARResults, Union[int, ADARResult]]:
    typ = AvailableADARTypes.CONTROL
    miner = AvailableADAREventMiners.CONTROL
    trace_len = len(trace.events)
    rule_len = len(rule.conditions[typ])
    i, j = 0, 0
    # If this holds, the trace cannot event match the IF part of the rule
    neutral = {AvailableADARResults.NEUTRAL: 0}
    matched = {AvailableADARResults.MATCHED: 0}
    if trace_len + 1 < rule_len:
        return neutral
    while True:
        if trace.events[i].act == rule.conditions[typ][j].val:
            # Matching -> both pointers need to be moved
            i += 1
            j += 1
        else:
            # Not matching -> only the trace needs to be traversed further
            i += 1
        # If the trace pointer is beyond the trace length, then we need to stop in any case
        if i + 1 > trace_len:
            if j + 2 < rule_len:
                # If at the same time less than all IF conditions except the last one was matched, the rule is neutral
                return neutral
            elif j + 2 == rule_len:
                # Whole IF part was matched, but the THEN part is missing in the trace
                return {AvailableADARResults.VIOLATED: ADARResult(tid=trace.id,
                                                                  rule=rule.conditions[typ],
                                                                  violating_eid=MISSING,
                                                                  violating_trace_pos=-1)}
            else:
                return matched
        else:
            # The rule is completely matched before reaching the end of the trace
            if j + 1 >= rule_len:
                return matched


def match_resource_condition_support(rule: ADAR,
                                     variant: bool,
                                     vmap_params: Dict[AvailableSelections, str],
                                     trace: Trace) -> bool:
    typ = AvailableADARTypes.RESOURCE
    rule_acts = {cond.val for cond in rule.conditions[typ]}
    rs = {event.vmap[vmap_params[AvailableSelections.RESOURCE]] for event in trace.events if event.act in rule_acts}
    if variant:
        # BOD
        return len(rs) == 1
    else:
        # SOD
        return len(rs) == len(rule.conditions[typ])


def match_resource_condition_rule(rule: ADAR,
                                  miner: AvailableADAREventMiners,
                                  vmap_params: Dict[AvailableSelections, str],
                                  trace: Trace) -> Dict[AvailableADARResults, Union[int, ADARResult]]:
    typ = AvailableADARTypes.RESOURCE
    neutral = {AvailableADARResults.NEUTRAL: 0}
    matched = {AvailableADARResults.MATCHED: 0}
    rule_acts = [cond.val for cond in rule.conditions[typ]]
    resource_key = vmap_params[AvailableSelections.RESOURCE]
    resources = [(event.vmap[resource_key], event.id)
                 for event in trace.events if event.act in rule_acts]
    rs = set([res[0] for res in resources])
    if miner is AvailableADAREventMiners.RESOURCE_BOD:
        if len(rs) == 1:
            return matched
        elif len(rs) == 0:
            return neutral
        else:
            # Look for first event with wrong resource
            first_resource = resources[0]
            for resource in resources[1:]:
                if resource != first_resource:
                    for violating_trace_pos in range(len(trace.events)):
                        if trace.events[violating_trace_pos].id == resource[1]:
                            return {AvailableADARResults.VIOLATED:
                                        ADARResult(tid=trace.id,
                                                   rule=rule.conditions[typ],
                                                   violating_eid=resource[1],
                                                   violating_trace_pos=violating_trace_pos)}

    else:
        # SOD
        if len(rs) == len(rule.conditions[typ]):
            return matched
        else:
            # Look for first pair of events having the same resource
            trace_len = len(trace.events)
            # Traverse all resource, eid pairs
            for resource in resources:
                # Traverse the trace
                for candidate_pos in range(trace_len):
                    # Look for the event matching the eid first, this is a possible candidate for the violating pair
                    if trace.events[candidate_pos].id == resource[1]:
                        # Look for the second event of the pair violating to have separate resources
                        for violating_trace_pos in range(candidate_pos + 1, trace_len):
                            # Same resource -> violating SOD
                            if trace.events[violating_trace_pos].vmap[resource_key] == resource[0]:
                                return {AvailableADARResults.VIOLATED:
                                            ADARResult(tid=trace.id,
                                                       rule=rule.conditions[typ],
                                                       violating_eid=resource[1],
                                                       violating_trace_pos=violating_trace_pos)}
                        # The resource of current candidate eid has a unique resource -> look further
            # Special case in which at least one event that motivated the current rule's conditions is missing
            # in the current trace -> too few resources, ie. len(rs) < len(rule.conditions[typ]) and this missing
            # event cannot be found in the above search for the second eid violating the SOD
            return {AvailableADARResults.VIOLATED:
                                            ADARResult(tid=trace.id,
                                                       rule=rule.conditions[typ],
                                                       violating_eid=MISSING,
                                                       violating_trace_pos=-1)}

