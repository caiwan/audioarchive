from contextlib import ExitStack
import uuid

from tapearchive.config import AppConfig, MongoDBConfig, RedisDBConfig

from tq.redis_task_queue import RedisTaskQueue
from tq.task_dispacher import TaskDispatcher
from tq.job_system import JobManager

from pymongo import MongoClient
import redis


from tapearchive.app import register_task_dispatchers

import pytest

REDIS_PORT = 6379
REDIS_HOST = "localhost"

MONGO_HOST = "localhost:27017"
MONGO_CONNECTION_STRING = "mongodb://root:toor@" + MONGO_HOST
PLACEHOLDER = "_placeholder"




@pytest.fixture(scope="function")
def redis_pool() -> redis.ConnectionPool:
    return redis.ConnectionPool(host=REDIS_HOST, port=REDIS_PORT, db=0)


@pytest.fixture(scope="function")
def redis_db_connection(db_pool) -> redis.Redis:
    db = redis.Redis(connection_pool=db_pool)
    yield db
    db.flushall()


@pytest.fixture(scope="session")
def mongo_db():
    test_user = "test_user"
    test_password = "test_password"
    test_db = "test_db"

    client = MongoClient(MONGO_CONNECTION_STRING)
    db = client.admin
    if not bool(
        db.system.users.find_one(
            {
                "user": test_user,
            }
        )
    ):
        db.command(
            "createUser",
            test_user,
            pwd=test_password,
            roles=[{"role": "readWrite", "db": test_db}],
        )

    if PLACEHOLDER not in list(client[test_db].list_collection_names()):
        client[test_db].create_collection(PLACEHOLDER)

    client.close()

    yield (test_user, test_password, test_db)

    client = MongoClient(MONGO_CONNECTION_STRING)
    client.drop_database(test_db)
    client.admin.command("dropUser", test_user)
    client.close()


@pytest.fixture(scope="function")
def mongodb_client(mongo_db) -> MongoClient:
    test_user, test_password, test_db = mongo_db
    client = MongoClient(
        f"mongodb://{test_user}:{test_password}@{MONGO_HOST}/{test_db}?authSource=admin"
    )

    yield client

    db = client.get_database(test_db)

    for collection_name in db.list_collection_names():
        if collection_name not in [PLACEHOLDER]:
            collection = db.get_collection(collection_name)
            collection.drop()

    client.close()


@pytest.fixture(scope="module")
def app_config(mongo_db):
    test_user, test_password, test_db = mongo_db
    return AppConfig(
        redis=RedisDBConfig(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=0,
        ),
        mongo=MongoDBConfig(
            url=f"mongodb://{test_user}:{test_password}@{MONGO_HOST}/{test_db}?authSource=admin",
        ),
        is_gui_enabled=True,
        is_manager=True,
        is_worker=True,
        task_queue_uuid=uuid.uuid4(),
    )


@pytest.fixture(scope="function")
def task_dispatcher(redis_pool) -> TaskDispatcher:
    task_queue = RedisTaskQueue(redis_pool)
    with ExitStack() as stack:
        job_manager = stack.enter_context(JobManager())
        dispatcher = stack.enter_context(TaskDispatcher(task_queue, job_manager))
        
        yield dispatcher

        dispatcher.terminate()
        job_manager.join(10)


@pytest.fixture(scope="function")
def worker_app(app_config, task_dispatcher, redis_pool, mongodb_client):
    register_task_dispatchers(task_dispatcher, mongodb_client, redis_pool, app_config)
