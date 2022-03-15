#!/bin/zsh

path="$CONTECT_PATH"

export PYTHONPATH="${path}/src/server/:${path}/src/evaluation/:$PYTHONPATH"

export REDIS_LOCALHOST_OR_DOCKER=localhost
export LOCALHOST_OR_DOCKER=localhost

${path}/venv/bin/python index.py