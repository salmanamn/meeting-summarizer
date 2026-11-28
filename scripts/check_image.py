"""Check the built image, then start it the way the platform's cluster will, without a network (D54).

uv run python scripts/check_image.py [--image meeting-summarizer:local] [--timeout 240]

Image (docker image inspect, and python3 inside it):
- user 10001:10001, port 8080, ASPNETCORE_URLS on 8080, MEETING_TRIGGER=queue (D55);
- the app's packages under .python_packages (Python 3.13 dependency isolation), the app itself, no local settings;
- the models lock in /opt/meeting-models, the same bytes as models.lock.json here, and the models Job's check runs
  (it must refuse: there are no models in the image, D56); the fake LLM in /opt/meeting-lab, and python3 runs it.
Host (one container: --network none, --user 10001:10001, all capabilities dropped, no new privileges; host keys as
files, read-only, AzureWebJobsSecretStorageType=kubernetes, the platform's D9):
- GET /api/health answers 200: the Python worker started and indexed the app (no exit 139);
- GET /admin/functions with the master key lists exactly the functions function_app.py registers with the queue
  trigger (no blob trigger);
- GET /api/meetings/m01-1 without a key: 401;
- the host log has no "exited with code" line.
No network on purpose: a host that downloads something at start would fail here, not as a pod that never gets
ready behind the cluster's default deny. Every line OK or FAIL; exit 1 on any FAIL. The container is removed.
"""

import argparse
import hashlib
import importlib
import json
import os
import secrets
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
USER = "10001:10001"
NAME = "meeting-image-check"
SITE = "/home/site/wwwroot/.python_packages/lib/site-packages"
PYTHONPATH = f"{SITE}:/home/site/wwwroot"
# Settings the host needs to index the app (values that go nowhere: there is no network).
SETTINGS = {
    "AzureWebJobsSecretStorageType": "kubernetes",
    "AzureWebJobsStorage": "UseDevelopmentStorage=true",
    "RecordingsStorage": "UseDevelopmentStorage=true",
}
PROBE = f"""
import hashlib, json, os
site = {SITE!r}
print(json.dumps({{
    "uid": os.getuid(), "gid": os.getgid(),
    "packages": sorted(n for n in os.listdir(site) if not n.endswith(".dist-info")),
    "app": sorted(os.listdir("/home/site/wwwroot")),
    "lab": sorted(os.listdir("/opt/meeting-lab")),
    "lock": hashlib.sha256(open("/opt/meeting-models/models.lock.json", "rb").read()).hexdigest(),
    "home_owner": os.stat("/home").st_uid,
}}))
"""
REQUEST = """
import os, sys, urllib.error, urllib.request
method, path = sys.argv[1:3]
headers = {"x-functions-key": os.environ["KEY"]} if os.environ.get("KEY") else {}
request = urllib.request.Request("http://127.0.0.1:8080" + path, method=method, headers=headers)
try:
    with urllib.request.urlopen(request, timeout=60) as response:
        print(response.status); print(response.read().decode())
except urllib.error.HTTPError as error:
    print(error.code); print(error.read().decode()[:200])
except OSError as error:
    print(0); print(type(error).__name__ + " (no HTTP answer)")
"""


def expected_functions() -> list[str]:
    """What function_app.py registers with the image's MEETING_TRIGGER=queue (so this check follows the code)."""
    if str(ROOT / "src") not in sys.path:
        sys.path.insert(0, str(ROOT / "src"))
    saved = os.environ.get("MEETING_TRIGGER")
    os.environ["MEETING_TRIGGER"] = "queue"
    try:
        import function_app

        app = importlib.reload(function_app).app
        names = sorted(f.get_function_name() for f in app.get_functions())
    finally:
        if saved is None:
            os.environ.pop("MEETING_TRIGGER")
        else:
            os.environ["MEETING_TRIGGER"] = saved
        importlib.reload(function_app)
    return names


def host_keys(functions: list[str]) -> dict[str, str]:
    """The key files the host reads (KubernetesSecretsRepository, file mode): the host's and one per function."""
    names = ["host.master", "host.function.default"] + [f"functions.{f.lower()}.default" for f in functions]
    return {name: secrets.token_urlsafe(32) for name in names}


