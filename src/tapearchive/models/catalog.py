from collections import defaultdict
import enum
import pathlib
from typing import Iterator, Optional, List, Dict, Tuple
from dataclasses import dataclass, field
from uuid import UUID
import bson
from dataclasses_json import config, DataClassJsonMixin
from marshmallow import fields

from marshmallow_dataclass import class_schema


from tq.database.db import transactional, BaseEntity
from tq.database.mongo_dao import BaseMongoDao, MongoDaoContext


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
    name: str
    type: AttachmentType = field(
        metadata=config(
            encoder=lambda x: x.value,
            decoder=lambda x: AttachmentType(x),
            mm_field=fields.Enum(AttachmentType),
        )
    )

    path: str = ""
    meta: Optional[Dict[str, str]] = field(default_factory=defaultdict(str))


@dataclass
class AudioAttachment(Attachment):
    format: Optional[str] = None  # mp3 | flac | etc


@dataclass
class Group(BaseEntity):
    name: Optional[str] = None


@dataclass
class RecordingEntry(BaseEntity):
    name: str
    source_channel_mode: ChannelMode = field(
        metadata=config(
            encoder=lambda x: x.value,
            decoder=lambda x: ChannelMode(x),
            mm_field=fields.Enum(ChannelMode),
        )
    )
    description: Optional[str] = None
    audio_files: Optional[List[AudioAttachment]] = None
    audio_sources: Optional[List[AudioAttachment]] = None
    meta: Optional[Dict[str, str]] = None


@dataclass
class CatalogEntry(BaseEntity):
    name: str
    recordings: List[RecordingEntry]
    groups: Optional[List[Group]] = None
    attachments: Optional[List[Attachment]] = None
    description: Optional[str] = None
    meta: Optional[Dict[str, str]] = None


# ---


class CatalogDao(BaseMongoDao):
    def __init__(self, db_pool):
        super().__init__(db_pool, CatalogEntry, key_prefix="catalog")

    @transactional
    def get_id_by_catalog_name(
        self, catalog_name: str, ctx: MongoDaoContext
    ) -> Iterator[UUID]:
        item = ctx.collection.find_one({"name": catalog_name}, {"_id": 1})
        if item is not None:
            yield bson.Binary.as_uuid(item["_id"])

    @transactional
    def get_entry_by_cat_number(
        self, catalog_name: str, ctx: MongoDaoContext
    ) -> CatalogEntry:
        item = ctx.collection.find_one({"name": catalog_name})
        if item is not None:
            item = ctx.desanitize(item)
            return self.schema.from_dict(item)
        return None

    @transactional
    def get_all_catalog_names(self, ctx: MongoDaoContext) -> Iterator[Tuple[UUID, str]]:
        for item in ctx.collection.find({}, {"name": 1}):
            yield bson.Binary.as_uuid(item["_id"]), item["name"]

    # TODO:
    #       - CRUD recordings
    #       - CRUD recording attachments [both]
    #       - CRUD attachments
    #       - CRUD groups
