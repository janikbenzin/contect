#!/bin/zsh

path="$CONTECT_PATH"

export PYTHONPATH="${path}/src/server/:${path}/src/evaluation/:$PYTHONPATH"


export REDIS_LOCALHOST_OR_DOCKER=localhost
export LOCALHOST_OR_DOCKER=localhost
export PYTHONUNBUFFERED=1
export SECRET_KEY=secret

cd "${path}/src/evaluation/evaluation" || exit
python evaluate.py
python post_process.py
python metrics.py