from contect.available.available import AvailableSituations, AvailableEntities, AvailableSituationType, \
    AvailableNormRanges, AvailableGranularity
from contect.available.constants import HOURS_IN_MONTH, HOURS_IN_YEAR
from contect.context.objects.situations.helpers.versions.extract import time_bin_range, time_of_time_bin_range, \
    enlarge_schedule_hours_to_full_weeks, stop_at_end_of_data
from contect.context.objects.timeunits.timeunit import split_log
from contect.parsedata.objects.ocdata import ObjectCentricData
from contect.parsedata.objects.oclog import ObjectCentricLog
from contect.context.objects.situations.helpers.factory import get_helper
from contect.context.objects.situations.helpers.additionaldata.additionaldata import AdditionalDataContainer
from contect.context.objects.situations.factory import get_situation
from contect.context.objects.contextentities.factory import get_contextentity
from contect.context.objects.context.versions.context import ContextEntityConfig, Context, SituationConfig, \
    SituationHelperConfig
from contect.context.objects.context.config.param import ContextParameters


def get_context(context_param: ContextParameters,
                data: ObjectCentricData,
                log: ObjectCentricLog,
                additional_data: AdditionalDataContainer = None,
                call_contextentity=get_contextentity,
                call_situation=get_situation,
                call_helper=get_helper) -> Context:
    # Important parameters
    selections = context_param.selections
    meta = data.meta
    objects = data.raw.objects
    selected_situations = context_param.selected_situations

    # Timespan and other time-related information incl. the log split into chunks corresponding to time units of size
    # equal to the granularity
    granularity = context_param.granularity
    container, timespan, events_timeunit = split_log(data, granularity)
    # The container has a meta object and the chunks of the split log
    # Events_timeunit contains a mapping from event ids to the assigned time unit for fast processing later on

    # For each context entity with its selection, the context entity is extracted and built for the respective time unit
    entities = {
        entity: {
            selection:
                {time: call_contextentity(entity=entity,
                                          selection=selection,
                                          chunk=chunk,
                                          time=time,
                                          meta=meta,
                                          vmap_param=data.vmap_param,
                                          objects=objects,
                                          log=log)
                 for time, chunk in container.events_split[granularity].items()}
            for selection in selections[entity]
        }
        for entity in selections
    }

    # The extracted entities are stored in the Config of Context with some additional information
    ce_cfg = ContextEntityConfig(
        selected_entities=list(selections.keys()),
        selections=selections,
        entities=entities
    )

    # The norm range is determined by asking the user whether the environment is turbulent or not and set for all
    # situations
    # Having granular bins will result in keys for helpers, that do not match the time unit keys,
    # so a mapping from those time keys to time bin keys is computed here
    # list(context_param.norm_range.keys())[0] is AvailableNormRanges.BINS and
    norm_range = list(context_param.norm_range.keys())[0]
    if norm_range is not AvailableNormRanges.GLOBAL:
        step_width = context_param.norm_range[norm_range]
        if granularity is AvailableGranularity.DAY:
            step_width = int(step_width / 24)
        # For granular helpers, the key is the time_bin and for the identificator, we need to transform the time to
        # that associated time_bin
        time_to_time_bin = {situation:
                                {time: time_bin
                                 for time_bin in time_bin_range(number_of_time_units_in_entities(entities,
                                                                                                 entity),
                                                                step_width)
                                 for time in time_of_time_bin_range(number_of_time_units_in_entities(entities,
                                                                                                     entity),
                                                                    step_width,
                                                                    time_bin)}
                            for entity in selections if entity in selected_situations
                            for situation in selected_situations[entity]
                            if situation is not AvailableSituations.SCHEDULE}
        schedule_entity = AvailableEntities.TIMEUNIT
        # Schedule has a special structure for time_to_time_bin, as it is always hours of a week
        if schedule_entity in selected_situations and AvailableSituations.SCHEDULE in selected_situations[
            schedule_entity]:
            # If the norm range is a week, this will be a month for schedules
            if step_width < HOURS_IN_MONTH:
                schedule_step_width = HOURS_IN_MONTH
            else:
                schedule_step_width = step_width
            # We extend the timespan for schedules to all hours of the week in the beginning and at the end
            # because this eases the computation of aggregates over the last weeks
            # The corresponding TimeContextEntities will all be having a value of 0, see the extractor
            end_hour_shift, start_hour_shift = enlarge_schedule_hours_to_full_weeks(timespan)
            data_len = number_of_time_units_in_entities(entities, schedule_entity)
            time_to_time_bin[AvailableSituations.SCHEDULE] = {
                time: time_bin
                # Time bins need to take the enlarged schedule timespan into account
                for time_bin in range(int(- start_hour_shift), int(data_len + end_hour_shift), schedule_step_width)
                for time in range(time_bin,
                                  stop_at_end_of_data(time_bin,
                                                      schedule_step_width,
                                                      int(data_len + start_hour_shift + end_hour_shift)))}
    else:
        # Dummy values to simplify the passing of variables to situations
        # Additional data needs to always have the correct structure for the corresponding helper
        # as currently it is just read into a corresponding helper without any further transformations, see extractor
        # Those transformations are not necessary anyway, as we should not aggregate this additional ground truth
        time_to_time_bin = {situation: 1
                            for entity in selections if entity in selected_situations
                            for situation in selected_situations[entity]}
        schedule_entity = AvailableEntities.TIMEUNIT
        if schedule_entity in selected_situations and AvailableSituations.SCHEDULE in selected_situations[
            schedule_entity]:
            # If the norm range is a week, this will be a month for schedules
            schedule_step_width = HOURS_IN_YEAR
            # We extend the timespan for schedules to all hours of the week in the beginning and at the end
            # because this eases the computation of aggregates over the last weeks
            # The corresponding TimeContextEntities will all be having a value of 0, see the extractor
            end_hour_shift, start_hour_shift = enlarge_schedule_hours_to_full_weeks(timespan)
            data_len = number_of_time_units_in_entities(entities, schedule_entity)
            time_to_time_bin[AvailableSituations.SCHEDULE] = {
                time: time_bin
                # Time bins need to take the enlarged schedule timespan into account
                for time_bin in range(int(- start_hour_shift), int(data_len + end_hour_shift), schedule_step_width)
                for time in range(time_bin,
                                  stop_at_end_of_data(time_bin,
                                                      schedule_step_width,
                                                      int(data_len + start_hour_shift + end_hour_shift)))}
        step_width = 1

    # The helpers contain either aggregates for normalization during situation identification or the additional data
    helpers = {
        entity: {
            situation: call_helper(timespan=timespan,
                                   param=context_param.situation_param[situation].helper,
                                   data=entities[entity],
                                   entity=entity,
                                   situation=situation,
                                   step_width=step_width,
                                   additional_data=additional_data.add_data_of_situations[situation] if
                                   additional_data is not None and situation in additional_data.add_data_of_situations else None
                                   )
            for situation in selected_situations[entity]
        }
        for entity in selections if entity in selected_situations
    }

    # As a last step, the situations are identified by the situation factory and its contained identificators
    # Some additional information and parameters for situations are additionally stored in the Config
    sit_cfg = SituationConfig(
        selected_situations=selected_situations,
        situations={
            entity: {situation: SituationHelperConfig(
                situation=call_situation(
                    entity=entity,
                    situation=situation,
                    selections=selections[entity],
                    entities=entities[entity],
                    helper=helpers[entity][situation],
                    time_to_time_bin=time_to_time_bin[situation],
                    situation_param=context_param.situation_param[situation]
                ),
                helper=helpers[entity][situation]
            )
                for situation in selected_situations[entity]}
            for entity in selections if entity in selected_situations
        },
        typing={typ: [situation for situation in context_param.situation_param
                      if context_param.situation_param[situation].typing is typ]
                for typ in AvailableSituationType},
        weights={situation: context_param.situation_param[situation].weights
                 for situation in context_param.situation_param
                 }
    )

    return Context(timespan=timespan,
                   time_to_time_bin=time_to_time_bin,
                   events_timeunits={granularity: events_timeunit},
                   context={granularity: ce_cfg},
                   situation={granularity: sit_cfg},
                   params={0: context_param})


def number_of_time_units_in_entities(entities, entity):
    return len(entities[entity][next(iter(entities[entity]))])
