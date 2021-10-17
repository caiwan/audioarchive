from types import List, Optional
import enum
from pathlib import Path

from dataclasses import dataclass
from dataclasses_json import DataClassJsonMixin


@enum.unique
class AttachmentType(enum.Enum):
    AUDIO_FILE = "audio"
    COVER = "cover"
    DOCUMENT = "document"
    AUDIOGRAM = "audiogram"


@enum.unique
class ChannelMode(enum.Enum):
    LEFT = "A"
    RIGHT = "B"
    STEREO = "AB"


@dataclass
class Attachment(DataClassJsonMixin):
    type: AttachmentType
    path: Path
    name: str
    meta: Optional[dict[str, str]]


@dataclass
class Group(DataClassJsonMixin):
    name: str


@dataclass
class Catalog(DataClassJsonMixin):
    id: str
    groups: List[Group]


@dataclass
class Session(DataClassJsonMixin):
    audio_sources: List[Attachment]
    channel_mode: ChannelMode


@dataclass
class Recording(DataClassJsonMixin):
    catalog: Catalog
    attachments: List[Attachment]
    sessions: List[Session]
