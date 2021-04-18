from backend.tasks.tasks import post_process
from contect.postprocessing.postprocessor import get_true_label, get_true_dn_label, get_true_dn_label_from_label
from contect.available.available import AvailableDetectors, AvailableSituations
from contect.resource.resource import get_resource_figurepath, pickle_data
from evaluation import util
from evaluation.constants import *

from sklearn.metrics import classification_report, balanced_accuracy_score, accuracy_score
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import warnings

warnings.filterwarnings("ignore")

experiments, post_experiments = util.get_experiment_names()

experiments = sorted(experiments)
post_experiments = sorted(post_experiments)

detectors = [detector for detector in AvailableDetectors]

detector_experiments = {detector: [exp for exp in experiments if detector.value in exp]
                        for detector in detectors}

detector_post_experiments = {detector: [f'{exp}.post.pickle' for exp in experiments if detector.value in exp]
                             for detector in detectors}


# The specified event-level deviation percentages are transformed to real trace-level deviation percentages
trace_deviating_02 = []
trace_deviating_05 = []
trace_deviating_10 = []
trace_deviating_02_ca = []
trace_deviating_05_ca = []
trace_deviating_10_ca = []
trace_ca_deviating_02 = []
trace_ca_deviating_05 = []
trace_ca_deviating_10 = []
trace_ca_normal_02 = []
trace_ca_normal_05 = []
trace_ca_normal_10 = []
trace_normal_02 = []
trace_normal_05 = []
trace_normal_10 = []
for experiment in experiments:
    experiment_data = util.get_pickled_experiment(experiment)
    perc_deviating = experiment_data.perc_deviating
    if perc_deviating == 0.02:
        trace_deviating_02.append(experiment_data.real_perc_deviating)
        trace_deviating_02_ca.append(experiment_data.real_perc_deviating_ca)
        trace_ca_deviating_02.append(experiment_data.real_perc_ca_deviating)
        trace_ca_normal_02.append(experiment_data.real_perc_ca_normal)
        trace_normal_02.append(experiment_data.real_perc_normal)
    elif perc_deviating == 0.05:
        trace_deviating_05.append(experiment_data.real_perc_deviating)
        trace_deviating_05_ca.append(experiment_data.real_perc_deviating_ca)
        trace_ca_deviating_05.append(experiment_data.real_perc_ca_deviating)
        trace_ca_normal_05.append(experiment_data.real_perc_ca_normal)
        trace_normal_05.append(experiment_data.real_perc_normal)
    else:
        trace_deviating_10.append(experiment_data.real_perc_deviating)
        trace_deviating_10_ca.append(experiment_data.real_perc_deviating_ca)
        trace_ca_deviating_10.append(experiment_data.real_perc_ca_deviating)
        trace_ca_normal_10.append(experiment_data.real_perc_ca_normal)
        trace_normal_10.append(experiment_data.real_perc_normal)

df_event_to_trace = pd.DataFrame({
    '% Events deviating before context': [0.02, 0.05, 0.10],
    '% Traces deviating before context': [
        util.get_median_and_std_dev_as_string(trace_deviating_02),
        util.get_median_and_std_dev_as_string(trace_deviating_05),
        util.get_median_and_std_dev_as_string(trace_deviating_10)
    ],
    '% Traces deviating after context': [
        util.get_median_and_std_dev_as_string(trace_deviating_02_ca),
        util.get_median_and_std_dev_as_string(trace_deviating_05_ca),
        util.get_median_and_std_dev_as_string(trace_deviating_10_ca)
    ],
    '% Traces normal after context': [
        util.get_median_and_std_dev_as_string(trace_normal_02),
        util.get_median_and_std_dev_as_string(trace_normal_05),
        util.get_median_and_std_dev_as_string(trace_normal_10)
    ],
    '% Traces context-aware-normal': [
        util.get_median_and_std_dev_as_string(trace_ca_normal_02),
        util.get_median_and_std_dev_as_string(trace_ca_normal_05),
        util.get_median_and_std_dev_as_string(trace_ca_normal_10)
    ],
    '% Traces context-aware-deviating': [
        util.get_median_and_std_dev_as_string(trace_ca_deviating_02),
        util.get_median_and_std_dev_as_string(trace_ca_deviating_05),
        util.get_median_and_std_dev_as_string(trace_ca_deviating_10)
    ],
})

util.save_df_to_ppt_table(df_event_to_trace, 'events_to_trace_deviations')
print(df_event_to_trace.to_latex(index=False))


# Context-unaware deviation results with only deviating or normal as classes
d_n_no_context = {
    detector:
        {experiment: {TRUE_LBL: [],
                      PRED_LBL: [],
                      PERC_D_LBL: 0,
                      PERC_POS_LBL: 0}
         for experiment in detector_experiments[detector]}
    for detector in detectors
}

d_n_no_context_metrics = {
    detector:
        util.default_metric_dict()
    for detector in detectors
}

sit1 = AvailableSituations.CAPACITY
sit2 = AvailableSituations.UNIT_PERFORMANCE

d_n_no_context_attr_metrics = {
    detector:
        {sit1: util.default_metric_dict(),
         sit2: util.default_metric_dict()}
    for detector in detectors
}

d_n_no_context_dev_metrics = {
    detector:
        util.default_metric_dict()
    for detector in detectors
}

# Context-unaware deviation results with all groups
ca_no_context = {
    detector:
        {experiment: {TRUE_LBL: [],
                      PRED_LBL: [],
                      PERC_D_LBL: 0,
                      PERC_POS_LBL: 0}
         for experiment in detector_experiments[detector]}
    for detector in detectors
}

ca_no_context_metrics = {
    detector:
        util.default_metric_dict()
    for detector in detectors
}

ca_no_context_attr_metrics = {
    detector:
        {sit1: util.default_metric_dict(),
         sit2: util.default_metric_dict()}
    for detector in detectors
}

ca_no_context_dev_metrics = {
    detector:
        util.default_metric_dict()
    for detector in detectors
}

# Optimized for accuracy during post-processing
ca_with_context_metrics = {
    detector:
        util.default_metric_dict()
    for detector in detectors
}

ca_with_context_attr_metrics = {
    detector:
        {sit1: util.default_metric_dict(),
         sit2: util.default_metric_dict()}
    for detector in detectors
}

ca_with_context_dev_metrics = {
    detector:
        util.default_metric_dict()
    for detector in detectors
}

# Optimized for Average Class Accuracy during post-processing
ca_with_context_bal_metrics = {
    detector:
        util.default_metric_dict()
    for detector in detectors
}

ca_with_context_bal_attr_metrics = {
    detector:
        {sit1: util.default_metric_dict(),
         sit2: util.default_metric_dict()}
    for detector in detectors
}

ca_with_context_bal_dev_metrics = {
    detector:
        util.default_metric_dict()
    for detector in detectors
}

cms_all = []
all_dfs = {detector: {}
           for detector in detectors}
