from typing import Dict, Union
import re

from contect.available.available import AvailableProfiles
from contect.deviationdetection.detectors.profiles.param.config import DependencyProfileParameters
from contect.parsedata.objects.oclog import ObjectCentricLog


def get_dependency_relation(log: ObjectCentricLog,
                            profiles_param: Dict[AvailableProfiles,
                                                 Union[DependencyProfileParameters]]) -> Dict[str, Dict[str, float]]:
    dep_param = profiles_param[AvailableProfiles.DF]
    min_conf = dep_param.min_conf
    min_supp = dep_param.min_supp
    fancy_co_occ_rel = {'single': {},
                        'pair': {}}
    traces = log.traces
    n_traces = len(traces)
    for tid in traces:
        events = traces[tid].events
        for i in range(len(events)):
            if events[i].act in fancy_co_occ_rel['single']:
                fancy_co_occ_rel['single'][events[i].act] += 1  # Count the frequencies of single activities
            else:
                fancy_co_occ_rel['single'][events[i].act] = 1  # Initialize unseen single activities
            for j in range(i + 1, len(events)):
                act1 = events[i].act
                act2 = events[j].act
                pair1 = (act1, act2)
                pair2 = (act2, act1)
                if pair1 in fancy_co_occ_rel['pair']:
                    fancy_co_occ_rel['pair'][pair1] += 1  # Count the frequencies of pairs of activities
                else:
                    fancy_co_occ_rel['pair'][pair1] = 1  # Initialize unseen pairs of activities
                if pair2 in fancy_co_occ_rel:
                    fancy_co_occ_rel['pair'][pair2] += 1  # Count the frequencies of reversed pairs of activities
                else:
                    fancy_co_occ_rel['pair'][pair2] = 1  # Initialize unseen pairs of activities
    enough_supp = {pair: count for pair, count in fancy_co_occ_rel['pair'].items() if count / n_traces >= min_supp}
    enough_conf = {pair: count for pair, count in fancy_co_occ_rel['pair'].items()
                   if count / fancy_co_occ_rel['single'][pair[0]] >= min_conf}
    return {pair[0] + ', ' + pair[1]: {'antecedent': pair[0],
                                       'count': count,
                                       'consequent': pair[1]} for pair, count in fancy_co_occ_rel['pair'].items() if
            pair in enough_supp and enough_conf}


# https://stackoverflow.com/questions/21024822/python-accessing-dictionary-with-wildcards
class RegexDict(dict):

    def get_matching(self, event):
        return (self[key] for key in self if re.match(event, key))

    def get_all_matching(self, events):
        return (match for event in events for match in self.get_matching(event))
