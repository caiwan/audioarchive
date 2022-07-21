import logging
import redis

import pytest
from waiting import wait
import docker

from tapearchive.config import DBConfig

LOGGER = logging.getLogger(__name__)

DB_PORT = 63792


@pytest.fixture(autouse=True, scope="session")
def db_container():
    client = docker.from_env()

    volume_name = "test_db_data"
    container_name = "redis-unit-test"

    try:
        container = client.containers.get(container_name)
        LOGGER.warning(f"Removing {container_name} container")
        container.stop()
        container.remove()
    except docker.errors.NotFound:
        pass

    try:
        volume = client.volumes.get(volume_name)
        LOGGER.warning(f"Removing {volume_name} volume")
        volume.remove()
    except docker.errors.NotFound:
        pass

    try:
        volume = client.volumes.create(name=volume_name, driver="local")
        container = client.containers.create(
            # TODO: Proper tag
            "redis",
            name=container_name,
            volumes={volume_name: {"bind": "/etc/redis/database", "mode": "rw"}},
            restart_policy={"Name": "always"},
            ports={"6379/tcp": DB_PORT},
            detach=True,
        )

        container.start()

        def database_is_ready():
            logs = str(container.logs(stream=False))
            return logs.rfind("Server initialized") < logs.rfind("Ready to accept connections") > -1

        wait(database_is_ready, timeout_seconds=10, sleep_seconds=0.1)
        yield container

    finally:
        container.stop()
        container.remove()
        volume.remove()


@pytest.fixture(scope="session")
def db_config(db_container) -> DBConfig:
    return DBConfig(
        host="localhost",
        port=DB_PORT,
        db=0,
        password=None,
    )


@pytest.fixture(scope="session")
def db_pool(db_container) -> redis.ConnectionPool:
    return redis.ConnectionPool(host="localhost", port=DB_PORT, db=0)


@pytest.fixture(scope="session")
def db_connection(db_pool) -> redis.Redis:
    db = redis.Redis(connection_pool=db_pool)
    yield db


@pytest.fixture(scope="function", autouse=True)
def db_autoclean(db_connection):
    yield
    db_connection.flushall()
