from typing import List
from uuid import UUID
from flask_restful import Resource
from marshmallow_dataclass import class_schema
import redis

from tapearchive.models.catalog import (
    Attachment,
    CatalogDao,
    CatalogEntry,
    RecordingEntry,
)

CatalogEntrySchema = class_schema(CatalogEntry)


class CatalogController:
    def __init__(self, connection_pool: redis.ConnectionPool):
        self._catalog_dao = CatalogDao(connection_pool)

    def get_catalog_entry(self, id: UUID) -> CatalogEntry:
        return self._catalog_dao.get_entity(id)

    def get_all_catalog_names(self) -> List[list]:
        return self._catalog_dao.get_all_cat_names()

    # Create a new catalog entry
    def create_catalog_entry(self, catalog_entry: CatalogEntry) -> CatalogEntry:
        #     return self._catalog_dao.create_entity(catalog_entry)
        pass

    # Update a catalog entry
    def update_catalog_entry(self, catalog_entry: CatalogEntry) -> CatalogEntry:
        #     return self._catalog_dao.update_entity(catalog_entry)
        pass

    # Delete a catalog entry
    def delete_catalog_entry(self, id: UUID) -> None:
        #     self._catalog_dao.delete_entity(id)
        pass

    # Add a recording to a catalog entry
    def add_recording_to_catalog_entry(
        self, id: UUID, recording: RecordingEntry
    ) -> CatalogEntry:
        #    return self._catalog_dao.add_recording_to_catalog_entry(id, recording)
        pass

    # Update a recording in a catalog entry
    def update_recording_in_catalog_entry(
        self, id: UUID, recording: RecordingEntry
    ) -> CatalogEntry:
        #   return self._catalog_dao.update_recording_in_catalog_entry(id, recording)
        pass

    # Add an attachment to a recording in a catalog entry
    def add_attachment_to_recording_in_catalog_entry(
        self, id: UUID, recording: RecordingEntry, attachment: Attachment
    ) -> CatalogEntry:
        #   return self._catalog_dao.add_attachment_to_recording_in_catalog_entry(id, recording, attachment)
        pass

    # Update an attachment to a recording in a catalog entry
    def update_attachment_in_recording_in_catalog_entry(
        self, id: UUID, recording: RecordingEntry, attachment: Attachment
    ) -> CatalogEntry:
        #   return self._catalog_dao.update_attachment_in_recording_in_catalog_entry(id, recording, attachment)
        pass


class CatalogEntryView(Resource):
    def __init__(self, catalog_controller: CatalogController):
        self.controller = catalog_controller

    def get(self, catalog_name: str) -> CatalogEntry:
        """
        Returns a catalog entry by id.
        ---
        parameters:
            - name: catalog_name
              in: path
              type: string
              required: true
              description: The name of the catalog entry to return.

        responses:
            200:
                description: The catalog entry.
                schema:
                    $ref: '#/definitions/CatalogEntrySchema'
        """
        return self.controller.get_catalog_entry(UUID(catalog_name))

    def post(self) -> CatalogEntry:
        """
        Creates a new catalog entry.
        ---
        requestBody:
            content:
                application/json:
                    schema:
                        $ref: '#/definitions/CatalogEntrySchema'
            required: true
        responses:
            200:
                description: The catalog entry.
                schema:
                    $ref: '#/definitions/CatalogEntrySchema'
        """

        pass

    def put(self, catalog_id: str) -> CatalogEntry:
        """
        Updates a catalog entry.
        ---
        parameters:
            - name: catalog_id
              in: path
              type: string
              required: true

        requestBody:
            content:
                application/json:
                    schema:
                        $ref: '#/definitions/CatalogEntrySchema'
            required: true
        responses:
            200:
                description: The catalog entry.
                schema:
                    $ref: '#/definitions/CatalogEntrySchema'
        """
        pass

    def delete(self, catalog_id: str) -> None:
        """
        Deletes a catalog entry.
        ---
        parameters:
            - name: catalog_name
              in: path
              type: string
              required: true
        responses:
            200:
                description: The catalog entry.
                schema:
                    $ref: '#/definitions/CatalogEntrySchema'
        """
        pass


class CatalogListView(Resource):
    def __init__(self, catalog_controller: CatalogController):
        self.controller = catalog_controller

    def get(self):
        """
        Returns a list of all catalog names.
        ---
        responses:
            200:
                description: A list of all catalog names.
                schema:
                    type: array
                    items:
                        $ref: '#/definitions/CatalogEntrySchema'
        """
        return self.controller.get_all_catalog_names()
