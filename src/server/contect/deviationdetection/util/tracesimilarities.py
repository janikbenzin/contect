from contect.parsedata.objects.oclog import Trace


# https://stackoverflow.com/questions/46975929/how-can-i-calculate-the-jaccard-similarity-of-two-lists-containing-strings-in-py
def jaccard_similarity(list1, list2):
    intersection = len(list(set(list1).intersection(list2)))
    union = (len(list1) + len(list2)) - intersection
    return float(intersection) / union


def score_jaccard(trace1: Trace, trace2: Trace) -> float:
    return jaccard_similarity([e.id for e in trace1.events], [e.id for e in trace2.events])


