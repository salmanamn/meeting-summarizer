"""Fetch model files and keep models.lock.json (see src/meeting/modelstore.py).

uv run python scripts/fetch_models.py                  status of every model in the catalog
uv run python scripts/fetch_models.py NAME [NAME ...]  download the locked revision, or the newest + a new lock entry
uv run python scripts/fetch_models.py --update NAME    move NAME's lock entry to the newest revision
uv run python scripts/fetch_models.py --verify         compare every locked model on disk with the lock
"""

import argparse
import sys
from pathlib import Path

from meeting.modelstore import CATALOG, LOCK_FILE, HuggingFaceHub, IntegrityError, fetch, read_lock, verify, write_lock
from meeting.settings import load

ROOT = Path(__file__).resolve().parents[1]


def status(models_dir: Path, lock: dict) -> None:
    for name, spec in CATALOG.items():
        entry = lock.get(name)
        revision = entry["revision"][:12] if entry else "not locked"
        if not (models_dir / name).is_dir():
            disk = "not downloaded"
        elif entry is None:
            disk = "on disk, no lock entry"
        else:
            problems = verify(name, models_dir, lock)
            disk = "ok" if not problems else f"{len(problems)} problem(s), run --verify"
        print(f"{name:22} {spec.repo:46} {revision:12}  {disk}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("names", nargs="*", metavar="NAME", help=", ".join(CATALOG))
    parser.add_argument(
        "--update", action="store_true", help="re-resolve the newest revision and rewrite the lock entry"
    )
    parser.add_argument(
        "--verify", action="store_true", help="check models on disk against the lock; exit 1 on a difference"
    )
    args = parser.parse_args()
    unknown = [name for name in args.names if name not in CATALOG]
    if unknown:
        parser.error(f"unknown model {', '.join(unknown)} (choose from {', '.join(CATALOG)})")

    models_dir = load().models_dir
    lock_path = ROOT / LOCK_FILE
    lock = read_lock(lock_path)

    if args.verify:
        names = args.names or [name for name in lock if (models_dir / name).is_dir()]
        problems = [problem for name in names for problem in verify(name, models_dir, lock)]
        for problem in problems:
            print(f"FAIL {problem}")
        print(f"{len(names) - len({p.split(':')[0] for p in problems})}/{len(names)} models match {LOCK_FILE}")
        return 1 if problems else 0

    if not args.names:
        status(models_dir, lock)
        return 0

    hub = HuggingFaceHub()
    for name in args.names:
        was_locked = name in lock and not args.update
        try:
            entry = fetch(name, models_dir, lock, hub, update=args.update)
        except IntegrityError as exc:
            print(f"FAIL {exc}")
            return 1
        write_lock(lock_path, lock)
        megabytes = sum(f["size"] for f in entry["files"].values()) / 1e6
        how = "matches the lock" if was_locked else f"new entry written to {LOCK_FILE}"
        source = f"{entry['repo']} @ {entry['revision'][:12]}"
        print(f"OK   {name}: {source}, {len(entry['files'])} files, {megabytes:.0f} MB, {how}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
