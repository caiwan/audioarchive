import argparse
import pathlib
import csv
import enum
import yaml
import logging
import shutil

import marshmallow.exceptions

from uuid import uuid4
from typing import Dict, Optional, Set, Tuple

from dataclasses import dataclass
from dataclasses_json import DataClassJsonMixin

from tqdm import tqdm
from tqdm.contrib.logging import logging_redirect_tqdm

from tapearchive.models import catalog
from tapearchive.utils import find_all_files


LOGGER = logging.getLogger(__name__)


class AttachmentType(enum.Enum):
    AUDIO_STEREO = "stereo"
    AUDIO_MONO = "mono"
    IMAGE_COVER = "cover"
    IMAGE_DOCUMENT = "document"
    INVALID = "invalid"


@dataclass
class CsvEntry(DataClassJsonMixin):
    file: str
    catalog: str
    side: str
    type: AttachmentType
    comment: Optional[str]


def parse_args() -> object:
    parser = argparse.ArgumentParser(description="Makes tapearchive recordings organized.")

    parser.add_argument(
        "--csv",
        "-c",
        dest="csv_file",
        type=pathlib.Path,
        required=True,
        help="CSV Ledger file of staging regordings",
    )

    # parser.add_argument(
    #     "--staging-dir",
    #     "-s",
    #     dest="staging_path",
    #     type=pathlib.Path,
    #     required=False,
    #     help="Directory of staging files.",
    # )

    parser.add_argument(
        "--dir",
        "-d",
        dest="archive_dir",
        type=pathlib.Path,
        required=True,
        help="Destination Directory of files.",
    )

    parser.add_argument(
        "--clean",
        "-x",
        dest="is_clean",
        # type=bool,
        action="store_true",
        default=False,
        help="Create meta files do not update them.",
    )

    parser.add_argument(
        "--export",
        "-e",
        dest="is_export",
        # type=bool,
        action="store_true",
        default=False,
        help="Exprot metadata to csv.",
    )

    parser.add_argument(
        "--verbose",
        dest="is_verbose",
        action="store_true",
        required=False,
        help="Print detailed log",
    )

    return parser.parse_args()


def load_csv_entries(csv_file: pathlib.Path) -> CsvEntry:
    with open(csv_file, "r") as csv_data_file:
        csv_data = csv.DictReader(csv_data_file)
        for record_data in csv_data:
            yield CsvEntry.schema().load(record_data)


def new_catalog_entry(csv_entry: CsvEntry) -> catalog.CatalogEntry:
    return catalog.CatalogEntry(
        id=uuid4(),
        name=csv_entry.catalog,
        recordings=[],
        groups=[],
        attachments=[],
        description=f"Recording {csv_entry.catalog}",
        meta={},
    )


def load_or_create_catalog_entry(catalog_file: pathlib.Path, csv_entry: CsvEntry) -> catalog.CatalogEntry:
    if pathlib.Path(catalog_file).exists():
        with open(catalog_file, "r") as f:
            return catalog.CatalogEntry.schema().load(yaml.safe_load(f))
    return new_catalog_entry(csv_entry)


def fetch_audio_channels(attachment_type: AttachmentType) -> catalog.ChannelMode:
    if attachment_type == AttachmentType.AUDIO_MONO:
        return [catalog.ChannelMode.LEFT, catalog.ChannelMode.RIGHT]
    if attachment_type == AttachmentType.AUDIO_STEREO:
        return [catalog.ChannelMode.STEREO]
    return []


def attach_record_to_catalog(csv_entry: CsvEntry, catalog: catalog.CatalogEntry):
    if csv_entry.type == AttachmentType.AUDIO_MONO or csv_entry.type == AttachmentType.AUDIO_STEREO:
        for channel in fetch_audio_channels(csv_entry.type):
            audio_source = catalog.AudioAttachment(
                id=uuid4(),
                type=catalog.AttachmentType.AUDIO_FILE,
                path=pathlib.Path(str(csv_entry.catalog).upper()) / pathlib.Path(csv_entry.file).name,
                format=pathlib.Path(csv_entry.file).suffix.replace(".", ""),
                name=pathlib.Path(csv_entry.file).name,
                meta={"source_file": csv_entry.file},
            )
            recording = catalog.RecordingEntry(
                id=uuid4(),
                name=f"{csv_entry.catalog}_side_{csv_entry.side}_channel_{channel.value}",
                audio_sources=[audio_source],
                audio_files=[],
                source_channel_mode=channel,
                description=f"Recording {csv_entry.catalog} side {csv_entry.side} channel {channel.value}",
                meta={"comment": csv_entry.comment, "side": csv_entry.side},
            )
            catalog.recordings.append(recording)

    if csv_entry.type == AttachmentType.IMAGE_COVER or csv_entry.type == AttachmentType.IMAGE_DOCUMENT:
        audio_source = catalog.Attachment(
            id=uuid4(),
            type=catalog.AttachmentType.COVER if csv_entry.type == AttachmentType.IMAGE_COVER else catalog.Attachment.DOCUMENT,
            path=pathlib.Path(str(csv_entry.catalog).upper()) / pathlib.Path(csv_entry.file).name,
            format=pathlib.Path(csv_entry.file).suffix.replace(".", ""),
            name=pathlib.Path(csv_entry.file).name,
            meta={"source_file": csv_entry.file},
        )
        catalog.attachments.append(audio_source)


