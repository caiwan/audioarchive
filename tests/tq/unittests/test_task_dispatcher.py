import pytest

from contextlib import ExitStack
from dataclasses import dataclass

from unittest.mock import Mock

import waiting
from tq.job_system import JobManager

from tq.task_dispacher import TaskDispatcher, LocalTaskQueue, task_handler

import logging

LOGGER = logging.getLogger(__name__)


@pytest.fixture(scope="function")
def task_dispatcher():
    task_queue = LocalTaskQueue()
    with ExitStack() as stack:
        job_manager = stack.enter_context(JobManager())
        dispatcher = stack.enter_context(TaskDispatcher(task_queue, job_manager))
        yield dispatcher


@dataclass
class DummyTaskOne:
    pass


@dataclass
class DummyTaskTwo:
    pass


@dataclass
class DummyTaskThree:
    pass


class DummyTaskHandler:
    def __init__(self) -> None:
        self.mocks = [Mock() for _ in range(3)]

    @task_handler(DummyTaskOne)
    def task_one(self, *a, **w):
        LOGGER.debug(f"Handling dummy task 1 {a} {w}")
        self.mocks[0]()

    @task_handler(DummyTaskTwo)
    def task_two(self, *a, **w):
        LOGGER.debug(f"Handling dummy task 2 {a} {w}")
        self.mocks[1]()

    @task_handler(DummyTaskOne, DummyTaskTwo, DummyTaskThree)
    def task_three(self, *a, **w):
        LOGGER.debug(f"Handling dummy task 3 {a} {w}")
        self.mocks[2]()


def test_task_dispatcher_register():
    dispatcher = TaskDispatcher(None, None)
    dispatcher.register_task_handler(DummyTaskHandler())

    assert len(dispatcher.task_handlers) == 3
    assert len(dispatcher.task_handlers[DummyTaskOne]) == 2
    assert len(dispatcher.task_handlers[DummyTaskTwo]) == 2
    assert len(dispatcher.task_handlers[DummyTaskThree]) == 1


def test_task_dipatcher_dispatches_task(task_dispatcher: TaskDispatcher):
    dummy_handler = DummyTaskHandler()
    task_dispatcher.register_task_handler(dummy_handler)

    all([task_dispatcher.post_task(t) for t in [DummyTaskOne(), DummyTaskTwo(), DummyTaskThree()]])

    waiting.wait(lambda: all(mock.called for mock in dummy_handler.mocks), sleep_seconds=0.1, timeout_seconds=3)
