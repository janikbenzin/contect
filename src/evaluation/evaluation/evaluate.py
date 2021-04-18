import os
from random import Random
from time import sleep

from backend.tasks.tasks import compute_evaluation_experiment
from contect.available.available import AvailableSituations, AvailableSelections, AvailableGranularity, \
    AvailableCorrelations
from contect.context.objects.situations.helpers.additionaldata.additionaldata import AdditionalDataContainer, \
    AdditionalDataSituation, AdditionalDataHelper
from contect.context.objects.timeunits.timeunit import get_start_end_time, round_start_to_granularity, get_timespan, \
    get_timedelta
from contect.parsedata.correlate import correlate_shared_objs
from contect.resource.resource import pickle_data, get_resource_filepath
from evaluation.objects.evaluation.evaluation import SyntheticEvaluation, parse_evaluation, default_csv_parameters
from evaluation.objects.param.config import EvaluationExperiment
from evaluation.scenarios.resourcecapacities import generate_resource_capacities

data_names = ['log1.csv', 'log2.csv', 'log3.csv']

syn_eval = SyntheticEvaluation(data_names=data_names,
                               sep=';')


excess_data = parse_evaluation('excess_demand.csv', ';', default_csv_parameters())
excess_log = correlate_shared_objs(excess_data,
                                   {'orders'},
                                   AvailableCorrelations.INITIAL_PAIR_CORRELATION)

seed = 20201110
random_gen = Random(seed)

# The evaluation experiment designs are all defined according to days -> need the daily timespan also
day_timespans = {}
granularity_d = AvailableGranularity.DAY
for data_name in data_names:
    start_time_d, end_time_d = get_start_end_time(syn_eval.datasets[data_name].raw.events)
    start_time_d = round_start_to_granularity(start_time_d, granularity_d)
    t_d, u_d, timespan_d = get_timespan(get_timedelta(granularity_d, 1), start_time_d, end_time_d, granularity_d)
    year_adjustment_d = t_d / 365  # The capacity day ranges are only for a year, so need to be adjusted
    day_timespans[data_name] = (timespan_d, year_adjustment_d)

data_to_resource = {}
for data_name in data_names:
    data_to_resource[data_name] = generate_resource_capacities(data=syn_eval.datasets[data_name],
                                                               timespan_d=day_timespans[data_name][0],
                                                               year_adjustment=day_timespans[data_name][1],
                                                               random=random_gen)
    seed += 1
    random_gen = Random(seed)

syn_eval.additional_data = {
    data_name:
        AdditionalDataContainer(
            add_data_of_situations={AvailableSituations.CAPACITY: AdditionalDataSituation(
                add_data_helpers={AvailableSelections.RESOURCE: AdditionalDataHelper(
                    double_granular_additional_data=data_to_resource[data_name][1]
                )}
            )}
        )
    for data_name in syn_eval.data_names
}


def set_additional_data(param: EvaluationExperiment,
                        additional_data: AdditionalDataContainer,
                        granularity: AvailableGranularity) -> None:
    param.additional_data = {granularity: additional_data}


[set_additional_data(param, syn_eval.additional_data[param.data_name], syn_eval.granularities[0])
 for experiment, param in syn_eval.params.items()]  #

tasks_id_seed_only = {}
failed = []
success = []
print(f'Starting {len(syn_eval.params)} experiments\n')
experiments = list(syn_eval.params.keys())
# If the evaluation stops for some reason, then continue only for the part that has not been computed
successful_experiments = [f for f in os.listdir(get_resource_filepath('')) if f.endswith('.pickle') and 'log' in f and 'post' not in f]
results = {}
tasks = {}
n_concurrent_tasks = 0
MAX_CONCURRENT = int(os.getenv('EVALUATION_MAX_CONCURRENT'))
# Compute evaluation by running max concurrent experiment in tasks in celery
for experiment in experiments:
    if any([f'{experiment}.pickle' in f.split('/')[0] for f in successful_experiments]):
        print(f'Skipping existing experiment {experiment}\n')
        del syn_eval.params[experiment]
        continue
    else:
        eval_param = syn_eval.params[experiment]
        parse_param = syn_eval.parse_param
        weeks = syn_eval.weeks[eval_param.data_name]
        weekly_demand = syn_eval.weekly_demands[eval_param.data_name]
        print(f'Starting experiment {experiment}\n')
        tasks[experiment] = compute_evaluation_experiment.delay(random_r=random_gen,
                                                                eval_param_r=eval_param,
                                                                weeks_r=weeks,
                                                                weekly_demand_r=weekly_demand,
                                                                day_timespans_r=day_timespans,
                                                                excess_log_r=excess_log,
                                                                parse_param_r=parse_param,
                                                                data_to_resource_r=data_to_resource)
        n_concurrent_tasks += 1
        tasks_id_seed_only[experiment] = (tasks[experiment].id, seed)
        print(f'{tasks_id_seed_only}\n')
        seed += 1
        random_gen = Random(seed)
        del syn_eval.params[experiment]
        while n_concurrent_tasks >= MAX_CONCURRENT:
            sleep(5)
            print(f'Looking for finished experiments\n')
            for exp, task in tasks.items():
                state = task.state
                if state == 'SUCCESS':
                    if exp not in results:
                        print(f'Successful experiment {exp}\n')
                        results[exp] = True
                        result = task.get()
                        pickle_data(result, f'{exp}')
                        success.append(exp)
                        print(f'Successful experiments: {success}')
                        task.forget()
                        n_concurrent_tasks -= 1
                        del result
                if state == 'FAILURE':
                    if exp not in results:
                        print(f'Failed experiment {exp}\n')
                        results[exp] = None
                        failed.append(exp)
                        print(f'Failed experiments: {failed}')
                        task.forget()
                        n_concurrent_tasks -= 1
                        pickle_data(None, f'{exp}')


del syn_eval

while len(tasks) != len(results):
    for exp, task in tasks.items():
        state = task.state
        if state == 'SUCCESS':
            if exp not in results:
                print(f'Successful experiment {exp}\n')
                results[exp] = True
                result = task.get()
                pickle_data(result, f'{exp}')
                task.forget()
                del result
        if state == 'FAILURE':
            if exp not in results:
                print(f'Failed experiment {exp}\n')
                results[exp] = None
                task.forget()
                pickle_data(None, f'{exp}')
    sleep(2)

print(f'{len(failed)} have failed:\n'
      f'{failed}')
