import enum
from typing import Optional, List, Dict, Iterator
from uuid import UUID
from dataclasses import dataclass

from tq.database import BaseDao, BaseEntity


@enum.unique
class AttachmentType(str, enum.Enum):
    AUDIO_FILE = "audio"
    COVER = "cover"
    DOCUMENT = "document"
    AUDIOGRAM = "audiogram"


@enum.unique
class ChannelMode(enum.Enum):
    LEFT = "left"
    RIGHT = "right"
    STEREO = "stereo"


@dataclass
class Attachment(BaseEntity):
    type: AttachmentType
    path: str
    name: str
    meta: Optional[Dict[str, str]]


@dataclass
class AudioAttachment(Attachment):
    format: str  # mp3 | flac | etc


@dataclass
class Group(BaseEntity):
    name: str


@dataclass
class RecordingEntry(BaseEntity):
    name: str
    source_channel_mode: ChannelMode
    description: Optional[str]
    audio_files: Optional[List[AudioAttachment]]
    audio_sources: Optional[List[AudioAttachment]]
    meta: Optional[Dict[str, str]]


@dataclass
class CatalogEntry(BaseEntity):
    name: str
    recordings: List[RecordingEntry]
    groups: Optional[List[Group]]
    attachments: Optional[List[Attachment]]
    description: Optional[str]
    meta: Optional[Dict[str, str]]


class CatalogDao(BaseDao):
    def __init__(self, db_pool):
        super().__init__(db_pool, CatalogEntry.schema(), key_prefix="catalog")

