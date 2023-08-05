from asyncio.log import logger
from asyncore import dispatcher
from contextlib import ExitStack

import json
import logging
from pymongo import MongoClient

import redis

from tq.task_dispacher import TaskDispatcher
from tq.redis_task_queue import RedisTaskQueue
from tq.job_system import JobManager

from tapearchive.config import AppConfig

from tapearchive.tasks.audio_convert import AudioConverterHandler

# from tapearchive.workflow.tasks.audio_analisis import FindKeyHandler


LOGGER = logging.getLogger(__name__)


# TODO: Move to workflow/
def register_task_dispatchers(
    dispatcher: TaskDispatcher,
    mongo_db: MongoClient,
    connection_pool: redis.ConnectionPool,
    config: AppConfig,
):
    dispatcher.register_task_handler(AudioConverterHandler(mongo_db, config=config))
    # dispatcher.register_task_handler(FindKeyHandler(connection_pool, config=config))
    pass


def create_dispatcher(
    connection_pool: redis.ConnectionPool,
    mongo_db: MongoClient,
    config: AppConfig,
    stack: ExitStack,
) -> TaskDispatcher:
    task_queue = RedisTaskQueue(connection_pool)
    job_manager = stack.enter_context(JobManager())
    dispatcher = stack.enter_context(TaskDispatcher(task_queue, job_manager))

    register_task_dispatchers(dispatcher, mongo_db, connection_pool, config)

    # The task dispatcher should be running at this point
    return dispatcher


def create_db_connection(config: AppConfig) -> redis.ConnectionPool:
    return redis.ConnectionPool(
        host=config.redis.host,
        port=config.redis.port,
        db=config.redis.db,
        username=config.redis.username,
        password=config.redis.password,
    )


def create_mongo_connection(config: AppConfig) -> MongoClient:
    return MongoClient(config.mongo.url)


def create_app(config: AppConfig, stack: ExitStack):
    LOGGER.info("---- Tape archive instance ----")

    connection_pool = create_db_connection(config)
    mongo_db = create_mongo_connection(config)
    dispatcher = create_dispatcher(connection_pool, mongo_db, config, stack)

    return dispatcher
