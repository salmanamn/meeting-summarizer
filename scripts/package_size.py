"""What a Flex Consumption deployment package of this app would weigh (D19), without Azure.

uv run python scripts/package_size.py [--out docs/evidence/m2-package-size.md]

Installs src/requirements.txt for Linux x86-64 / Python 3.13 (the Flex runtime) into a temporary folder with uv,
adds the app's own code, zips it like a deployment package, and reports the sizes, plus the Whisper model that
running speech to text inside the Function would need (models/<STT_MODEL>).
"""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from datetime import UTC, datetime
from pathlib import Path

from meeting.settings import load

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"


def size_of(path: Path) -> int:
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())


def mb(n: int) -> str:
    return f"{n / 1e6:.0f} MB"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    settings = load()
    with tempfile.TemporaryDirectory() as tmp:
        site = Path(tmp) / "app" / ".python_packages" / "lib" / "site-packages"
        command = [
            "uv", "pip", "install", "--quiet", "--target", str(site), "-r", str(SRC / "requirements.txt"),
            "--python-platform", "x86_64-manylinux_2_28", "--python-version", "3.13",
        ]  # fmt: skip
        subprocess.run(command, check=True)  # noqa: S603 (fixed command)
        shutil.copytree(SRC / "meeting", Path(tmp) / "app" / "meeting", ignore=shutil.ignore_patterns("__pycache__"))
        for name in ("function_app.py", "host.json", "requirements.txt"):
            shutil.copy(SRC / name, Path(tmp) / "app" / name)
        packages = size_of(site)
        biggest = sorted(((size_of(p), p.name) for p in site.iterdir() if p.is_dir()), reverse=True)[:6]
        archive = Path(tmp) / "package.zip"
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
            for f in (Path(tmp) / "app").rglob("*"):
                if f.is_file():
                    z.write(f, f.relative_to(Path(tmp) / "app"))
        zipped = archive.stat().st_size
        unpacked = size_of(Path(tmp) / "app")
    model_dir = settings.stt_model_dir if settings.stt_model_dir.is_absolute() else ROOT / settings.stt_model_dir
    model = size_of(model_dir) if model_dir.is_dir() else 0

    lines = [
        f"- packages for Linux x86-64, Python 3.13: {mb(packages)} unpacked",
        f"- largest: {', '.join(f'{name} {mb(n)}' for n, name in biggest)}",
        f"- app package: {mb(unpacked)} unpacked, {mb(zipped)} as a zip",
        f"- Whisper model {settings.stt_model}: {mb(model)}" + ("" if model else " (not on this disk)"),
        f"- package + model: {mb(unpacked + model)} unpacked",
    ]
    print("\n".join(lines))
    if args.out:
        text = [
            "# M2: the size of a Functions deployment package with Whisper in it",
            "",
            f"- Date: {datetime.now(UTC):%Y-%m-%d %H:%M} UTC, `src/requirements.txt` (groups stt, storage, function)",
            *lines,
            "",
        ]
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text("\n".join(text), encoding="utf-8")
        print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    os.environ.setdefault("UV_NO_PROGRESS", "1")
    sys.exit(main())
