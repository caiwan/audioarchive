import logging
from typing import Optional
from dataclasses import dataclass, field
from dataclasses_json import DataClassJsonMixin
from dataclasses_json import config # as dc_config
from uuid import UUID, uuid4
import pathlib
import marshmallow

import yaml

LOGGER = logging.getLogger(__name__)


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
    redis: RedisDBConfig = field(default_factory=RedisDBConfig)
    mongo: MongoDBConfig = field(default_factory=MongoDBConfig)
    is_manager: bool = True
    is_gui_enabled: bool = True
    is_worker: bool = True
    max_threads: int = 0
    task_queue_uuid: UUID = field(
        metadata=config(
            encoder=lambda x: str(x),
            decoder=lambda x: UUID(x),
            mm_field=marshmallow.fields.String(),
        ),
        default_factory=uuid4
    )
    
    data_directory: pathlib.Path = field(
        metadata=config(
            encoder=lambda x: str(x),
            decoder=lambda x: pathlib.Path(x),
            mm_field=marshmallow.fields.String(),
        ),
        default_factory=lambda: pathlib.Path("/data")
    )


# TODO Flask config?
def get_config(filename: str) -> AppConfig:
    config_file = pathlib.Path(filename)
    if not config_file.exists():
        new_config = AppConfig()
        with config_file.open("w") as f:
            yaml.dump(new_config.to_dict(), f)

        raise FileNotFoundError(f"Config file {filename} not found. Created default config file. Please edit it and restart.")

    with config_file.open("r") as f:
        return AppConfig.schema().load(yaml.safe_load(f))
    # TODO: Default
