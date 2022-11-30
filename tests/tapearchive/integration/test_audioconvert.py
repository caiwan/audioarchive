import os
import pathlib


from tq.task_dispacher import TaskDispatcher
from tapearchive.tasks.audio_convert import ConvertAudio, AudioConversionDone
from tapearchive.models.catalog import ChannelMode
from tapearchive.models.raw_data import FileDao

import pytest
from unittest.mock import Mock
from waiting import wait

MAX_TIMEOUT = 30


@pytest.fixture()
def sample_audio_file(db_pool):
    file_dao = FileDao(db_pool)
    return file_dao.pull_from_disk(pathlib.Path(__file__).parent.absolute() / "data" / "wav_868kb.wav")


@pytest.mark.slow
def test_audio_convert_stereo(db_pool, worker_app, task_dispatcher: TaskDispatcher, sample_audio_file):

    convert_done_callback = Mock()
    task_dispatcher.register_task_handler_callback(AudioConversionDone, convert_done_callback)

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

    task_done: AudioConversionDone = convert_done_callback.call_args.args[0]
    assert task_done
    assert task_done.target_file_id

    file_dao = FileDao(db_pool)
    with file_dao.as_tempfile(task_done.target_file_id) as file:
        assert os.path.getsize(pathlib.Path(file.name)) > 0


MAX_TIMEOUT


@pytest.mark.slow
def test_audio_convert_split_mono(db_pool, worker_app, task_dispatcher: TaskDispatcher, sample_audio_file):

    convert_done_callback = Mock()
    task_dispatcher.register_task_handler_callback(AudioConversionDone, convert_done_callback)

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
        task_done: AudioConversionDone = arg
        assert task_done
        assert task_done.target_file_id

        file_dao = FileDao(db_pool)
        with file_dao.as_tempfile(task_done.target_file_id) as file:
            assert os.path.getsize(pathlib.Path(file.name)) > 0
