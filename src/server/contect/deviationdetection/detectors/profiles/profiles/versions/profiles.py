from typing import Dict, Counter

from contect.parsedata.objects.oclog import Trace
from contect.deviationdetection.detectors.profiles.profiles.versions.util import RegexDict


def apply_dr_profile(dfg: Counter,
                     max_freq: int,
                     trace: Trace) -> float:
    events = trace.events
    length = len(events)
    if length >= 2:
        nominator = sum([dfg[(events[i].act, events[i+1].act)] for i in range(length - 1)])
        return nominator / ((length - 1) * max_freq)
    else:
        return 0


def apply_df_profile(dep_rel: RegexDict,
                     trace: Trace) -> float:
    acts = {event.act for event in trace.events}
    dep_acts = {d['consequent'] for d in dep_rel.get_all_matching(list(acts))}
    if dep_acts.issubset(acts):
        return 1
    else:
        return 0



