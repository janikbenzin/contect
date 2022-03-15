#!/bin/zsh

path="$CONTECT_PATH"

export PYTHONPATH="${path}/src/server/:${path}/src/evaluation/:$PYTHONPATH"


export REDIS_LOCALHOST_OR_DOCKER=localhost
export LOCALHOST_OR_DOCKER=localhost

cd "${path}/src/server/backend/tasks" || exit
${path}/venv/bin/celery -A tasks worker --loglevel=INFO