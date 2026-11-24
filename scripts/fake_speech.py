"""A stand-in for Azure AI Speech batch transcription (REST API 2025-10-15), for the unit and CI tests of the Speech
transcriber (D45). No audio is transcribed: every succeeded job answers the documented result in
tests/fixtures/speech/. Standard library only.

uv run python scripts/fake_speech.py [--port 6200]        or, in a test:  FakeSpeech().start() ... .stop()

What it does, from the API reference and the batch transcription how-to pages (not recorded from the service; M7 is
the first run against the real one):
- POST /speechtotext/transcriptions:submit (201, the job `NotStarted`), GET /speechtotext/transcriptions/<id>
  (`Running` for `running_polls` polls, then the outcome), GET …/<id>/files (the result files), DELETE …/<id> (204);
  a job deleted, or never created, is 404;
- every call to those paths must carry `Authorization: Bearer …` (401 otherwise);
- the result files are served under /_content/<id>/, standing in for the SAS URLs on Microsoft-managed storage: a
  request there WITH an Authorization header is refused with 400, so a client that leaks its token fails;
- `outcome`: succeeded | failed-audio (InvalidAudioFormat, permanent) | failed-transient (InternalServerError) |
  report-only (the job succeeds, the recording doesn't: only the report, with its errorKind);
- `next_status` (a list of HTTP codes, e.g. [503]) is used up one API request at a time first.
Every request is kept in `requests` as (method, path, had a token); every submitted body in `submitted`.
"""

import argparse
import json
import sys
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

FIXTURES = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "speech"
PREFIX = "/speechtotext/transcriptions"
FIXTURE_JOB_ID = "ba7ea6f5-3065-40b7-b49a-a90f48584683"
TERMINAL = {
    "succeeded": ("job-succeeded.json", "files.json"),
    "report-only": ("job-succeeded.json", "files-report-only.json"),
    "failed-audio": ("job-failed-audio.json", None),
    "failed-transient": ("job-failed-transient.json", None),
}


class FakeSpeech:
    def __init__(self, port: int = 0) -> None:
        self.requests: list[tuple[str, str, bool]] = []
        self.submitted: list[dict] = []
        self.jobs: dict[str, dict] = {}  # id -> {"polls": n, "outcome": ..., "audio": url, "deleted": bool}
        self.next_status: list[int] = []
        self.running_polls = 0
        self.outcome = "succeeded"
        fake = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                self._route("GET")

            def do_POST(self):
                self._route("POST")

            def do_DELETE(self):
                self._route("DELETE")

            def _route(self, method: str) -> None:
                path = urlsplit(self.path).path
                token = self.headers.get("Authorization", "").startswith("Bearer ")
                fake.requests.append((method, path, token))
                if path.startswith("/_content/"):
                    return self._content(path, token)
                if not path.startswith(PREFIX):
                    return self._send(404, {"error": {"code": "NotFound", "message": "no such path"}})
                if not token:
                    return self._send(401, {"error": {"code": "Unauthorized", "message": "no bearer token"}})
                if fake.next_status:
                    status = fake.next_status.pop(0)
                    return self._send(status, {"error": {"code": "ServiceUnavailable", "message": f"fake {status}"}})
                if method == "POST" and path == f"{PREFIX}:submit":
                    return self._submit()
                rest = path[len(PREFIX) + 1 :].split("/")
                job = fake.jobs.get(rest[0])
                if job is None or job["deleted"]:
                    return self._send(404, {"error": {"code": "NotFound", "message": "no such transcription"}})
                if method == "DELETE" and len(rest) == 1:
                    job["deleted"] = True
                    return self._send(204, None)
                if method == "GET" and len(rest) == 1:
                    return self._job(rest[0], job)
                if method == "GET" and rest[1:] == ["files"]:
                    files = TERMINAL[job["outcome"]][1]
                    return self._send(200, fake.fixture(files, rest[0], job)) if files else self._send(404, {})
                return self._send(404, {"error": {"code": "NotFound", "message": "no such path"}})

            def _submit(self) -> None:
                body = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
                fake.submitted.append(body)
                missing = [k for k in ("displayName", "locale", "contentUrls", "properties") if k not in body]
                if missing:
                    return self._send(400, {"error": {"code": "InvalidRequest", "message": f"missing {missing}"}})
                job_id = str(uuid.uuid4())
                job = {"polls": 0, "outcome": fake.outcome, "audio": body["contentUrls"][0], "deleted": False}
                fake.jobs[job_id] = job
                self._send(201, fake.fixture("job-notstarted.json", job_id, job))

            def _job(self, job_id: str, job: dict) -> None:
                job["polls"] += 1
                if job["polls"] <= fake.running_polls:
                    return self._send(200, fake.fixture("job-running.json", job_id, job))
                self._send(200, fake.fixture(TERMINAL[job["outcome"]][0], job_id, job))

            def _content(self, path: str, token: bool) -> None:
                if token:  # a SAS URL on someone else's storage: the client's token must never go there
                    return self._send(400, {"error": {"code": "InvalidRequest", "message": "token sent to storage"}})
                _, _, job_id, name = path.split("/", 3)
                job = fake.jobs.get(job_id)
                if job is None or job["deleted"] or not (FIXTURES / name).is_file():
                    return self._send(404, {})
                self._send(200, fake.fixture(name, job_id, job))

            def _send(self, status: int, payload) -> None:
                data = b"" if payload is None else json.dumps(payload).encode()
                self.send_response(status)
                if payload is not None:
                    self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def log_message(self, *args):
                pass

        self._server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
        self.url = f"http://127.0.0.1:{self._server.server_address[1]}"

    def fixture(self, name: str, job_id: str, job: dict) -> dict:
        """A documented answer, with this server's origin, the job's id, its content URL and its audio filled in."""
        text = (FIXTURES / name).read_text(encoding="utf-8")
        text = text.replace("{origin}", self.url).replace(FIXTURE_JOB_ID, job_id)
        text = text.replace("{content}", f"{self.url}/_content/{job_id}").replace("{audio}", job["audio"])
        return json.loads(text)

    def api_calls(self) -> list[tuple[str, str]]:
        return [(m, p) for m, p, _ in self.requests if p.startswith(PREFIX)]

    def start(self) -> "FakeSpeech":
        threading.Thread(target=self._server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True).start()
        return self

    def stop(self) -> None:
        self._server.shutdown()
        self._server.server_close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--port", type=int, default=6200)
    parser.add_argument("--running-polls", type=int, default=2)
    args = parser.parse_args()
    fake = FakeSpeech(args.port)
    fake.running_polls = args.running_polls
    print(f"fake Speech on {fake.url}")
    try:
        fake._server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
