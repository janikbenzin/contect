from typing import Tuple, List, Dict
from sklearn.model_selection import train_test_split

from contect.available.available import AvailableSelections
from contect.deviationdetection.util.util import pad_list
from numpy import ndarray
import pandas as pd
import numpy as np

from contect.parsedata.objects.oclog import ObjectCentricLog


def transform_input(log: ObjectCentricLog,
                    acts: List[str],
                    ress: List[str],
                    vmap_params: Dict[AvailableSelections, str],
                    test_size: float,
                    max_trace_len: int) -> Tuple[ndarray, ndarray, ndarray]:
    acts_s = pd.Series(acts)
    act_zeros = np.zeros(len(acts))
    acts_one_hot = pd.get_dummies(acts_s)

    ress_s = pd.Series(ress)
    res_zeros = np.zeros(len(ress))
    ress_one_hot = pd.get_dummies(ress_s)

    res_key = vmap_params[AvailableSelections.RESOURCE]

    all_padded = [(pad_list([acts_one_hot[event.act].to_numpy()
                                 for event in trace.events], n=max_trace_len, pad_val=act_zeros),
                   pad_list([ress_one_hot[event.vmap[res_key]].to_numpy()
                                 for event in trace.events], n=max_trace_len, pad_val=res_zeros))
                  for tid, trace in log.traces.items()]
    all_data = np.array([np.hstack([np.concatenate((act, res))
                                    for act, res in zip(act_trace, res_trace)])
                         for act_trace, res_trace in all_padded])
    train_data, test_data = train_test_split(all_data, test_size=test_size)

    return all_data, train_data, test_data
