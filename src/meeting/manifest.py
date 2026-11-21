"""The upload contract (D15): `incoming/<meeting-id>/` holds the recording and any attachments, and `meeting.json`,
uploaded last, says what the folder holds. The manifest is what triggers the job, so nothing is read before the
client has said the upload is complete, and every file is checked against it (size, SHA-256) before any model runs.

    {"schema_version": 1, "meeting_id": "m01-1", "title": "Release planning", "language": "en",
     "attendees": ["Sara", "Omar"],
     "recording": {"name": "recording.wav", "size": 3696044, "sha256": "<64 hex>"},
     "attachments": [{"name": "agenda.pdf", "size": 48211, "sha256": "<64 hex>"}]}
"""

import json
import re
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, ValidationError, model_validator

MANIFEST_NAME = "meeting.json"
SUPPORTED_LANGUAGES = ("en",)  # D2: English until the evaluation covers more (M3)

MEETING_ID_PATTERN = r"^[a-z0-9][a-z0-9-]{2,62}$"  # lower case: blob names are case-sensitive, ids should not be
MeetingId = Annotated[str, StringConstraints(pattern=MEETING_ID_PATTERN)]
FileName = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$")]  # no folders
Sha256 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class FileRef(_Strict):
    name: FileName
    size: int = Field(ge=1)
    sha256: Sha256


class Manifest(_Strict):
    schema_version: Literal[1]
    meeting_id: MeetingId
    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
    language: Annotated[str, StringConstraints(pattern=r"^[a-z]{2}$")]
    attendees: list[Name] = Field(max_length=30)
    recording: FileRef
    attachments: list[FileRef] = Field(default_factory=list, max_length=5)

    @model_validator(mode="after")
    def _distinct_names(self) -> "Manifest":
        names = [self.recording.name, *(a.name for a in self.attachments)]
        if MANIFEST_NAME in names:
            raise ValueError(f"{MANIFEST_NAME} cannot be listed as a file")
        if len(set(names)) != len(names):
            raise ValueError("file names must be distinct")
        return self

    @property
    def files(self) -> list[FileRef]:
        return [self.recording, *self.attachments]


class ManifestInvalid(ValueError):
    """The manifest is not JSON or breaks the contract. The message names the place and the problem (a Pydantic
    error type, or one of this module's own sentences), never the content: anything in an upload is untrusted."""


def parse(raw: bytes, folder_id: str) -> Manifest:
    try:
        data = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise ManifestInvalid("not JSON") from None
    try:
        manifest = Manifest.model_validate(data)
    except ValidationError as exc:
        first = exc.errors()[0]
        where = ".".join(str(p) for p in first["loc"]) or "(root)"
        what = first["msg"].removeprefix("Value error, ") if first["type"] == "value_error" else first["type"]
        raise ManifestInvalid(f"{exc.error_count()} problem(s), first at {where}: {what}") from None
    if manifest.meeting_id != folder_id:
        raise ManifestInvalid("meeting_id differs from the folder name")
    if manifest.language not in SUPPORTED_LANGUAGES:
        raise ManifestInvalid(f"language must be one of {', '.join(SUPPORTED_LANGUAGES)}")
    return manifest


def meeting_id_from_path(blob_path: str, container: str) -> str | None:
    """'incoming/<id>/meeting.json' (the trigger's blob name, with or without the container) -> '<id>', or None
    when the path is not a manifest in a valid meeting folder."""
    parts = blob_path.strip("/").split("/")
    if parts and parts[0] == container:
        parts = parts[1:]
    if len(parts) != 2 or parts[1] != MANIFEST_NAME or not re.fullmatch(MEETING_ID_PATTERN, parts[0]):
        return None
    return parts[0]
