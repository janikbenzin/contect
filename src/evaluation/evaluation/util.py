import os
import pickle
from typing import List, Dict, Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from contect.available.available import AvailableDetectors
from contect.parsedata.objects.oclog import Trace
from contect.resource.resource import get_resource_figurepath, get_resource_pptpath, get_resource_filepath
from evaluation.constants import *
from sklearn.metrics import confusion_matrix


def extract_label_with_ca(trace: Trace, detector: AvailableDetectors) -> str:
    if detector in trace.deviating and trace.deviating[detector]:
        return 'deviating'
    elif detector in trace.normal and trace.normal[detector]:
        return 'normal'
    elif detector in trace.ca_normal and trace.ca_normal[detector]:
        return 'ca_normal'
    else:
        return 'ca_deviating'


def temp_extract_label_with_ca_pred(trace: Trace, detector: AvailableDetectors) -> str:
    if detector in trace.deviating:
        if trace.deviating[detector]:
            return 'deviating'
        else:
            return 'normal'


def extract_label_wo_ca(trace: Trace, detector: AvailableDetectors) -> str:
    if detector in trace.deviating and trace.deviating[detector]:
        return 'deviating'
    elif detector in trace.normal and trace.normal[detector]:
        return 'normal'
    elif detector in trace.ca_normal and trace.ca_normal[detector]:
        return 'deviating'
    else:
        return 'normal'


def plot_confusion_matrix(y_true, y_pred, classes, title, normalize=True):
    # Calculate confusion matrix
    cm = confusion_matrix(y_true, y_pred, labels=classes)

    # Normalize for each expected feature value
    if normalize:
        cm = cm.astype('float') / cm.sum(axis=1)[:, np.newaxis]

    return plot_and_save_confusion_matrix(classes, cm, normalize, title)


def plot_and_save_confusion_matrix(classes, cm, normalize, title):
    # Label and reorder
    df = pd.DataFrame(cm, classes, classes)
    # Plot the confusion matrix
    plt.subplots(figsize=(10, 10))
    sns.set(font_scale=1.5)
    sns.heatmap(df, annot=True, fmt='.2f' if normalize else '', cmap="Blues", annot_kws={"size": 20})
    plt.title(title, y=1.05)
    plt.xlabel('Predicted')
    plt.ylabel('True')
    plt.savefig(get_resource_figurepath(title + '.png'), bbox_inches='tight')
    plt.close('all')
    return cm


def get_median_and_std_dev_as_string(inp: List) -> str:
    return str(np.round(np.mean(inp), 2)) + '±' + str(np.round(np.std(inp), 3))


def default_metric_dict() -> Dict[str, Dict[Any, Any]]:
    return {CMS_LBL: {}, REPORT_LBL: {}, B_ACC_LBL: {}, ACC_LBL: {},
            PREC_LBL: {}, RECALL_LBL: {}, R_ACC_LBL: {}, R_PREC_LBL: {},
            R_RECALL_LBL: {}}


def save_df_to_ppt_table(df: pd.DataFrame, name: str) -> None:
    try:
        from pd2ppt import df_to_powerpoint
        df_to_powerpoint(get_resource_pptpath(name), df)
    except (ImportError, ModuleNotFoundError) as e:
        print(f'Please install package pd2ppt following instructions from https://github.com/robintw/PandasToPowerpoint'
              f' in your current venv to get powerpoint table outputs')


def plot_metrics(x: str, y: str, hue: str, data: pd.DataFrame, title) -> None:
    fig, ax1 = plt.subplots(figsize=(10, 10))
    plt.ylim(0, 1)
    tidy = data.melt(id_vars=x).rename(columns=str.title)
    sns.barplot(x=x, y=y, hue=hue, data=tidy, ax=ax1)
    sns.despine(fig)

    plt.savefig(get_resource_figurepath(title + '.png'), bbox_inches='tight')
    plt.close('all')


def existing_optimized(acc, key, ca_with_context_metrics, detector, ACC_LBL, ca_no_context_metrics):
    return acc if key not in ca_with_context_metrics[detector][ACC_LBL] \
        else ca_with_context_metrics[detector][ACC_LBL][key]


def get_pickled_experiment(name: str):
    with open(get_resource_filepath(name), 'rb') as pickle_file:
        data = pickle.load(pickle_file)
    return data


def get_experiment_names():
    experiments = [f.split('/')[-1] for f in os.listdir(get_resource_filepath('')) if f.endswith('.pickle')
                   and 'post' not in f.split('/')[-1]]
    post_experiments = [f for f in os.listdir(get_resource_filepath('')) if f.endswith('.post.pickle')]
    return experiments, post_experiments
