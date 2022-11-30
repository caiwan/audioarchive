from contextlib import ExitStack
import logging
import redis

import pytest

from tapearchive.config import DBConfig
from tq.job_system import JobManager
from tq.task_dispacher import LocalTaskQueue, TaskDispatcher

LOGGER = logging.getLogger(__name__)

DB_PORT = 6379
DB_HOST = "redis"


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
def db_config() -> DBConfig:
    return DBConfig(
        host=DB_HOST,
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


@pytest.fixture(scope="function")
def task_dispatcher():
    task_queue = LocalTaskQueue()
    with ExitStack() as stack:
        job_manager = stack.enter_context(JobManager())
        dispatcher = stack.enter_context(TaskDispatcher(task_queue, job_manager))
        yield dispatcher
        dispatcher.terminate()