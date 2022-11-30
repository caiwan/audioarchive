from contextlib import ExitStack
from uuid import uuid4

from tapearchive.config import AppConfig

from tq.redis_task_queue import RedisTaskQueue
from tq.task_dispacher import TaskDispatcher
from tq.job_system import JobManager

from tapearchive.app import register_task_dispatchers

import pytest


@pytest.fixture(scope="module")
def app_config(db_config):
    return AppConfig(
        db=db_config,
        is_gui_enabled=True,
        is_manager=True,
        is_worker=True,
        task_queue_uuid=uuid4(),
    )


@pytest.fixture(scope="function")
def task_dispatcher(db_pool) -> TaskDispatcher:
    task_queue = RedisTaskQueue(db_pool)
    with ExitStack() as stack:
        job_manager = stack.enter_context(JobManager())
        dispatcher = stack.enter_context(TaskDispatcher(task_queue, job_manager))
        yield dispatcher


@pytest.fixture(scope="function")
def worker_app(app_config, task_dispatcher, db_pool, db_autoclean):
    register_task_dispatchers(task_dispatcher, db_pool, app_config)


