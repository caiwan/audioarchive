import pathlib
import random
import tempfile

from tapearchive.models.raw_data import FileDao

import pytest
import filecmp
import os



@pytest.fixture()
def generate_random_file(size=3 * 1024**2) -> pathlib.Path:
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(random.randbytes(size))
        tmp_file = pathlib.Path(tmp.name)
        yield tmp_file
        tmp_file.unlink()


def test_file_dao(db_pool, generate_random_file):
    testfile = generate_random_file
    dao = FileDao(db_pool)

    file_id = dao.pull_from_disk(testfile)

    assert file_id is not None

    with tempfile.NamedTemporaryFile() as read_tmp:
        testfile_read = pathlib.Path(read_tmp.name)
        assert dao.push_to_disk(file_id, testfile_read)

        assert os.path.getsize(testfile_read) == 3 * 1024**2
        assert filecmp.cmp(testfile_read, testfile) == 0


def test_file_delete(db_pool, generate_random_file):
    testfile = generate_random_file
    dao = FileDao(db_pool)

    file_id = dao.pull_from_disk(testfile)

    assert file_id is not None

    assert dao.delete_file(file_id)

    with tempfile.NamedTemporaryFile() as read_tmp:
        assert not dao.push_to_disk(file_id, pathlib.Path(read_tmp.name))


def test_file_delete_then_cleanup_orpaned_chunks(db_pool, generate_random_file):
    testfile = generate_random_file
    dao = FileDao(db_pool)

    file_id = dao.pull_from_disk(testfile)

    assert file_id is not None

    assert dao.delete_file(file_id)

    with tempfile.NamedTemporaryFile() as read_tmp:
        assert not dao.push_to_disk(file_id, pathlib.Path(read_tmp.name))

    assert dao.find_orphans()
    assert dao.cleanup_orphans() > 0
    assert not dao.find_orphans()
