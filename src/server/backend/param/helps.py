GUIDANCE_HELP = '''To differentiate interesting contexts from uninteresting ones, we apply heuristic filters to your chosen contexts if **guide** is selected.. 
The heuristic filters automatically remove uninteresting contexts.
In general, the aim of the heuristic filters are to translate the conceptual properties of contexts from the causal model below into properties of context values.
Please refer to the master thesis for details on the respective heuristic filters.'''
TYPE_HELP = '''The two types of contexts - **positive** and **negative** - determine whether the context explains process deviations (first relationship in the causal model) or is in itself a deviation (second relationship in the causal model).'''
STABILITY_HELP = '''The context dynamics determine what history of your data is considered for determining what normal contexts are. If your context dynamics are **insignificant**, then the context values are compared to the complete history of contexts that covers the whole time span of your data. 
IF your context dynamics are **very significant**, then only the last week of a context is considered for determining whether the current context is more normal or more deviating. The option **moderate** means that the last year is used and the option **significant** means that the last month is used.'''
INTRINSIC_HELP = '''Process deviations are deviations in traces that are represented by higher deviation scores of your selected deviation detection method. These deviations occur in the process. The majority of existing deviation detection methods only considers the process perspective in deviation detection and in the case of multiple perspectives almost all existing deviation detection methods only take the organizational perspective into account resulting in deviations of these two process dimensions.
Hence, these deviations are called process deviations. 
'''
EXTERNAL_HELP = '''Context deviations are more deviating contexts compared to the current history set by context dynamics parameter. These context deviations are detected by both positive and negative contexts, but the former explains process deviations, whereas the latter is used to detect context deviations that are interesting as a deviation in itself to you.
'''
TIME_UNIT_HELP = '''The time unit size determines the size of bins of equal-width binning the period of time from the first to the last timestamp of your data. The resulting set of time units (bins) is the time span of your data that is used to measure contexts for each of the contained time units.'''