#!/bin/bash

conf=${CONF_FILE:-"/config/config.yaml"}
logger_config=${LOG_CONF_FILE:-"/config/logging.config"}

if [[ -z "$*" ]]; then
    exec audio-processor --logging-config "$logger_config" -c "$conf" 
fi

exec "$@"