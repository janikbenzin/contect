from contect.available.available import AvailableSelections, AvailableEntities
import contect.context.objects.contextentities.versions.entities as ent

AVAILABLE_CE = {
    AvailableEntities.TIMEUNIT: {'constructor': ent.UnitTimeContextEntity,
                                 'type': ent.UnitTimeContextEntity(None, 0, AvailableSelections.GLOBAL)},
    AvailableEntities.DIRECTLYFOLLOWS: {'constructor': ent.DirectlyTimeContextEntity,
                                        'type': ent.DirectlyTimeContextEntity(None, 0, AvailableSelections.GLOBAL)},
    AvailableEntities.CAPACITYUTIL: {'constructor': ent.CapacitySystemContextEntity,
                                     'type': ent.CapacitySystemContextEntity(None, 0, AvailableSelections.GLOBAL,
                                                                             {AvailableSelections.GLOBAL: {
                                                                                 AvailableSelections.GLOBAL: 0
                                                                             }})}
}

SUPPORTED_SELECTIONS = {
    AvailableEntities.TIMEUNIT: [AvailableSelections.GLOBAL, AvailableSelections.ACTIVITY,
                                 AvailableSelections.OBJECTTYPE, AvailableSelections.RESOURCE,
                                 AvailableSelections.LOCATION],
    AvailableEntities.DIRECTLYFOLLOWS: [AvailableSelections.ACTIVITY],
    AvailableEntities.CAPACITYUTIL: [AvailableSelections.RESOURCE, AvailableSelections.LOCATION]
}
