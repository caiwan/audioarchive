import logging
import redis

import pytest

from tapearchive.config import DBConfig

LOGGER = logging.getLogger(__name__)

DB_PORT = 6379
DB_HOST = "redis"


@pytest.fixture(scope="session")
def db_config() -> DBConfig:
    return DBConfig(
        host=DB_HOST ,
        port=DB_PORT,
        db=0,
        password=None,
    )


@pytest.fixture(scope="session")
def db_pool() -> redis.ConnectionPool:
    return redis.ConnectionPool(host=DB_HOST, port=DB_PORT, db=0)


@pytest.fixture(scope="session")
def db_connection(db_pool) -> redis.Redis:
    db = redis.Redis(connection_pool=db_pool)
    yield db


@pytest.fixture(scope="function", autouse=True)
def db_autoclean(db_connection):
    yield
    db_connection.flushall()
