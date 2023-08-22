import uuid
import pytest

from tapearchive.models.catalog import (
    AttachmentType,
    AudioAttachment,
    CatalogDao,
    CatalogEntry,
    ChannelMode,
    RecordingEntry,
)


@pytest.fixture(scope="function")
def catalog_dao(mongodb_client):
    catalog_dao = CatalogDao(mongodb_client)
    yield catalog_dao


@pytest.fixture(scope="function")
def dummy_catalog_entries():
    return [
        CatalogEntry(
            id=uuid.uuid4(),
            name=f"catalog_{uuid.uuid4()}",
            recordings=[
                RecordingEntry(
                    id=uuid.uuid4(),
                    name=f"recording_{uuid.uuid4()}",
                    source_channel_mode=ChannelMode.STEREO,
                    description="",
                    audio_files=[
                        AudioAttachment(
                            id=uuid.uuid4(),
                            type=AttachmentType.AUDIO_FILE,
                            path="",
                            name="",
                            meta={},
                            format="mp3",
                        )
                        for _ in range(10)
                    ],
                    audio_sources=[
                        AudioAttachment(
                            id=uuid.uuid4(),
                            type=AttachmentType.AUDIO_FILE,
                            path="",
                            name="",
                            meta={},
                            format="mp3",
                        )
                        for _ in range(10)
                    ],
                    meta={},
                )
                for _ in range(10)
            ],
            groups=[],
            attachments=[],
            description="",
            meta={},
        )
        for _ in range(10)
    ]


def validate_catalog_entry(
    actual_entry: CatalogEntry,
    expected_entry: CatalogEntry,
):
    assert actual_entry is not None
    assert actual_entry.id == expected_entry.id
    assert actual_entry.name == expected_entry.name
    assert len(actual_entry.recordings) == len(expected_entry.recordings)
    assert len(actual_entry.groups) == len(expected_entry.groups)
    assert len(actual_entry.attachments) == len(expected_entry.attachments)
    assert actual_entry.description == expected_entry.description
    assert actual_entry.meta == expected_entry.meta


def test_catalog_read_write(catalog_dao: CatalogDao, dummy_catalog_entries: list):
    entity_ids = catalog_dao.bulk_create_or_update(dummy_catalog_entries)

    for entity_id, catalog_entry in zip(entity_ids, dummy_catalog_entries):
        entry_from_db = catalog_dao.get_entity(entity_id)
        validate_catalog_entry(entry_from_db, catalog_entry)


def test_fetch_all_catalog_entries(catalog_dao: CatalogDao, dummy_catalog_entries: list):
    catalog_dao.bulk_create_or_update(dummy_catalog_entries)

    for catalog_entry in dummy_catalog_entries:
        entry_from_db = catalog_dao.get_entry_by_cat_number(catalog_entry.name)
        validate_catalog_entry(entry_from_db, catalog_entry)


def test_fetch_all_catalog_names(catalog_dao: CatalogDao, dummy_catalog_entries: list):
    entity_ids = catalog_dao.bulk_create_or_update(dummy_catalog_entries)

    catalog = catalog_dao.get_all_catalog_names()

    for catalog_id, catalog_name in catalog:
        assert catalog_name in [entry.name for entry in dummy_catalog_entries]
        assert catalog_id in entity_ids
