"""The evidence scripts against fake `az` and `gh` (M8, D51): telemetry.sh goes on after a failed query, and
run_evidence.sh keeps a run's result lines without the commands GitHub echoes or terraform's colours."""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
pytestmark = pytest.mark.skipif(not (shutil.which("bash") and shutil.which("jq")), reason="needs bash and jq")

FAKE_AZ = r'''#!PYTHON
"""A stand-in for az: the workspace and the operator resolve, the stack is gone, queries answer one row."""
import json, os, sys
args = sys.argv[1:]
if args[:3] == ["monitor", "log-analytics", "workspace"]:
    print("00000000-0000-0000-0000-00000000aaaa")
elif args[:2] in (["identity", "show"], ["cognitiveservices", "account"]):
    print("ERROR: (ResourceGroupNotFound) Resource group 'rg-meet-azure' could not be found.", file=sys.stderr)
    sys.exit(3)
elif args[:3] == ["ad", "signed-in-user", "show"]:
    print("11111111-2222-3333-4444-555555555555")
elif args[:1] == ["rest"]:
    query = json.loads(args[args.index("--body") + 1])["query"]
    with open(os.environ["FAKE_AZ_QUERIES"], "a") as f:
        f.write(query.replace("\n", " ") + "\n")
    fail = os.environ.get("FAKE_AZ_FAIL")
    if fail and fail in query:
        print('ERROR: Bad Request({"error":{"message":"The request had some invalid properties"}})', file=sys.stderr)
        sys.exit(1)
    if query.endswith("| count"):
        print(json.dumps({"tables": [{"columns": [{"name": "Count"}], "rows": [[7]]}]}))
    else:
        print(json.dumps({"tables": [{"columns": [{"name": "Name"}, {"name": "rows"}], "rows": [["x", 7]]}]}))
else:
    sys.exit(f"fake az: unexpected {args}")
'''

FAKE_GH = r"""#!PYTHON
import os, sys
assert sys.argv[1:3] == ["run", "view"] and sys.argv[4] == "--log", sys.argv
sys.stdout.write(open(os.environ["FAKE_GH_LOG"], encoding="utf-8").read())
"""

ESC = "\x1b"
FLEX = "module.stack.module.functionapp[0].azurerm_function_app_flex_consumption.this"
STAMP = "2026-11-24T23:10:01.1234567Z"
RUN_LOG = "".join(
    f"plan\t{step}\t{STAMP} {line}\n"
    for step, line in [
        ("terraform plan", f"{ESC}[36;1m  terraform plan -lock-timeout=5m -detailed-exitcode -out=tfplan{ESC}[0m"),
        ("terraform plan", "##[group]Run terraform plan"),
        ("terraform plan", f"  {ESC}[1m# {FLEX}{ESC}[0m will be updated in-place"),
        ("terraform plan", f"{ESC}[1mPlan:{ESC}[0m {ESC}[0m1 to add, 1 to change, 0 to destroy."),
        (
            "Policy gate",
            f'{ESC}[36;1mconftest test --no-color --policy ../../policy plan.json | grep -E "^FAIL|tests,"{ESC}[0m',
        ),
        ("Policy gate", "50 tests, 50 passed, 0 warnings, 0 failures, 0 exceptions"),
        ("apply", f"Apply complete! Resources: 1 added, 1 changed, 0 destroyed.{ESC}[0m"),
        ("apply", f'{ESC}[36;1mtest "$x" = 0 && echo "OK   nothing left"{ESC}[0m'),
        ("apply", "OK   removed azurerm's key-based AzureWebJobsStorage from func-meet-azure-q9406 and restarted it"),
    ]
)


def fake_bin(tmp_path: Path, name: str, body: str) -> None:
    path = tmp_path / "bin" / name
    path.parent.mkdir(exist_ok=True)
    path.write_text(body.replace("#!PYTHON", f"#!{sys.executable}"), encoding="utf-8")
    path.chmod(0o755)


def run(tmp_path: Path, script: str, *args: str, **env: str) -> subprocess.CompletedProcess:
    full = {**os.environ, "PATH": f"{tmp_path / 'bin'}{os.pathsep}{os.environ['PATH']}", **env}
    return subprocess.run(  # noqa: S603
        [shutil.which("bash"), str(ROOT / "scripts" / script), *args],
        env=full,
        capture_output=True,
        text=True,
        timeout=60,
    )