def docker(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(["docker", *args], capture_output=True, text=True, check=False, env=env)  # noqa: S603, S607


def line(ok: bool, what: str, seen: str) -> str:
    return f"{'OK  ' if ok else 'FAIL'} {what}: {seen}"


def run_in(image: str, *args: str) -> subprocess.CompletedProcess:
    base = ["run", "--rm", "--network", "none", "-e", f"PYTHONPATH={PYTHONPATH}", "--entrypoint", "python3", image]
    return docker(*base, *args)


def check_image(image: str) -> list[str]:
    inspected = docker("image", "inspect", image, "--format", "{{json .Config}}")
    if inspected.returncode != 0:
        return [line(False, "image", inspected.stderr.strip()[-200:])]
    config = json.loads(inspected.stdout)
    env = dict(item.split("=", 1) for item in config.get("Env") or [])
    lines = [
        line(config.get("User") == USER, "configured user", config.get("User") or "root"),
        line(
            "8080/tcp" in (config.get("ExposedPorts") or {}),
            "exposed port",
            ", ".join(config.get("ExposedPorts") or {}),
        ),
        line(env.get("ASPNETCORE_URLS") == "http://+:8080", "host listens on", env.get("ASPNETCORE_URLS", "unset")),
        line(env.get("MEETING_TRIGGER") == "queue", "MEETING_TRIGGER", env.get("MEETING_TRIGGER", "unset")),
    ]
    probe = run_in(image, "-c", PROBE)
    if probe.returncode != 0:
        return [*lines, line(False, "probe inside the image", probe.stderr.strip()[-200:])]
    seen = json.loads(probe.stdout)
    packages = set(seen["packages"])
    lock = hashlib.sha256((ROOT / "models.lock.json").read_bytes()).hexdigest()
    lines += [
        line(f"{seen['uid']}:{seen['gid']}" == USER, "a process runs as", f"{seen['uid']}:{seen['gid']}"),
        line(
            {"azure", "openai", "pydantic", "faster_whisper", "av", "httpx"} <= packages,
            "app packages in .python_packages",
            f"{len(packages)} top-level",
        ),
        line("function_app.py" in seen["app"] and "meeting" in seen["app"], "app in wwwroot", ", ".join(seen["app"])),
        line(
            not any(n.startswith(("local.settings", "azure.settings")) for n in seen["app"]),
            "no settings files",
            "none",
        ),
        line(seen["lock"] == lock, "models lock is models.lock.json", seen["lock"][:12]),
        line(seen["lab"] == ["fake_llm.py"], "lab tools", ", ".join(seen["lab"])),
        line(seen["home_owner"] == 10001, "/home owned by", str(seen["home_owner"])),
    ]
    ran = run_in(image, "/opt/meeting-lab/fake_llm.py", "--help")
    lines.append(
        line(ran.returncode == 0 and "--host" in ran.stdout, "python3 fake_llm.py --help", f"exit {ran.returncode}")
    )
    ran = run_in(image, "-m", "meeting.fetch_job", "check", "stt-tiny")
    refused = ran.returncode == 1 and "FAIL stt-tiny" in ran.stdout
    lines.append(line(refused, "models check refuses an empty models dir", (ran.stdout or ran.stderr).strip()[-120:]))
    return lines


def request(method: str, path: str, key: str | None = None) -> tuple[int, str]:
    env = {**os.environ, "KEY": key or ""}
    result = docker("exec", "-e", "KEY", NAME, "python3", "-c", REQUEST, method, path, env=env)
    status, _, body = result.stdout.partition("\n")
    return (int(status) if status.strip().isdigit() else 0), body.strip()


def check_host(image: str, timeout: float) -> list[str]:
    functions = expected_functions()
    keys = host_keys(functions)
    with tempfile.TemporaryDirectory(prefix="meeting-keys-") as tmp:
        folder = Path(tmp)
        folder.chmod(0o755)
        for name, value in keys.items():
            (folder / name).write_text(value, encoding="utf-8")
            (folder / name).chmod(0o644)
        docker("rm", "-f", NAME)
        args = ["run", "-d", "--name", NAME, "--network", "none", "--user", USER, "--cap-drop", "ALL"]
        args += ["--security-opt", "no-new-privileges", "-v", f"{folder}:/run/secrets/functions-keys:ro"]
        for name, value in SETTINGS.items():
            args += ["-e", f"{name}={value}"]
        started = docker(*args, image)
        if started.returncode != 0:
            return [line(False, "host container started", started.stderr.strip()[-200:])]
        try:
            deadline = time.monotonic() + timeout
            status, waited = 0, time.monotonic()
            while time.monotonic() < deadline:
                status, _ = request("GET", "/api/health")
                if status == 200:
                    break
                time.sleep(3)
            lines = [line(status == 200, "GET /api/health", f"{status} after {time.monotonic() - waited:.0f} s")]
            status, body = request("GET", "/admin/functions", keys["host.master"])
            listed = sorted(f["name"] for f in json.loads(body)) if status == 200 else []
            lines.append(line(listed == functions, "functions loaded", ", ".join(listed) or f"HTTP {status}"))
            status, _ = request("GET", "/api/meetings/m01-1")
            lines.append(line(status == 401, "GET /api/meetings/m01-1 without a key", str(status)))
            logs = docker("logs", NAME)
            text = logs.stdout + logs.stderr
            crashed = [entry for entry in text.splitlines() if "exited with code" in entry]
            lines.append(line(not crashed, "worker never exited", crashed[0][-160:] if crashed else "no exit"))
            if any(entry.startswith("FAIL") for entry in lines):
                lines += ["--- last 40 log lines ---", *text.splitlines()[-40:]]
            return lines
        finally:
            docker("rm", "-f", NAME)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--image", default="meeting-summarizer:local")
    parser.add_argument("--timeout", type=float, default=240, help="seconds to wait for the host (default 240)")
    args = parser.parse_args()
    lines = check_image(args.image)
    print("\n".join(lines), flush=True)
    if not any(entry.startswith("FAIL") for entry in lines):
        host = check_host(args.image, args.timeout)
        print("\n".join(host))
        lines += host
    failures = sum(entry.startswith("FAIL") for entry in lines)
    print(f"FAIL {failures} check(s)" if failures else "IMAGE CHECKS PASSED")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
