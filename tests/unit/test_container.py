"""The container image (D54): what the Dockerfile and the image check must keep true."""

import importlib.util
import re
from pathlib import Path

import pytest

from meeting import fetch_job

ROOT = Path(__file__).resolve().parents[2]
DOCKERFILE = (ROOT / "Dockerfile").read_text()


def load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_base_image_is_pinned_by_digest():
    (line,) = [entry for entry in DOCKERFILE.splitlines() if entry.startswith("FROM ")]
    assert re.fullmatch(r"FROM mcr\.microsoft\.com/azure-functions/python:4-python3\.13@sha256:[0-9a-f]{64}", line)


def test_image_runs_as_a_fixed_user_on_8080_with_the_queue_trigger():
    assert re.search(r"^USER 10001:10001$", DOCKERFILE, re.M)
    assert "ASPNETCORE_URLS=http://+:8080" in DOCKERFILE
    assert "MEETING_TRIGGER=queue" in DOCKERFILE  # D55: no Event Grid webhook into a cluster


def test_packages_go_where_the_python_3_13_worker_looks():
    assert "--target /home/site/wwwroot/.python_packages/lib/site-packages -r /tmp/requirements.txt" in DOCKERFILE
    assert "COPY src/requirements.txt /tmp/requirements.txt" in DOCKERFILE  # the Flex package's requirements (D37)


def test_only_the_app_the_lock_and_the_fake_llm_are_in_the_build_context():
    ignore = [entry for entry in (ROOT / ".dockerignore").read_text().splitlines() if entry and entry[0] != "#"]
    assert ignore[0] == "*"  # everything is excluded first
    assert {p for p in ignore if p.startswith("!")} == {"!src/", "!models.lock.json", "!scripts/fake_llm.py"}
    assert {"src/local.settings.json", "src/local.settings.json.example", "src/azure.settings.json"} <= set(ignore)


def test_the_image_lock_is_the_repository_lock():
    """The chart's Job reads the lock baked into the image; it must be the committed one."""
    assert "COPY models.lock.json /opt/meeting-models/models.lock.json" in DOCKERFILE
    assert "MODELS_LOCK=/opt/meeting-models/models.lock.json" in DOCKERFILE
    assert fetch_job.DEFAULT_LOCK == "/opt/meeting-models/models.lock.json"


def test_host_keys_cover_every_function():
    functions = ["health", "meeting_queue_job", "meeting_status"]
    keys = load("check_image").host_keys(functions)
    assert {"host.master", "host.function.default"} <= set(keys)
    assert {f"functions.{f}.default" for f in functions} <= set(keys)
    assert len(set(keys.values())) == len(keys) and all(len(v) >= 40 for v in keys.values())


def test_the_image_check_expects_the_queue_trigger():
    assert load("check_image").expected_functions() == ["health", "meeting_queue_job", "meeting_status"]


def test_pinning_rewrites_only_the_from_line():
    pin = load("pin_base_image")
    digest = "sha256:" + "a" * 64
    text = "# base\nFROM mcr.microsoft.com/azure-functions/python:4-python3.13\nUSER 10001:10001\n"
    once = pin.pinned(text, digest)
    assert once == f"# base\nFROM mcr.microsoft.com/azure-functions/python:4-python3.13@{digest}\nUSER 10001:10001\n"
    assert pin.pinned(once, "sha256:" + "b" * 64).count("@sha256:") == 1
    with pytest.raises(SystemExit):
        pin.base("FROM a:1\nFROM b:2\n")


def test_the_fake_llm_listens_on_the_address_it_is_given():
    fake = load("fake_llm").FakeLLM(0, "0.0.0.0")  # noqa: S104
    try:
        assert fake._server.server_address[0] == "0.0.0.0"  # noqa: S104
    finally:
        fake._server.server_close()
