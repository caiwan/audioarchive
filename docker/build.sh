#!/bin/bash

mkdir -p ./docker/context

rsync -zarvh ./tapearchive ./docker/context
rsync -zarvh ./tq ./docker/context
rsync -zavh ./setup.py ./docker/context/setup.py
rsync -zavh ./config.yaml ./docker/context/config.yaml
rsync -zavh ./logging.config ./docker/context/logging.config
rsync -zavh ./docker/entrypoint.sh ./docker/context/entrypoint.sh

DOCKER_BUILDKIT=1 docker build \
--target app \
-t caiwan/tapearchive:latest \
-f ./docker/Dockerfile ./docker/context

# TODO remove only if needed eg. clean build 
# rm -rf ./docker/context