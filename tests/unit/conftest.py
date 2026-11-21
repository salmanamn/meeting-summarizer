"""Shared test helpers: a transcript factory and a local OpenAI-compatible chat endpoint."""

import json
import threading
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from factories import make_transcript

from meeting.transcript import Transcript


@pytest.fixture
def transcript() -> Transcript:
    return make_transcript(
        (0.0, 6.5, "Good morning. Omar, please send the numbers by Wednesday."),
        (7.0, 12.0, "Sure, I will send them by Wednesday."),
        (13.0, 20.0, "Then we release on the fifteenth of March. Agreed."),
        (75.0, 80.0, "Who presents at the all hands? We will come back to that."),
    )


@dataclass
class ChatServer:
    url: str
    answer: str | None = "{}"
    finish_reason: str = "stop"
    status: int = 200
    requests: list[dict] = field(default_factory=list)


@pytest.fixture
def chat():
    """An OpenAI-compatible /v1/chat/completions that records each request and returns `chat.answer`."""
    state = ChatServer(url="")

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            state.requests.append({"path": self.path, "auth": self.headers.get("Authorization"), "body": body})
            if state.status != 200:
                payload = {"error": {"message": "test error", "type": "test", "code": None}}
            else:
                payload = {
                    "id": "chatcmpl-test",
                    "object": "chat.completion",
                    "created": 0,
                    "model": body["model"],
                    "choices": [
                        {
                            "index": 0,
                            "finish_reason": state.finish_reason,
                            "message": {"role": "assistant", "content": state.answer},
                        }
                    ],
                    "usage": {"prompt_tokens": 120, "completion_tokens": 80, "total_tokens": 200},
                }
            data = json.dumps(payload).encode()
            self.send_response(state.status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True).start()
    state.url = f"http://127.0.0.1:{server.server_address[1]}/v1"
    yield state
    server.shutdown()
    server.server_close()
