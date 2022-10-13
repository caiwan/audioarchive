from typing import Optional
from dataclasses import dataclass
from dataclasses_json import DataClassJsonMixin
from uuid import UUID, uuid4
import pathlib


@dataclass
class DBConfig(DataClassJsonMixin):
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    username: Optional[str] = None
    password: Optional[str] = None


@dataclass
class AppConfig(DataClassJsonMixin):
    db: DBConfig
    is_manager: bool = True
    is_gui_enabled: bool = True
    is_worker: bool = True
    max_threads: int = 0
    task_queue_uuid: UUID = uuid4()
    data_directory: pathlib.Path = pathlib.Path("/data")


# TODO Flask config?