@pytest.fixture
def az(tmp_path):
    fake_bin(tmp_path, "az", FAKE_AZ)
    queries = tmp_path / "queries.txt"
    queries.touch()
    return queries


def test_telemetry_goes_on_after_a_failed_query(tmp_path, az):
    done = run(
        tmp_path, "telemetry.sh", "2026-11-24T22:52:26Z", "m7-", FAKE_AZ_QUERIES=str(az), FAKE_AZ_FAIL="AppExceptions"
    )
    assert done.returncode == 0, done.stderr
    out = done.stdout
    exceptions = out.split("== Exceptions")[1].split("\n==")[0]
    assert "query failed: ERROR: Bad Request" in exceptions
    for section in ("by table (one query each)", "AzureDiagnostics by provider", "Recordings account", "Event Grid"):
        assert f"{section}" in out, section  # every section after the failed one still ran
    assert "identities looked up: app no, speech no" in out


def test_telemetry_counts_each_table_with_its_own_query(tmp_path, az):
    done = run(
        tmp_path, "telemetry.sh", "2026-11-24T22:52:26Z", FAKE_AZ_QUERIES=str(az), FAKE_AZ_FAIL="StorageQueueLogs"
    )
    assert done.returncode == 0, done.stderr
    tables = done.stdout.split("one query each)\n")[1].split("\n\n")[0].splitlines()
    assert [line.split()[0] for line in tables] == [
        "AzureDiagnostics", "CDBDataPlaneRequests", "StorageBlobLogs", "StorageQueueLogs", "FunctionAppLogs",
        "AEGDeliveryFailureLogs", "AEGDataPlaneRequests",
    ]  # fmt: skip
    assert "query failed" in tables[3] and tables[2].split() == ["StorageBlobLogs", "7"]
    assert not any("union" in q for q in az.read_text().splitlines())


def test_telemetry_after_the_destroy_reads_a_fixed_window_and_labels_unknown_callers(tmp_path, az):
    done = run(tmp_path, "telemetry.sh", "2026-11-24T22:52:26Z", "m7-", "2026-11-25T01:00:00Z", FAKE_AZ_QUERIES=str(az))
    assert done.returncode == 0, done.stderr
    queries = az.read_text().splitlines()
    assert all("between (datetime(2026-11-24T22:52:26Z) .. datetime(2026-11-25T01:00:00Z))" in q for q in queries)
    (recordings,) = [q for q in queries if "StorageBlobLogs" in q and "Caller" in q]
    assert "RequesterObjectId == ''" not in recordings  # an unknown identity must not match anonymous requests
    assert "strcat('other ', substring(RequesterObjectId, 0, 8))" in recordings and "UserAgentHeader" in recordings
    (traces,) = [q for q in queries if q.startswith("AppTraces")]
    assert "startswith 'Request URL:'" in traces and "startswith 'Request ['" in traces
    assert run(tmp_path, "telemetry.sh", "2026-11-24", FAKE_AZ_QUERIES=str(az)).returncode == 2


def test_run_evidence_keeps_the_results_and_drops_echoed_commands_and_colours(tmp_path):
    fake_bin(tmp_path, "gh", FAKE_GH)
    log = tmp_path / "run.log"
    log.write_text(RUN_LOG, encoding="utf-8")
    pattern = "Plan:|tests,|OK   |Apply complete|will be"
    done = run(tmp_path, "run_evidence.sh", "E3 apply", "45508935508", pattern, FAKE_GH_LOG=str(log))
    assert done.returncode == 0, done.stderr
    assert done.stdout.splitlines() == [
        "## E3 apply (run 45508935508)",
        "```",
        f"  # {FLEX} will be updated in-place",
        "Plan: 1 to add, 1 to change, 0 to destroy.",
        "50 tests, 50 passed, 0 warnings, 0 failures, 0 exceptions",
        "Apply complete! Resources: 1 added, 1 changed, 0 destroyed.",
        "OK   removed azurerm's key-based AzureWebJobsStorage from func-meet-azure-q9406 and restarted it",
        "```",
        "",
    ]
    nothing = run(tmp_path, "run_evidence.sh", "E3", "45508935508", "no such line", FAKE_GH_LOG=str(log))
    assert nothing.returncode == 1 and "no line of run 45508935508 matches" in nothing.stderr
    assert run(tmp_path, "run_evidence.sh", "E3", "run-1", pattern, FAKE_GH_LOG=str(log)).returncode == 2
