"""A deterministic stand-in for an OpenAI-compatible chat endpoint, for CI's pipeline test (D36). No model, no
network, standard library only.

uv run python scripts/fake_llm.py [--port 11434]       or, in a test:  FakeLLM().start() ... .stop()

POST /v1/chat/completions answers the way a model following this project's contract would, from the request alone:
- a request without `response_format: json_schema` and `strict: true`, or with a schema outside the strict subset
  (an object that does not list every property as required, or allows additional properties), gets 400: the same
  requests Azure OpenAI's strict mode refuses (D4);
- `meeting_summary`: one decision, the longest line of the <transcript> block word for word, with that line's time as
  its evidence; no action items, no open questions. The schema's own `evidence` enum must contain that time, or the
  answer is 400 (the request did not offer the transcript's times, D14);
- any other schema (the long-meeting merge): the smallest valid instance (strings "fake", empty lists, nulls);
- `next_status` (a list of HTTP codes, e.g. [500]) is used up one request at a time first: a test makes the model fail.
Every request is kept in `requests`. GET /health answers 200. It checks the request shape, not summary quality.
"""

import argparse
import json
import re
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

LINE = re.compile(r"^\[(\d+:\d{2}(?::\d{2})?)\] (?:Guest-\d+: )?(.+)$")


def strict_problems(schema: dict, where: str = "(root)") -> list[str]:
    """Where a schema leaves Azure OpenAI's strict subset: objects must require every property and forbid others."""
    problems = []
    if schema.get("type") == "object":
        props = schema.get("properties", {})
        if schema.get("additionalProperties") is not False:
            problems.append(f"{where}: additionalProperties must be false")
        if sorted(schema.get("required", [])) != sorted(props):
            problems.append(f"{where}: every property must be required")
        for name, sub in props.items():
            problems += strict_problems(sub, f"{where}.{name}")
    if "items" in schema:
        problems += strict_problems(schema["items"], f"{where}[]")
    for i, sub in enumerate(schema.get("anyOf", [])):
        problems += strict_problems(sub, f"{where}|{i}")
    return problems


def minimal(schema: dict):
    """The smallest instance of a strict schema."""
    if "anyOf" in schema:
        return minimal(schema["anyOf"][-1])  # this project puts null last
    kind = schema.get("type")
    if isinstance(kind, list):
        return None if "null" in kind else minimal({**schema, "type": kind[0]})
    if "enum" in schema:
        return schema["enum"][0]
    if kind == "object":
        return {name: minimal(sub) for name, sub in schema["properties"].items()}
    if kind == "array":
        return []
    if kind == "null":
        return None
    return "fake"


def evidence_enum(schema: dict) -> list[str]:
    decision = schema["properties"]["decisions"]["items"]["properties"]["evidence"]
    return next(s["enum"] for s in decision["anyOf"] if "enum" in s)


def transcript_lines(user: str) -> list[tuple[str, str]]:
    body = user.partition("<transcript>\n")[2].rpartition("\n</transcript>")[0]
    return [(m.group(1), m.group(2)) for m in map(LINE.match, body.splitlines()) if m]


def answer(body: dict) -> tuple[int, dict | str]:
    """(HTTP status, the message content as an object, or an error text)."""
    fmt = body.get("response_format") or {}
    spec = fmt.get("json_schema") or {}
    if fmt.get("type") != "json_schema" or spec.get("strict") is not True or "schema" not in spec:
        return 400, "response_format must be a strict json_schema"
    schema = spec["schema"]
    problems = strict_problems(schema)
    if problems:
        return 400, f"schema outside the strict subset: {problems[0]}"
    content = minimal(schema)
    if spec.get("name") == "meeting_summary":
        user = next((m["content"] for m in body.get("messages", []) if m.get("role") == "user"), "")
        lines = transcript_lines(user)
        if not lines:
            return 400, "no <transcript> lines in the user message"
        _, (when, text) = max(enumerate(lines), key=lambda x: (len(x[1][1].split()), -x[0]))  # longest, first
        if when not in evidence_enum(schema):
            return 400, f"evidence enum does not offer the transcript time {when}"
        item = minimal(schema["properties"]["decisions"]["items"])
        content.update(title="Fake summary", overview="A summary written by the CI stand-in model.")
        content["decisions"] = [{**item, "text": text, "evidence": when}]
    return 200, content


class FakeLLM:
    def __init__(self, port: int = 0) -> None:
        self.requests: list[dict] = []
        self.next_status: list[int] = []
        fake = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                self._send(200, {"status": "ok"}) if self.path == "/health" else self._send(404, {"error": "no"})

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
                fake.requests.append(body)
                if self.path != "/v1/chat/completions":
                    return self._send(404, {"error": {"message": "not found"}})
                if fake.next_status:
                    status = fake.next_status.pop(0)
                    return self._send(status, {"error": {"message": f"fake error {status}", "type": "fake"}})
                status, content = answer(body)
                if status != 200:
                    return self._send(status, {"error": {"message": content, "type": "invalid_request_error"}})
                self._send(
                    200,
                    {
                        "id": "chatcmpl-fake",
                        "object": "chat.completion",
                        "created": 0,
                        "model": body.get("model", "fake"),
                        "choices": [
                            {
                                "index": 0,
                                "finish_reason": "stop",
                                "message": {"role": "assistant", "content": json.dumps(content)},
                            }
                        ],
                        "usage": {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
                    },
                )

            def _send(self, status: int, payload: dict) -> None:
                data = json.dumps(payload).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def log_message(self, *args):
                pass

        self._server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
        self.url = f"http://127.0.0.1:{self._server.server_address[1]}/v1"

    def start(self) -> "FakeLLM":
        threading.Thread(target=self._server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True).start()
        return self

    def stop(self) -> None:
        self._server.shutdown()
        self._server.server_close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--port", type=int, default=11434)
    args = parser.parse_args()
    fake = FakeLLM(args.port)
    print(f"fake LLM on {fake.url}")
    try:
        fake._server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
