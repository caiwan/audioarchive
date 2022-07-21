from typing import Optional, Type, List, Callable, Iterator, Dict, Any, Union
from uuid import UUID, uuid4

from functools import wraps

import json

from enum import Enum

from dataclasses import dataclass
from dataclasses_json import DataClassJsonMixin
from marshmallow import Schema

import redis

import logging

LOGGER = logging.getLogger(__name__)


class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, UUID):
            return str(obj)

        if issubclass(type(obj), Enum):
            return str(obj)

        if issubclass(type(obj), DataClassJsonMixin):
            return obj.to_dict()

        return json.JSONEncoder.default(self, obj)


# https://github.com/redis/redis-py
# https://redis.io/commands

DEFAULT_BUCKET_SIZE = 10


@dataclass
class BaseEntity(DataClassJsonMixin):
    id: UUID


# TODO: Add db maintainer - aka save after X db commit


class DaoContext(object):
    def __init__(self, db: redis.Redis, key_prefix: str):
        self._db = db
        self._key_prefix: redis.ConnectionPool = key_prefix

    @property
    def db(self):
        return self._db

    @property
    def wildcard(self) -> str:
        return f"{self._key_prefix}:*"

    def _key(self, id: UUID) -> str:
        return f"{self._key_prefix}:{str(id)}"

    def is_exists(self, id: UUID) -> bool:
        return self._db.exists(self._key(id))

    def set(self, id: UUID, data: bytes) -> UUID:
        key = self._key(id)
        self._db.set(key, data)
        return id

    def create_or_update(self, obj: Dict, id: UUID = None) -> UUID:
        return self.set(
            id if id else uuid4(),
            json.dumps(obj, cls=CustomJSONEncoder),
        )

    def get(self, id: UUID) -> Optional[bytes]:
        key = self._key(id)
        if not self._db.exists(key):
            return None
        return self._db.get(key)

    def get_entity(self, id: UUID) -> Optional[Dict]:
        item = self.get(id)
        return json.loads(item) if item else None

    def iterate_all_keys(self) -> Iterator[UUID]:
        for db_key in self._db.scan_iter(self.wildcard):
            key = db_key.decode("utf-8").split(":")[-1]
            yield UUID(key)

    def iterate_all_entities(self) -> Iterator[Dict]:
        for db_key in self._db.scan_iter(self.wildcard):
            item = self._db.get(db_key)
            yield json.loads(item) if item else None

    def delete(self, id: UUID):
        self._db.delete(self._key(id))

    def list_push(self, id: UUID, data: Union[str, bytes]) -> int:
        key = self._key(id)
        return self._db.lpush(key, data)

    def list_push_entity(self, id: UUID, obj: Dict) -> int:
        return self.list_push(id, json.dumps(obj, cls=CustomJSONEncoder))

    def list_pop(self, id: UUID) -> bytes:
        key = self._key(id)
        return self._db.lpop(key)

    def list_pop_entity(self, id: UUID) -> Dict:
        item = self.list_pop(id)
        return json.loads(item.decode()) if item else None

    def get_list_length(self, id: UUID) -> int:
        key = self._key(id)
        if not self._db.exists(key):
            return 0

        return self._db.llen(key)

    def iter_all_from_list(self, id: UUID, fetch_bucket_size: int = DEFAULT_BUCKET_SIZE) -> Iterator[Any]:
        fetch_bucket_size = fetch_bucket_size if fetch_bucket_size > 0 else DEFAULT_BUCKET_SIZE
        key = self._key(id)
        count = self.get_list_length(id)
        if count > 0:
            cursor = 0
            while cursor < count:
                delta = min(fetch_bucket_size, count - cursor)
                items = self._db.lrange(key, cursor, cursor + delta)
                for item in items:
                    yield item
                cursor += delta

    def iter_all_entities_from_list(self, id: UUID, fetch_bucket_size: int = DEFAULT_BUCKET_SIZE) -> Iterator[Any]:
        for item in self.iter_all_from_list(id, fetch_bucket_size=fetch_bucket_size):
            yield json.loads(item) if item else None

    def remove_from_list(self, id: UUID, obj: Any):
        key = self._key(id)
        return self._db.lrem(key, 1, json.dumps(obj, cls=CustomJSONEncoder))

    def remove_from_list_by_id(self, id: UUID, index: int):
        placeholder = str(uuid4())
        key = self._key(id)
        self._db.lset(key, index, placeholder)
        return self._remove_from_list(key, placeholder)

    def bulk_remove_from_list_by_id(self, id: UUID, indices: List[int]):
        placeholders: List[str] = []
        key = self._key(id)
        for index in indices:
            random_uuid = str(uuid4())
            self._db.lset(key, index, random_uuid)
            placeholders.append(random_uuid)
        count = 0
        for placeholder in placeholders:
            count += self._remove_from_list(key, placeholder)
        return count

    def cleanup(self) -> int:
        counter = 0
        for key in self._db.scan_iter(self._wildcard):
            counter += self._db.delete(key)
        return counter

    def add_to_set(self, id: UUID, obj: Any):
        key = self._key(id)
        self._db.sadd(key, json.dumps(obj, cls=CustomJSONEncoder))

    def get_all_entities_from_set(self, id: UUID) -> Iterator[Any]:
        key = self._key(id)
        for item in self._db.smembers(key):
            yield json.loads(item) if item else None

    def get_set_length(self, id: UUID):
        key = self._key(id)
        if not self._db.exists(key):
            return 0
        return self._db.scard(self.key)

    def iterate_all_entities_from_set(self, id: UUID) -> Iterator[Any]:
        if self._get_set_length(id) > 0:
            # Bazdmeg az anyad te fos szar
            for item in self._get_all_from_set(id):
                yield json.loads(item) if item else None

    # TODO: Add Optional expiration time

    def trigger_db_cleanup(self):
        try:
            self._db.bgsave()
            self._db.bgrewriteaof()  # AOF Should be disabled anyways
        except Exception:
            # Ignore if already in progress
            pass


