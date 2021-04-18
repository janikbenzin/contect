import os
from time import sleep

from backend.tasks.tasks import compute_post_evaluation_experiment
from contect.available.available import AvailableDetectors
from contect.resource.resource import pickle_data
from evaluation.util import get_pickled_experiment, get_experiment_names

experiments, post_experiments = get_experiment_names()

# parameters = list(itertools.product([p for p in map(lambda i: i / 10, range(11))], repeat=2))
# Typically, the post-processing is sensitive for parameters close to zero and less sensitive the farther away they are
parameters = [p for p in map(lambda i: i / 1000, range(0, 100))] + \
             [p for p in map(lambda i: i / 1000, range(100, 500, 10))] + \
             [p for p in map(lambda i: i / 100, range(50, 105, 5))]

detectors = [detector for detector in AvailableDetectors]

for detector in detectors:
    tasks_id_only = {}
    failed = []
    success = []
    print(f'Starting {len(experiments)} experiments of detector {detector.value}\n')
    results = {}
    tasks = {}
    n_concurrent_tasks = 0
    MAX_CONCURRENT = int(os.getenv('EVALUATION_MAX_CONCURRENT'))
    # Compute evaluation by running max concurrent experiment in tasks in celery
    for experiment in [exp for exp in experiments if detector.value in exp]:
        if any([experiment.split('/')[0] in f for f in post_experiments]):
            print(f'Skipping existing experiment {experiment} for detector {detector.value}\n')
            continue
        else:
            print(f'Starting post-processing experiment {experiment}\n')
            experiment_data = get_pickled_experiment(experiment)
            tasks[experiment] = compute_post_evaluation_experiment.delay(detector_r=detector,
                                                                         experiment_data_r=experiment_data,
                                                                         parameters_r=parameters)
            n_concurrent_tasks += 1
            tasks_id_only[experiment] = tasks[experiment].id
            print(f'{tasks_id_only}\n')
            del experiment_data
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
                            pickle_data(result, f'{exp}.post')
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

    while len(tasks) != len(results):
        for exp, task in tasks.items():
            state = task.state
            if state == 'SUCCESS':
                if exp not in results:
                    print(f'Successful experiment {exp}\n')
                    results[exp] = True
                    result = task.get()
                    pickle_data(result, f'{exp}.post')
                    task.forget()
                    del result
            if state == 'FAILURE':
                if exp not in results:
                    print(f'Failed experiment {exp}\n')
                    results[exp] = None
                    failed.append(exp)
                    print(f'Failed experiments: {failed}')
                    task.forget()
        sleep(2)

    print(f'{len(failed)} have failed for detector {detector.value}:\n'
          f'{failed}')
