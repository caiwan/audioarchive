from typing import List
import os
import pathlib


def find_all_files(name: str, path: pathlib.Path) -> List[pathlib.Path]:
    result = []
    for root, dirs, files in os.walk(path):
        if name in files:
            result.append(os.path.join(root, name))
    return result
