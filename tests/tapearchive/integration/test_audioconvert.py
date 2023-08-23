import os
import pathlib


from tq.task_dispacher import TaskDispatcher, TaskResult
from tq.database.gridfs_dao import BucketGridFsDao

from tapearchive.tasks.audio_convert import ConvertAudio, ConvertAudioResult, SliceAudio, SliceAudioResult
from tapearchive.models.catalog import ChannelMode


import pytest
from unittest.mock import Mock
from waiting import wait

MAX_TIMEOUT = 10


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

    result: ConvertAudioResult = convert_done_callback.call_args.args[0]
    assert result is not None and not result.is_failed
    assert result.target_file_id

    file_dao = BucketGridFsDao(mongodb_client)
    with file_dao.as_tempfile(result.target_file_id) as file:
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
        result: ConvertAudioResult = arg
        assert result is not None and not result.is_failed
        assert result.target_file_id

        file_dao = BucketGridFsDao(mongodb_client)
        with file_dao.as_tempfile(result.target_file_id) as file:
            assert os.path.getsize(pathlib.Path(file.name)) > 0


def test_audio_slicing(mongodb_client, worker_app, task_dispatcher: TaskDispatcher, sample_audio_file):
    convert_done_callback = Mock()
    task_dispatcher.register_task_handler_callback(SliceAudioResult, convert_done_callback)

    task_dispatcher.post_task(
        SliceAudio(
            source_file_id=sample_audio_file,
            segment_length=1,
            file_format="wav",
        )
    )

    wait(lambda: convert_done_callback.call_count == 1, sleep_seconds=0.1, timeout_seconds=MAX_TIMEOUT)

    for arg in convert_done_callback.call_args.args:
        result: SliceAudioResult = arg
        assert result is not None and not result.is_failed
        assert result.target_file_ids

        for file_id in result.target_file_ids:
            file_dao = BucketGridFsDao(mongodb_client)
            with file_dao.as_tempfile(file_id) as file:
                assert os.path.getsize(pathlib.Path(file.name)) > 0

