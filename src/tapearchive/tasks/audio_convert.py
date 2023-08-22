from contextlib import ExitStack
import time
from typing import List, Optional
from dataclasses import dataclass
import pathlib
import threading
import subprocess
import logging
import tempfile
from uuid import UUID, uuid4

from tq import bind_function

from tq.job_system import JobManager, Job
from tq.task_dispacher import Task, TaskDispatcher, TaskResult, task_handler
from tq.database.gridfs_dao import BucketGridFsDao

from tapearchive.models.catalog import ChannelMode
from tapearchive.tasks.utils import poll_subprocess

LOGGER = logging.getLogger(__name__)


@dataclass
class ConvertAudio(Task):
    source_file_id: str
    source_format: str
    source_channel: ChannelMode
    target_format: str
    bitrate_kbps: Optional[int]


@dataclass
class ConvertAudioResult(TaskResult):
    target_file_id: Optional[str] = None


@dataclass
class SliceAudio(Task):
    source_file_id: str
    file_format: str = "mp3"
    segment_length: int = 15


@dataclass
class SliceAudioResult(TaskResult):
    target_file_ids: Optional[List[str]] = None


@dataclass
class AppendAlbumArt(Task):
    source_file_id: str
    album_art_file_id: str


@dataclass
class AppendAlbumArtResult(TaskResult):
    target_file_id: Optional[str] = None


