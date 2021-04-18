from backend.components.misc import markdown_text, container

about = '''
Contect is a framework for context-aware deviation detection in process executions. 
It allows you to upload object-centric event data, correlate events based on three different correlation approaches 
with customizable objects, detect deviations using four state-of-the-art deviation detection methods from the research
literature and enrich/post-process the detection results such that they become context-aware.

### Detection Methods

The framework offers its own implementations of existing detection methods that are in their core completely 
based on the respective scientific publications cited in the following: 

- Profiles detection method: Li, G., & Van Der Aalst, W. M. P. (2017). A framework for detecting deviations in complex event logs. Intelligent Data Analysis, 21(4), 759–779. https://doi.org/10.3233/IDA-160044
- Inductive detection method: Is adapted from the method in Jalali, H., & Baraani, A. (2010). Genetic-based anomaly detection in logs of process aware systems. World Academy of Science, Engineering and Technology, 64(4), 304–309. The adaptation uses the IMf and alignments methods of the pm4py library. Please refer to their references at [pm4py webpage](https://pm4py.fit.fraunhofer.de).
- Anomaly Detection Association Rules detection method: Böhmer, K., & Rinderle-Ma, S. (2020). Mining association rules for anomaly detection in dynamic process runtime behavior and explaining the root cause to users. Information Systems, 90, 101438. https://doi.org/10.1016/j.is.2019.101438
- Autoencoder detection method: Li, G., & Van Der Aalst, W. M. P. (2017). A framework for detecting deviations in complex event logs. Intelligent Data Analysis, 21(4), 759–779. https://doi.org/10.3233/IDA-160044
'''

page_layout = container('About Contect',
                        [
                            markdown_text(about)
                        ]
                        )
