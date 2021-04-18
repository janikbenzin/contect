from math import ceil

from contect.available.available import AvailableGranularity


def sample_n_any(days, year_adjustment, random):
    return random.sample(  # Sample the number of decreased capacity days per department
        [ceil(day * year_adjustment) for day in
         list(days)],
        1)[0]


def sample_days(n, timespan_d, random):
    return random.sample(list(timespan_d.units[AvailableGranularity.DAY]),
                         n)


def sample_any(rng, n, random):
    return random.sample(list(rng), n)