# TODO: Add Read only flag
def transactional(fn: Callable) -> Callable:
    @wraps(fn)
    def tansaction_wrapper(*args, **kwargs):
        obj_self = args[0]
        connection_pool = obj_self._db_pool
        ctx = DaoContext(redis.Redis(connection_pool=connection_pool), obj_self._key_prefix)

        # TODO use pipe with context
        return ctx._db.transaction(lambda pipe: fn(obj_self, ctx, *args[1:], **kwargs), value_from_callable=True)

    return tansaction_wrapper


class BaseDao:
    def __init__(self, db_pool: redis.ConnectionPool, schema: Type[Schema], key_prefix: str = ""):
        super().__init__()
        self._db_pool: redis.ConnectionPool = db_pool
        self._key_prefix: redis.ConnectionPool = key_prefix
        self._schema: Type[Schema] = schema

    @transactional
    def create_or_update(self, ctx: DaoContext, obj: DataClassJsonMixin) -> UUID:
        return ctx.create_or_update(obj.to_dict(), obj.id)

    @transactional
    def get_entity(self, ctx: DaoContext, id: UUID) -> DataClassJsonMixin:
        data = ctx.get_entity(id)
        return self._schema.load(data) if data else None

    @transactional
    def get_all(self, ctx: DaoContext) -> List[DataClassJsonMixin]:
        return list([entity for entity in self.iterate_all(ctx)])

    @transactional
    def iterate_all(self, ctx: DaoContext) -> Iterator[DataClassJsonMixin]:
        for entity in ctx.iterate_all_entities():
            yield self._schema.load(entity) if entity else None

    @transactional
    def iterate_all_keys(self, ctx: DaoContext) -> Iterator[DataClassJsonMixin]:
        for key in ctx.iterate_all_keys():
            yield key

    @transactional
    def delete(self, ctx: DaoContext, id: UUID):
        return ctx.delete(id)

    @property
    def schema(self):
        return self._schema
