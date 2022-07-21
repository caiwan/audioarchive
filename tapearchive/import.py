import pathlib
import argparse
import yaml
import logging

import redis

import marshmallow.exceptions

from tqdm import tqdm
from tqdm.contrib.logging import logging_redirect_tqdm

from tapearchive.models import catalog
from tapearchive import config
from tapearchive.utils import find_all_files, get_config

LOGGER = logging.getLogger(__name__)


def parse_args() -> object:
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

    return parser.parse_args()


def create_db_pool(db_config: config.DBConfig) -> redis.ConnectionPool:
    return redis.ConnectionPool(**db_config.to_dict())


def main():
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s]: %(message)s")

    config = get_config(args.config)
    logging.info(f"AppConfig={config.to_dict()}")
    pool = create_db_pool(config.db)

    catalog_dao = catalog.CatalogDao(pool)

    with logging_redirect_tqdm():
        for yaml_path in tqdm(find_all_files("meta.yaml", args.data_path), desc="Loading manifests into db"):
            with open(yaml_path, "r") as f:
                try:
                    entry = catalog.CatalogEntry.schema().load(yaml.safe_load(f))
                    id = catalog_dao.create_or_update(entry)
                    LOGGER.info(f"Catalog entry [{entry.name}] had been imported id={id}")
                except marshmallow.exceptions.ValidationError as e:
                    LOGGER.error(f"Catalog manifest file {yaml_path} cannot be loaded.", exc_info=e if args.is_verbose else None)


if __name__ == "__main__":
    main()
