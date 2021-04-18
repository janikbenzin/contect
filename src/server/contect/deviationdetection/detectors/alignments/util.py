from typing import Counter
from pm4py.objects.dfg.filtering import dfg_filtering as dfg_filter
from pm4py.algo.discovery.dfg import algorithm as dfg_discovery
from pm4py.algo.discovery.inductive import algorithm as inductive_miner
from pm4py.objects.log.log import EventLog
from pm4py.evaluation.replay_fitness import evaluator as replay_fitness_evaluator
from pm4py.evaluation.precision import evaluator as precision_evaluator
from pm4py.evaluation.generalization import evaluator as generalization_evaluator
from pm4py.evaluation.simplicity import evaluator as simplicity_evaluator
from pm4py.algo.conformance.alignments import algorithm as alignments


def align(log, net, im, fm):
    return alignments.apply_log(log, net, im, fm)


def discover_process_model(log: EventLog, threshold: float):
    dfg = discover_dfg(log)
    dfg_filtered = filter_dfg(dfg, threshold)

    net, im, fm = inductive_miner.apply_dfg(dfg_filtered)

    return net, im, fm


def evaluate_quality(log: EventLog, net, im, fm) -> float:
    fitness = replay_fitness_evaluator.apply(log, net, im, fm,
                                             variant=replay_fitness_evaluator.Variants.TOKEN_BASED)['log_fitness']
    precision = precision_evaluator.apply(log, net, im, fm, variant=precision_evaluator.Variants.ETCONFORMANCE_TOKEN)
    gen = generalization_evaluator.apply(log, net, im, fm)
    simplicity = simplicity_evaluator.apply(net)
    return fitness + precision + gen + simplicity


def discover_dfg(log: EventLog) -> Counter:
    return dfg_discovery.apply(log)


def filter_dfg(dfg: Counter, threshold: float) -> Counter:
    """Applies DFG filtering

    :dfg: DFG that should be filtered
    :threshold: The filtering threshold
    :returns: DFG filtered DFG

    """

    # Parameters for filtering
    filter_param = {"noiseThreshold": threshold}

    # Filter DFG
    dfg_filtered = dfg_filter.apply(dfg, filter_param)
    return dfg_filtered