def main():
    args = parse_args()
    logging.basicConfig(level=logging.INFO if not args.is_verbose else logging.DEBUG, format="[%(levelname)s]: %(message)s")

    with logging_redirect_tqdm():
        if not args.is_export:
            import_from_csv(args)
        else:
            export_to_csv(args)


def import_from_csv(args):
    catalog: Dict[str, catalog.CatalogEntry] = {}
    for csv_entry in load_csv_entries(args.csv_file):
        logging.debug(csv_entry)
        if args.is_clean:
            if csv_entry.catalog not in catalog:
                catalog[csv_entry.catalog] = new_catalog_entry(csv_entry)
            attach_record_to_catalog(csv_entry, catalog[csv_entry.catalog])
        else:
            if csv_entry.catalog not in catalog:
                catalog_src = args.archive_dir / csv_entry.catalog / "meta.yaml"
                catalog[csv_entry.catalog] = load_or_create_catalog_entry(catalog_src, csv_entry)
            attach_record_to_catalog(csv_entry, catalog[csv_entry.catalog])

    file_list: Set(Tuple(str, pathlib.Path, pathlib.Path)) = set()
    for catalog_entry in tqdm(catalog.values(), desc="Saving metadata files"):
        catalog_dst = args.archive_dir / catalog_entry.name
        catalog_dst.mkdir(parents=True, exist_ok=True)
        with open(catalog_dst / "meta.yaml", "w") as yaml_file:
            LOGGER.info(f"Exporting metadata for {catalog_entry.name} recordings={len(catalog_entry.recordings)}")
            data = catalog.CatalogEntry.schema().dump(catalog_entry)
            yaml.dump(data, yaml_file, sort_keys=True, default_flow_style=False)
        for recording in catalog_entry.recordings:
            for audio_file in recording.audio_sources:
                file_list.add(
                    (
                        catalog_entry.name,
                        audio_file.meta["source_file"],
                        args.archive_dir / audio_file.path,
                    )
                )

        for attachment_file in catalog_entry.attachments:
            src_file = attachment_file.meta["source_file"]
            dst_file = attachment_file.path
            if not pathlib.Path(dst_file).exists():
                LOGGER.info(f"Moving staging recording={recording.name} for catalog={catalog_entry.name} from={src_file} to={dst_file}")
                try:
                    shutil.move(src_file, dst_file)
                except FileNotFoundError:
                    LOGGER.error(f"File {src_file} does not exist.")

    for (catalog, src_file, dst_file) in tqdm(file_list, desc="Moving files"):
        if not pathlib.Path(dst_file).exists():
            try:
                shutil.move(src_file, dst_file)
                LOGGER.info(f"Moved staging file for catalog={catalog} from={src_file} to={dst_file}")
            except FileNotFoundError:
                LOGGER.error(f"File {src_file} for {catalog} does not exist.")


def export_to_csv(args):
    csv_data = []
    for yaml_path in tqdm(find_all_files("meta.yaml", args.archive_dir), desc="Loading manifests into db"):
        with open(yaml_path, "r") as f:
            try:
                entry = catalog.CatalogEntry.schema().load(yaml.safe_load(f))
                for recording in entry.recordings:
                    csv_entry = CsvEntry(
                        file=recording.audio_sources[0].path,
                        catalog=entry.name,
                        side="",
                        type=AttachmentType.INVALID.value,
                        comment=f'{recording.name} {recording.meta["comment"]}',
                    )
                    csv_data.append(csv_entry)
            except marshmallow.exceptions.ValidationError as e:
                LOGGER.error(f"Catalog manifest file {yaml_path} cannot be loaded.", exc_info=e if args.is_verbose else None)

    with open(args.csv_file, "w", newline="") as csvfile:
        csv_writer = csv.DictWriter(csvfile, [k for k in csv_data[0].to_dict().keys()], delimiter=",")
        csv_writer.writeheader()
        for row in csv_data:
            csv_writer.writerow(row.to_dict())


if __name__ == "__main__":
    main()
