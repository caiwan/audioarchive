import os
import pathlib


from tq.task_dispacher import TaskDispatcher, TaskResult
from tq.database.gridfs_dao import BucketGridFsDao

from tapearchive.tasks.audio_convert import ConvertAudio, ConvertAudioResult
from tapearchive.models.catalog import ChannelMode


import pytest
from unittest.mock import Mock
from waiting import wait

MAX_TIMEOUT = 30


@pytest.fixture()
def sample_audio_file(mongodb_client):
    file_dao = BucketGridFsDao(mongodb_client)

    with (pathlib.Path(__file__).parent.absolute() / "data" / "wav_868kb.wav").open("rb") as file:
        return file_dao.store("wav_868kb.wav", file.read())


def test_audio_convert_stereo(mongodb_client, worker_app, task_dispatcher: TaskDispatcher, sample_audio_file):
    convert_done_callback = Mock()
    task_dispatcher.register_task_handler_callback(ConvertAudioResult, convert_done_callback)

    task_dispatcher.post_task(
        ConvertAudio(
            source_file_id=sample_audio_file,
            source_format="wav",
            source_channel=ChannelMode.STEREO,
            target_format="mp3",
            bitrate_kbps=320,
        )
    )

    wait(lambda: convert_done_callback.called, sleep_seconds=0.1, timeout_seconds=MAX_TIMEOUT)

    task_done: ConvertAudioResult = convert_done_callback.call_args.args[0]
    assert task_done is not None and not task_done.is_failed
    assert task_done.target_file_id

    file_dao = BucketGridFsDao(mongodb_client)
    with file_dao.as_tempfile(task_done.target_file_id) as file:
        assert os.path.getsize(pathlib.Path(file.name)) > 0


def test_audio_convert_split_mono(mongodb_client, worker_app, task_dispatcher: TaskDispatcher, sample_audio_file):

    convert_done_callback = Mock()
    task_dispatcher.register_task_handler_callback(ConvertAudioResult, convert_done_callback)

    for ch in [ChannelMode.LEFT, ChannelMode.RIGHT]:
        task_dispatcher.post_task(
            ConvertAudio(
                source_file_id=sample_audio_file,
                source_format="wav",
                source_channel=ch,
                target_format="mp3",
                bitrate_kbps=320,
            )
        )

    wait(lambda: convert_done_callback.call_count == 2, sleep_seconds=0.1, timeout_seconds=MAX_TIMEOUT)

    for arg in convert_done_callback.call_args.args:
        task_done: ConvertAudioResult = arg
        assert task_done is not None and not task_done.is_failed
        assert task_done.target_file_id

        file_dao = BucketGridFsDao(mongodb_client)
        with file_dao.as_tempfile(task_done.target_file_id) as file:
            assert os.path.getsize(pathlib.Path(file.name)) > 0
