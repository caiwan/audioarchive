from asyncio.log import logger
from asyncore import dispatcher
from contextlib import ExitStack

import json
import logging

import redis

from tq.task_dispacher import TaskDispatcher
from tq.redis_task_queue import RedisTaskQueue
from tq.job_system import JobManager

from tapearchive.config import AppConfig

from tapearchive.workflow.tasks.audio_convert import AudioConverterHandler
from tapearchive.workflow.tasks.audio_analisis import FindKeyHandler


LOGGER = logging.getLogger(__name__)


# TODO: Move to workflow/
def register_task_dispatchers(dispatcher: TaskDispatcher, connection_pool: redis.ConnectionPool, config: AppConfig):
    dispatcher.register_task_handler(AudioConverterHandler(connection_pool, config=config))
    dispatcher.register_task_handler(FindKeyHandler(connection_pool, config=config))


def create_dispatcher(connection_pool: redis.ConnectionPool, config: AppConfig, stack: ExitStack) -> TaskDispatcher:
    task_queue = RedisTaskQueue(connection_pool)
    job_manager = stack.enter_context(JobManager())
    dispatcher = stack.enter_context(TaskDispatcher(task_queue, job_manager))

    register_task_dispatchers(dispatcher, connection_pool, config)

    # The task dispatcher should be running at this point
    return dispatcher


def create_db_connection(config: AppConfig) -> redis.ConnectionPool:
    return redis.ConnectionPool(
        host=config.db.host,
        port=config.db.port,
        db=config.db.db,
        username=config.db.username,
        password=config.db.password,
    )


def create_app(config: AppConfig, stack: ExitStack):
    LOGGER.info("---- Tape archive instance ----")

    connection_pool = create_db_connection(config)
    dispatcher = create_dispatcher(connection_pool, config, stack)

    return dispatcher