for detector in detectors:
    for exp, post_exp in zip(detector_experiments[detector],
                             detector_post_experiments[detector]):
        experiment_data = util.get_pickled_experiment(exp)
        post_experiment_data = util.get_pickled_experiment(post_exp)

        # Init
        d_n_no_context[detector][exp][TRUE_LBL] = [get_true_dn_label(trace, detector)
                                                   for tid, trace in experiment_data.log_with_classification.items()]
        d_n_no_context[detector][exp][PRED_LBL] = [get_true_dn_label_from_label(label)
                                                   for label in experiment_data.log.labels[detector]]
        d_n_no_context[detector][exp][PERC_POS_LBL] = '; '.join([f'{sit.value}: {v}'
                                                                 for sit, v in
                                                                 experiment_data.perc_pos_attributable.items()])
        d_n_no_context[detector][exp][sit1] = experiment_data.perc_pos_attributable[sit1]
        d_n_no_context[detector][exp][sit2] = experiment_data.perc_pos_attributable[sit2]
        d_n_no_context[detector][exp][PERC_D_LBL] = experiment_data.perc_deviating

        # Metrics
        d_n_y_true = d_n_no_context[detector][exp][TRUE_LBL]
        d_n_y_pred = d_n_no_context[detector][exp][PRED_LBL]
        key = (exp,
               d_n_no_context[detector][exp][sit1],
               d_n_no_context[detector][exp][sit2],
               d_n_no_context[detector][exp][PERC_D_LBL])
        d_n_no_context_metrics[detector][CMS_LBL][key] = util.plot_confusion_matrix(d_n_y_true,
                                                                                    d_n_y_pred,
                                                                                    D_N_CLASSES,
                                                                                    f'cms_cu_{detector.value}'
                                                                                    f'_d_n_{exp}',
                                                                                    False)
        d_n_no_context_metrics[detector][REPORT_LBL][key] = classification_report(d_n_y_true,
                                                                                  d_n_y_pred,
                                                                                  labels=D_N_CLASSES,
                                                                                  target_names=D_N_CLASSES,
                                                                                  output_dict=True)
        d_n_no_context_metrics[detector][B_ACC_LBL][key] = balanced_accuracy_score(d_n_y_true,
                                                                                   d_n_y_pred)
        d_n_no_context_metrics[detector][ACC_LBL][key] = accuracy_score(d_n_y_true,
                                                                        d_n_y_pred)

        # Init
        ca_no_context[detector][exp][TRUE_LBL] = [get_true_label(trace, detector)
                                                  for tid, trace in experiment_data.log_with_classification.items()]
        ca_no_context[detector][exp][PRED_LBL] = [label.value for label in experiment_data.log.labels[detector]]
        ca_no_context[detector][exp][PERC_POS_LBL] = '; '.join([f'{sit.value}: {v}'
                                                                for sit, v in
                                                                experiment_data.perc_pos_attributable.items()])
        ca_no_context[detector][exp][sit1] = experiment_data.perc_pos_attributable[sit1]
        ca_no_context[detector][exp][sit2] = experiment_data.perc_pos_attributable[sit2]
        ca_no_context[detector][exp][PERC_D_LBL] = experiment_data.perc_deviating

        # Metrics
        ca_y_true = ca_no_context[detector][exp][TRUE_LBL]
        ca_y_pred = ca_no_context[detector][exp][PRED_LBL]
        key = (exp,
               ca_no_context[detector][exp][sit1],
               ca_no_context[detector][exp][sit2],
               ca_no_context[detector][exp][PERC_D_LBL])
        ca_no_context_metrics[detector][CMS_LBL][key] = util.plot_confusion_matrix(ca_y_true,
                                                                                   ca_y_pred,
                                                                                   CLASSES,
                                                                                   f'cms_cu_{detector.value}'
                                                                                   f'_ca_{exp}',
                                                                                   False)
        ca_no_context_metrics[detector][REPORT_LBL][key] = classification_report(ca_y_true,
                                                                                 ca_y_pred,
                                                                                 labels=CLASSES,
                                                                                 target_names=CLASSES,
                                                                                 output_dict=True)
        ca_no_context_metrics[detector][B_ACC_LBL][key] = balanced_accuracy_score(ca_y_true,
                                                                                  ca_y_pred)
        ca_no_context_metrics[detector][ACC_LBL][key] = accuracy_score(ca_y_true,
                                                                       ca_y_pred)

        # If result could be improved
        if len(post_experiment_data['optimized']) > 0:
            # Optimized for acc
            alpha_ps = post_experiment_data['optimized']['params'][0]
            alpha_ng = post_experiment_data['optimized']['params'][1]
            new_log = post_process(alpha_ps=alpha_ps,
                                   alpha_ng=alpha_ng,
                                   threshold=experiment_data.log.detector_thresholds[detector],
                                   log=experiment_data.log,
                                   detector=detector,
                                   variant=True)

            ca_y_pred = [label.value for label in new_log.labels[detector]]
            ca_with_context_metrics[detector][CMS_LBL][key] = util.plot_confusion_matrix(ca_y_true,
                                                                                         ca_y_pred,
                                                                                         CLASSES,
                                                                                         f'cms_ca_{detector.value}'
                                                                                         f'_ca_{exp}',
                                                                                         False)
            ca_with_context_metrics[detector][REPORT_LBL][key] = classification_report(ca_y_true,
                                                                                       ca_y_pred,
                                                                                       labels=CLASSES,
                                                                                       target_names=CLASSES,
                                                                                       output_dict=True)
            ca_with_context_metrics[detector][B_ACC_LBL][key] = post_experiment_data['optimized']['balanced_acc']
            ca_with_context_metrics[detector][ACC_LBL][key] = post_experiment_data['optimized']['acc']

        if len(post_experiment_data['balanced']) > 0:
            # Optimized for balanced acc
            alpha_ps = post_experiment_data['balanced']['params'][0]
            alpha_ng = post_experiment_data['balanced']['params'][1]
            new_log = post_process(alpha_ps=alpha_ps,
                                   alpha_ng=alpha_ng,
                                   threshold=experiment_data.log.detector_thresholds[detector],
                                   log=experiment_data.log,
                                   detector=detector,
                                   variant=True)
            ca_y_pred = [label.value for label in new_log.labels[detector]]
            ca_with_context_bal_metrics[detector][CMS_LBL][key] = util.plot_confusion_matrix(ca_y_true,
                                                                                             ca_y_pred,
                                                                                             CLASSES,
                                                                                             f'cms_ca_{detector.value}'
                                                                                             f'_ca_{exp}',
                                                                                             False)
            ca_with_context_bal_metrics[detector][REPORT_LBL][key] = classification_report(ca_y_true,
                                                                                           ca_y_pred,
                                                                                           labels=CLASSES,
                                                                                           target_names=CLASSES,
                                                                                           output_dict=True)
            ca_with_context_bal_metrics[detector][B_ACC_LBL][key] = post_experiment_data['balanced']['balanced_acc']
            ca_with_context_bal_metrics[detector][ACC_LBL][key] = post_experiment_data['balanced']['acc']

        del experiment_data
        del post_experiment_data

    # Confusion matrices all
    cu_d_n_all_cms = sum([cm for exp, cm in d_n_no_context_metrics[detector][CMS_LBL].items()])
    cu_ca_all_cms = sum([cm for exp, cm in ca_no_context_metrics[detector][CMS_LBL].items()])
    ca_ca_all_cms = sum([cm if exp not in ca_with_context_metrics[detector][CMS_LBL] else
                         ca_with_context_metrics[detector][CMS_LBL][exp]
                         for exp, cm in ca_no_context_metrics[detector][CMS_LBL].items()])
    cms_all.append(ca_ca_all_cms)

    cu_d_n_all_cms = util.plot_and_save_confusion_matrix(D_N_CLASSES,
                                                         cu_d_n_all_cms,
                                                         False,
                                                         f'{detector.value}_cms_cu_d_n_sum')
    cu_ca_all_cms = util.plot_and_save_confusion_matrix(CLASSES,
                                                        cu_ca_all_cms,
                                                        False,
                                                        f'{detector.value}_cms_cu_ca_sum')
    ca_ca_all_cms = util.plot_and_save_confusion_matrix(CLASSES,
                                                        ca_ca_all_cms,
                                                        False,
                                                        f'{detector.value}_cms_ca_ca_sum')

    # Optimized by acc
    # Accuracies all average
    cu_d_n_all_accs_avg = np.mean([acc for exp, acc in d_n_no_context_metrics[detector][ACC_LBL].items()])
    cu_ca_all_accs_avg = np.mean([acc for exp, acc in ca_no_context_metrics[detector][ACC_LBL].items()])
    ca_ca_all_accs_avg = np.mean([
        acc
        if exp not in ca_with_context_metrics[detector][ACC_LBL] else ca_with_context_metrics[detector][ACC_LBL][exp]
        for exp, acc in ca_no_context_metrics[detector][ACC_LBL].items()
    ])

    # Balanced accuracies all average
    cu_d_n_all_bal_accs_avg = np.mean([acc for exp, acc in d_n_no_context_metrics[detector][B_ACC_LBL].items()])
    cu_ca_all_bal_accs_avg = np.mean([acc for exp, acc in ca_no_context_metrics[detector][B_ACC_LBL].items()])
    ca_ca_all_bal_accs_avg = np.mean([
        acc
        if exp not in ca_with_context_metrics[detector][B_ACC_LBL] else ca_with_context_metrics[detector][B_ACC_LBL][
            exp]
        for exp, acc in ca_no_context_metrics[detector][B_ACC_LBL].items()
    ])

    # Precision all average
    cu_d_n_all_accs_avg_prec = np.mean([report[W_AVG_LBL][PREC_LBL]
                                        for key, report in d_n_no_context_metrics[detector][REPORT_LBL].items()])
    cu_ca_all_accs_avg_prec = np.mean([report[W_AVG_LBL][PREC_LBL]
                for key, report in ca_no_context_metrics[detector][REPORT_LBL].items()])
    ca_ca_all_accs_avg_prec = np.mean([
        report[W_AVG_LBL][PREC_LBL]
        if key not in ca_with_context_metrics[detector][ACC_LBL]
        else ca_with_context_metrics[detector][REPORT_LBL][key][W_AVG_LBL][PREC_LBL]
        for key, report in ca_no_context_metrics[detector][REPORT_LBL].items()
    ])

    # Recall all average
    cu_d_n_all_bal_accs_avg_rec = np.mean([report[W_AVG_LBL][RECALL_LBL]
                                           for key, report in d_n_no_context_metrics[detector][REPORT_LBL].items()])
    cu_ca_all_bal_accs_avg_rec = np.mean([report[W_AVG_LBL][RECALL_LBL]
                for key, report in ca_no_context_metrics[detector][REPORT_LBL].items()])
    ca_ca_all_bal_accs_avg_rec = np.mean([
        report[W_AVG_LBL][RECALL_LBL]
        if key not in ca_with_context_metrics[detector][ACC_LBL]
        else ca_with_context_metrics[detector][REPORT_LBL][key][W_AVG_LBL][RECALL_LBL]
        for key, report in ca_no_context_metrics[detector][REPORT_LBL].items()
    ])

    df_all_accs_avg = pd.DataFrame({
        'Context-unaware - Classes deviating & normal': [cu_d_n_all_accs_avg, cu_d_n_all_bal_accs_avg,
                                                         cu_d_n_all_accs_avg_prec, cu_d_n_all_bal_accs_avg_rec],
        'Context-unaware - All Classes': [cu_ca_all_accs_avg, cu_ca_all_bal_accs_avg,
                                          cu_ca_all_accs_avg_prec, cu_ca_all_bal_accs_avg_rec],
        'Context-aware - All Classes': [ca_ca_all_accs_avg, ca_ca_all_bal_accs_avg,
                                        ca_ca_all_accs_avg_prec, ca_ca_all_bal_accs_avg_rec]
    }, index=['Accuracy', 'Average class accuracy', 'Precision', 'Recall'])

    name = f'{detector.value}_accs_all_avg'
    all_dfs[detector][name] = df_all_accs_avg
    util.save_df_to_ppt_table(df_all_accs_avg, name)
    print("\n\n")
    print(df_all_accs_avg.to_latex(index=False))

    # Optimized by bal acc
    # Accuracies all average
    cu_d_n_all_accs_avg = np.mean([acc for exp, acc in d_n_no_context_metrics[detector][ACC_LBL].items()])
    cu_ca_all_accs_avg = np.mean([acc for exp, acc in ca_no_context_metrics[detector][ACC_LBL].items()])
    ca_ca_all_accs_avg = np.mean([
        acc
        if exp not in ca_with_context_bal_metrics[detector][ACC_LBL] else
        ca_with_context_bal_metrics[detector][ACC_LBL][exp]
        for exp, acc in ca_no_context_metrics[detector][ACC_LBL].items()
    ])

    # Balanced accuracies all average
    cu_d_n_all_bal_accs_avg = np.mean([acc for exp, acc in d_n_no_context_metrics[detector][B_ACC_LBL].items()])
    cu_ca_all_bal_accs_avg = np.mean([acc for exp, acc in ca_no_context_metrics[detector][B_ACC_LBL].items()])
    ca_ca_all_bal_accs_avg = np.mean([
        acc
        if exp not in ca_with_context_bal_metrics[detector][B_ACC_LBL] else
        ca_with_context_bal_metrics[detector][B_ACC_LBL][
            exp]
        for exp, acc in ca_no_context_metrics[detector][B_ACC_LBL].items()
    ])

    df_all_accs_avg = pd.DataFrame({
        'Context-unaware - Classes deviating & normal': [cu_d_n_all_accs_avg, cu_d_n_all_bal_accs_avg],
        'Context-unaware - All Classes': [cu_ca_all_accs_avg, cu_ca_all_bal_accs_avg],
        'Context-aware - All Classes': [ca_ca_all_accs_avg, ca_ca_all_bal_accs_avg]
    }, index=['Accuracy', 'Average class accuracy'])

    name = f'{detector.value}_accs_all_avg_bal'
    all_dfs[detector][name] = df_all_accs_avg
    util.save_df_to_ppt_table(df_all_accs_avg, name)
    print("\n\n")
    print(df_all_accs_avg.to_latex(index=False))

    # Context-unaware
    # Percentage positive attributable
    # Aggregate by Capacity through keeping the other constant
    for perc2 in PERCS:
        # Deviating and normal only
        # Mean accuracies
        d_n_no_context_attr_metrics[detector][sit1][ACC_LBL][perc2] = np.mean(
            [
                acc
                for key, acc in d_n_no_context_metrics[detector][ACC_LBL].items()
                if key[2] == perc2
            ]
        )
        # mean average class accuracies
        d_n_no_context_attr_metrics[detector][sit1][B_ACC_LBL][perc2] = np.mean(
            [
                acc
                for key, acc in d_n_no_context_metrics[detector][B_ACC_LBL].items()
                if key[2] == perc2
            ]
        )
        # mean precisions
        d_n_no_context_attr_metrics[detector][sit1][PREC_LBL][perc2] = np.mean(
            [
                report[W_AVG_LBL][PREC_LBL]
                for key, report in d_n_no_context_metrics[detector][REPORT_LBL].items()
                if key[2] == perc2
            ]
        )
        # mean recalls
        d_n_no_context_attr_metrics[detector][sit1][RECALL_LBL][perc2] = np.mean(
            [
                report[W_AVG_LBL][RECALL_LBL]
                for key, report in d_n_no_context_metrics[detector][REPORT_LBL].items()
                if key[2] == perc2
            ]
        )
        # All classes
        # mean accuracies
        ca_no_context_attr_metrics[detector][sit1][ACC_LBL][perc2] = np.mean(
            [
                acc
                for key, acc in ca_no_context_metrics[detector][ACC_LBL].items()
                if key[2] == perc2
            ]
        )
        # Raw accuracies
        ca_no_context_attr_metrics[detector][sit1][R_ACC_LBL][perc2] = [
            acc
            for key, acc in ca_no_context_metrics[detector][ACC_LBL].items()
            if key[2] == perc2
        ]
        # mean average class accuracies
        ca_no_context_attr_metrics[detector][sit1][B_ACC_LBL][perc2] = np.mean(
            [
                acc
                for key, acc in ca_no_context_metrics[detector][B_ACC_LBL].items()
                if key[2] == perc2
            ]
        )
        # mean precisions
        ca_no_context_attr_metrics[detector][sit1][PREC_LBL][perc2] = np.mean(
            [
                report[W_AVG_LBL][PREC_LBL]
                for key, report in ca_no_context_metrics[detector][REPORT_LBL].items()
                if key[2] == perc2
            ]
        )
        # Raw precisions
        ca_no_context_attr_metrics[detector][sit1][R_PREC_LBL][perc2] = [
            report[W_AVG_LBL][PREC_LBL]
            for key, report in ca_no_context_metrics[detector][REPORT_LBL].items()
            if key[2] == perc2
        ]
        # mean recalls
        ca_no_context_attr_metrics[detector][sit1][RECALL_LBL][perc2] = np.mean(
            [
                report[W_AVG_LBL][RECALL_LBL]
                for key, report in ca_no_context_metrics[detector][REPORT_LBL].items()
                if key[2] == perc2
            ]
        )
        # Raw recalls
        ca_no_context_attr_metrics[detector][sit1][R_RECALL_LBL][perc2] = [
            report[W_AVG_LBL][RECALL_LBL]
            for key, report in ca_no_context_metrics[detector][REPORT_LBL].items()
            if key[2] == perc2
        ]

    df_cu_d_n_capacity_perc_attributable_metrics = pd.DataFrame({
        '% Context Attributable': PERCS,
        'Accuracy': [d_n_no_context_attr_metrics[detector][sit1][ACC_LBL][perc] for perc in PERCS],
        PREC_LBL: [d_n_no_context_attr_metrics[detector][sit1][PREC_LBL][perc] for perc in PERCS],
        RECALL_LBL: [d_n_no_context_attr_metrics[detector][sit1][RECALL_LBL][perc] for perc in PERCS]
    })

    name = f'{detector.value}_cu_d_n_metrics_attributable_capacity'
    all_dfs[detector][name] = df_cu_d_n_capacity_perc_attributable_metrics
    util.plot_metrics('% Context Attributable', 'Value', 'Variable', df_cu_d_n_capacity_perc_attributable_metrics,
                      name)

    df_cu_ca_capacity_perc_attributable_metrics = pd.DataFrame({
        '% Context Attributable': PERCS,
        'Accuracy': [ca_no_context_attr_metrics[detector][sit1][ACC_LBL][perc] for perc in PERCS],
        PREC_LBL: [ca_no_context_attr_metrics[detector][sit1][PREC_LBL][perc] for perc in PERCS],
        RECALL_LBL: [ca_no_context_attr_metrics[detector][sit1][RECALL_LBL][perc] for perc in PERCS]
    })

    name = f'{detector.value}_cu_ca_metrics_attributable_capacity'
    all_dfs[detector][name] = df_cu_ca_capacity_perc_attributable_metrics
    util.plot_metrics('% Context Attributable', 'Value', 'Variable', df_cu_ca_capacity_perc_attributable_metrics,
                      name)

    # Aggregate by Time Unit Performance through keeping the other constant
    for perc1 in PERCS:
        # Deviating and normal only
        # Mean accuracies
        d_n_no_context_attr_metrics[detector][sit2][ACC_LBL][perc1] = np.mean(
            [
                acc
                for key, acc in d_n_no_context_metrics[detector][ACC_LBL].items()
                if key[1] == perc1
            ]
        )
        # mean average class accuracies
        d_n_no_context_attr_metrics[detector][sit2][B_ACC_LBL][perc1] = np.mean(
            [
                acc
                for key, acc in d_n_no_context_metrics[detector][B_ACC_LBL].items()
                if key[1] == perc1
            ]
        )
        # mean precisions
        d_n_no_context_attr_metrics[detector][sit2][PREC_LBL][perc1] = np.mean(
            [
                report[W_AVG_LBL][PREC_LBL]
                for key, report in d_n_no_context_metrics[detector][REPORT_LBL].items()
                if key[1] == perc1
            ]
        )
        # mean recalls
        d_n_no_context_attr_metrics[detector][sit2][RECALL_LBL][perc1] = np.mean(
            [
                report[W_AVG_LBL][RECALL_LBL]
                for key, report in d_n_no_context_metrics[detector][REPORT_LBL].items()
                if key[1] == perc1
            ]
        )
        # All classes
        # mean accuracies
        ca_no_context_attr_metrics[detector][sit2][ACC_LBL][perc1] = np.mean(
            [
                acc
                for key, acc in ca_no_context_metrics[detector][ACC_LBL].items()
                if key[1] == perc1
            ]
        )
        # Raw accuracies
        ca_no_context_attr_metrics[detector][sit2][R_ACC_LBL][perc1] = [
            acc
            for key, acc in ca_no_context_metrics[detector][ACC_LBL].items()
            if key[2] == perc1
        ]
        # mean average class accuracies
        ca_no_context_attr_metrics[detector][sit2][B_ACC_LBL][perc1] = np.mean(
            [
                acc
                for key, acc in ca_no_context_metrics[detector][B_ACC_LBL].items()
                if key[1] == perc1
            ]
        )
        # mean precisions
        ca_no_context_attr_metrics[detector][sit2][PREC_LBL][perc1] = np.mean(
            [
                report[W_AVG_LBL][PREC_LBL]
                for key, report in ca_no_context_metrics[detector][REPORT_LBL].items()
                if key[1] == perc1
            ]
        )
        # Raw precisions
        ca_no_context_attr_metrics[detector][sit2][R_PREC_LBL][perc1] = [
            report[W_AVG_LBL][PREC_LBL]
            for key, report in ca_no_context_metrics[detector][REPORT_LBL].items()
            if key[1] == perc1
        ]
        # mean recalls
        ca_no_context_attr_metrics[detector][sit2][RECALL_LBL][perc1] = np.mean(
            [
                report[W_AVG_LBL][RECALL_LBL]
                for key, report in ca_no_context_metrics[detector][REPORT_LBL].items()
                if key[1] == perc1
            ]
        )
        # Raw recalls
        ca_no_context_attr_metrics[detector][sit2][R_RECALL_LBL][perc1] = [
            report[W_AVG_LBL][RECALL_LBL]
            for key, report in ca_no_context_metrics[detector][REPORT_LBL].items()
            if key[1] == perc1
        ]

    df_cu_d_n_tu_perc_attributable_metrics = pd.DataFrame({
        '% Context Attributable': PERCS,
        'Accuracy': [d_n_no_context_attr_metrics[detector][sit2][ACC_LBL][perc] for perc in PERCS],
        PREC_LBL: [d_n_no_context_attr_metrics[detector][sit2][PREC_LBL][perc] for perc in PERCS],
        RECALL_LBL: [d_n_no_context_attr_metrics[detector][sit2][RECALL_LBL][perc] for perc in PERCS]
    })

    name = f'{detector.value}_cu_d_n_metrics_attributable_tu'
    all_dfs[detector][name] = df_cu_d_n_tu_perc_attributable_metrics
    util.plot_metrics('% Context Attributable', 'Value', 'Variable', df_cu_d_n_tu_perc_attributable_metrics,
                      name)

    df_cu_ca_tu_perc_attributable_metrics = pd.DataFrame({
        '% Context Attributable': PERCS,
        'Accuracy': [ca_no_context_attr_metrics[detector][sit2][ACC_LBL][perc] for perc in PERCS],
        PREC_LBL: [ca_no_context_attr_metrics[detector][sit2][PREC_LBL][perc] for perc in PERCS],
        RECALL_LBL: [ca_no_context_attr_metrics[detector][sit2][RECALL_LBL][perc] for perc in PERCS]
    })

    name = f'{detector.value}_cu_ca_metrics_attributable_tu'
    all_dfs[detector][name] = df_cu_ca_tu_perc_attributable_metrics
    util.plot_metrics('% Context Attributable', 'Value', 'Variable', df_cu_ca_tu_perc_attributable_metrics,
                      name)

    # Percentage deviating
    for perc in DEVS:
        # Deviating and normal only
        # mean accuracies
        d_n_no_context_dev_metrics[detector][ACC_LBL][perc] = np.mean(
            [
                acc for key, acc in d_n_no_context_metrics[detector][ACC_LBL].items()
                if key[3] == perc
            ]
        )
        # mean average class accuracies
        d_n_no_context_dev_metrics[detector][B_ACC_LBL][perc] = np.mean(
            [
                acc for key, acc in d_n_no_context_metrics[detector][B_ACC_LBL].items()
                if key[3] == perc
            ]
        )
        # mean precisions
        d_n_no_context_dev_metrics[detector][PREC_LBL][perc] = np.nanmean(
            [
                report[W_AVG_LBL][PREC_LBL]
                for key, report in d_n_no_context_metrics[detector][REPORT_LBL].items()
                if key[3] == perc
            ]
        )
        # mean recalls
        d_n_no_context_dev_metrics[detector][RECALL_LBL][perc] = np.nanmean(
            [
                report[W_AVG_LBL][RECALL_LBL]
                for key, report in d_n_no_context_metrics[detector][REPORT_LBL].items()
                if key[3] == perc
            ]
        )

        # All classes
        # mean accuracies
        ca_no_context_dev_metrics[detector][ACC_LBL][perc] = np.mean(
            [
                acc
                for key, acc in ca_no_context_metrics[detector][ACC_LBL].items()
                if key[3] == perc
            ]
        )
        # Raw accuracies
        ca_no_context_dev_metrics[detector][R_ACC_LBL][perc] = [
            acc
            for key, acc in ca_no_context_metrics[detector][ACC_LBL].items()
            if key[3] == perc
        ]
        # mean average class accuracies
        ca_no_context_dev_metrics[detector][B_ACC_LBL][perc] = np.mean(
            [
                acc
                for key, acc in ca_no_context_metrics[detector][B_ACC_LBL].items()
                if key[3] == perc
            ]
        )
        # mean precisions
        ca_no_context_dev_metrics[detector][PREC_LBL][perc] = np.nanmean(
            [
                report[W_AVG_LBL][PREC_LBL]
                for key, report in ca_no_context_metrics[detector][REPORT_LBL].items()
                if key[3] == perc
            ]
        )
        # raw precisions
        ca_no_context_dev_metrics[detector][R_PREC_LBL][perc] = [
            report[W_AVG_LBL][PREC_LBL]
            for key, report in ca_no_context_metrics[detector][REPORT_LBL].items()
            if key[3] == perc
        ]
        # mean recalls
        ca_no_context_dev_metrics[detector][RECALL_LBL][perc] = np.nanmean(
            [
                report[W_AVG_LBL][RECALL_LBL]
                for key, report in ca_no_context_metrics[detector][REPORT_LBL].items()
                if key[3] == perc
            ]
        )
        # raw recalls
        ca_no_context_dev_metrics[detector][R_RECALL_LBL][perc] = [
            report[W_AVG_LBL][RECALL_LBL]
            for key, report in ca_no_context_metrics[detector][REPORT_LBL].items()
            if key[3] == perc
        ]

    df_cu_d_n_perc_deviating_metrics = pd.DataFrame({
        '% Deviating Events': DEVS,
        'Average Class Accuracy': [d_n_no_context_dev_metrics[detector]['balanced_accs'][perc] for perc in
                                   DEVS],
        'Accuracy': [d_n_no_context_dev_metrics[detector]['accs'][perc] for perc in DEVS],
        'Precision': [d_n_no_context_dev_metrics[detector]['precision'][perc] for perc in DEVS],
        'Recall': [d_n_no_context_dev_metrics[detector]['recall'][perc] for perc in DEVS]
    })

    name = f'{detector.value}_cu_d_n_metrics_deviating'
    all_dfs[detector][name] = df_cu_d_n_perc_deviating_metrics
    util.plot_metrics('% Deviating Events', 'Value', 'Variable', df_cu_d_n_perc_deviating_metrics,
                      name)

    df_cu_ca_perc_deviating_metrics = pd.DataFrame({
        '% Deviating Events': DEVS,
        'Accuracy': [ca_no_context_dev_metrics[detector][ACC_LBL][perc] for perc in DEVS],
        PREC_LBL: [ca_no_context_dev_metrics[detector][PREC_LBL][perc] for perc in DEVS],
        RECALL_LBL: [ca_no_context_dev_metrics[detector][RECALL_LBL][perc] for perc in DEVS]
    })

    name = f'{detector.value}_cu_ca_metrics_deviating'
    all_dfs[detector][name] = df_cu_ca_perc_deviating_metrics
    util.plot_metrics('% Deviating Events', 'Value', 'Variable', df_cu_ca_perc_deviating_metrics,
                      name)

    # Context-aware
    # Optimized for acc
    # Accuracies all average
    ca_ca_all_accs_avg = np.mean([
        util.existing_optimized(acc, key, ca_with_context_metrics, detector, ACC_LBL, ca_no_context_metrics)
        for key, acc in ca_no_context_metrics[detector][ACC_LBL].items()])

    # Balanced accuracies all average
    ca_ca_all_bal_accs_avg = np.mean([
        util.existing_optimized(acc, key, ca_with_context_metrics, detector, B_ACC_LBL, ca_no_context_metrics)
        for key, acc in ca_no_context_metrics[detector][B_ACC_LBL].items()])

    df_ca_all_accs_avg = pd.DataFrame({
        'All Classes': [ca_ca_all_bal_accs_avg, ca_ca_all_accs_avg]
    }, index=['Average class accuracy', 'Accuracy'])

    util.save_df_to_ppt_table(df_ca_all_accs_avg, f'accs_ca_{detector.value}_acc_opt_avg')
    print("\n\n")
    print(df_ca_all_accs_avg.to_latex(index=False))

    # Optimized for balanced acc
    # Accuracies all average
    ca_ca_all_accs_bal_avg = np.mean([
        util.existing_optimized(acc, key, ca_with_context_bal_metrics, detector, ACC_LBL, ca_no_context_metrics)
        for key, acc in ca_no_context_metrics[detector][ACC_LBL].items()])

    # Balanced accuracies all average
    ca_ca_all_bal_accs_bal_avg = np.mean([
        util.existing_optimized(acc, key, ca_with_context_bal_metrics, detector, B_ACC_LBL, ca_no_context_metrics)
        for key, acc in ca_no_context_metrics[detector][B_ACC_LBL].items()])

    df_ca_all_accs_bal_avg = pd.DataFrame({
        'All Classes': [ca_ca_all_bal_accs_bal_avg, ca_ca_all_accs_bal_avg]
    }, index=['Average class accuracy', 'Accuracy'])

    name = f'{detector.value}_accs_ca_bal_opt_avg'
    all_dfs[detector][name] = df_ca_all_accs_bal_avg
    util.save_df_to_ppt_table(df_ca_all_accs_bal_avg, name)
    print("\n\n")
    print(df_ca_all_accs_bal_avg.to_latex(index=False))

    # Percentage positive attributable
    # Optimized by acc
    # Aggregate by Capacity through keeping the other constant
    for perc2 in PERCS:
        # All classes
        # mean accuracies
        ca_with_context_attr_metrics[detector][sit1][ACC_LBL][perc2] = np.mean(
            [
                util.existing_optimized(acc, key, ca_with_context_metrics, detector, ACC_LBL, ca_no_context_metrics)
                for key, acc in ca_no_context_metrics[detector][ACC_LBL].items()
                if key[2] == perc2
            ]
        )
        # Raw accuracies
        ca_with_context_attr_metrics[detector][sit1][R_ACC_LBL][perc2] = [
            util.existing_optimized(acc, key, ca_with_context_metrics, detector, ACC_LBL, ca_no_context_metrics)
            for key, acc in
            ca_no_context_metrics[detector][
                ACC_LBL].items()
            if key[2] == perc2]
        # mean average class accuracies
        ca_with_context_attr_metrics[detector][sit1][B_ACC_LBL][perc2] = np.mean(
            [
                util.existing_optimized(acc, key, ca_with_context_metrics, detector, B_ACC_LBL, ca_no_context_metrics)
                for key, acc in ca_no_context_metrics[detector][B_ACC_LBL].items()
                if key[2] == perc2
            ]
        )
        # mean precisions
        ca_with_context_attr_metrics[detector][sit1][PREC_LBL][perc2] = np.mean(
            [
                report[W_AVG_LBL][PREC_LBL]
                if key not in ca_with_context_metrics[detector][ACC_LBL]
                else ca_with_context_metrics[detector][REPORT_LBL][key][W_AVG_LBL][PREC_LBL]
                for key, report in ca_no_context_metrics[detector][REPORT_LBL].items()
                if key[2] == perc2
            ]
        )
        # Raw precisions
        ca_with_context_attr_metrics[detector][sit1][R_PREC_LBL][perc2] = [
            report[W_AVG_LBL][PREC_LBL]
            if key not in ca_with_context_metrics[detector][ACC_LBL]
            else ca_with_context_metrics[detector][REPORT_LBL][key][W_AVG_LBL][PREC_LBL]
            for key, report in ca_no_context_metrics[detector][REPORT_LBL].items()
            if key[2] == perc2]
        # mean recalls
        ca_with_context_attr_metrics[detector][sit1][RECALL_LBL][perc2] = np.mean(
            [
                report[W_AVG_LBL][RECALL_LBL]
                if key not in ca_with_context_metrics[detector][ACC_LBL]
                else ca_with_context_metrics[detector][REPORT_LBL][key][W_AVG_LBL][RECALL_LBL]
                for key, report in ca_no_context_metrics[detector][REPORT_LBL].items()
                if key[2] == perc2
            ]
        )
        # Raw recalls
        ca_with_context_attr_metrics[detector][sit1][R_RECALL_LBL][perc2] = [
            report[W_AVG_LBL][RECALL_LBL]
            if key not in ca_with_context_metrics[detector][ACC_LBL]
            else ca_with_context_metrics[detector][REPORT_LBL][key][W_AVG_LBL][RECALL_LBL]
            for key, report in ca_no_context_metrics[detector][REPORT_LBL].items()
            if key[2] == perc2]

    df_ca_ca_capacity_perc_attributable_metrics = pd.DataFrame({
        '% Context Attributable': PERCS,
        'Accuracy': [ca_with_context_attr_metrics[detector][sit1][ACC_LBL][perc] for perc in PERCS],
        PREC_LBL: [ca_with_context_attr_metrics[detector][sit1][PREC_LBL][perc] for perc in PERCS],
        RECALL_LBL: [ca_with_context_attr_metrics[detector][sit1][RECALL_LBL][perc] for perc in PERCS]
    })

    name = f'{detector.value}_ca_ca_metrics_attributable_capacity'
    all_dfs[detector][name] = df_ca_ca_capacity_perc_attributable_metrics
    util.plot_metrics('% Context Attributable', 'Value', 'Variable', df_ca_ca_capacity_perc_attributable_metrics,
                      name)

    # Aggregate by Time Unit Performance through keeping the other constant
    for perc1 in PERCS:
        # All classes
        # mean accuracies
        ca_with_context_attr_metrics[detector][sit2][ACC_LBL][perc1] = np.mean(
            [
                util.existing_optimized(acc, key, ca_with_context_metrics, detector, ACC_LBL, ca_no_context_metrics)
                for key, acc in ca_no_context_metrics[detector][ACC_LBL].items()
                if key[1] == perc1
            ]
        )
        # Raw accuracies
        ca_with_context_attr_metrics[detector][sit2][R_ACC_LBL][perc1] = [
            util.existing_optimized(acc, key, ca_with_context_metrics, detector, ACC_LBL, ca_no_context_metrics)
            for key, acc in ca_no_context_metrics[detector][ACC_LBL].items()
            if key[1] == perc1]
        # mean average class accuracies
        ca_with_context_attr_metrics[detector][sit2][B_ACC_LBL][perc1] = np.mean(
            [
                util.existing_optimized(acc, key, ca_with_context_metrics, detector, B_ACC_LBL, ca_no_context_metrics)
                for key, acc in ca_no_context_metrics[detector][B_ACC_LBL].items()
                if key[1] == perc1
            ]
        )
        # mean precisions
        ca_with_context_attr_metrics[detector][sit2][PREC_LBL][perc1] = np.mean(
            [
                report[W_AVG_LBL][PREC_LBL]
                if key not in ca_with_context_metrics[detector][ACC_LBL]
                else ca_with_context_metrics[detector][REPORT_LBL][key][W_AVG_LBL][PREC_LBL]
                for key, report in ca_no_context_metrics[detector][REPORT_LBL].items()
                if key[1] == perc1
            ]
        )
        # Raw precisions
        ca_with_context_attr_metrics[detector][sit2][R_PREC_LBL][perc1] = [
            report[W_AVG_LBL][PREC_LBL]
            if key not in ca_with_context_metrics[detector][ACC_LBL]
            else ca_with_context_metrics[detector][REPORT_LBL][key][W_AVG_LBL][PREC_LBL]
            for key, report in ca_no_context_metrics[detector][REPORT_LBL].items()
            if key[1] == perc1]
        # mean recalls
        ca_with_context_attr_metrics[detector][sit2][RECALL_LBL][perc1] = np.mean(
            [
                report[W_AVG_LBL][RECALL_LBL]
                if key not in ca_with_context_metrics[detector][ACC_LBL]
                else ca_with_context_metrics[detector][REPORT_LBL][key][W_AVG_LBL][RECALL_LBL]
                for key, report in ca_no_context_metrics[detector][REPORT_LBL].items()
                if key[1] == perc1
            ]
        )
        # Raw recalls
        ca_with_context_attr_metrics[detector][sit2][R_RECALL_LBL][perc1] = [
            report[W_AVG_LBL][RECALL_LBL]
            if key not in ca_with_context_metrics[detector][ACC_LBL]
            else ca_with_context_metrics[detector][REPORT_LBL][key][W_AVG_LBL][RECALL_LBL]
            for key, report in ca_no_context_metrics[detector][REPORT_LBL].items()
            if key[1] == perc1]

    df_ca_ca_tu_perc_attributable_metrics = pd.DataFrame({
        '% Context Attributable': PERCS,
        'Accuracy': [ca_with_context_attr_metrics[detector][sit2][ACC_LBL][perc] for perc in PERCS],
        PREC_LBL: [ca_with_context_attr_metrics[detector][sit2][PREC_LBL][perc] for perc in PERCS],
        RECALL_LBL: [ca_with_context_attr_metrics[detector][sit2][RECALL_LBL][perc] for perc in PERCS]
    })

    name = f'{detector.value}_ca_ca_metrics_attributable_tu'
    all_dfs[detector][name] = df_ca_ca_tu_perc_attributable_metrics
    util.plot_metrics('% Context Attributable', 'Value', 'Variable', df_ca_ca_tu_perc_attributable_metrics,
                      name)

    # Optimized by balanced acc
    # Aggregate by Capacity through keeping the other constant
    for perc2 in PERCS:
        # All classes
        # mean accuracies
        ca_with_context_bal_attr_metrics[detector][sit1][ACC_LBL][perc2] = np.mean(
            [
                util.existing_optimized(acc, key, ca_with_context_bal_metrics, detector, ACC_LBL, ca_no_context_metrics)
                for key, acc in ca_no_context_metrics[detector][ACC_LBL].items()
                if key[2] == perc2
            ]
        )
        # Raw accuracies
        ca_with_context_bal_attr_metrics[detector][sit1][R_ACC_LBL][perc2] = [
            util.existing_optimized(acc, key, ca_with_context_bal_metrics, detector, ACC_LBL, ca_no_context_metrics)
            for key, acc in
            ca_no_context_metrics[detector][
                ACC_LBL].items()
            if key[2] == perc2]
        # mean average class accuracies
        ca_with_context_bal_attr_metrics[detector][sit1][B_ACC_LBL][perc2] = np.mean(
            [
                util.existing_optimized(acc, key, ca_with_context_bal_metrics, detector, B_ACC_LBL,
                                        ca_no_context_metrics)
                for key, acc in ca_no_context_metrics[detector][B_ACC_LBL].items()
                if key[2] == perc2
            ]
        )
        # mean precisions
        ca_with_context_bal_attr_metrics[detector][sit1][PREC_LBL][perc2] = np.mean(
            [
                report[W_AVG_LBL][PREC_LBL]
                if key not in ca_with_context_bal_metrics[detector][ACC_LBL]
                else ca_with_context_bal_metrics[detector][REPORT_LBL][key][W_AVG_LBL][PREC_LBL]
                for key, report in ca_no_context_metrics[detector][REPORT_LBL].items()
                if key[2] == perc2
            ]
        )
        # Raw precisions
        ca_with_context_bal_attr_metrics[detector][sit1][R_PREC_LBL][perc2] = [
            report[W_AVG_LBL][PREC_LBL]
            if key not in ca_with_context_bal_metrics[detector][ACC_LBL]
            else ca_with_context_bal_metrics[detector][REPORT_LBL][key][W_AVG_LBL][PREC_LBL]
            for key, report in ca_no_context_metrics[detector][REPORT_LBL].items()
            if key[2] == perc2]
        # mean recalls
        ca_with_context_bal_attr_metrics[detector][sit1][RECALL_LBL][perc2] = np.mean(
            [
                report[W_AVG_LBL][RECALL_LBL]
                if key not in ca_with_context_bal_metrics[detector][ACC_LBL]
                else ca_with_context_bal_metrics[detector][REPORT_LBL][key][W_AVG_LBL][RECALL_LBL]
                for key, report in ca_no_context_metrics[detector][REPORT_LBL].items()
                if key[2] == perc2
            ]
        )
        # Raw recalls
        ca_with_context_bal_attr_metrics[detector][sit1][R_RECALL_LBL][perc2] = [
            report[W_AVG_LBL][RECALL_LBL]
            if key not in ca_with_context_bal_metrics[detector][ACC_LBL]
            else ca_with_context_bal_metrics[detector][REPORT_LBL][key][W_AVG_LBL][RECALL_LBL]
            for key, report in ca_no_context_metrics[detector][REPORT_LBL].items()
            if key[2] == perc2]

    df_ca_ca_capacity_perc_attributable_bal_metrics = pd.DataFrame({
        '% Context Attributable': PERCS,
        'Accuracy': [ca_with_context_bal_attr_metrics[detector][sit1][ACC_LBL][perc] for perc in PERCS],
        PREC_LBL: [ca_with_context_bal_attr_metrics[detector][sit1][PREC_LBL][perc] for perc in PERCS],
        RECALL_LBL: [ca_with_context_bal_attr_metrics[detector][sit1][RECALL_LBL][perc] for perc in PERCS]
    })

    name = f'{detector.value}_ca_ca_bal_metrics_attributable_capacity'
    all_dfs[detector][name] = df_ca_ca_capacity_perc_attributable_bal_metrics
    util.plot_metrics('% Context Attributable', 'Value', 'Variable', df_ca_ca_capacity_perc_attributable_bal_metrics,
                      name)

    # Aggregate by Time Unit Performance through keeping the other constant
    for perc1 in PERCS:
        # All classes
        # mean accuracies
        ca_with_context_bal_attr_metrics[detector][sit2][ACC_LBL][perc1] = np.mean(
            [
                util.existing_optimized(acc, key, ca_with_context_bal_metrics, detector, ACC_LBL, ca_no_context_metrics)
                for key, acc in ca_no_context_metrics[detector][ACC_LBL].items()
                if key[1] == perc1
            ]
        )
        # Raw accuracies
        ca_with_context_bal_attr_metrics[detector][sit2][R_ACC_LBL][perc1] = [
            util.existing_optimized(acc, key, ca_with_context_metrics, detector, ACC_LBL, ca_no_context_metrics)
            for key, acc in
            ca_no_context_metrics[detector][
                ACC_LBL].items()
            if key[1] == perc1]
        # mean average class accuracies
        ca_with_context_bal_attr_metrics[detector][sit2][B_ACC_LBL][perc1] = np.mean(
            [
                util.existing_optimized(acc, key, ca_with_context_bal_metrics, detector, B_ACC_LBL,
                                        ca_no_context_metrics)
                for key, acc in ca_no_context_metrics[detector][B_ACC_LBL].items()
                if key[1] == perc1
            ]
        )
        # mean precisions
        ca_with_context_bal_attr_metrics[detector][sit2][PREC_LBL][perc1] = np.mean(
            [
                report[W_AVG_LBL][PREC_LBL]
                if key not in ca_with_context_bal_metrics[detector][ACC_LBL]
                else ca_with_context_bal_metrics[detector][REPORT_LBL][key][W_AVG_LBL][PREC_LBL]
                for key, report in ca_no_context_metrics[detector][REPORT_LBL].items()
                if key[1] == perc1
            ]
        )
        # Raw precisions
        ca_with_context_bal_attr_metrics[detector][sit2][R_PREC_LBL][perc1] = [
            report[W_AVG_LBL][PREC_LBL]
            if key not in ca_with_context_bal_metrics[detector][ACC_LBL]
            else ca_with_context_bal_metrics[detector][REPORT_LBL][key][W_AVG_LBL][PREC_LBL]
            for key, report in ca_no_context_metrics[detector][REPORT_LBL].items()
            if key[1] == perc1]
        # mean recalls
        ca_with_context_bal_attr_metrics[detector][sit2][RECALL_LBL][perc1] = np.mean(
            [
                report[W_AVG_LBL][RECALL_LBL]
                if key not in ca_with_context_bal_metrics[detector][ACC_LBL]
                else ca_with_context_bal_metrics[detector][REPORT_LBL][key][W_AVG_LBL][RECALL_LBL]
                for key, report in ca_no_context_metrics[detector][REPORT_LBL].items()
                if key[1] == perc1
            ]
        )
        # Raw recalls
        ca_with_context_bal_attr_metrics[detector][sit2][R_RECALL_LBL][perc1] = [
            report[W_AVG_LBL][RECALL_LBL]
            if key not in ca_with_context_bal_metrics[detector][ACC_LBL]
            else ca_with_context_bal_metrics[detector][REPORT_LBL][key][W_AVG_LBL][RECALL_LBL]
            for key, report in ca_no_context_metrics[detector][REPORT_LBL].items()
            if key[1] == perc1]

    df_ca_ca_tu_perc_attributable_bal_metrics = pd.DataFrame({
        '% Context Attributable': PERCS,
        'Accuracy': [ca_with_context_bal_attr_metrics[detector][sit2][ACC_LBL][perc] for perc in PERCS],
        PREC_LBL: [ca_with_context_bal_attr_metrics[detector][sit2][PREC_LBL][perc] for perc in PERCS],
        RECALL_LBL: [ca_with_context_bal_attr_metrics[detector][sit2][RECALL_LBL][perc] for perc in PERCS]
    })

    name = f'{detector.value}_ca_ca_bal_metrics_attributable_tu'
    all_dfs[detector][name] = df_ca_ca_tu_perc_attributable_bal_metrics
    util.plot_metrics('% Context Attributable', 'Value', 'Variable', df_ca_ca_tu_perc_attributable_bal_metrics,
                      name)

    # Percentage deviating
    # Optimized for acc
    for perc in DEVS:
        # All classes
        # mean accuracies
        ca_with_context_dev_metrics[detector][ACC_LBL][perc] = np.mean(
            [
                util.existing_optimized(acc, key, ca_with_context_metrics, detector, ACC_LBL, ca_no_context_metrics)
                for key, acc in ca_no_context_metrics[detector][ACC_LBL].items()
                if key[3] == perc
            ]
        )
        # Raw accuracies
        ca_with_context_dev_metrics[detector][R_ACC_LBL][perc] = [
            util.existing_optimized(acc, key, ca_with_context_metrics, detector, ACC_LBL, ca_no_context_metrics)
            for key, acc in ca_no_context_metrics[detector][ACC_LBL].items()
            if key[3] == perc
        ]
        # mean average class accuracies
        ca_with_context_dev_metrics[detector][B_ACC_LBL][perc] = np.mean(
            [
                util.existing_optimized(acc, key, ca_with_context_metrics, detector, B_ACC_LBL, ca_no_context_metrics)
                for key, acc in ca_no_context_metrics[detector][B_ACC_LBL].items()
                if key[3] == perc
            ]
        )
        # mean precisions
        ca_with_context_dev_metrics[detector][PREC_LBL][perc] = np.nanmean(
            [
                report[W_AVG_LBL][PREC_LBL]
                if key not in ca_with_context_metrics[detector][ACC_LBL]
                else ca_with_context_metrics[detector][REPORT_LBL][key][W_AVG_LBL][PREC_LBL]
                for key, report in ca_no_context_metrics[detector][REPORT_LBL].items()
                if key[3] == perc
            ]
        )
        # raw precisions
        ca_with_context_dev_metrics[detector][R_PREC_LBL][perc] = [
            report[W_AVG_LBL][PREC_LBL]
            if key not in ca_with_context_metrics[detector][ACC_LBL]
            else ca_with_context_metrics[detector][REPORT_LBL][key][W_AVG_LBL][PREC_LBL]
            for key, report in ca_no_context_metrics[detector][REPORT_LBL].items()
            if key[3] == perc
        ]
        # mean recalls
        ca_with_context_dev_metrics[detector][RECALL_LBL][perc] = np.nanmean(
            [
                report[W_AVG_LBL][RECALL_LBL]
                if key not in ca_with_context_metrics[detector][ACC_LBL]
                else ca_with_context_metrics[detector][REPORT_LBL][key][W_AVG_LBL][RECALL_LBL]
                for key, report in ca_no_context_metrics[detector][REPORT_LBL].items()
                if key[3] == perc
            ]
        )
        # raw recalls
        ca_with_context_dev_metrics[detector][R_RECALL_LBL][perc] = [
            report[W_AVG_LBL][RECALL_LBL]
            if key not in ca_with_context_metrics[detector][ACC_LBL]
            else ca_with_context_metrics[detector][REPORT_LBL][key][W_AVG_LBL][RECALL_LBL]
            for key, report in ca_no_context_metrics[detector][REPORT_LBL].items()
            if key[3] == perc
        ]

    df_ca_ca_perc_deviating_metrics = pd.DataFrame({
        '% Deviating Events': DEVS,
        'Accuracy': [ca_with_context_dev_metrics[detector][ACC_LBL][perc] for perc in DEVS],
        PREC_LBL: [ca_with_context_dev_metrics[detector][PREC_LBL][perc] for perc in DEVS],
        RECALL_LBL: [ca_with_context_dev_metrics[detector][RECALL_LBL][perc] for perc in DEVS]
    })

    name = f'{detector.value}_cu_ca_metrics_deviating'
    all_dfs[detector][name] = df_ca_ca_perc_deviating_metrics
    util.plot_metrics('% Deviating Events', 'Value', 'Variable', df_ca_ca_perc_deviating_metrics,
                      name)

    # Percentage deviating
    # Optimized for bal acc
    for perc in DEVS:
        # All classes
        # mean accuracies
        ca_with_context_bal_dev_metrics[detector][ACC_LBL][perc] = np.mean(
            [
                util.existing_optimized(acc, key, ca_with_context_bal_metrics, detector, ACC_LBL, ca_no_context_metrics)
                for key, acc in ca_no_context_metrics[detector][ACC_LBL].items()
                if key[3] == perc
            ]
        )
        # Raw accuracies
        ca_with_context_bal_dev_metrics[detector][R_ACC_LBL][perc] = [
            util.existing_optimized(acc, key, ca_with_context_bal_metrics, detector, ACC_LBL, ca_no_context_metrics)
            for key, acc in ca_no_context_metrics[detector][ACC_LBL].items()
            if key[3] == perc
        ]
        # mean average class accuracies
        ca_with_context_bal_dev_metrics[detector][B_ACC_LBL][perc] = np.mean(
            [
                util.existing_optimized(acc, key, ca_with_context_bal_metrics, detector, B_ACC_LBL,
                                        ca_no_context_metrics)
                for key, acc in ca_no_context_metrics[detector][B_ACC_LBL].items()
                if key[3] == perc
            ]
        )
        # mean precisions
        ca_with_context_bal_dev_metrics[detector][PREC_LBL][perc] = np.nanmean(
            [
                report[W_AVG_LBL][PREC_LBL]
                if key not in ca_with_context_bal_metrics[detector][ACC_LBL]
                else ca_with_context_bal_metrics[detector][REPORT_LBL][key][W_AVG_LBL][PREC_LBL]
                for key, report in ca_no_context_metrics[detector][REPORT_LBL].items()
                if key[3] == perc
            ]
        )
        # raw precisions
        ca_with_context_bal_dev_metrics[detector][R_PREC_LBL][perc] = [
            report[W_AVG_LBL][PREC_LBL]
            if key not in ca_with_context_bal_metrics[detector][ACC_LBL]
            else ca_with_context_bal_metrics[detector][REPORT_LBL][key][W_AVG_LBL][PREC_LBL]
            for key, report in ca_no_context_metrics[detector][REPORT_LBL].items()
            if key[3] == perc
        ]
        # mean recalls
        ca_with_context_bal_dev_metrics[detector][RECALL_LBL][perc] = np.nanmean(
            [
                report[W_AVG_LBL][RECALL_LBL]
                if key not in ca_with_context_bal_metrics[detector][ACC_LBL]
                else ca_with_context_bal_metrics[detector][REPORT_LBL][key][W_AVG_LBL][RECALL_LBL]
                for key, report in ca_no_context_metrics[detector][REPORT_LBL].items()
                if key[3] == perc
            ]
        )
        # raw recalls
        ca_with_context_bal_dev_metrics[detector][R_RECALL_LBL][perc] = [
            report[W_AVG_LBL][RECALL_LBL]
            if key not in ca_with_context_bal_metrics[detector][ACC_LBL]
            else ca_with_context_bal_metrics[detector][REPORT_LBL][key][W_AVG_LBL][RECALL_LBL]
            for key, report in ca_no_context_metrics[detector][REPORT_LBL].items()
            if key[3] == perc
        ]

    df_ca_ca_perc_deviating_bal_metrics = pd.DataFrame({
        '% Deviating Events': DEVS,
        'Accuracy': [ca_with_context_bal_dev_metrics[detector][ACC_LBL][perc] for perc in DEVS],
        PREC_LBL: [ca_with_context_bal_dev_metrics[detector][PREC_LBL][perc] for perc in DEVS],
        RECALL_LBL: [ca_with_context_bal_dev_metrics[detector][RECALL_LBL][perc] for perc in DEVS]
    })

    name = f'{detector.value}_cu_ca_metrics_deviating'
    all_dfs[detector][name] = df_ca_ca_perc_deviating_bal_metrics
    util.plot_metrics('% Deviating Events', 'Value', 'Variable', df_ca_ca_perc_deviating_bal_metrics,
                      name)

    # Diff plots perc attributable
    # Optimized by acc
    # Capacity situation
    balanced_accuracy = [ca_no_context_attr_metrics[detector][sit1][B_ACC_LBL][perc] for perc in PERCS]
    balanced_accuracy_post = [ca_with_context_attr_metrics[detector][sit1][B_ACC_LBL][perc] for perc in PERCS]
    precision = [ca_no_context_attr_metrics[detector][sit1][PREC_LBL][perc] for perc in PERCS]
    precision_post = [ca_with_context_attr_metrics[detector][sit1][PREC_LBL][perc] for perc in PERCS]
    accuracy = [ca_no_context_attr_metrics[detector][sit1][ACC_LBL][perc] for perc in PERCS]
    accuracy_post = [ca_with_context_attr_metrics[detector][sit1][ACC_LBL][perc] for perc in PERCS]
    recall = [ca_no_context_attr_metrics[detector][sit1][RECALL_LBL][perc] for perc in PERCS]
    recall_post = [ca_with_context_attr_metrics[detector][sit1][RECALL_LBL][perc] for perc in PERCS]

    balanced_accuracy_post_diff = [balanced_accuracy_post[i] - balanced_accuracy[i]
                                   for i in range(len(balanced_accuracy))]
    accuracy_post_diff = [accuracy_post[i] - accuracy[i]
                          for i in range(len(accuracy))]
    precision_post_diff = [precision_post[i] - precision[i]
                           for i in range(len(precision))]
    recall_post_diff = [recall_post[i] - recall[i]
                        for i in range(len(recall))]

    df_ca_diff_perc_attributable_capacity_metrics = pd.DataFrame({
        '% Context Attributable': PERCS,
        'Average Class Accuracy': balanced_accuracy,
        'Average Class Accuracy Post': balanced_accuracy_post_diff,
        'Accuracy': accuracy,
        'Accuracy Post': accuracy_post_diff,
        'Precision': precision,
        'Precision Post': precision_post_diff,
        'Recall': recall,
        'Recall Post': recall_post_diff
    })

    name = f'{detector.value}_diff_ca_metrics_attributable_capacity.png'
    all_dfs[detector][name] = df_ca_diff_perc_attributable_capacity_metrics
    fig, ax1 = plt.subplots(figsize=(10, 8))
    plt.ylim(0, 1)
    df_ca_diff_perc_attributable_capacity_metrics.plot.bar(x='% Context Attributable',
                                                           y=['Accuracy', 'Average Class Accuracy', 'Precision',
                                                              'Recall'],
                                                           yerr=df_ca_diff_perc_attributable_capacity_metrics[
                                                               ['Accuracy Post',
                                                                'Average Class Accuracy Post',
                                                                'Precision Post',
                                                                'Recall Post']].T.values,
                                                           ylim=(0, 1),
                                                           ax=ax1)

    plt.savefig(get_resource_figurepath(name), bbox_inches='tight')
    plt.close('all')

    fig, ax1 = plt.subplots(figsize=(10, 8))
    plt.ylim(0, 1)
    df_ca_diff_perc_attributable_capacity_metrics.plot.bar(x='% Context Attributable',
                                                           y=['Accuracy', 'Average Class Accuracy'],
                                                           yerr=df_ca_diff_perc_attributable_capacity_metrics[
                                                               ['Accuracy Post',
                                                                'Average Class Accuracy Post']].T.values,
                                                           ylim=(0, 1),
                                                           ax=ax1)

    plt.savefig(get_resource_figurepath(f'{detector.value}_diff_ca_metrics_attributable_capacity_accuracies.png'),
                bbox_inches='tight')
    plt.close('all')

    # util.plot_metrics('% Context Attributable', 'Value', 'Variable', df_ca_perc_attributable_metrics,
    #                  'ca_metrics_attributable')

    # Time Unit Performance situation
    balanced_accuracy = [ca_no_context_attr_metrics[detector][sit2][B_ACC_LBL][perc] for perc in PERCS]
    balanced_accuracy_post = [ca_with_context_attr_metrics[detector][sit2][B_ACC_LBL][perc] for perc in PERCS]
    precision = [ca_no_context_attr_metrics[detector][sit2][PREC_LBL][perc] for perc in PERCS]
    precision_post = [ca_with_context_attr_metrics[detector][sit2][PREC_LBL][perc] for perc in PERCS]
    accuracy = [ca_no_context_attr_metrics[detector][sit2][ACC_LBL][perc] for perc in PERCS]
    accuracy_post = [ca_with_context_attr_metrics[detector][sit2][ACC_LBL][perc] for perc in PERCS]
    recall = [ca_no_context_attr_metrics[detector][sit2][RECALL_LBL][perc] for perc in PERCS]
    recall_post = [ca_with_context_attr_metrics[detector][sit2][RECALL_LBL][perc] for perc in PERCS]

    balanced_accuracy_post_diff = [balanced_accuracy_post[i] - balanced_accuracy[i]
                                   for i in range(len(balanced_accuracy))]
    accuracy_post_diff = [accuracy_post[i] - accuracy[i]
                          for i in range(len(accuracy))]
    precision_post_diff = [precision_post[i] - precision[i]
                           for i in range(len(precision))]
    recall_post_diff = [recall_post[i] - recall[i]
                        for i in range(len(recall))]

    df_ca_diff_perc_attributable_tu_metrics = pd.DataFrame({
        '% Context Attributable': PERCS,
        'Average Class Accuracy': balanced_accuracy,
        'Average Class Accuracy Post': balanced_accuracy_post_diff,
        'Accuracy': accuracy,
        'Accuracy Post': accuracy_post_diff,
        'Precision': precision,
        'Precision Post': precision_post_diff,
        'Recall': recall,
        'Recall Post': recall_post_diff
    })

    name = f'{detector.value}_diff_ca_metrics_attributable_tu.png'
    all_dfs[detector][name] = df_ca_diff_perc_attributable_tu_metrics
    fig, ax1 = plt.subplots(figsize=(10, 8))
    plt.ylim(0, 1)
    df_ca_diff_perc_attributable_tu_metrics.plot.bar(x='% Context Attributable',
                                                     y=['Accuracy', 'Average Class Accuracy', 'Precision', 'Recall'],
                                                     yerr=df_ca_diff_perc_attributable_tu_metrics[
                                                         ['Accuracy Post',
                                                          'Average Class Accuracy Post',
                                                          'Precision Post',
                                                          'Recall Post']].T.values,
                                                     ylim=(0, 1),
                                                     ax=ax1)

    plt.savefig(get_resource_figurepath(name), bbox_inches='tight')
    plt.close('all')

    fig, ax1 = plt.subplots(figsize=(10, 8))
    plt.ylim(0, 1)
    df_ca_diff_perc_attributable_tu_metrics.plot.bar(x='% Context Attributable',
                                                     y=['Accuracy', 'Average Class Accuracy'],
                                                     yerr=df_ca_diff_perc_attributable_tu_metrics[
                                                         ['Accuracy Post',
                                                          'Average Class Accuracy Post']].T.values,
                                                     ylim=(0, 1),
                                                     ax=ax1)

    plt.savefig(get_resource_figurepath(f'{detector.value}_ca_metrics_attributable_tu_accuracies.png'),
                bbox_inches='tight')
    plt.close('all')

    # Optimized by balanced acc
    # Capacity situation
    balanced_accuracy = [ca_no_context_attr_metrics[detector][sit1][B_ACC_LBL][perc] for perc in PERCS]
    balanced_accuracy_post = [ca_with_context_bal_attr_metrics[detector][sit1][B_ACC_LBL][perc] for perc in PERCS]
    precision = [ca_no_context_attr_metrics[detector][sit1][PREC_LBL][perc] for perc in PERCS]
    precision_post = [ca_with_context_bal_attr_metrics[detector][sit1][PREC_LBL][perc] for perc in PERCS]
    accuracy = [ca_no_context_attr_metrics[detector][sit1][ACC_LBL][perc] for perc in PERCS]
    accuracy_post = [ca_with_context_bal_attr_metrics[detector][sit1][ACC_LBL][perc] for perc in PERCS]
    recall = [ca_no_context_attr_metrics[detector][sit1][RECALL_LBL][perc] for perc in PERCS]
    recall_post = [ca_with_context_bal_attr_metrics[detector][sit1][RECALL_LBL][perc] for perc in PERCS]

    balanced_accuracy_post_diff = [balanced_accuracy_post[i] - balanced_accuracy[i]
                                   for i in range(len(balanced_accuracy))]
    accuracy_post_diff = [accuracy_post[i] - accuracy[i]
                          for i in range(len(accuracy))]
    precision_post_diff = [precision_post[i] - precision[i]
                           for i in range(len(precision))]
    recall_post_diff = [recall_post[i] - recall[i]
                        for i in range(len(recall))]

    df_ca_diff_perc_attributable_capacity_bal_metrics = pd.DataFrame({
        '% Context Attributable': PERCS,
        'Average Class Accuracy': balanced_accuracy,
        'Average Class Accuracy Post': balanced_accuracy_post_diff,
        'Accuracy': accuracy,
        'Accuracy Post': accuracy_post_diff,
        'Precision': precision,
        'Precision Post': precision_post_diff,
        'Recall': recall,
        'Recall Post': recall_post_diff
    })

    name = f'{detector.value}_diff_ca_metrics_attributable_capacity_bal.png'
    all_dfs[detector][name] = df_ca_diff_perc_attributable_capacity_bal_metrics
    fig, ax1 = plt.subplots(figsize=(10, 8))
    plt.ylim(0, 1)
    df_ca_diff_perc_attributable_capacity_bal_metrics.plot.bar(x='% Context Attributable',
                                                               y=['Accuracy', 'Average Class Accuracy', 'Precision',
                                                                  'Recall'],
                                                               yerr=df_ca_diff_perc_attributable_capacity_bal_metrics[
                                                                   ['Accuracy Post',
                                                                    'Average Class Accuracy Post',
                                                                    'Precision Post',
                                                                    'Recall Post']].T.values,
                                                               ylim=(0, 1),
                                                               ax=ax1)

    plt.savefig(get_resource_figurepath(name), bbox_inches='tight')
    plt.close('all')

    fig, ax1 = plt.subplots(figsize=(10, 8))
    plt.ylim(0, 1)
    df_ca_diff_perc_attributable_capacity_bal_metrics.plot.bar(x='% Context Attributable',
                                                               y=['Accuracy', 'Average Class Accuracy'],
                                                               yerr=df_ca_diff_perc_attributable_capacity_bal_metrics[
                                                                   ['Accuracy Post',
                                                                    'Average Class Accuracy Post']].T.values,
                                                               ylim=(0, 1),
                                                               ax=ax1)

    plt.savefig(get_resource_figurepath(f'{detector.value}_diff_ca_metrics_attributable_capacity_accuracies_bal.png'),
                bbox_inches='tight')
    plt.close('all')

    # util.plot_metrics('% Context Attributable', 'Value', 'Variable', df_ca_perc_attributable_metrics,
    #                  'ca_metrics_attributable')

    # Time Unit Performance situation
    balanced_accuracy = [ca_no_context_attr_metrics[detector][sit2][B_ACC_LBL][perc] for perc in PERCS]
    balanced_accuracy_post = [ca_with_context_bal_attr_metrics[detector][sit2][B_ACC_LBL][perc] for perc in PERCS]
    precision = [ca_no_context_attr_metrics[detector][sit2][PREC_LBL][perc] for perc in PERCS]
    precision_post = [ca_with_context_bal_attr_metrics[detector][sit2][PREC_LBL][perc] for perc in PERCS]
    accuracy = [ca_no_context_attr_metrics[detector][sit2][ACC_LBL][perc] for perc in PERCS]
    accuracy_post = [ca_with_context_bal_attr_metrics[detector][sit2][ACC_LBL][perc] for perc in PERCS]
    recall = [ca_no_context_attr_metrics[detector][sit2][RECALL_LBL][perc] for perc in PERCS]
    recall_post = [ca_with_context_bal_attr_metrics[detector][sit2][RECALL_LBL][perc] for perc in PERCS]

    balanced_accuracy_post_diff = [balanced_accuracy_post[i] - balanced_accuracy[i]
                                   for i in range(len(balanced_accuracy))]
    accuracy_post_diff = [accuracy_post[i] - accuracy[i]
                          for i in range(len(accuracy))]
    precision_post_diff = [precision_post[i] - precision[i]
                           for i in range(len(precision))]
    recall_post_diff = [recall_post[i] - recall[i]
                        for i in range(len(recall))]

    df_ca_diff_perc_attributable_tu_bal_metrics = pd.DataFrame({
        '% Context Attributable': PERCS,
        'Average Class Accuracy': balanced_accuracy,
        'Average Class Accuracy Post': balanced_accuracy_post_diff,
        'Accuracy': accuracy,
        'Accuracy Post': accuracy_post_diff,
        'Precision': precision,
        'Precision Post': precision_post_diff,
        'Recall': recall,
        'Recall Post': recall_post_diff
    })

    name = f'{detector.value}_diff_ca_metrics_attributable_tu_bal.png'
    all_dfs[detector][name] = df_ca_diff_perc_attributable_tu_bal_metrics
    fig, ax1 = plt.subplots(figsize=(10, 8))
    plt.ylim(0, 1)
    df_ca_diff_perc_attributable_tu_bal_metrics.plot.bar(x='% Context Attributable',
                                                         y=['Accuracy', 'Average Class Accuracy', 'Precision',
                                                            'Recall'],
                                                         yerr=df_ca_diff_perc_attributable_tu_bal_metrics[
                                                             ['Accuracy Post',
                                                              'Average Class Accuracy Post',
                                                              'Precision Post',
                                                              'Recall Post']].T.values,
                                                         ylim=(0, 1),
                                                         ax=ax1)

    plt.savefig(get_resource_figurepath(name), bbox_inches='tight')
    plt.close('all')

    fig, ax1 = plt.subplots(figsize=(10, 8))
    plt.ylim(0, 1)
    df_ca_diff_perc_attributable_tu_bal_metrics.plot.bar(x='% Context Attributable',
                                                         y=['Accuracy', 'Average Class Accuracy'],
                                                         yerr=df_ca_diff_perc_attributable_tu_bal_metrics[
                                                             ['Accuracy Post',
                                                              'Average Class Accuracy Post']].T.values,
                                                         ylim=(0, 1),
                                                         ax=ax1)

    plt.savefig(get_resource_figurepath(f'{detector.value}_ca_metrics_attributable_tu_accuracies_bal.png'),
                bbox_inches='tight')
    plt.close('all')

    # Diff plots perc deviating
    # Optimized by acc
    balanced_accuracy = [ca_no_context_dev_metrics[detector][B_ACC_LBL][perc] for perc in DEVS]
    balanced_accuracy_post = [ca_with_context_dev_metrics[detector][B_ACC_LBL][perc] for perc in DEVS]
    accuracy = [ca_no_context_dev_metrics[detector][ACC_LBL][perc] for perc in DEVS]
    accuracy_post = [ca_with_context_dev_metrics[detector][ACC_LBL][perc] for perc in DEVS]
    precision = [ca_no_context_dev_metrics[detector][PREC_LBL][perc] for perc in DEVS]
    precision_post = [ca_with_context_dev_metrics[detector][PREC_LBL][perc] for perc in DEVS]
    recall = [ca_no_context_dev_metrics[detector][RECALL_LBL][perc] for perc in DEVS]
    recall_post = [ca_with_context_dev_metrics[detector][RECALL_LBL][perc] for perc in DEVS]

    balanced_accuracy_post_diff = [balanced_accuracy_post[i] - balanced_accuracy[i]
                                   for i in range(len(balanced_accuracy))]
    accuracy_post_diff = [accuracy_post[i] - accuracy[i] for i in range(len(accuracy))]
    precision_post_diff = [precision_post[i] - precision[i] for i in range(len(precision))]
    recall_post_diff = [recall_post[i] - recall[i] for i in range(len(recall))]

    df_ca_diff_perc_deviating_metrics = pd.DataFrame({
        '% Deviating Events': DEVS,
        'Average Class Accuracy': balanced_accuracy,
        'Average Class Accuracy Post': balanced_accuracy_post_diff,
        'Accuracy': accuracy,
        'Accuracy Post': accuracy_post_diff,
        'Precision': precision,
        'Precision Post': precision_post_diff,
        'Recall': recall,
        'Recall Post': recall_post_diff
    })

    name = f'{detector.value}_diff_ca_metrics_deviating.png'
    all_dfs[detector][name] = df_ca_diff_perc_deviating_metrics
    fig, ax1 = plt.subplots(figsize=(10, 8))
    plt.ylim(0, 1)
    df_ca_diff_perc_deviating_metrics.plot.bar(x='% Deviating Events',
                                               y=['Accuracy', 'Average Class Accuracy', 'Precision', 'Recall'],
                                               yerr=df_ca_diff_perc_deviating_metrics[
                                                   ['Accuracy Post',
                                                    'Average Class Accuracy Post',
                                                    'Precision Post',
                                                    'Recall Post']].T.values,
                                               ylim=(0, 1),
                                               ax=ax1)

    plt.savefig(get_resource_figurepath(name), bbox_inches='tight')
    plt.close('all')

    fig, ax1 = plt.subplots(figsize=(10, 8))
    plt.ylim(0, 1)
    df_ca_diff_perc_deviating_metrics.plot.bar(x='% Deviating Events',
                                               y=['Accuracy', 'Average Class Accuracy'],
                                               yerr=df_ca_diff_perc_deviating_metrics[
                                                   ['Accuracy Post',
                                                    'Average Class Accuracy Post']].T.values,
                                               ylim=(0, 1),
                                               ax=ax1)

    plt.savefig(get_resource_figurepath(f'{detector.value}_diff_ca_metrics_deviating_accuracies.png'),
                bbox_inches='tight')
    plt.close('all')

    util.plot_metrics('% Deviating Events', 'Value', 'Variable',
                      df_ca_diff_perc_deviating_metrics, f'{detector.value}_diff_ca_metrics_deviating_alt')

    # Optimized by acc
    balanced_accuracy = [ca_no_context_dev_metrics[detector][B_ACC_LBL][perc] for perc in DEVS]
    balanced_accuracy_post = [ca_with_context_bal_dev_metrics[detector][B_ACC_LBL][perc] for perc in DEVS]
    accuracy = [ca_no_context_dev_metrics[detector][ACC_LBL][perc] for perc in DEVS]
    accuracy_post = [ca_with_context_bal_dev_metrics[detector][ACC_LBL][perc] for perc in DEVS]
    precision = [ca_no_context_dev_metrics[detector][PREC_LBL][perc] for perc in DEVS]
    precision_post = [ca_with_context_bal_dev_metrics[detector][PREC_LBL][perc] for perc in DEVS]
    recall = [ca_no_context_dev_metrics[detector][RECALL_LBL][perc] for perc in DEVS]
    recall_post = [ca_with_context_bal_dev_metrics[detector][RECALL_LBL][perc] for perc in DEVS]

    balanced_accuracy_post_diff = [balanced_accuracy_post[i] - balanced_accuracy[i]
                                   for i in range(len(balanced_accuracy))]
    accuracy_post_diff = [accuracy_post[i] - accuracy[i] for i in range(len(accuracy))]
    precision_post_diff = [precision_post[i] - precision[i] for i in range(len(precision))]
    recall_post_diff = [recall_post[i] - recall[i] for i in range(len(recall))]

    df_ca_diff_perc_deviating_bal_metrics = pd.DataFrame({
        '% Deviating Events': DEVS,
        'Average Class Accuracy': balanced_accuracy,
        'Average Class Accuracy Post': balanced_accuracy_post_diff,
        'Accuracy': accuracy,
        'Accuracy Post': accuracy_post_diff,
        'Precision': precision,
        'Precision Post': precision_post_diff,
        'Recall': recall,
        'Recall Post': recall_post_diff
    })

    name = f'{detector.value}_diff_ca_metrics_deviating_bal.png'
    all_dfs[detector][name] = df_ca_diff_perc_deviating_bal_metrics
    fig, ax1 = plt.subplots(figsize=(10, 8))
    plt.ylim(0, 1)
    df_ca_diff_perc_deviating_bal_metrics.plot.bar(x='% Deviating Events',
                                                   y=['Accuracy', 'Average Class Accuracy', 'Precision', 'Recall'],
                                                   yerr=df_ca_diff_perc_deviating_bal_metrics[
                                                       ['Accuracy Post',
                                                        'Average Class Accuracy Post',
                                                        'Precision Post',
                                                        'Recall Post']].T.values,
                                                   ylim=(0, 1),
                                                   ax=ax1)

    plt.savefig(get_resource_figurepath(name), bbox_inches='tight')
    plt.close('all')

    fig, ax1 = plt.subplots(figsize=(10, 8))
    plt.ylim(0, 1)
    df_ca_diff_perc_deviating_bal_metrics.plot.bar(x='% Deviating Events',
                                                   y=['Accuracy', 'Average Class Accuracy'],
                                                   yerr=df_ca_diff_perc_deviating_bal_metrics[
                                                       ['Accuracy Post',
                                                        'Average Class Accuracy Post']].T.values,
                                                   ylim=(0, 1),
                                                   ax=ax1)

    plt.savefig(get_resource_figurepath(f'{detector.value}_diff_ca_metrics_deviating_accuracies_bal.png'),
                bbox_inches='tight')
    plt.close('all')

    util.plot_metrics('% Deviating Events', 'Value', 'Variable',
                      df_ca_diff_perc_deviating_bal_metrics, f'{detector.value}_diff_ca_metrics_deviating_bal_alt')

pickle_data(cms_all, 'cms_all')
pickle_data(all_dfs, 'metrics_all_dfs')