class AudioConverterHandler:
    def __init__(self, db_pool, **kwargs) -> None:
        self._lock = threading.Lock()

        self._running_processes = []

        self._file_dao = BucketGridFsDao(db_pool)

        # TODO: Config
        self._max_processes = 16

    @task_handler(ConvertAudio)
    def convert_audio(
        self,
        task: ConvertAudio,
        dispatcher: TaskDispatcher = None,
        job: Job = None,
        manager: JobManager = None,
    ):
        if len(self._running_processes) > self._max_processes:
            # Put back the taske at the end of the queue
            dispatcher.post_task(task)
            return

        filter_stack = []
        if task.source_channel == ChannelMode.LEFT:
            filter_stack.append(
                "[0:a]channelsplit=channel_layout=stereo:channels=FL[in]"
            )
        elif task.source_channel == ChannelMode.RIGHT:
            filter_stack.append(
                "[0:a]channelsplit=channel_layout=stereo:channels=FR[in]"
            )
        else:
            filter_stack.append("acopy[in]")

        # TODO: Make Normalization process Configurable
        # Apply soft AGC w/ ~10dB gain max
        # https://superuser.com/questions/323119/how-can-i-normalize-audio-using-ffmpeg#323127
        # https://ffmpeg.org/ffmpeg-all.html#dynaudnorm
        filter_stack.append(
            "[in]dynaudnorm=framelen=1000:maxgain=3:coupling=false[out]"
        )

        bitrate_option = f" -b:a {task.bitrate_kbps}k" if task.bitrate_kbps else ""

        context = ExitStack()

        target_file = pathlib.Path(
            context.enter_context(
                tempfile.NamedTemporaryFile("wb", suffix=f".{task.target_format}")
            ).name
        )

        source_file = pathlib.Path(
            context.enter_context(
                self._file_dao.as_tempfile(
                    task.source_file_id, suffix=f".{task.source_format}"
                )
            ).name
        )

        ffmpeg_commnad = f"ffmpeg -y -i {source_file.absolute()} -filter_complex {';'.join(filter_stack)} -map [out]{bitrate_option} {target_file.absolute()}".split()

        LOGGER.debug(f"FFMPEG command: {' '.join(ffmpeg_commnad)}")

        ffmpeg_process = subprocess.Popen(
            ffmpeg_commnad, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        self._running_processes.append(ffmpeg_process)

        ffmpeg_job = manager.create_child_job(
            job,
            bind_function(AudioConverterHandler._poll_ffmpeg, self),
            ffmpeg_process,
        )
        manager.schedule_job(ffmpeg_job)
        manager.wait(ffmpeg_job)

        LOGGER.debug(
            f"FFMPEG {ffmpeg_process.pid} finished, return code: {ffmpeg_job.result}"
        )

        if ffmpeg_job.result == 0:
            target_temp_file = context.enter_context(open(target_file, "rb"))
            db_file = context.enter_context(
                self._file_dao.open(f"{uuid4()}.{task.target_format}", "wb")
            )
            db_file.write(target_temp_file.read())

            dispatcher.post_task(
                ConvertAudioResult(
                    task=task,
                    target_file_id=str(db_file._id),
                )
            )

        else:
            dispatcher.post_task(
                ConvertAudioResult(
                    task=task,
                ).failed(f"FFMPEG failed with return code {ffmpeg_job.result}")
            )

        self._running_processes.remove(ffmpeg_process)
        context.close()

    @task_handler(ConvertAudioResult)
    def convert_audio_result(
        self,
        task_result: ConvertAudioResult,
        *args,
        **kwargs,
    ):
        with self._lock:
            if task_result.is_failed:
                LOGGER.error(f"Audio conversion failed: {task_result.failure_reason}")
            else:
                LOGGER.debug(
                    f"Audio conversion finished, {len(self._running_processes)} processes running"
                )

    @task_handler(SliceAudio)
    def slice_audio(
        self,
        task: SliceAudio,
        dispatcher: TaskDispatcher = None,
        job: Job = None,
        manager: JobManager = None,
    ):
        if len(self._running_processes) > self._max_processes:
            # Put back the taske at the end of the queue
            dispatcher.post_task(task)
            return

        context = ExitStack()

        tmp_source = pathlib.Path(
            context.enter_context(self._file_dao.as_tempfile(task.source_file_id)).name
        )
        tmp_target = pathlib.Path(context.enter_context(tempfile.TemporaryDirectory()))

        ffmpeg_command = f"ffmpeg -y -i {tmp_source} -f segment -segment_time {task.segment_length} -c copy {tmp_target}/output_%03d.{task.file_format}".split()

        LOGGER.debug(f"FFMPEG command: {' '.join(ffmpeg_command)}")

        ffmpeg_process = subprocess.Popen(
            ffmpeg_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )

        self._running_processes.append(ffmpeg_process)

        ffmpeg_job = manager.create_child_job(
            job,
            bind_function(AudioConverterHandler._poll_ffmpeg, self),
            ffmpeg_process,
        )
        manager.schedule_job(ffmpeg_job)
        manager.wait(ffmpeg_job)

        LOGGER.debug(
            f"FFMPEG {ffmpeg_process.pid} finished, return code: {ffmpeg_job.result}"
        )

        if ffmpeg_job.result == 0:
            target_files = []
            for file_path in tmp_target.iterdir():
                file_copy_context = ExitStack()

                file = file_copy_context.enter_context(open(file_path, "rb"))

                db_file = file_copy_context.enter_context(
                    self._file_dao.open(f"{uuid4()}.mp3", "wb")
                )
                db_file.write(file.read())
                target_files.append(str(db_file._id))

                file_copy_context.close()

            LOGGER.debug(f"Created {len(target_files)} files")

            dispatcher.post_task(
                SliceAudioResult(
                    task=task,
                    target_file_ids=target_files,
                )
            )
        else:
            dispatcher.post_task(
                ConvertAudioResult(
                    task=task,
                ).failed(f"FFMPEG failed with return code {ffmpeg_job.result}")
            )

        self._running_processes.remove(ffmpeg_process)

        context.close()

    @task_handler(SliceAudioResult)
    def slice_audio_result(
        self,
        task_result: SliceAudioResult,
        *args,
        **kwargs,
    ):
        with self._lock:
            if task_result.is_failed:
                LOGGER.error(f"Audio slicing failed: {task_result.failure_reason}")
            else:
                LOGGER.debug(
                    f"Audio slicing finished, {len(self._running_processes)} processes running"
                )

    @task_handler(AppendAlbumArt)
    def append_album_art(
        self,
        task: AppendAlbumArt,
        dispatcher: TaskDispatcher = None,
        job: Job = None,
        manager: JobManager = None,
    ):
        if len(self._running_processes) > self._max_processes:
            # Put back the taske at the end of the queue
            dispatcher.post_task(task)
            return
        
        context = ExitStack()

        # ... 
        # ffmpeg -i input.mp3 -i album_art.jpg -c:a copy -c:v copy -map 0 -map 1 -metadata:s:v title="Album cover" -metadata:s:v comment="Cover (Front)" output.mp3

        context.close()

    @task_handler(AppendAlbumArtResult)
    def append_album_art_result(
        self,
        task_result: AppendAlbumArtResult,
        *args,
        **kwargs,
    ):
        with self._lock:
            if task_result.is_failed:
                LOGGER.error(f"Audio slicing failed: {task_result.failure_reason}")
            else:
                LOGGER.debug(
                    f"Audio slicing finished, {len(self._running_processes)} processes running"
                )

    def _poll_ffmpeg(self, ffmpeg_process: subprocess.Popen, *args, **kwargs):
        returncode = None

        while returncode is None:
            returncode = poll_subprocess(ffmpeg_process, timeout=1, logger=LOGGER)
            LOGGER.debug(f"FFMPEG {ffmpeg_process.pid} return code: {returncode}")
        return returncode
