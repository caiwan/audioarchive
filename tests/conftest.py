from contextlib import ExitStack
import logging
import redis

import pytest

from tapearchive.config import RedisDBConfig

LOGGER = logging.getLogger(__name__)

# TODO: Use fakeredis (to an extent)

DB_PORT = 6379
DB_HOST = "localhost"


def pytest_addoption(parser):
    parser.addoption("--runslow", action="store_true", default=False, help="run slow tests")


def pytest_collection_modifyitems(config, items):
    if config.getoption("--runslow"):
        # --runslow given in cli: do not skip slow tests
        return
    skip_slow = pytest.mark.skip(reason="need --runslow option to run")
    for item in items:
        if "slow" in item.keywords:
            item.add_marker(skip_slow)


@pytest.fixture(scope="session")
def redis_db_config() -> RedisDBConfig:
    return RedisDBConfig(
        host=DB_HOST,
        port=DB_PORT,
        db=0,
        password=None,
    )


@pytest.fixture(scope="session")
def redis_db_pool() -> redis.ConnectionPool:
    return redis.ConnectionPool(host=DB_HOST, port=DB_PORT, db=0)


@pytest.fixture(scope="session")
def redis_db_connection(db_pool) -> redis.Redis:
    db = redis.Redis(connection_pool=db_pool)
    yield db
    db.flushall()
