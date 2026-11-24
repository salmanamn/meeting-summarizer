"""The helper scripts' own logic: the manifest the uploader builds, and what the status script prints."""

import json

import meeting_status
import pytest
import upload_meeting
from fakes import wav_bytes

from meeting.manifest import parse


def test_the_uploader_builds_a_manifest_the_job_accepts(tmp_path):
    recording = tmp_path / "M01.wav"
    recording.write_bytes(wav_bytes(1.0))
    agenda = tmp_path / "agenda.pdf"
    agenda.write_bytes(b"%PDF-1.7")
    manifest = upload_meeting.build_manifest("m01-1", "Planning", ["Sara", "Omar"], recording, [agenda])
    again = parse(manifest.model_dump_json().encode(), "m01-1")
    assert again == manifest
    assert [f.name for f in again.files] == ["M01.wav", "agenda.pdf"]
    assert again.recording.size == recording.stat().st_size


def test_evidence_is_masked(monkeypatch, tmp_path):
    monkeypatch.setattr(meeting_status.Path, "home", lambda: tmp_path)
    assert meeting_status.mask(f"{tmp_path}/x user@example.com") == "~/x user at example.com"


def test_stage_lines():
    job = {
        "files": [{}],
        "stt_runs": 1,
        "recording_seconds": 83.8,
        "transcript": {"segments": 39, "audio_seconds": 83.8, "seconds": 30.2, "engine": "faster-whisper stt-small"},
        "summary_meta": {"model": "phi4-mini:3.8b", "seconds": 49.9, "completion_tokens": 417},
        "error": {"code": "too_long", "stage": "received", "message": "61.0 minutes", "retryable": False},
    }
    assert meeting_status.stage_line(job, "received") == "1 file(s), 83.8 s of audio"
    assert meeting_status.stage_line(job, "transcribed").endswith("(faster-whisper stt-small; transcriptions: 1)")
    assert meeting_status.stage_line(job, "summarised") == "phi4-mini:3.8b, 49.9 s, 417 completion tokens"
    assert meeting_status.stage_line(job, "failed") == "too_long at received: 61.0 minutes"
    job["files"].append({"document": {"blocks": 5}})
    job["summary_meta"].update(parts=2)
    assert meeting_status.stage_line(job, "received") == "2 file(s), 83.8 s of audio, attachments read: 5 block(s)"
    assert meeting_status.stage_line(job, "summarised").endswith("417 completion tokens, 2 parts + merge")
    assert json.dumps(job)


def test_ami_sentences_come_from_the_decisions_and_actions_sections():
    import ami_set

    xml = b"""<?xml version="1.0"?>
<nite:root nite:id="ES2002b.abssumm" xmlns:nite="http://nite.sourceforge.net/">
  <abstract nite:id="a"><sentence nite:id="s1">The project manager opened the meeting.</sentence></abstract>
  <actions nite:id="b"><sentence nite:id="s2">The industrial designer will   look at the
    components.</sentence></actions>
  <decisions nite:id="c"><sentence nite:id="s3">The remote will have a kinetic battery.</sentence>
    <sentence nite:id="s4">It will be yellow.</sentence></decisions>
  <problems nite:id="d"><sentence nite:id="s5">Speech recognition may be too expensive.</sentence></problems>
</nite:root>"""
    assert ami_set.sentences(xml) == {
        "decisions": ["The remote will have a kinetic battery.", "It will be yellow."],
        "action_items": ["The industrial designer will look at the components."],
    }


def test_ami_xml_with_entities_is_refused():
    import ami_set
    from defusedxml import EntitiesForbidden

    bomb = (
        b'<?xml version="1.0"?><!DOCTYPE r [<!ENTITY a "aaaa">]><r><decisions><sentence>&a;</sentence></decisions></r>'
    )
    with pytest.raises(EntitiesForbidden):
        ami_set.sentences(bomb)


def test_the_test_meetings_attachments_are_readable(tmp_path, monkeypatch):
    import make_meeting

    from meeting.documents import LocalReader

    monkeypatch.setattr(make_meeting, "OUT", tmp_path)
    meeting = make_meeting.read_meeting("M04")
    paths = make_meeting.write_attachments(meeting)
    assert [p.name for p in paths] == ["agenda.docx", "budget.pdf"]
    reader = LocalReader()
    agenda = reader.read(paths[0], "agenda.docx", "docx")
    budget = reader.read(paths[1], "budget.pdf", "pdf")
    assert agenda.blocks[0].text == "## Agenda: website launch meeting" and len(agenda.blocks) == 5
    assert [b.ref for b in budget.blocks] == ["budget.pdf p1.1", "budget.pdf p2.1"]
    assert budget.blocks[1].text.startswith("Page two: agency fees")


