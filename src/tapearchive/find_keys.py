import json
from typing import Any, Dict, Optional, Tuple
from collections import defaultdict
from dataclasses import dataclass, field
from contextlib import ExitStack
from uuid import UUID, uuid4
from time import sleep

import pathlib
import glob
import argparse
import logging


from tqdm import tqdm
from tqdm.contrib.logging import logging_redirect_tqdm

from tq.database import BaseDao, BaseEntity, CustomJSONEncoder
from tq.task_dispacher import task_handler

from tapearchive import app
from tapearchive.utils import get_config

from tapearchive.workflow.tasks.audio_analisis import FindTuneKey, FindKeyFailed, FindKeyDone
from tapearchive.models.raw_data import FileDao

LOGGER = logging.getLogger(__name__)


@dataclass
class PendingTask(BaseEntity):
    file_id: UUID
    file_name: str


@dataclass
class PendingTasksDao(BaseDao):
    def __init__(self, db_pool):
        super().__init__(db_pool, PendingTask.schema(), key_prefix=f"pending_tasks.{uuid4()}")
        # Note: This should not be don this way. Daos are not chared yet. They should be singletons anyway.
        self.pending_tasks: Dict[UUID, PendingTask] = defaultdict(PendingTask)

    def create_or_update(self, obj: PendingTask) -> UUID:
        self.pending_tasks[obj.id] = obj
        return super().create_or_update(obj)

    def delete(self, id: UUID):
        del self.pending_tasks[id]
        return super().delete(id)


@dataclass
class TuneKey(BaseEntity):
    file_name: str
    chroma_map: Dict[str, float]
    most_likely_key: str
    most_likely_key_confidence: float
    second_most_likely_key: Optional[str]
    second_most_likely_key_confidence: Optional[float]


class TuneKeysDao(BaseDao):
    def __init__(self, db_pool):
        super().__init__(db_pool, TuneKey.schema(), key_prefix="tune_key")
        pass


def parse_args() -> object:
    parser = argparse.ArgumentParser(description="Finds key of songs in one directory recursively")

    parser.add_argument(
        "--dir",
        "-d",
        dest="data_dir",
        type=pathlib.Path,
        required=True,
        help="Source Directory of files.",
    )

    parser.add_argument(
        "--output",
        "-o",
        dest="target_file",
        type=pathlib.Path,
        required=True,
        help="Target report file",
    )

    parser.add_argument(
        "--config",
        dest="config",
        type=str,
        default="./config.yaml",
        help="Application config",
    )

    parser.add_argument(
        "--verbose",
        dest="is_verbose",
        action="store_true",
        required=False,
        help="Print detailed log",
    )

    return parser.parse_args()


class FindKeyTaskResultHandler:
    def __init__(self, pending_tasks_dao: PendingTasksDao, tune_keys_dao: TuneKeysDao) -> None:
        self._pending_tasks_dao = pending_tasks_dao
        self._tune_keys_dao = tune_keys_dao

    @task_handler(FindKeyDone)
    def handle_find_key_done(self, task: FindKeyDone, *args, **kwargs):
        task_entry: PendingTask = self._pending_tasks_dao.get_entity(task.task_id)
        self._tune_keys_dao.create_or_update(
            TuneKey(
                id=uuid4(),
                file_name=task_entry.file_name,
                chroma_map=dict([(k, float(v)) for k, v in task.chroma_map.items()]),
                most_likely_key=task.most_likely_key[0],
                most_likely_key_confidence=float(task.most_likely_key[1]),
                second_most_likely_key=task.second_most_likely_key[0] if task.second_most_likely_key else None,
                second_most_likely_key_confidence=float(task.second_most_likely_key[1]) if task.second_most_likely_key else None,
            )
        )
        self._pending_tasks_dao.delete(task.task_id)

    @task_handler(FindKeyFailed)
    def handle_find_key_failed(self, task: FindKeyFailed, *args, **kwargs):
        task_entry: PendingTask = self._pending_tasks_dao.get_entity(task.task_id)
        logging.error(f"Failed to find key for song {task_entry.file_name}. Reason: {task.error}")
        self._pending_tasks_dao.delete(task.task_id)


def dump_database(tune_keys_dao: TuneKeysDao, target_file: pathlib.Path):
    with open(target_file, "w") as f:
        all_data = list(tune_keys_dao.iterate_all())
        json.dump(all_data, f, cls=CustomJSONEncoder)


def main():
    args = parse_args()
    logging.basicConfig(level=logging.INFO if not args.is_verbose else logging.DEBUG, format="[%(levelname)s]: %(message)s")
    with logging_redirect_tqdm():
        with ExitStack() as exit_stack:
            app_config = get_config(args.config)

            connection_pool = app.create_db_connection(app_config)
            dispatcher = app.create_dispatcher(connection_pool, app_config, exit_stack)

            pending_tasks_dao = PendingTasksDao(connection_pool)
            tune_keys_dao = TuneKeysDao(connection_pool)

            dispatcher.register_task_handler(
                FindKeyTaskResultHandler(
                    pending_tasks_dao=pending_tasks_dao,
                    tune_keys_dao=tune_keys_dao,
                )
            )

            file_dao = FileDao(connection_pool)
            input_files = list([pathlib.Path(f) for f in glob.iglob(f"{args.data_dir}/**/*.*", recursive=True)])

            total_task_count = 0

            for input_file in tqdm(input_files, desc="Importing files"):
                if input_file.is_file():
                    file_id = file_dao.pull_from_disk(input_file)

                    LOGGER.info(f"File imported: {input_file} file_id={file_id}")
                    task_id = dispatcher.post_task(FindTuneKey(source_file_id=file_id, source_format=input_file.suffix))
                    pending_tasks_dao.create_or_update(PendingTask(id=task_id, file_id=file_id, file_name=str(input_file)))

                    total_task_count += 1

            LOGGER.debug("------------")

            progress = tqdm(total=total_task_count)
            previous_value = total_task_count
            while len(pending_tasks_dao.pending_tasks) > 0:
                value = total_task_count - len(pending_tasks_dao.pending_tasks)
                if value != previous_value:
                    progress.update(value)
                    dump_database(tune_keys_dao, args.target_file)
                    previous_value = value
                sleep(1)

            dump_database(tune_keys_dao, args.target_file)
