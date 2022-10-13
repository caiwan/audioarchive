import enum
from typing import Optional, List, Dict
from dataclasses import dataclass
from uuid import UUID

from dataclasses_json import DataClassJsonMixin

from tq.database import BaseDao, BaseEntity, DaoContext, transactional


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

    def _catalog_ctx(self, ctx: DaoContext) -> DaoContext:
        return DaoContext(ctx.db, "catalog_numbers")

    @transactional
    def create_or_update(self, ctx: DaoContext, obj: CatalogEntry) -> UUID:
        # TODO: add catalog number -> id [name := catalog number]
        return ctx.create_or_update(obj.to_dict(), obj.id)

    @transactional
    def get_ids_by_catalog_name(self, ctx: DaoContext, catalog_name:str) -> List[UUID]:
        # catalog_ctx = self._catalog_ctx(ctx)
        # catalog_ctx.list_push()
        return []

    @transactional
    def get_entries_by_cat_number(self, ctx: DaoContext, catalog_name:str) -> List[CatalogEntry]:
        return []

    @transactional
    def delete(self, ctx: DaoContext, id: UUID):
        # TODO: Remove catalog name
        return ctx.delete(id)