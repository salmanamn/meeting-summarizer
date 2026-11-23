"""What a Flex Consumption deployment package of this app would weigh (D19), without Azure; and, in CI, a gate on it.

uv run python scripts/package_size.py [--out docs/evidence/m3-package-size.md]
uv run python scripts/package_size.py --max-zip-mb 200 --forbid torch,onnxruntime-gpu,piper-tts,pytest,ruff   (CI)

Installs src/requirements.txt for Linux x86-64 / Python 3.13 (the Flex runtime) into a temporary folder with uv,
adds the app's own code, zips it like a deployment package, and reports the sizes, plus the Whisper model that
running speech to text inside the Function would need (models/<STT_MODEL>).

The gate (D37), exit 1 when it fails: the zip is at most --max-zip-mb, and none of the --forbid distributions is in
the package (PyTorch and the GPU ONNX Runtime that D22 kept out, Piper (GPL, test meetings only, D10), the dev tools).
"""

import argparse
import os
import re
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


def canonical(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def installed(site: Path) -> set[str]:
    """Distribution names in a --target folder, from their `<name>-<version>.dist-info` directories."""
    return {canonical(d.name.removesuffix(".dist-info").rsplit("-", 1)[0]) for d in site.glob("*.dist-info")}


def gate(zipped: int, dists: set[str], max_zip_mb: float | None, forbidden: list[str]) -> list[str]:
    """What breaks the package rules (D37); an empty list means the package passes."""
    problems = [f"{name} is in the package" for name in sorted({canonical(f) for f in forbidden} & dists)]
    if max_zip_mb is not None and zipped > max_zip_mb * 1e6:
        problems.append(f"the zip is {mb(zipped)}, over the {max_zip_mb:.0f} MB budget")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--max-zip-mb", type=float, help="fail when the zip is larger (MB, 10^6 bytes)")
    parser.add_argument("--forbid", default="", help="comma-separated distributions that must not be in the package")
    args = parser.parse_args()
    forbidden = [name.strip() for name in args.forbid.split(",") if name.strip()]
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
        dists = installed(site)
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
            "# The size of a Functions deployment package with Whisper and the attachment readers in it",
            "",
            f"- Date: {datetime.now(UTC):%Y-%m-%d %H:%M} UTC, `src/requirements.txt` (groups stt, storage, function, "
            "docs)",
            *lines,
            "",
        ]
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text("\n".join(text), encoding="utf-8")
        print(f"wrote {args.out}")
    problems = gate(zipped, dists, args.max_zip_mb, forbidden)
    if args.max_zip_mb is not None or forbidden:
        for problem in problems:
            print(f"FAIL {problem}")
        if not problems:
            budget = f"zip {mb(zipped)} <= {args.max_zip_mb:.0f} MB" if args.max_zip_mb is not None else "no budget"
            print(f"PACKAGE OK   {len(dists)} distributions, {budget}, none of {', '.join(forbidden) or '-'}")
    return 1 if problems else 0


if __name__ == "__main__":
    os.environ.setdefault("UV_NO_PROGRESS", "1")
    sys.exit(main())
