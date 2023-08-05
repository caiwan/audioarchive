from contextlib import ExitStack
from typing import Optional
from dataclasses import dataclass
import pathlib
import threading
import subprocess
import logging
import tempfile
from uuid import UUID

from tq import bind_function

from tq.job_system import JobManager, Job
from tq.task_dispacher import Task, TaskDispatcher, TaskResult, task_handler
from tq.database.gridfs_dao import BucketGridFsDao

from tapearchive.models.catalog import ChannelMode

LOGGER = logging.getLogger(__name__)


@dataclass
class ConvertAudio(Task):
    source_file_id: UUID
    source_format: str
    source_channel: ChannelMode
    target_format: str
    bitrate_kbps: Optional[int]


@dataclass
class AudioConversionDone(TaskResult):
    target_file_id: UUID
    task: ConvertAudio


@dataclass
class AudioConversionError(TaskResult):
    returncode: int
    task: ConvertAudio


class AudioConverterHandler:
    def __init__(self, db_pool, **kwargs) -> None:
        self.lock = threading.Lock()
        self.tasks_finished = []

        self.running_processes = []

        self.file_dao = BucketGridFsDao(db_pool)

        # TODO: Config
        self.max_processes = 16

    @task_handler(ConvertAudio)
    def convert_audio(self, task: ConvertAudio, dispatcher: TaskDispatcher = None, job: Job = None, manager: JobManager = None):
        if len(self.running_processes) > self.max_processes:
            # Put back the taske at the end of the queue
            dispatcher.post_task(task)
            return

        filter_stack = []
        if task.source_channel == ChannelMode.LEFT:
            filter_stack.append("[0:a]channelsplit=channel_layout=stereo:channels=FL[in]")
        elif task.source_channel == ChannelMode.RIGHT:
            filter_stack.append("[0:a]channelsplit=channel_layout=stereo:channels=FR[in]")
        else:
            filter_stack.append("acopy[in]")

        # TODO: Make Normalization process Configurable
        # Apply soft AGC w/ ~10dB gain max
        # https://superuser.com/questions/323119/how-can-i-normalize-audio-using-ffmpeg#323127
        # https://ffmpeg.org/ffmpeg-all.html#dynaudnorm
        filter_stack.append("[in]dynaudnorm=framelen=1000:maxgain=3:coupling=false[out]")

        bitrate_option = f" -b:a {task.bitrate_kbps}k" if task.bitrate_kbps else ""

        tmp_files_context = ExitStack()
        tmp_source = tmp_files_context.enter_context(self.file_dao.as_tempfile(task.source_file_id, suffix=f".{task.source_format}"))
        tmp_target = tmp_files_context.enter_context(tempfile.NamedTemporaryFile("wb", suffix=f".{task.target_format}"))

        target_file = pathlib.Path(tmp_target.name)
        source_file = pathlib.Path(tmp_source.name)
        ffmpeg_commnad = f"ffmpeg -y -i {source_file.absolute()} -filter_complex {';'.join(filter_stack)} -map [out]{bitrate_option} {target_file.absolute()}".split()

        LOGGER.debug(f"FFMPEG command: {' '.join(ffmpeg_commnad)}")

        ffmpeg_process = subprocess.Popen(ffmpeg_commnad, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.running_processes.append(ffmpeg_process)

        # TODO: Configure sync/async execution
        # Asyncronous execution, create job on top to poll the result then resolve it
        ffmpeg_job = manager.create_child_job(job, bind_function(AudioConverterHandler._poll_ffmpeg, self), ffmpeg_process, task, target_file, tmp_files_context, dispatcher=dispatcher)
        manager.schedule_job(ffmpeg_job)
        manager.wait(ffmpeg_job)

    def _poll_ffmpeg(self, ffmpeg_process: subprocess.Popen, task: ConvertAudio, target_file_name: pathlib.Path, tmp_file_context: ExitStack, dispatcher: TaskDispatcher = None, job: Job = None, manager: JobManager = None):
        returncode = ffmpeg_process.poll()
        if returncode is None:
            try:
                stdout_data, stderr_data = ffmpeg_process.communicate(timeout=30)

            except subprocess.TimeoutExpired:
                ffmpeg_process.kill()
                stdout_data, stderr_data = ffmpeg_process.communicate()
                # More specifically?
                returncode = -1

            if stdout_data:
                LOGGER.info(stdout_data.decode("UTF-8"))
            if stderr_data:
                LOGGER.error(stderr_data.decode("UTF-8"))

            if returncode is None:
                manager.create_job(bind_function(AudioConverterHandler._poll_ffmpeg, self), ffmpeg_process, task, target_file_name, tmp_file_context, dispatcher=dispatcher)
                manager.schedule_job(job)
                return

        else:
            # TODO: Remove redundant code
            stdout_data, stderr_data = ffmpeg_process.communicate()
            if stdout_data:
                LOGGER.info(stdout_data.decode("UTF-8"))
            if stderr_data:
                LOGGER.error(stderr_data.decode("UTF-8"))

            # Todo: invoke callback here
            if returncode == 0:
                target_file_id = self.file_dao.pull_from_disk(target_file_name)
                dispatcher.post_task(
                    AudioConversionDone(
                        target_file_id=target_file_id,
                        task=task,
                    )
                )
            else:
                dispatcher.post_task(
                    AudioConversionError(
                        task=task,
                        returncode=returncode,
                    )
                )

            tmp_file_context.close()

    @task_handler(AudioConversionDone)
    def conversion_done(self, task: AudioConversionDone, dispatcher: TaskDispatcher = None, job: Job = None, manager: JobManager = None):
        LOGGER.info(f"Conversion done: {task}")
        with self.lock:
            self.tasks_finished.append(task)

    @task_handler(AudioConversionError)
    def conversion_error(self, task: AudioConversionError, dispatcher: TaskDispatcher = None, job: Job = None, manager: JobManager = None):
        LOGGER.error(f"Failed to convert audio: {task}")
