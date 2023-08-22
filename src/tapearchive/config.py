from typing import Optional
from dataclasses import dataclass
from dataclasses_json import DataClassJsonMixin
from uuid import UUID, uuid4
import pathlib


@dataclass
class RedisDBConfig(DataClassJsonMixin):
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    username: Optional[str] = None
    password: Optional[str] = None


@dataclass
class MongoDBConfig(DataClassJsonMixin):
    url: str = "mongodb://localhost:27017"


@dataclass
class AppConfig(DataClassJsonMixin):
    redis: RedisDBConfig
    mongo: MongoDBConfig
    is_manager: bool = True
    is_gui_enabled: bool = True
    is_worker: bool = True
    max_threads: int = 0
    task_queue_uuid: UUID = uuid4()
    data_directory: pathlib.Path = pathlib.Path("/data")


# TODO Flask config?
