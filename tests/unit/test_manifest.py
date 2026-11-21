"""The upload contract (D15): what meeting.json must say."""

import json

import pytest

from meeting.manifest import ManifestInvalid, meeting_id_from_path, parse

SHA = "a" * 64


def body(**changes) -> bytes:
    data = {
        "schema_version": 1,
        "meeting_id": "m01-1",
        "title": "Release planning",
        "language": "en",
        "attendees": ["Sara", "Omar"],
        "recording": {"name": "recording.wav", "size": 100, "sha256": SHA},
        "attachments": [{"name": "agenda.pdf", "size": 10, "sha256": SHA}],
    }
    data.update(changes)
    return json.dumps(data).encode()


def test_a_valid_manifest():
    manifest = parse(body(), "m01-1")
    assert [f.name for f in manifest.files] == ["recording.wav", "agenda.pdf"]
    assert manifest.attendees == ["Sara", "Omar"]
    assert parse(body(attachments=[]), "m01-1").attachments == []


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"schema_version": 2}, "first at schema_version: literal_error"),
        ({"meeting_id": "M01"}, "first at meeting_id: string_pattern_mismatch"),
        ({"title": " "}, "first at title: string_too_short"),
        (
            {"recording": {"name": "../x.wav", "size": 1, "sha256": SHA}},
            "first at recording.name: string_pattern_mismatch",
        ),
        (
            {"recording": {"name": "a/b.wav", "size": 1, "sha256": SHA}},
            "first at recording.name: string_pattern_mismatch",
        ),
        ({"recording": {"name": "r.wav", "size": 0, "sha256": SHA}}, "first at recording.size: greater_than_equal"),
        (
            {"recording": {"name": "r.wav", "size": 1, "sha256": "A" * 64}},
            "first at recording.sha256: string_pattern_mismatch",
        ),
        ({"attachments": [{"name": "recording.wav", "size": 1, "sha256": SHA}]}, "file names must be distinct"),
        ({"attachments": [{"name": "meeting.json", "size": 1, "sha256": SHA}]}, "cannot be listed as a file"),
        ({"attachments": [{"name": f"a{i}.pdf", "size": 1, "sha256": SHA} for i in range(6)]}, "attachments: too_long"),
        ({"attendees": ["x"] * 31}, "first at attendees: too_long"),
        ({"extra": 1}, "first at extra: extra_forbidden"),
    ],
)
def test_contract_violations_name_the_place_not_the_content(changes, message):
    with pytest.raises(ManifestInvalid, match=message.replace(".", r"\.")):
        parse(body(**changes), "m01-1")


def test_folder_language_and_json():
    with pytest.raises(ManifestInvalid, match="differs from the folder name"):
        parse(body(), "m01-2")
    with pytest.raises(ManifestInvalid, match="language must be one of en"):
        parse(body(language="ar"), "m01-1")
    with pytest.raises(ManifestInvalid, match=r"^not JSON$"):
        parse(b"\xff\xfe not json", "m01-1")


@pytest.mark.parametrize(
    ("path", "meeting_id"),
    [
        ("incoming/m01-1/meeting.json", "m01-1"),
        ("m01-1/meeting.json", "m01-1"),
        ("/incoming/m01-1/meeting.json", "m01-1"),
        ("incoming/m01-1/recording.wav", None),
        ("incoming/meeting.json", None),
        ("incoming/a/b/meeting.json", None),
        ("incoming/M01/meeting.json", None),
        ("incoming/ab/meeting.json", None),
        ("other/m01-1/meeting.json", None),
    ],
)
def test_meeting_id_from_the_trigger_path(path, meeting_id):
    assert meeting_id_from_path(path, "incoming") == meeting_id
