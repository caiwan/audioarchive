from asyncio.log import logger
from dataclasses import dataclass
import imp
import pathlib
from typing import Dict, Optional, Tuple
from uuid import UUID
import numpy as np
import librosa
from tapearchive.models.raw_data import FileDao
from tq.job_system import LOGGER, Job, JobManager

from tq.task_dispacher import Task, TaskDispatcher, TaskResult, task_handler

# class that uses the librosa library to analyze the key that an mp3 is in
# arguments:
#     waveform: an mp3 file loaded by librosa, ideally separated out from any percussive sources
#     sr: sampling rate of the mp3, which can be obtained when the file is read with librosa
#     tstart and tend: the range in seconds of the file to be analyzed; default to the beginning and end of file if not specified
class TonalFragment(object):
    def __init__(self, waveform, sr, tstart=None, tend=None):
        self.waveform = waveform
        self.sr = sr
        self.tstart = tstart
        self.tend = tend

    def calculate(self):
        if self.tstart is not None:
            self.tstart = librosa.time_to_samples(self.tstart, sr=self.sr)
        if self.tend is not None:
            self.tend = librosa.time_to_samples(self.tend, sr=self.sr)
        self.y_segment = self.waveform[self.tstart : self.tend]
        self.chromograph = librosa.feature.chroma_cqt(y=self.y_segment, sr=self.sr, bins_per_octave=24)

        # chroma_vals is the amount of each pitch class present in this time interval
        self.chroma_vals = []
        for i in range(12):
            self.chroma_vals.append(np.sum(self.chromograph[i]))
        pitches = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
        # dictionary relating pitch names to the associated intensity in the song
        self.keyfreqs = {pitches[i]: self.chroma_vals[i] for i in range(12)}

        keys = [pitches[i] + " major" for i in range(12)] + [pitches[i] + " minor" for i in range(12)]

        # use of the Krumhansl-Schmuckler key-finding algorithm, which compares the chroma
        # data above to typical profiles of major and minor keys:
        maj_profile = [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88]
        min_profile = [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17]

        # finds correlations between the amount of each pitch class in the time interval and the above profiles,
        # starting on each of the 12 pitches. then creates dict of the musical keys (major/minor) to the correlation
        self.min_key_corrs = []
        self.maj_key_corrs = []
        for i in range(12):
            key_test = [self.keyfreqs.get(pitches[(i + m) % 12]) for m in range(12)]
            # correlation coefficients (strengths of correlation for each key)
            self.maj_key_corrs.append(round(np.corrcoef(maj_profile, key_test)[1, 0], 3))
            self.min_key_corrs.append(round(np.corrcoef(min_profile, key_test)[1, 0], 3))

        # names of all major and minor keys
        self.key_dict = {**{keys[i]: self.maj_key_corrs[i] for i in range(12)}, **{keys[i + 12]: self.min_key_corrs[i] for i in range(12)}}

        # this attribute represents the key determined by the algorithm
        self.key = max(self.key_dict, key=self.key_dict.get)
        self.bestcorr = max(self.key_dict.values())

        # this attribute represents the second-best key determined by the algorithm,
        # if the correlation is close to that of the actual key determined
        self.altkey = None
        self.altbestcorr = None

        for key, corr in self.key_dict.items():
            if corr > self.bestcorr * 0.9 and corr != self.bestcorr:
                self.altkey = key
                self.altbestcorr = corr

    @property
    def chroma_map(self):
        self.chroma_max = max(self.chroma_vals)
        return dict([(key, chrom / self.chroma_max) for key, chrom in self.keyfreqs.items()])

    @property
    def likely_key(self) -> Tuple[str, float]:
        return max(self.key_dict, key=self.key_dict.get), self.bestcorr

    @property
    def second_likely_key(self) -> Optional[Tuple[str, float]]:
        if self.altkey is not None:
            return self.altkey, self.altbestcorr
        return None


@dataclass
class FindTuneKey(Task):
    source_file_id: UUID
    source_format: str


@dataclass
class FindKeyDone(TaskResult):
    chroma_map: Dict[str, float]
    most_likely_key: Tuple[str, float]
    second_most_likely_key: Optional[Tuple[str, float]]


@dataclass
class FindKeyFailed(TaskResult):
    error: str


class FindKeyHandler:
    def __init__(self, db_pool, **kwargs) -> None:
        self.file_dao = FileDao(db_pool)

    @task_handler(FindTuneKey)
    def find_key(self, task: FindTuneKey, dispatcher: TaskDispatcher = None, job: Job = None, manager: JobManager = None):
        try:
            with self.file_dao.as_tempfile(task.source_file_id, suffix=task.source_format) as tmpfile:
                input_file = pathlib.Path(tmpfile.name)

                # -- Job 1
                y, sr = librosa.load(
                    input_file,
                )

                LOGGER.debug(f"Audio data={len(y)} samples")

                y_harmonic, y_percussive = librosa.effects.hpss(y)

                # TODO: Find bpm for song as well?

                # -- Job 2
                tf = TonalFragment(y_harmonic, sr)
                tf.calculate()

                # -- Result
                dispatcher.post_task(
                    FindKeyDone(
                        task=task,
                        chroma_map=tf.chroma_map,
                        most_likely_key=tf.likely_key,
                        second_most_likely_key=tf.second_likely_key,
                    )
                )
        except Exception as e:
            logger.error("Error", exc_info=e)
            dispatcher.post_task(
                FindKeyFailed(
                    task=task,
                    error="Failed to find key",
                )
            )
