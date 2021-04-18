import itertools
from typing import Dict
from functools import partial

from contect.available.available import AvailableCorrelations
from contect.parsedata.objects.ocdata import ObjectCentricData, Event
from contect.parsedata.objects.oclog import Trace, ObjectCentricLog


def correlate_obj_path(data: ObjectCentricData, selection: set) -> Dict[str, ObjectCentricLog]:
    events = data.raw.events
    objects = data.raw.objects
    logs = {}
    ordered_selections = itertools.permutations(selection)
    key_list = list(events.keys())

    for ordered_selection in ordered_selections:
        tid = 0
        pos = 0
        start_event = events[key_list[pos]]
        corr = start_event.corr
        all_correlated = False
        log = ObjectCentricLog({}, {}, objects, data.meta, data.vmap_param)
        pos_selection = 0  # Current position on ordered selection
        event_to_trace = {}

        while not all_correlated:

            while True:
                if len(events) - 1 == pos:  # finished
                    all_correlated = True
                    break
                if start_event.corr is not corr:  # already correlated events are not correlated again
                    pos += 1
                    start_event = events[key_list[pos]]
                elif len(get_obj_ids(start_event, objects,
                                     {ordered_selection[
                                          pos_selection]})) == 0:  # events with no matching object type are skipped
                    start_event.corr = not corr  # Mark as "correlated"
                    pos += 1
                    start_event = events[key_list[pos]]
                else:
                    break
            if all_correlated:
                break
            obj_ids = get_obj_ids(start_event, objects, selection)
            trace = Trace(events=[start_event],
                          id=tid)
            event_to_trace[start_event.id] = trace.id
            tid += 1
            start_event.corr = not corr
            if len(events) - 1 == pos:  # If the first event of a trace is the last in events, then we are done
                log.traces[trace.id] = trace
                all_correlated = True
                break
            pos += 1
            pos_trace = pos
            # We search the rest of events for more events correlated to the first event of the new trace
            next_event = events[key_list[pos_trace]]
            while True:
                if next_event.corr is not corr:
                    pass
                # Correlated events share objects ids of the correct type
                elif not set(next_event.omap).isdisjoint(obj_ids):
                    trace.events.append(next_event)
                    event_to_trace[next_event.id] = trace.id
                    next_event.corr = not corr
                    pos_selection += 1

                    if pos_selection == len(ordered_selection):
                        break
                    # the current event's object id's for the correct type need to be shared by the next event
                    obj_ids = get_obj_ids(next_event, objects, {ordered_selection[pos_selection]})
                if len(events) - 1 == pos_trace:  # All events were searched for that trac
                    break
                pos_trace += 1
                next_event = events[key_list[pos_trace]]
            # Add trace to log and remove already correlated events
            log.traces[trace.id] = trace
            log.event_to_traces = event_to_trace
            pos_selection = 0
        logs[str(ordered_selection)] = log

    return logs


def compare_partition(event_corr, corr):
    return event_corr[1] is not corr


def compare_all(start, event_corr, corr):
    if start:
        # Batch events that are already correlated, cannot be start events
        return event_corr[1] is not corr
    else:
        return event_corr[0] is not corr


def correlate_shared_objs(data: ObjectCentricData,
                          selection: set,
                          version=AvailableCorrelations.MAXIMUM_CORRELATION,
                          partition=True) -> ObjectCentricLog:
    events = data.raw.events
    objects = data.raw.objects
    log = ObjectCentricLog({}, {}, objects, data.meta, data.vmap_param)
    if partition:
        start_condition = compare_partition
        condition = compare_partition
    else:
        start_condition = partial(compare_all, True)
        condition = partial(compare_all, False)

    tid = 0
    pos = 0
    key_list = list(events.keys())
    start_event = events[key_list[pos]]
    corr = start_event.corr
    for eid, e in events.items():
        e.corr = (e.corr, e.corr)
    all_correlated = False
    event_to_trace = {}
    # Correlate while uncorrelated events exist
    while not all_correlated:
        # The first event with correct object is always the start event
        # Assume events to be sorted according to total order
        while True:
            if len(events) - 1 == pos:  # finished
                all_correlated = True
                break
            if start_condition(start_event.corr, corr):  # already correlated events are not correlated again
                pos += 1
                start_event = events[key_list[pos]]
            elif len(get_obj_ids(start_event, objects,
                                 selection)) == 0:  # events with no matching object type are skipped
                start_event.corr = (not corr, not corr)  # Mark as "correlated"
                pos += 1
                start_event = events[key_list[pos]]
            else:
                break
        if all_correlated:
            break
        obj_ids = get_obj_ids(start_event, objects, selection)
        trace = Trace(events=[start_event],
                      id=tid)
        event_to_trace[start_event.id] = trace.id
        tid += 1
        start_event.corr = (not corr, not corr)
        if len(events) - 1 == pos:  # If the first event of a trace is the last in events, then we are done
            log.traces[trace.id] = trace
            all_correlated = True
            break
        #pos += 1
        pos_trace = pos  # We search the rest of events for more events correlated to the first event of the new trace
        next_event = events[key_list[pos_trace]]
        while True:
            if condition(next_event.corr, corr):  # Already correlated events cannot be correlated again
                pass
            elif not set(next_event.omap).isdisjoint(
                    obj_ids):  # Correlated events share objects ids of the correct type
                trace.events.append(next_event)
                event_to_trace[next_event.id] = trace.id
                if partition:
                    next_event.corr = (not corr, not corr)
                else:
                    batch = False
                    for sel in selection:
                        if len(get_obj_ids(next_event, objects, {sel})) > 1:
                            batch = True
                    if batch:
                        next_event.corr = (corr, not corr)  # Batch events are correlated multiple times
                    else:
                        next_event.corr = (not corr, not corr)
                if version == AvailableCorrelations.MAXIMUM_CORRELATION:
                    obj_ids.update({obj for obj in next_event.omap if
                                    data.raw.objects[obj].type in selection})
            if len(events) - 1 == pos_trace:
                break
            pos_trace += 1
            next_event = events[key_list[pos_trace]]

        # Add trace to log and remove already correlated events
        log.traces[trace.id] = trace
    log.event_to_traces = event_to_trace
    return log


def get_obj_ids(event: Event, objects: dict, selection: set) -> set:
    return {obj for obj in event.omap if
            objects[obj].type in selection
            }
