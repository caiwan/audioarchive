from dataclasses import dataclass
import more_itertools
from typing import Optional
from uuid import UUID
from tapearchive.models.catalog import AudioAttachment, CatalogDao, CatalogEntry, ChannelMode, RecordingEntry
from tapearchive.models.raw_data import FileDao
from tapearchive.tasks.audio_convert import ConvertAudio
from tapearchive.workflow.base_workflow import AbstractFlowStep
from tq.database import BaseEntity
from tq.task_dispacher import TaskDispatcher


@dataclass
class AudioSource(BaseEntity):
    catalog_id: UUID
    recording_id: UUID
    file_id: UUID


class AudioConversionStep(AbstractFlowStep):
    def __init__(self, name: str, timeout: int = 0) -> None:
        super().__init__(name, timeout)

    @staticmethod
    def _find_recording(catalog_id: UUID, recording_id: UUID, catalog_dao: CatalogDao = None) -> Optional[RecordingEntry]:
        catalog_entry: CatalogEntry = catalog_dao.get_entity(catalog_id)
        # TODO: AttachmentType.AUDIO
        return more_itertools.first_true(catalog_entry.recordings, pred=lambda r: r.id == recording_id) if catalog_entry else None

    def _find_target_filename(catalog_id: UUID, recording_id: UUID, catalog_dao: CatalogDao = None) -> Optional[str]:
        pass

    def create_task(
        self,
        catalog_id: UUID,
        recording_id: UUID,
        *args,
        task_dispatcher: TaskDispatcher = None,
        catalog_dao: CatalogDao = None,
        file_dao: FileDao = None,
        **kwargs,
    ) -> Optional[UUID]:
        if not task_dispatcher or not catalog_dao or not file_dao:
            raise ValueError("not task_dispatcher or not catalog_dao or not file_dao")

        recording: RecordingEntry = AudioConversionStep._find_recording(catalog_id, recording_id, catalog_dao)
        if not recording:
            # TODO: Log
            return None

        # Find file in DB
        # If not Upload source file
        if not recording.audio_sources:
            # TODO Log
            return None

        # TODO: If muliple source files are ther -> theread them as one stream
        # (Conversion task is not ready for this scenario yet)

        # TODO: AttachmentType.AUDIO
        source: AudioAttachment = more_itertools.first(recording.audio_sources)
        # TODO: Add data root
        source.path

        # Create task

        return task_dispatcher.post_task(
            ConvertAudio(
                source_file_id=source_id,
                # TDO: Fill form recording 
                source_format="wav",
                source_channel=ChannelMode.STEREO,
                target_format="mp3",

                # TODO: fill form configs 
                bitrate_kbps=320,
            )
        )

    def verify_done(
        self,
        catalog_id: UUID,
        recording_id: UUID,
        *args,
        task_dispatcher: TaskDispatcher = None,
        catalog_dao: CatalogDao = None,
        **kwargs,
    ) -> bool:
        if not task_dispatcher or not catalog_dao:
            raise ValueError("not task_dispatcher or not catalog_dao")
        pass
