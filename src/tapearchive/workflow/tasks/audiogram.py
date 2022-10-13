from typing import List, Optional
from dataclasses import dataclass
from uuid import UUID
import pathlib
import tempfile

import librosa
import numpy as np
import matplotlib.pyplot as plt

from tq.job_system import JobManager, Job
from tq.task_dispacher import Task, TaskDispatcher, TaskResult, task_handler


@dataclass
class AudiogramSettings:
    block_length: int = 128
    frame_length: int = 4096
    fft_length: int = 512
    image_resolution: int = 64
    hop_length: Optional[int] = None
    duration: Optional[int] = None


@dataclass
class CreateSpectorgram(Task):
    id: UUID
    filename: pathlib.Path
    settings: AudiogramSettings


@dataclass
class CreateSpectorgramResult(TaskResult):
    spectogram_ids: List[UUID]


# class AudiogramHandler:
#     def gen_audio_blocks(infile: pathlib.Path, settings: AudiogramSettings = AudiogramSettings()) -> np.array:
#         hop_length = settings.hop_length if settings.hop_length else settings.frame_length
#         for block in librosa.stream(infile, block_length=settings.block_length, frame_length=settings.frame_length, hop_length=hop_length, duration=settings.duration):
#             yield block

#     def gen_spectral_data(block: np.array, settings: AudiogramSettings = AudiogramSettings()) -> np.ndarray:
#         hop_length = settings.hop_length if settings.hop_length else settings.frame_length
#         return librosa.amplitude_to_db(np.abs(librosa.stft(block, n_fft=settings.fft_length, hop_length=hop_length)), ref=np.max)

#     def gen_spectorgram_image(spectrum_data: np.ndarray, sample_rate: float, audio_length: float, settings: AudiogramSettings = AudiogramSettings()) -> bytearray:
#         # This is not the most optimal way to store, It would rather more optimal if the raw data would be nicely interpolated and carried out instead of png mafgic.
#         fig, spectorgram = plt.subplots(figsize=(0.1 * settings.image_resolution, 0.1 * settings.image_resolution), dpi=100, sharex=True)
#         librosa.display.specshow(spectrum_data, sr=sample_rate / 8, ax=spectorgram, y_axis="log", x_axis="time")
#         spectorgram.set(xlim=(0, audio_length))

#         spectorgram.set_axis_off()
#         fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
#         with tempfile.NamedTemporaryFile("wb", suffix=".png") as tmp:
#             fig.savefig(tmp, bbox_inches="tight", pad_inches=0, dpi=10, format="png")
#             tmp.seek(0)
#             return bytearray(tmp.read())

    @task_handler(CreateSpectorgram)
    def create_spectorgram(self, task: CreateSpectorgram, dispatcher: TaskDispatcher = None, job: Job = None, manager: JobManager = None):
        sample_rate = librosa.get_samplerate(task.filename)
        for block in self.gen_audio_blocks(task.filename, settings=task.settings):
            # create task here
            spectrum_data = self.gen_spectral_data(block, settings=task.settings)
            # ceate child task here
            spectrum_image = self.gen_spectorgram_image(spectrum_data, sample_rate, block.size / sample_rate, settings=task.settings)
            # save everything to db
            # ...
            # raise finished signal
            # ... 
            pass
