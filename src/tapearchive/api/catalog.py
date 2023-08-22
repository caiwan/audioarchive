from typing import List, Tuple
from uuid import UUID
from flask_restful import Resource
import redis

from tapearchive.models.catalog import CatalogDao, CatalogEntry


class CatalogController:
    def __init__(self, connection_pool: redis.ConnectionPool):
        self._catalog_dao = CatalogDao(connection_pool)

    def get_catalog_entry(self, id: UUID) -> CatalogEntry:
        return self._catalog_dao.get_entity(id)

    def get_all_catalog_names(self) -> List[list]:
        return self._catalog_dao.get_all_cat_names()


class CatalogEntryView(Resource):
    def __init__(self, catalog_controller: CatalogController):
        self.controller = catalog_controller

    def get(self, catalog_name: str) -> CatalogEntry:
        return self.controller.get_catalog_entry(UUID(catalog_name))


class CatalogListView(Resource):
    def __init__(self, catalog_controller: CatalogController):
        self.controller = catalog_controller

    def get(self):
        return self.controller.get_all_catalog_names()
