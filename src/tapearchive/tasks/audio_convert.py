from contextlib import ExitStack
from typing import Optional
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


class AudioConverterHandler:
    def __init__(self, db_pool, **kwargs) -> None:
        self._lock = threading.Lock()
        self._tasks_finished = []

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

        tmp_files_context = ExitStack()
        tmp_source = tmp_files_context.enter_context(
            self._file_dao.as_tempfile(
                task.source_file_id, suffix=f".{task.source_format}"
            )
        )
        tmp_target = tmp_files_context.enter_context(
            tempfile.NamedTemporaryFile("wb", suffix=f".{task.target_format}")
        )

        target_file = pathlib.Path(tmp_target.name)
        source_file = pathlib.Path(tmp_source.name)
        ffmpeg_commnad = f"ffmpeg -y -i {source_file.absolute()} -filter_complex {';'.join(filter_stack)} -map [out]{bitrate_option} {target_file.absolute()}".split()

        LOGGER.debug(f"FFMPEG command: {' '.join(ffmpeg_commnad)}")

        ffmpeg_process = subprocess.Popen(
            ffmpeg_commnad, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        self._running_processes.append(ffmpeg_process)

        # TODO: Configure sync/async execution
        # Asyncronous execution, create job on top to poll the result then resolve it
        ffmpeg_job = manager.create_child_job(
            job,
            bind_function(AudioConverterHandler._poll_ffmpeg, self),
            ffmpeg_process,
            task,
            target_file,
            tmp_files_context,
            dispatcher=dispatcher,
        )
        manager.schedule_job(ffmpeg_job)
        manager.wait(ffmpeg_job)

    def _poll_ffmpeg(
        self,
        ffmpeg_process: subprocess.Popen,
        task: ConvertAudio,
        target_file_name: pathlib.Path,
        tmp_file_context: ExitStack,
        dispatcher: TaskDispatcher = None,
        job: Job = None,
        manager: JobManager = None,
    ):
        returncode = poll_subprocess(ffmpeg_process)

        if returncode is None:
            manager.create_job(
                bind_function(AudioConverterHandler._poll_ffmpeg, self),
                ffmpeg_process,
                task,
                target_file_name,
                tmp_file_context,
                dispatcher=dispatcher,
            )
            manager.schedule_job(job)
            return
        else:
            if returncode == 0:
                temp_file = tmp_file_context.enter_context(open(target_file_name, "rb"))
                db_file = tmp_file_context.enter_context(
                    self._file_dao.open(f"{uuid4()}.{task.target_format}", "wb")
                )
                db_file.write(temp_file.read())

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
                    ).failed(f"FFMPEG failed with return code {returncode}")
                )

            self._running_processes.remove(ffmpeg_process)
            tmp_file_context.close()

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
                self._tasks_finished.append(task_result)
                LOGGER.debug(
                    f"Audio conversion finished, {len(self._running_processes)} processes running"
                )
