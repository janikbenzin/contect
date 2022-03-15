FROM javert899/pm4py as base
MAINTAINER Janik Benzin

FROM base as builder

RUN mkdir /install
WORKDIR /install
COPY requirements.txt /requirements.txt

# Upgrade installed packages
RUN apt-get update && apt-get upgrade -y && apt-get clean

# Install git
RUN apt-get install -y git && apt-get install -y libpq-dev

# Install libgraphviz
RUN apt-get install -y libgraphviz-dev pkg-config

# Install requirements
RUN pip install --target=/install -r /requirements.txt

FROM base

COPY --from=builder /install /usr/local
#COPY --from=builder /usr/lib/python3.8/site-packages /usr/lib/python3.8/site-packages

# Change working directory to new user
WORKDIR /home/contect

ENV PYTHONPATH "${PYTHONPATH}:/install:/home/contect:/usr/local:/home/contect"

COPY . .


# Add user for safe celery execution
RUN useradd -ms /bin/bash contectworker

# Install git
#RUN apt-get install -y git && apt-get install -y libpq-dev

# We copy just the requirements.txt first to leverage Docker cache


# Get gcc
#ENV DEBIAN_FRONTEND noninteractive
#RUN apt-get update && \
#    apt-get -y install gcc mono-mcs && \
#    rm -rf /var/lib/apt/lists/*

# Install dependencies of Flask project
#RUN pip install -e .

# Change working directory to new root
# WORKDIR /code/anomalydetection

# WORKDIR /home/contect/backend/tasks

# Set the rest of environment variables
ENV FLASK_ENV="${FLASK_ENV}" \
    PYTHONPATH="${PYTHONPATH}:/home/contect/server:/home/contect/evaluation:/home/contect/backend:" \
    UID_CONTECT="$(id -u)"

# Only expose port 8050 for dash application
EXPOSE 8050

