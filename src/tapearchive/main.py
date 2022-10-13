import pathlib
import argparse
from contextlib import ExitStack
from waiting import wait

import logging
import logging.config


from tapearchive.config import AppConfig
from tapearchive.utils import get_config

from tapearchive.app import create_app, create_db_connection, create_dispatcher, create_manager_app


def fetch_args():
    parser = argparse.ArgumentParser(description="Tapearchive worker/manager.")

    parser.add_argument(
        "--config",
        "-c",
        dest="config_path",
        type=pathlib.Path,
        required=True,
        help="App configuration file",
    )

    parser.add_argument(
        "--logging-config",
        dest="logging_config",
        type=pathlib.Path,
        required=False,
        default=pathlib.Path("./logging.config"),  # TODO: Load from package default otherwise
        help="App logging config file",
    )

    return parser.parse_args()


def main():
    args = fetch_args()
    config: AppConfig = get_config(args.config_path)
    logging.config.fileConfig(args.logging_config, disable_existing_loggers=False)

    with ExitStack() as stack:
        dispatcher = create_app(config, stack)
        wait(dispatcher.is_exit)


def worker_entrypoint():
    args = fetch_args()
    config: AppConfig = get_config(args.config_path)
    logging.config.fileConfig(args.logging_config, disable_existing_loggers=False)
    connection_pool = create_db_connection(config)

    with ExitStack() as stack:
        dispatcher = create_dispatcher(connection_pool, config, stack)
        wait(dispatcher.is_exit)


if __name__ == "__main__":
    main()
