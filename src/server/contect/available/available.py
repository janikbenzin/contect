from enum import Enum
from contect.available.constants import HOURS_IN_YEAR, HOURS_IN_MONTH, HOURS_IN_WEEK

class AvailableEntities(Enum):
    TIMEUNIT = 'timeunit'
    DIRECTLYFOLLOWS = 'directlyfollows'
    CAPACITYUTIL = 'capacityutil'


class AvailableSituations(Enum):
    UNIT_PERFORMANCE = 'time unit performance'.title()
    CAPACITY = 'capacity utilization performance'.title()
    SCHEDULE = 'schedule pattern breach'.title()
    WAIT_PERFORMANCE = 'waiting time performance'.title()


class AvailableSituationType(Enum):
    POSITIVE = 'positive'
    NEGATIVE = 'negative'


def get_simple_available_from_name(name, default, available):
    for candidate in available:
        if name == candidate.value:
            return candidate
    return default


class AvailableSelections(Enum):
    GLOBAL = 'global'.title()
    ACTIVITY = 'activity'.title()
    OBJECTTYPE = 'object type'.title()
    RESOURCE = 'resource'.title()
    LOCATION = 'location'.title()


class AvailableCorrelations(Enum):
    MAXIMUM_CORRELATION = 'shared object id (maximum)'.title()
    INITIAL_PAIR_CORRELATION = 'shared object id (partition, minimum)'.title()
    OBJ_PATH_CORRELATION = 'object path correlation'.title()
    MAXIMUM_CORRELATION_NON = 'shared object id (maximum)'.title()
    INITIAL_PAIR_CORRELATION_NON = 'shared object id (minimum)'.title()


class AvailableGranularity(Enum):
    SEC = 'sec'
    MIN = 'min'
    HR = 'hour'
    DAY = 'day'
    WK = 'wk'
    MON = 'mon'
    YR = 'yr'


class AvailableNormRanges(Enum):
    GLOBAL = 'insignificant'
    BINS = {'moderate': HOURS_IN_YEAR,
            'significant': HOURS_IN_MONTH,
            'very significant': HOURS_IN_WEEK}


def extract_options(ranges):
    options = [ranges.GLOBAL.value]
    return options + [option for option in ranges.BINS.value]


def get_range_from_name(name):
    if name == AvailableNormRanges.GLOBAL.value:
        return {AvailableNormRanges.GLOBAL: 1}
    elif name in AvailableNormRanges.BINS.value:
        return {AvailableNormRanges.BINS: AvailableNormRanges.BINS.value[name]}


class AvailablePerfToDevRelationships(Enum):
    ANTI = 'anti'
    PROP = 'prop'
    TWOSIDED = 'twosided'
    ONESIDED = 'onesided'


class AvailableAggregators(Enum):
    MIN = 1
    MAX = 2
    AVG = 3
    MED = 4


class AvailableDeviationTypes(Enum):
    ADD = 'add'
    REM = 'rem'
    REPL = 'repl'
    REPLR = 'replr'


class AvailableClassifications(Enum):
    N = 'Normal'
    D = 'Deviating'
    CAN = 'Context-aware normal'
    CAD = 'Context-aware deviating'


class AvailableClassificationValues(Enum):
    TRUE = 'yes'
    FALSE = 'no'


class AvailableEvaluationTypes(Enum):
    SYN = 1
    QUASI = 2


class AvailableDataFormats(Enum):
    CSV = 'csv'
    JSON = 'json'
    OCDATA = 'ocdata'
    OCLOG = 'oclog'
    CONTEXT = 'context'
    DETECT = 'detect'


class AvailableProfiles(Enum):
    DF = 'directlyfollows'
    DR = 'dependencyrelation'


class AvailableTasks(Enum):
    PARSE = 'parse'
    UPLOAD = 'upload'
    CORR = 'correlate'
    CONTEXT = 'context'
    DETECT = 'detect'
    GUIDE = 'guide'
    DETECT_PROF = 'detect_prof'
    DETECT_ADAR = 'detect_adar'
    DETECT_ALIGN = 'detect_align'
    DETECT_AUTOENC = 'detect_autoenc'
    POST = 'post'
    CONTEXT_RESULT = 'context_result'
    POST_DATA = 'post_data'


class AvailableColorPalettes(Enum):
    BLIND = 'colorblind'


class AvailableADARTypes(Enum):
    CONTROL = 'control'
    RESOURCE = 'resource'


class AvailableADAREventMiners(Enum):
    CONTROL = AvailableADARTypes.CONTROL, 0
    RESOURCE_SOD = AvailableADARTypes.RESOURCE, 1
    RESOURCE_BOD = AvailableADARTypes.RESOURCE, 2


class AvailableADARStates(Enum):
    NEW = 0
    OLD = 1


class AvailableADARResults(Enum):
    MATCHED = 0
    VIOLATED = 1
    NEUTRAL = 2  # Not matching the IF part of a rule


class AvailableDetectors(Enum):
    PROF = 'profiles'.title()
    ALIGN = 'inductive'.title()
    ADAR = 'anomaly detection association rules'.title()
    AUTOENC = 'autoencoder'.title()


def get_available_granularity_from_name(granularity):
    if granularity == AvailableGranularity.HR.value.title():
        granularity = AvailableGranularity.HR
    else:
        granularity = AvailableGranularity.DAY
    return granularity