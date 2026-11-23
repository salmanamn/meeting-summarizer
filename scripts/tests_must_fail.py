"""Tests must fail: apply known-bad changes one at a time and require the unit tests to catch each one (D35).

Each mutation breaks one promise the project makes: nothing but a manifest starts a job; every file is checked
(size, type from its bytes, SHA-256, length) before any model runs; a duplicate delivery redoes nothing, a retry
reuses the stored transcript, attempts are bounded and a model error waits; the schema is strict and its evidence
can only be the transcript's times; grounding removes owners, deadlines, decisions and repeats the meeting did not
say; the transcript cannot close its own block; an answer cut off is refused; long meetings keep a question unless a
later item answers it; attachments are checked before Docling or pypdfium2 reads them; reasoning models get their
own request shape; the status endpoint shows no Cosmos system fields; the package gate catches what must not ship.

The script works on a temporary copy of the repository (tracked and new files, not ignored ones), so the working
tree is never changed. Exit 1 when a mutation survives (the tests still pass: add a test), when its anchor text is
no longer in the code (update the mutation together with the code), or when the clean copy fails.

Usage: uv run python scripts/tests_must_fail.py [--only NAME] [--list]
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUMMARY = re.compile(r"(\d+) failed")


@dataclass(frozen=True)
class Mutation:
    name: str
    file: str
    old: str
    new: str
    tests: str  # pytest target that must fail


MUTATIONS = [
    Mutation(
        "any-blob-starts-a-job",
        "src/meeting/manifest.py",
        "if len(parts) != 2 or parts[1] != MANIFEST_NAME or not",
        "if len(parts) != 2 or not",
        "tests/unit/test_manifest.py",
    ),
    Mutation(
        "size-not-compared",
        "src/meeting/job.py",
        "            if info.size != ref.size:",
        "            if False:",
        "tests/unit/test_job.py",
    ),
    Mutation(
        "type-from-the-name",
        "src/meeting/job.py",
        "            if kind is None:\n                allowed",
        "            if kind is None and False:\n                allowed",
        "tests/unit/test_job.py",
    ),
    Mutation(
        "hash-not-compared",
        "src/meeting/job.py",
        '            if sha != ref.sha256:\n                raise Rejected("hash_mismatch", f"{ref.name}: the SHA-256',
        '            if False:\n                raise Rejected("hash_mismatch", f"{ref.name}: the SHA-256',
        "tests/unit/test_job.py",
    ),
    Mutation(
        "no-length-limit",
        "src/meeting/job.py",
        "        if seconds > self.s.max_recording_seconds:",
        "        if False:",
        "tests/unit/test_job.py",
    ),
    Mutation(
        "duplicate-redone",
        "src/meeting/job.py",
        'if job["stage"] == "summarised" or (job["stage"] == "failed" and not error.get("retryable")):',
        'if job["stage"] == "failed" and not error.get("retryable"):',
        "tests/unit/test_job.py",
    ),
    Mutation(
        "transcript-not-reused",
        "src/meeting/job.py",
        "        stored = self.blobs.read_text(self.s.transcripts_container, name)\n        if stored is not None:",
        "        stored = None\n        if stored is not None:",
        "tests/unit/test_job.py",
    ),
    Mutation(
        "attempts-unbounded",
        "src/meeting/job.py",
        "        if attempt > limit:",
        "        if False:",
        "tests/unit/test_job.py",
    ),
    Mutation(
        "model-error-retried-at-once",
        "src/meeting/job.py",
        "                self.sleep(delay)",
        "                pass",
        "tests/unit/test_job.py",
    ),
    Mutation(
        "schema-allows-extra-fields",
        "src/meeting/summary.py",
        '"required": list(properties), "additionalProperties": False}',
        '"required": list(properties), "additionalProperties": True}',
        "tests/unit/test_summary.py",
    ),
    Mutation(
        "evidence-any-string",
        "src/meeting/summary.py",
        "    evidence = _one_of(stamps)",
        "    evidence = _NULLABLE",
        "tests/unit/test_summary.py",
    ),
    Mutation(
        "owner-not-checked",
        "src/meeting/summary.py",
        "            if not said:",
        "            if False:",
        "tests/unit/test_summary.py",
    ),
    Mutation(
        "due-not-checked",
        "src/meeting/summary.py",
        "        if due is not None and not contains_phrase(transcript.text, due):",
        "        if False:",
        "tests/unit/test_summary.py",
    ),
    Mutation(
        "undecided-kept",
        "src/meeting/summary.py",
        "        if NOT_DECIDED.search(d.text):",
        "        if False:",
        "tests/unit/test_summary.py",
    ),
    Mutation(
        "repeated-action-kept-as-decision",
        "src/meeting/summary.py",
        "        if twin is not None:",
        "        if False:",
        "tests/unit/test_summary.py",
    ),
    Mutation(
        "transcript-closes-its-block",
        "src/meeting/summarize.py",
        "    body = clean(transcript.timestamped())",
        "    body = transcript.timestamped()",
        "tests/unit/test_summarize.py",
    ),
    Mutation(
        "cut-off-answer-accepted",
        "src/meeting/summarize.py",
        '    if completion.finish_reason == "length":',
        "    if False:",
        "tests/unit/test_summarize.py",
    ),
    Mutation(
        "answered-question-taken-on-trust",
        "src/meeting/summarize.py",
        "        if any(covers(question.question, t) > ANSWERED for t in later):",
        "        if True:",
        "tests/unit/test_summarize.py",
    ),
    Mutation(
        "encrypted-docx-read",
        "src/meeting/documents.py",
        "    if any(m.flag_bits & 0x1 for m in members):",
        "    if False:",
        "tests/unit/test_documents.py",
    ),
    Mutation(
        "pdf-pages-unbounded",
        "src/meeting/documents.py",
        "            if pages > self.max_pages:",
        "            if False:",
        "tests/unit/test_documents.py",
    ),
    Mutation(
        "reasoning-model-gets-temperature",
        "src/meeting/llm.py",
        "        if self.reasoning_effort:\n",
        "        if False:\n",
        "tests/unit/test_summarize.py",
    ),
    Mutation(
        "status-shows-system-fields",
        "src/meeting/job.py",
        '    return {k: v for k, v in doc.items() if not k.startswith("_")}',
        "    return dict(doc)",
        "tests/unit/test_function_app.py",
    ),
    Mutation(
        "package-gate-ignores-forbidden",
        "scripts/package_size.py",
        'problems = [f"{name} is in the package" for name in sorted({canonical(f) for f in forbidden} & dists)]',
        "problems = []",
        "tests/unit/test_package_size.py",
    ),
]


def copy_tree(dest: Path) -> None:
    """The files git would see (tracked, and new ones not ignored), as they are on disk now."""
    listed = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],  # noqa: S607
        cwd=ROOT,
        capture_output=True,
        check=True,
    ).stdout.decode()
    for name in filter(None, listed.split("\0")):
        src = ROOT / name
        if src.is_file():
            (dest / name).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest / name)


def pytest(cwd: Path, target: str) -> tuple[int, str]:
    cmd = [sys.executable, "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider", target]
    # The project is installed in the venv as an editable package pointing at the real src/: put the copy first.
    env = {**os.environ, "PYTHONPATH": os.pathsep.join([str(cwd / "src"), str(cwd / "scripts")])}
    proc = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, timeout=600)  # noqa: S603
    lines = [line for line in proc.stdout.splitlines() if line.strip()]
    return proc.returncode, lines[-1] if lines else proc.stderr.strip()[-200:]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--only", help="run a single mutation by name")
    parser.add_argument("--list", action="store_true", help="list the mutations and exit")
    args = parser.parse_args()
    mutations = [m for m in MUTATIONS if not args.only or m.name == args.only]
    if args.list or not mutations:
        for m in MUTATIONS:
            print(f"{m.name:34} {m.file}")
        return 0 if args.list else 2

    with tempfile.TemporaryDirectory(prefix="tests-must-fail-") as tmp:
        work = Path(tmp)
        copy_tree(work)
        code, summary = pytest(work, "tests/unit")
        if code != 0:
            print(f"ERROR    baseline: unit tests fail on the unmodified copy ({summary})")
            return 1
        print(f"OK       baseline: {summary}")

        problems = 0
        for m in mutations:
            path = work / m.file
            original = path.read_text(encoding="utf-8")
            if original.count(m.old) != 1:
                print(f"STALE    {m.name:34} anchor found {original.count(m.old)}x in {m.file}; update the mutation")
                problems += 1
                continue
            path.write_text(original.replace(m.old, m.new), encoding="utf-8")
            try:
                code, summary = pytest(work, m.tests)
            finally:
                path.write_text(original, encoding="utf-8")
            if code == 1 and SUMMARY.search(summary):
                print(f"KILLED   {m.name:34} {m.tests}")
            elif code == 0:
                print(f"SURVIVED {m.name:34} {m.tests} still passes: add a test for this behaviour")
                problems += 1
            else:
                print(f"ERROR    {m.name:34} pytest exit {code} (not a test failure): {summary}")
                problems += 1

    print(f"{len(mutations) - problems}/{len(mutations)} mutations killed")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
