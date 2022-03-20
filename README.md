# Contect

## Demo video
A demo of the software can be viewed [here](https://youtu.be/VD4N8QhriLw).

## Overview

Contect is a framework for context-aware deviation detection in process executions that are extracted from object-centric event logs (see [OCEL Standard](http://ocel-standard.org) for a primer).
The framework is implemented in the package *Contect*. 
It offers its functionality through four main packages: *ParseData*, *Context*, *DeviationDetection* and *PostProcessing*.
The theoretical foundations and derivations of the framework can be found in the corresponding master thesis **Context-aware detection of deviations in process executions** written by Janik-Vasily Benzin, examined by Prof. Wil van der Aalst and supervised by Gyunam Park at the Process and Data Science Chair at RWTH Aachen.
To showcase the framework, a number of contexts and deviation detection methods are implemented and 
ready for use as a web service through the package *Backend*.
There are two main deployment options available, which are explained in detail under *Deployment*.

## Dependencies
This project relies on various dependencies, which are listed in detail in [Notice](NOTICE.md)

## Detection Methods

The framework offers its own implementations of existing detection methods that are in their core completely 
based on the respective scientific publications cited in the following: 

- Profiles detection method: Li, G., & Van Der Aalst, W. M. P. (2017). A framework for detecting deviations in complex event logs. Intelligent Data Analysis, 21(4), 759–779. https://doi.org/10.3233/IDA-160044
- Inductive detection method: Is adapted from the method in Jalali, H., & Baraani, A. (2010). Genetic-based anomaly detection in logs of process aware systems. World Academy of Science, Engineering and Technology, 64(4), 304–309. The adaptation uses the IMf and alignments methods of the pm4py library. Please refer to their references at [pm4py webpage](https://pm4py.fit.fraunhofer.de).
- Anomaly Detection Association Rules detection method: Böhmer, K., & Rinderle-Ma, S. (2020). Mining association rules for anomaly detection in dynamic process runtime behavior and explaining the root cause to users. Information Systems, 90, 101438. https://doi.org/10.1016/j.is.2019.101438
- Autoencoder detection method: Li, G., & Van Der Aalst, W. M. P. (2017). A framework for detecting deviations in complex event logs. Intelligent Data Analysis, 21(4), 759–779. https://doi.org/10.3233/IDA-160044

## Deployment

There are two deployment options: Automatic and manual. Both require Docker.

### Automatic
For automatic and platform-independent deployment, simply execute the following commands:
```shell script
git clone https://gitlab.com/janikbenzin/contect.git
cd src/server
docker-compose up
```
The web service is now available at *127.0.0.1/8050*. 
The default username is *admin*, and the default password is *test123* for logging into the system.
If you would like the Dash web service to run in debug mode, then change the value of the environment variable **DEBUG_MODE** in the [env file](src/server/.env) to **true**.

### Manual
The manual deployment is recommended for developers and service providers of the framework. 
Please make sure to install the binaries of [Graphviz](https://graphviz.org) and [Python 3.8.8](https://www.python.org/downloads/release/python-388/) (s.t. *python3* will invoke this interpreter's binary) before you proceed.
In the following, shell scripts are developed for the zsh, so if you use a different shell, then you need to modify the scripts accordingly.

```shell script
git clone https://gitlab.com/janikbenzin/contect.git
```

#### Use without IDE
If you would like to simply run the system without extending it or recompute the evaluation, the fastest option is to do the following.
Start with creating a virtual environment as described in [venv](https://docs.python.org/3/tutorial/venv.html) and activate it.
Now, run:

```shell script
pip install -e .
cd src/server/backend/db
docker-compose up
```

In a second shell:

```shell script
export CONTECT_PATH=<path_to_your_project_root> # the directory where src/ is located
cd src/server/backend
chmod +x ./run_celery.sh
./run_celery.sh
```

If you use a *Windows* machine, then the following commands are recommended in a second shell:
```shell script
pip install eventlet  
set REDIS_LOCALHOST_OR_DOCKER=localhost
set RABBIT_LOCALHOST_OR_DOCKER=localhost
set RABBITMQ_USER=contect
set RABBITMQ_PASSWORD=contect191! 
cd src/server/backend/tasks
celery -A tasks worker --loglevel=INFO -P eventlet
```

If you would like to compute the evaluation, proceed in a third shell:
```shell script
export CONTECT_PATH=<path_to_your_project_root> # the directory where src/ is located
export EVALUATION_MAX_CONCURRENT=7  # Should equal the number of cores of your CPU - 1 
cd src/evaluation/evaluation
chmod +x ./run_evaluation.sh
./run_evaluation.sh
```

Please note that the evaluation may likely take multiple days to finish.

If you would like to use Contect, proceed in a third shell:
```shell script
export CONTECT_PATH=<path_to_your_project_root> # the directory where src/ is located
cd src/server/backend
chmod +x ./run_contect.sh
./run_contect.sh
```

The default username is *admin*, and the default password is *test123* for logging into the system available at *127.0.0.1/8050*.

#### PyCharm
In PyCharm, please configure a Python 3.8.8 interpreter with a venv in the project root and open the *requirements.txt* in the root directory.
Select PyCharm's option to install the dependencies in the *requirements.txt*.
Then, proceed as follows: 
Navigate to *Preferences > Project Interpreter > Show All > Show paths for the selected interpreter*
Here, the paths *<path_to_dir_of_git_project_root>/src/server* and *<path_to_dir_of_git_project_root>/src/evaluation*
should be included. 
Now, navigate to *Run > Edit Configurations... > Add New Configuration > Python*
In the corresponding *Configuration > Script paths* insert **<path_to_dir_of_git_project_root>/src/server/backend/index.py** here.
Then, in the section *Environment Variables* add variables **REDIS_LOCALHOST_OR_DOCKER** and **LOCALHOST_OR_DOCKER** with the value **localhost** and **CONTECT_PATH** with the value **<path_to_your_project_root>**. 
If you would like Dash to run in debug mode, then additionally add variable **DEBUG_MODE** with the value **true**. 
Press the *Apply* button, then *Ok*. 
Now, proceed with a shell in PyCharm:

```shell script
cd src/server/backend/db
docker-compose up
```
If you work on a *Unix* based system, run the following commands in a new shell:

```shell script
cd src/server/backend
export CONTECT_PATH=<path_to_your_project_root> # the directory where src/ is located
chmod +x ./run_celery.sh
./run_celery.sh
```
Now, you can locally deploy the web service using PyCharm's *Run* of your newly specified *Run Configuration*
or debug it using the *Debug* of the same configuration.
The default username is *admin*, and the default password is *test123* for logging into the system available at *127.0.0.1/8050*.

If you use a *Windows* machine, then the following commands are recommended in a shell of PyCharm:
```shell script
pip install eventlet  
set REDIS_LOCALHOST_OR_DOCKER=localhost
set RABBIT_LOCALHOST_OR_DOCKER=localhost
set RABBITMQ_USER=contect
set RABBITMQ_PASSWORD=contect191! 
cd src/server/backend/tasks
celery -A tasks worker --loglevel=INFO -P eventlet
```

## Extend the framework
You can easily add one of the following to the framework: Context entities (Entities), situations (Situations), deviation detection methods (Detectors) and event correlation methods (Correlations).
In short, a context entity is the raw data container for extracted feature values from the event log.
A situation maps one or multiple context entities of the same context entity type to a value between 0 (completely normal context) and 1 (completely deviating context).
Please read the corresponding sections of the master thesis to understand the distinction between context entities and situations in more detail.
To extend one of the mentioned parts of the framework, you need to extend two enumeration classes:
[Available\<part to be extended\>Ext](src/server/backend/param/available.py) and [Available\<part to be extended\>](src/server/contect/available/available.py).
Please read the documentation of the [ContextExtension](src/server/contect/available/ext.py) class before you add your option and add your options in the *Ext* enumeration the same way as the existing ones.
At last, you can rebuild your docker container or use the manual deployment to use your newly added option.