def test_the_evaluation_loads_both_kinds_of_meeting():
    import eval_meetings

    scripted = eval_meetings.load_meeting("M04")
    assert (scripted["kind"], scripted["attendees"]) == ("script", ("Noor", "Yusuf", "Hana"))
    assert [p.name for p in scripted["attachments"]] == ["agenda.docx", "budget.pdf"]
    assert scripted["script"].startswith("Hello Yusuf, hello Hana.")
    assert eval_meetings.slug("phi4-mini:3.8b") == "phi4-mini-3.8b"


def test_ami_fetch_writes_the_answers_and_refuses_a_changed_file(tmp_path, monkeypatch):
    import io
    import zipfile

    import ami_set
    from fakes import wav_bytes

    xml = b"<r><decisions><sentence>A yellow remote.</sentence></decisions>"
    xml += b"<actions><sentence>Draw it.</sentence></actions></r>"
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w") as z:
        z.writestr("ami_public_manual_1.6.2/abstractive/ES2002b.abssumm.xml", xml)
    files = {ami_set.ANNOTATIONS_URL: archive.getvalue(), ami_set.AUDIO_URL.format(m="ES2002b"): wav_bytes(1.0)}

    def fake_get(client, url, target):
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(files[url])
        return target

    for name, value in (("AMI", tmp_path / "eval"), ("AUDIO", tmp_path / "audio"), ("DOWNLOADS", tmp_path / "dl")):
        monkeypatch.setattr(ami_set, name, value)
    monkeypatch.setattr(ami_set, "SOURCES", tmp_path / "eval" / "sources.json")
    monkeypatch.setattr(ami_set, "resumable_get", fake_get)
    assert ami_set.fetch(["ES2002b"]) == 0
    doc = json.loads((tmp_path / "eval" / "ES2002b.json").read_text())
    assert doc["answers"] == {"decisions": [{"text": "A yellow remote."}], "action_items": [{"text": "Draw it."}]}
    assert doc["source"]["licence"].startswith("CC BY 4.0")
    assert set(json.loads(ami_set.SOURCES.read_text())) == {"ami_public_manual_1.6.2.zip", "ES2002b.Mix-Headset.wav"}
    (tmp_path / "audio" / "ES2002b.wav").write_bytes(wav_bytes(2.0))  # a different file under the same name
    with pytest.raises(SystemExit, match="SHA-256 differs"):
        ami_set.fetch(["ES2002b"])
    with zipfile.ZipFile(archive, "a") as z:
        z.writestr(
            "abstractive/TS3003a.abssumm.xml", b"<r><abstract><sentence>Only an abstract.</sentence></abstract></r>"
        )
    files[ami_set.ANNOTATIONS_URL] = archive.getvalue()
    (tmp_path / "dl" / "ami_public_manual_1.6.2.zip").unlink()
    ami_set.SOURCES.unlink()
    with pytest.raises(
        SystemExit,
        match=r"TS3003a: no DECISIONS or ACTIONS sentences; sections in the file: \['abstract'\]",
    ):
        ami_set.fetch(["TS3003a"])


def test_show_names_the_attachment_an_item_is_about():
    from summarize_file import show

    from meeting.summary import MeetingSummary

    s = MeetingSummary.model_validate(
        {
            "title": "Launch",
            "overview": "o",
            "decisions": [],
            "action_items": [
                {
                    "task": "Update the figures",
                    "owner": "Hana",
                    "due": "Tuesday",
                    "evidence": "00:21",
                    "source": "budget.pdf p2.1",
                }
            ],
            "open_questions": [],
        }
    )
    assert show(s)[2] == "action    [00:21] Hana: Update the figures (due: Tuesday) (source: budget.pdf p2.1)"


def test_placement_reads_where_ollama_holds_the_model():
    import threading
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    import eval_meetings

    loaded = {
        "models": [
            {"name": "granite4:3b", "size": 4000, "size_vram": 4000},
            {"name": "x:1b", "size": 10, "size_vram": 4},
        ]
    }

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            data = json.dumps(loaded).encode()
            self.send_response(200)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_address[1]}/v1"
    try:
        assert eval_meetings.placement(base, "granite4:3b") == "100% GPU"
        assert eval_meetings.placement(base, "x:1b") == "40% GPU / 60% CPU"
        assert eval_meetings.placement(base, "qwen3.5:4b") == "unknown (model not loaded)"
    finally:
        server.shutdown()
    assert eval_meetings.placement("https://example.openai.azure.com/openai/v1", "gpt-5.4-mini") == "not Ollama"
