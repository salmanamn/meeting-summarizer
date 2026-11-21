"""Upload a meeting the way the contract says (D15): the files first, `meeting.json` last.

uv run python scripts/upload_meeting.py out/meetings/M01.wav --id m01-1 --expect M01
uv run python scripts/upload_meeting.py rec.m4a --id board-0312 --title "Board call" --attendees "Sara,Omar" \
    [--attach agenda.pdf] [--replace]

--expect ID   title and attendees from eval/meetings/<ID>.json
--replace     upload the folder again (meeting.json exists): restarts a failed job, a finished one ignores it
--bad-sha256  write a wrong SHA-256 for the recording into the manifest (to watch the job refuse it)

The manifest is built with the same Pydantic model the job checks it with (src/meeting/manifest.py), and written
with If-None-Match: * unless --replace (the service refuses it if the file exists): two uploads to the same
folder cannot both start a job by accident.
"""

import argparse
import hashlib
import json
import mimetypes
import sys
from pathlib import Path

from azure.core.exceptions import ResourceExistsError
from azure.storage.blob import ContentSettings

from meeting.manifest import MANIFEST_NAME, FileRef, Manifest
from meeting.settings import load
from meeting.stores import BlobStore

ROOT = Path(__file__).resolve().parents[1]


def file_ref(path: Path) -> FileRef:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        while chunk := fh.read(1024 * 1024):
            digest.update(chunk)
    return FileRef(name=path.name, size=path.stat().st_size, sha256=digest.hexdigest())


def build_manifest(
    meeting_id: str, title: str, attendees: list[str], recording: Path, attachments: list[Path]
) -> Manifest:
    return Manifest(
        schema_version=1,
        meeting_id=meeting_id,
        title=title,
        language="en",
        attendees=attendees,
        recording=file_ref(recording),
        attachments=[file_ref(a) for a in attachments],
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("recording", type=Path)
    parser.add_argument("--id", required=True, dest="meeting_id")
    parser.add_argument("--expect", metavar="ID", help="title and attendees from eval/meetings/<ID>.json")
    parser.add_argument("--title")
    parser.add_argument("--attendees", help="comma-separated names")
    parser.add_argument("--attach", type=Path, action="append", default=[], help="a PDF or DOCX (repeatable)")
    parser.add_argument("--replace", action="store_true")
    parser.add_argument("--bad-sha256", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()

    title, attendees = args.title, []
    if args.expect:
        meeting = json.loads((ROOT / "eval" / "meetings" / f"{args.expect}.json").read_text(encoding="utf-8"))
        title, attendees = title or meeting["title"], list(meeting["speakers"])
    if args.attendees is not None:
        attendees = [n.strip() for n in args.attendees.split(",") if n.strip()]
    if not title:
        parser.error("--title (or --expect) is required")

    try:
        manifest = build_manifest(args.meeting_id, title, attendees, args.recording, args.attach)
    except ValueError as exc:  # pydantic's ValidationError is a ValueError: the same rules as the job's
        print(f"FAIL the manifest would be invalid: {exc}")
        return 1
    if args.bad_sha256:
        manifest = manifest.model_copy(update={"recording": manifest.recording.model_copy(update={"sha256": "0" * 64})})

    settings = load()
    store = BlobStore.from_settings(settings)
    container = store.service.get_container_client(settings.incoming_container)
    folder = f"{settings.incoming_container}/{args.meeting_id}"
    if not args.replace and container.get_blob_client(f"{args.meeting_id}/{MANIFEST_NAME}").exists():
        print(f"FAIL {folder}/{MANIFEST_NAME} exists: use a new --id, or --replace to upload the folder again")
        return 1

    for path, ref in zip([args.recording, *args.attach], manifest.files, strict=True):
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        with path.open("rb") as fh:
            container.upload_blob(
                f"{args.meeting_id}/{ref.name}", fh, overwrite=True, content_settings=ContentSettings(content_type)
            )
        print(f"uploaded {folder}/{ref.name} ({ref.size / 1e6:.1f} MB, sha256 {ref.sha256[:12]})")

    body = manifest.model_dump_json(indent=2).encode()
    try:  # without --replace: overwrite=False, i.e. If-None-Match: * on the request, checked by the service
        container.upload_blob(
            f"{args.meeting_id}/{MANIFEST_NAME}",
            body,
            overwrite=args.replace,
            content_settings=ContentSettings("application/json"),
        )
    except ResourceExistsError:
        print(f"FAIL {folder}/{MANIFEST_NAME} appeared during the upload: another upload to the same folder")
        return 1
    print(f"uploaded {folder}/{MANIFEST_NAME} last ({len(body)} bytes): this upload is what starts the job")
    return 0


if __name__ == "__main__":
    sys.exit(main())
