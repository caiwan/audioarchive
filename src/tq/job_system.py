from cmath import log
from typing import Any, Callable, List

import atomic
import abc
import threading
import multiprocessing
import random
import time

import logging


LOGGER = logging.getLogger(__name__)


class Job(abc.ABC):
    def __init__(self, fn, parent, manager, *argv, **kwargs):
        self._fn = fn
        self._data = (argv, kwargs)
        self._parent = parent
        self._result = None
        self._manager = manager

        self._unfinished_jobs = atomic.AtomicLong(1)

    def __call__(self, *argv, **kwargs):
        argv, kwargs = self._data
        self._result = self._fn(*argv, **kwargs, job=self, manager=self._manager)

    @property
    def is_finished(self) -> bool:
        self._manager._is_job_done(self)


class BoundedMPMCQueue:
    """
    PY version of multi producer multi conumer lockless queue
    Inspired by https://www.1024cores.net/home/lock-free-algorithms/queues/bounded-mpmc-queue
    """

    def __init__(self, queue_size=4096):
        assert queue_size >= 2 and (queue_size & (queue_size - 1)) == 0, "queue_size must be power of two, and at least 2"
        self._queue_size_mask = queue_size - 1
        self._queue = list([atomic.AtomicLong(i), None] for i in range(queue_size))
        self._head = atomic.AtomicLong(0)
        self._tail = atomic.AtomicLong(0)

    def push(self, item: Any):
        pos = self._tail.value
        while True:
            index = pos & self._queue_size_mask
            seq_atomic = self._queue[index][0]
            seq = seq_atomic.value
            diff = pos - seq
            if diff == 0:
                if self._tail.compare_and_swap(pos, pos + 1):
                    self._queue[index][1] = item
                    self._queue[index][0].value = pos + 1
                    return True
            elif diff < 0:
                return False
            pos = self._tail.value

    def pop(self) -> Any:
        pos = self._head.value
        while True:
            index = pos & self._queue_size_mask
            seq_atomic = self._queue[index][0]
            seq = seq_atomic.value
            diff = pos - seq + 1
            if diff == 0:
                if self._head.compare_and_swap(pos, pos + 1):
                    item = self._queue[index][1]
                    self._queue[index][0].value = pos + self._queue_size_mask + 1
                    return item
            elif diff < 0:
                return None
            pos = self._head.value

    @property
    def is_empty(self) -> bool:
        head = self._head.value
        tail = self._tail.value
        return tail <= head

    @property
    def size(self) -> int:
        head = self._head.value
        tail = self._tail.value
        return tail - head if tail > head else 0


class Worker(threading.Thread):
    def __init__(self, manager, *argv, **kwargs):
        threading.Thread.__init__(self, *argv, **kwargs)
        self._jobs = BoundedMPMCQueue()
        self._manager = manager
        self._is_terminated = atomic.AtomicLong(0)
        self._ident = threading.get_ident()

    def add_job(self, job):
        self._jobs.push(job)

    def run(self):
        LOGGER.debug(f"Worker {self} starts")
        while self._is_terminated.value == 0:
            job = self._manager._get_job()
            if callable(job):
                try:
                    LOGGER.debug(f"Worker {self} starts")
                    job()
                except Exception as e:
                    LOGGER.error("Unhandled Exception had occured", exc_info=e)
                    job.result = None
                    job._unfinished_jobs.value = -1
                job._unfinished_jobs -= 1
                if job._parent:
                    job._parent._unfinished_jobs -= 1


# TODO: inherit abstract context manager
class JobManager:
    def __init__(self, num_of_workers=0):
        super().__init__()
        self.num_of_workers = num_of_workers if num_of_workers > 0 else multiprocessing.cpu_count() - 1
        self.workers = List[threading.Thread]

    def _spawn_workers(self):
        LOGGER.debug(f"Creating {self.num_of_workers} workers")
        self.workers = [Worker(self, daemon=True) for _ in range(self.num_of_workers)]
        for worker in self.workers:
            worker.start()

    def __enter__(self):
        self._spawn_workers()
        return self

    def __exit__(self, *argv, **kwargs):
        LOGGER.debug(f"Terminating job system")
        self.join()

    def create_job(self, fn: Callable, *argv, **kwargs) -> Job:
        return Job(fn, None, self, *argv, **kwargs)

    def create_child_job(self, parent: Job, fn: Callable, *argv, **kwargs) -> Job:
        parent._unfinished_jobs += 1
        return Job(fn, parent, self, *argv, **kwargs)

    def schedule_job(self, job: Job):
        if job._unfinished_jobs.value > 0:
            worker:Worker = random.choice(self.workers)
            worker.add_job(job)

    def wait(self, job):
        while job._unfinished_jobs.value > 0:
            another_job = self._get_job()
            if callable(another_job):
                try:
                    another_job(self)
                except Exception as e:
                    LOGGER.error("Exception occured", exc_info=e)
                    another_job.result = None
                another_job._unfinished_jobs -= 1
                if another_job._parent:
                    another_job._parent._unfinished_jobs -= 1

    def join(self, timeout: float = None):
        for worker in self.workers:
            worker._is_terminated += 1
        for worker in self.workers:
            worker.join(timeout=timeout)

    def _steal(self):
        return random.choice(self.workers)

    def _find_worker(self):
        current_thread_ident = threading.get_ident()
        for worker in self.workers:
            if worker.ident == current_thread_ident:
                return worker
        return None

    def _get_job(self):
        worker = self._find_worker()
        if not worker:
            return None

        if worker._jobs.is_empty:
            steal_from_worker = self._steal()
            if steal_from_worker == worker or steal_from_worker._jobs.is_empty:
                time.sleep(0.3)
                return None
            stolen_job = steal_from_worker._jobs.pop()
            return stolen_job
        else:
            job = worker._jobs.pop()
            return job

    def _is_job_done(self, job: Job) -> Job:
        return job._unfinished_jobs.value == 0

    def _get_child_job_count(self, job: Job) -> Job:
        return job._unfinished_jobs.value
