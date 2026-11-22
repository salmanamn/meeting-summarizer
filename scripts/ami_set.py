"""Real meetings for the evaluation (D26): recordings and human-written summaries from the AMI Meeting Corpus.

uv run python scripts/ami_set.py fetch            the meetings in eval/sets.json, or name them: fetch ES2002b ...
uv run python scripts/ami_set.py status

The AMI Meeting Corpus (University of Edinburgh and the AMI consortium) is released under CC BY 4.0, signals and
the public manual annotations alike. For every meeting this writes eval/ami/<ID>.json (committed): the DECISIONS
and ACTIONS sentences of the annotators' abstractive summary, which are the answers the summary is scored
against, and the SHA-256 of the recording; the recording itself (the headset mix, one WAV of all four
participants) goes to data/ami/<ID>.wav and stays out of git. The first fetch records the hashes of the
annotations archive and of each recording; a later fetch refuses files that differ (as models.lock.json does).

The archive is untrusted input: only the named abssumm.xml members are read, with defusedxml, never extracted.
"""

import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path

import httpx
from defusedxml import ElementTree

from meeting.download import resumable_get

ROOT = Path(__file__).resolve().parents[1]
AMI = ROOT / "eval" / "ami"
AUDIO = ROOT / "data" / "ami"
DOWNLOADS = ROOT / "data" / "downloads"
ANNOTATIONS_URL = "https://groups.inf.ed.ac.uk/ami/AMICorpusAnnotations/ami_public_manual_1.6.2.zip"
# The mirror path as the AMI loader of Hugging Face datasets writes it (double slash included).
AUDIO_URL = "https://groups.inf.ed.ac.uk/ami/AMICorpusMirror//amicorpus/{m}/audio/{m}.Mix-Headset.wav"
SOURCES = AMI / "sources.json"
LICENCE = "CC BY 4.0, AMI Meeting Corpus (University of Edinburgh and the AMI consortium)"
SECTIONS = {"decisions": "decisions", "actions": "action_items"}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        while chunk := fh.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].casefold()


def sentences(xml: bytes) -> dict[str, list[str]]:
    """The DECISIONS and ACTIONS sentences of one abssumm.xml, as answers kinds -> texts."""
    root = ElementTree.fromstring(xml)
    out = {kind: [] for kind in SECTIONS.values()}
    for section in root.iter():
        kind = SECTIONS.get(local(section.tag))
        if kind is None:
            continue
        for node in section.iter():
            if local(node.tag) == "sentence":
                text = " ".join("".join(node.itertext()).split())
                if text:
                    out[kind].append(text)
    return out


def checked(path: Path, key: str, sources: dict) -> None:
    """Record the file's SHA-256 the first time, refuse a different file afterwards."""
    digest, size = sha256_file(path), path.stat().st_size
    known = sources.get(key)
    if known is None:
        sources[key] = {"sha256": digest, "size": size}
    elif known["sha256"] != digest:
        raise SystemExit(
            f"{path.name}: SHA-256 differs from eval/ami/{SOURCES.name} ({key}); delete it and fetch again"
        )


def fetch(meetings: list[str]) -> int:
    AMI.mkdir(parents=True, exist_ok=True)
    sources = json.loads(SOURCES.read_text()) if SOURCES.is_file() else {}
    archive = DOWNLOADS / "ami_public_manual_1.6.2.zip"
    timeout = httpx.Timeout(30.0, read=120.0)
    with httpx.Client(follow_redirects=True, timeout=timeout, headers={"User-Agent": "meeting-ami-set"}) as client:
        if not archive.is_file():
            resumable_get(client, ANNOTATIONS_URL, archive)
        checked(archive, archive.name, sources)
        with zipfile.ZipFile(archive) as z:
            names = z.namelist()
            for meeting in meetings:
                wanted = f"abstractive/{meeting}.abssumm.xml"  # at the top of the archive or in one folder
                member = next((n for n in names if n == wanted or n.endswith(f"/{wanted}")), None)
                if member is None:
                    raise SystemExit(f"{meeting}: no {wanted} in the annotations (only ES, IS and TS have one)")
                answers = sentences(z.read(member))
                if not any(answers.values()):  # the section names this script expects are not in the file
                    tags = sorted({local(e.tag) for e in ElementTree.fromstring(z.read(member))})
                    raise SystemExit(f"{meeting}: no DECISIONS or ACTIONS sentences; sections in the file: {tags}")
                target = AUDIO / f"{meeting}.wav"
                if not target.is_file():
                    resumable_get(client, AUDIO_URL.format(m=meeting), target)
                checked(target, f"{meeting}.Mix-Headset.wav", sources)
                doc = {
                    "id": meeting,
                    "title": f"AMI {meeting}: remote control design project",
                    "source": {
                        "licence": LICENCE,
                        "answers": f"ami_public_manual_1.6.2.zip, {wanted} (DECISIONS and ACTIONS)",
                        "audio": f"{meeting}.Mix-Headset.wav",
                    },
                    "answers": {kind: [{"text": t} for t in texts] for kind, texts in answers.items()},
                }
                (AMI / f"{meeting}.json").write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
                print(
                    f"{meeting}: {len(answers['decisions'])} decisions, {len(answers['action_items'])} actions, "
                    f"{target.stat().st_size / 1e6:.0f} MB of audio"
                )
    SOURCES.write_text(json.dumps(sources, indent=2, sort_keys=True) + "\n")
    return 0


def status() -> int:
    for path in sorted(AMI.glob("*.json")):
        if path == SOURCES:
            continue
        doc = json.loads(path.read_text())
        audio = AUDIO / f"{doc['id']}.wav"
        a = doc["answers"]
        print(
            f"{doc['id']:8} {len(a['decisions'])} decisions, {len(a['action_items'])} actions, "
            f"audio {'ok' if audio.is_file() else 'missing'}"
        )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=["fetch", "status"])
    parser.add_argument("meetings", nargs="*", metavar="ID")
    args = parser.parse_args()
    if args.command == "status":
        return status()
    meetings = args.meetings
    if not meetings:
        sets = json.loads((ROOT / "eval" / "sets.json").read_text())
        meetings = [m.removeprefix("ami:") for s in sets.values() for m in s if m.startswith("ami:")]
    return fetch(meetings)


if __name__ == "__main__":
    sys.exit(main())
