#!/bin/bash

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

echo scfip $SCRIPT_DIR

TARGET="app"
IMAGE="caiwan/tapearchive"
TAG="latest"
BASE_IMAGE="ubuntu:20.04"

case $1 in
    app)
        TARGET="app"
        TAG="latest"
        ;;
    dev)
        TARGET="dev"
        TAG="latest-dev"
        ;;
    *)
        echo "Invalid target: $1"
        exit 1
        ;;
esac

mkdir -p ./docker/context

rsync -zarvh $SCRIPT_DIR/../src $SCRIPT_DIR/context
# rsync -zarvh $SCRIPT_DIR/tq ./docker/context
rsync -zavh  $SCRIPT_DIR/../setup.py $SCRIPT_DIR/context/setup.py
rsync -zavh  $SCRIPT_DIR/../setup.cfg $SCRIPT_DIR/context/setup.cfg
rsync -zavh  $SCRIPT_DIR/../config.yaml $SCRIPT_DIR/context/config.yaml
rsync -zavh  $SCRIPT_DIR/../logging.config $SCRIPT_DIR/context/logging.config
rsync -zavh  $SCRIPT_DIR/entrypoint.sh $SCRIPT_DIR/context/entrypoint.sh

DOCKER_BUILDKIT=1 docker build \
--target $TARGET \
--build-arg base_image=$BASE_IMAGE \
-t "$IMAGE:$TAG" \
-f ./docker/Dockerfile ./docker/context

# TODO remove only if needed eg. clean build 
# rm -rf ./docker/context
