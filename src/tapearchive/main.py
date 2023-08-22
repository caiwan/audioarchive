import pathlib
import argparse
from contextlib import ExitStack

import marshmallow
import yaml
from tapearchive.flask_app import create_flask_app
from waiting import wait

import logging
import logging.config

from tqdm import tqdm
from tqdm.contrib.logging import logging_redirect_tqdm

from tapearchive.config import AppConfig
from tapearchive.models.catalog import CatalogDao, CatalogEntry
from tapearchive.utils import find_all_files, get_config

from tapearchive.app import create_app, create_db_connection, create_dispatcher

LOGGER = logging.getLogger(__name__)


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


def flask_entrypoint():
    args = fetch_args()
    config: AppConfig = get_config(args.config_path)
    logging.config.fileConfig(args.logging_config, disable_existing_loggers=False)

    app = create_flask_app(config)
    app.run(debug=True, host="0.0.0.0")


# ---

# TODO: Split these stuff up


def data_import_entrypont():
    parser = argparse.ArgumentParser(description="Imports tapearchive to db.")

    parser.add_argument(
        "--dir",
        "-d",
        dest="data_path",
        type=pathlib.Path,
        required=True,
        help="Source Directory of files.",
    )

    parser.add_argument(
        "--config",
        dest="config",
        type=str,
        default="./config.yaml",
        help="Application config",
    )

    parser.add_argument(
        "--verbose",
        dest="is_verbose",
        action="store_true",
        required=False,
        help="Print detailed log",
    )

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="[%(levelname)s]: %(message)s")

    config = get_config(args.config)
    logging.info(f"AppConfig={config.to_dict()}")
    pool = create_db_connection(config)

    catalog_dao = CatalogDao(pool)

    with logging_redirect_tqdm():
        for yaml_path in tqdm(find_all_files("meta.yaml", args.data_path), desc="Loading manifests into db"):
            with open(yaml_path, "r") as f:
                try:
                    entry = CatalogEntry.schema().load(yaml.safe_load(f))
                    id = catalog_dao.create_or_update(entry)
                    LOGGER.info(f"Catalog entry [{entry.name}] had been imported id={id}")
                except marshmallow.exceptions.ValidationError as e:
                    LOGGER.error(f"Catalog manifest file {yaml_path} cannot be loaded.", exc_info=e if args.is_verbose else None)


if __name__ == "__main__":
    main()
