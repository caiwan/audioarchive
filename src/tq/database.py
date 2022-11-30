from contextlib import contextmanager
import time
from typing import Optional, Set, Type, List, Callable, Iterator, Dict, Any, Union
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
            return str(obj.value)

        if issubclass(type(obj), DataClassJsonMixin):
            return obj.to_dict()

        return json.JSONEncoder.default(self, obj)


def _to_json(obj: Any) -> str:
    return json.dumps(obj, cls=CustomJSONEncoder)


def _from_json(_json: Optional[bytes]) -> Optional[Any]:
    return json.loads(_json.decode()) if _json else None


# https://github.com/redis/redis-py
# https://redis.io/commands

DEFAULT_BUCKET_SIZE = 10


@dataclass
class BaseEntity(DataClassJsonMixin):
    id: Optional[UUID]


# TODO: Unfuck names [type] _ [what_operation] like hash_get_keys() or the other way aorund, make it uniform at least

# TODO: Add db maintainer - aka save after X amoount of db commits
@dataclass
class DaoContext(object):

    # TODO: Properties + use proper setters
    shard_hint: Optional[str] = None
    watches: Optional[Set[str]] = None
    value_from_callable: bool = True
    watch_delay: Optional[float] = None

    def __init__(self, db: redis.Redis, name_prefix: str):
        self._db = db
        self._name_prefix: redis.ConnectionPool = name_prefix

    @contextmanager
    def create_sub_context(self, name_prefix):
        # TODO: When creating a new sub-ctx make it able to set certain flags for the transaction in the root context itself
        yield DaoContext(self._db, name_prefix)

    @property
    def db(self):
        return self._db

    @property
    def wildcard(self) -> str:
        return f"{self._name_prefix}:*"

    def _name(self, id: Optional[UUID]) -> str:
        return f"{self._name_prefix}:{str(id)}" if id else self._name_prefix

    def is_exists(self, id: Optional[UUID]) -> bool:
        return self._db.exists(self._name(id))

    def set(self, id: Optional[UUID], data: bytes) -> UUID:
        id = id if id else uuid4()
        name = self._name(id)
        self._db.set(name, data)
        return id

    def create_or_update(self, obj: Dict, id: Optional[UUID] = None) -> UUID:
        return self.set(
            id if id else uuid4(),
            _to_json(obj),
        )

    def get(self, id: Optional[UUID]) -> Optional[bytes]:
        name = self._name(id)
        if not self._db.exists(name):
            return None
        return self._db.get(name)

    def get_entity(self, id: Optional[UUID]) -> Optional[Dict]:
        item = self.get(id)
        return _from_json(item)

    def iterate_all_keys(self) -> Iterator[UUID]:
        for db_key in self._db.scan_iter(self.wildcard):
            name = db_key.decode("utf-8").split(":")[-1]
            yield UUID(name)

    def iterate_all_entities(self) -> Iterator[Dict]:
        for db_key in self._db.scan_iter(self.wildcard):
            item = self._db.get(db_key)
            yield _from_json(item)

    def delete(self, id: Optional[UUID]):
        self._db.delete(self._name(id))

    def list_push(self, id: Optional[UUID], data: Union[str, bytes]) -> int:
        name = self._name(id)
        return self._db.lpush(name, data)

    def list_push_entity(self, id: Optional[UUID], obj: Dict) -> int:
        return self.list_push(id, _to_json(obj))

    def list_pop(self, id: Optional[UUID]) -> Optional[bytes]:
        name = self._name(id)
        return self._db.lpop(name)

    def list_pop_entity(self, id: Optional[UUID]) -> Optional[Dict]:
        return _from_json(self.list_pop(id))

    def get_list_length(self, id: Optional[UUID]) -> int:
        name = self._name(id)
        if not self._db.exists(name):
            return 0

        return self._db.llen(name)

    def iter_all_from_list(self, id: Optional[UUID], fetch_bucket_size: int = DEFAULT_BUCKET_SIZE) -> Iterator[Any]:
        fetch_bucket_size = fetch_bucket_size if fetch_bucket_size > 0 else DEFAULT_BUCKET_SIZE
        name = self._name(id)
        count = self.get_list_length(id)
        if count > 0:
            cursor = 0
            while cursor < count:
                delta = min(fetch_bucket_size, count - cursor)
                items = self._db.lrange(name, cursor, cursor + delta)
                for item in items:
                    yield item
                cursor += delta

    def iter_all_entities_from_list(self, id: Optional[UUID], fetch_bucket_size: int = DEFAULT_BUCKET_SIZE) -> Iterator[Any]:
        for item in self.iter_all_from_list(id, fetch_bucket_size=fetch_bucket_size):
            yield _from_json(item)

    def remove_from_list(self, id: Optional[UUID], obj: Any):
        name = self._name(id)
        return self._db.lrem(name, 1, _to_json(obj))

    def remove_from_list_by_id(self, id: Optional[UUID], index: int):
        placeholder = str(uuid4())
        name = self._name(id)
        self._db.lset(name, index, placeholder)
        return self._remove_from_list(name, placeholder)

    def bulk_remove_from_list_by_id(self, id: Optional[UUID], indices: List[int]):
        placeholders: List[str] = []
        name = self._name(id)
        for index in indices:
            random_uuid = str(uuid4())
            self._db.lset(name, index, random_uuid)
            placeholders.append(random_uuid)
        count = 0
        for placeholder in placeholders:
            count += self._remove_from_list(name, placeholder)
        return count

    def get_hash(self, id: Optional[UUID], key: str) -> Optional[bytes]:
        name = self._name(id)
        return self._db.hget(name, key)

    def set_hash(self, id: Optional[UUID], key: str, value: bytes) -> int:
        name = self._name(id)
        return self._db.hset(name, key, value)

    def has_hash_key(self, id: Optional[UUID], key: str) -> bool:
        return self._db.hexists(self._name(id), key)

    def get_hash_entity(self, id: Optional[UUID], key: str) -> Optional[Any]:
        return _from_json(self.get_hash(id, key))

    def set_hash_entity(self, id: Optional[UUID], key: str, value: Any) -> int:
        name = self._name(id)
        return self.set_hash(id, key, _to_json(value))

    def iterate_hash_keys(self, id: Optional[UUID]) -> Iterator[str]:
        for key in self._db.hkeys(self._name(id)):
            yield key.decode()

    def cleanup(self) -> int:
        counter = 0
        for name in self._db.scan_iter(self._wildcard):
            counter += self._db.delete(name)
        return counter

    def add_to_set(self, id: Optional[UUID], obj: Any):
        name = self._name(id)
        self._db.sadd(name, _to_json(obj))

    def iterate_all_entities_from_set(self, id: Optional[UUID]) -> Iterator[Any]:
        name = self._name(id)
        for item in self._db.smembers(name):
            yield _from_json(item)

    def get_set_length(self, id: Optional[UUID]):
        name = self._name(id)
        return self._db.scard(name) if self._db.exists(name) else 0

    # TODO: Add Optional expiration time - maybe through soem decoration like AOP?

    def trigger_db_cleanup(self):
        try:
            self._db.bgsave()
            self._db.bgrewriteaof()  # AOF Should be disabled anyways
        except Exception:
            # Ignore if already in progress
            pass


# TODO: Add a Read-only flag
def transactional(fn: Callable) -> Callable:
    @wraps(fn)
    def tansaction_wrapper(*args, **kwargs):
        obj_self = args[0]
        connection_pool = obj_self._db_pool
        ctx = DaoContext(redis.Redis(connection_pool=connection_pool), obj_self._key_prefix)

        # TODO add params from ctx
        return ctx._db.transaction(
            lambda pipe: fn(obj_self, ctx, *args[1:], **kwargs),
            value_from_callable=ctx.value_from_callable,
            shard_hint=ctx.shard_hint,
            watches=ctx.watches,
            watch_delay=ctx.watch_delay,
        )

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
    def get_entity(self, ctx: DaoContext, id: Optional[UUID]) -> DataClassJsonMixin:
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
    def delete(self, ctx: DaoContext, id: Optional[UUID]):
        return ctx.delete(id)

    @property
    def schema(self):
        return self._schema
