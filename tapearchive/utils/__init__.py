from typing import List
import os
import pathlib
import yaml
from tapearchive.config import AppConfig


def find_all_files(name: str, path: pathlib.Path) -> List[pathlib.Path]:
    result = []
    for root, dirs, files in os.walk(path):
        if name in files:
            result.append(os.path.join(root, name))
    return result


def get_config(filename: str) -> AppConfig:
    with open(filename) as f:
        return AppConfig.schema().load(yaml.safe_load(f))
    # TODO: Default
