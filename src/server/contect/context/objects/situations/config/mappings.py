from contect.available.available import AvailableSelections, AvailableEntities
import contect.context.objects.situations.versions.situations as sit

AVAILABLE_SIT = {
    AvailableEntities.TIMEUNIT: {'constructor': sit.SelectableFunctionalSituation,
                                 'type': sit.SelectableFunctionalSituation(
                                     value=None,
                                     time=0,
                                     selection=AvailableSelections.GLOBAL
                                 )},
    AvailableEntities.DIRECTLYFOLLOWS: {'constructor': sit.SelectableFunctionalSituation,
                                        'type': sit.SelectableFunctionalSituation(
                                            value=None,
                                            time=0,
                                            selection=AvailableSelections.GLOBAL
                                        )},
    AvailableEntities.CAPACITYUTIL: {'constructor': sit.DoubleSelectionFunctionalSituation,
                                     'type': sit.DoubleSelectionFunctionalSituation(
                                         value=None,
                                         time=0,
                                         selection=AvailableSelections.GLOBAL,
                                         nested_value={
                                             AvailableSelections.GLOBAL: {
                                                 AvailableSelections.GLOBAL: 0
                                             }
                                         },
                                         selection2=AvailableSelections.GLOBAL
                                     )}
}