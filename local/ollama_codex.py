"""Adapt the local Ollama Responses stream for a Windows Codex workspace."""

from collections import deque
from contextlib import contextmanager
from http.client import HTTPConnection, HTTPException
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
from threading import Thread


LOOPBACK = "127.0.0.1"
RESPONSE_PATH = "/v1/responses"
PLACEHOLDER = r"C:\workspace"
SHELL_TOOLS = {"exec_command", "shell_command"}


def unique_object(pairs):
    value = dict(pairs)
    if len(value) != len(pairs):
        raise ValueError("Duplicate JSON object key")
    return value


def json_object(data):
    if isinstance(data, (str, bytes)):
        try:
            value = json.loads(data, object_pairs_hook=unique_object)
        except (ValueError, RecursionError):
            return {}
        if isinstance(value, dict):
            return value
    return {}


def shell_item(item):
    return (
        isinstance(item, dict)
        and item.get("type") == "function_call"
        and isinstance(item.get("name"), str)
        and item["name"] in SHELL_TOOLS
        and item.get("namespace") in (None, "", "functions")
    )


def correct_arguments(item, key, workspace):
    arguments = json_object(item.get(key))
    workdir = arguments.get("workdir")
    if not isinstance(workdir, str) or os.path.normcase(workdir.rstrip("\\/")) != os.path.normcase(PLACEHOLDER):
        return False
    try:
        Path(workdir).stat()
    except FileNotFoundError:
        arguments["workdir"] = str(workspace)
        item[key] = json.dumps(arguments, ensure_ascii=True)
        return True
    except OSError:
        pass
    return False


def correct_output(response, workspace):
    output = response.get("output") if isinstance(response, dict) else None
    if not isinstance(output, list):
        return False
    changed = False
    for item in output:
        if shell_item(item) and correct_arguments(item, "arguments", workspace):
            changed = True
    return changed


class StreamFrame:
    def __init__(self, lines):
        self.lines = lines
        self.data_indices = [index for index, line in enumerate(lines) if line.startswith(b"data:")]
        data = (lines[index][5:].removeprefix(b" ").rstrip(b"\r\n") for index in self.data_indices)
        self.event = json_object(b"\n".join(data))
        self.changed = False
        self.waiting = False

    def encode(self):
        if not self.changed:
            return b"".join(self.lines)
        first, *rest = self.data_indices
        line = self.lines[first]
        ending = line[len(line.rstrip(b"\r\n")):]
        self.lines[first] = b"data: " + json.dumps(self.event).encode("utf-8") + ending
        return b"".join(line for index, line in enumerate(self.lines) if index not in rest)


class ShellCall:
    def __init__(self, item_id, output_index):
        self.item_id = item_id
        self.output_index = output_index
        self.fragments = []

    def matches(self, item_id, output_index):
        if item_id is not None and self.item_id is not None:
            return item_id == self.item_id and (
                output_index is None or self.output_index is None or output_index == self.output_index
            )
        return output_index is not None and output_index == self.output_index

    def release(self, workspace):
        deltas = [frame.event.get("delta") for frame in self.fragments]
        if workspace is not None and all(isinstance(delta, str) for delta in deltas):
            joined = {"arguments": "".join(deltas)}
            if correct_arguments(joined, "arguments", workspace):
                remaining = joined["arguments"]
                last = len(deltas) - 1
                for index, (frame, delta) in enumerate(zip(self.fragments, deltas)):
                    # Keep each event in its original position and retain its sequence number.
                    size = len(remaining) if index == last else len(delta)
                    frame.event["delta"] = remaining[:size]
                    remaining = remaining[size:]
                    frame.changed = True
        for frame in self.fragments:
            frame.waiting = False
        self.fragments.clear()


def sse_frames(upstream):
    lines = []
    for line in upstream:
        lines.append(line)
        if line in (b"\n", b"\r\n"):
            yield StreamFrame(lines)
            lines = []
    if lines:
        yield StreamFrame(lines)


def response_chunks(upstream, workspace):
    shell_calls = []
    pending = deque()
    for frame in sse_frames(upstream):
        pending.append(frame)
        event = frame.event
        kind = event.get("type")
        item = event.get("item")
        output_index = event.get("output_index")
        output_index = output_index if type(output_index) is int else None
        if kind in ("response.output_item.added", "response.output_item.done") and shell_item(item):
            item_id = item.get("id")
            item_id = item_id if isinstance(item_id, str) else None
            if item_id is not None or output_index is not None:
                if kind == "response.output_item.added":
                    shell_calls.append(ShellCall(item_id, output_index))
                else:
                    call = next((call for call in shell_calls if call.matches(item_id, output_index)), None)
                    if call is not None:
                        call.release(workspace)
                        shell_calls.remove(call)
            frame.changed = correct_arguments(item, "arguments", workspace)
        elif kind in ("response.function_call_arguments.delta", "response.function_call_arguments.done"):
            item_id = event.get("item_id")
            item_id = item_id if isinstance(item_id, str) else None
            call = next((call for call in shell_calls if call.matches(item_id, output_index)), None)
            if call is not None and kind.endswith(".delta"):
                frame.waiting = True
                call.fragments.append(frame)
            elif call is not None:
                call.release(workspace)
                frame.changed = correct_arguments(event, "arguments", workspace)
        elif kind in ("response.completed", "response.incomplete", "response.failed"):
            for call in shell_calls:
                call.release(workspace)
            shell_calls.clear()
            frame.changed = correct_output(event.get("response"), workspace)
        while pending and not pending[0].waiting:
            yield pending.popleft().encode()
    yield from (frame.encode() for frame in pending)


class CodexProxyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.partition("?")[0] not in ("/v1/models", "/api/tags", "/api/version"):
            self.send_error(404)
            return
        self.forward()

    def do_POST(self):
        if self.path.partition("?")[0] not in (RESPONSE_PATH, "/v1/responses/compact"):
            self.send_error(404)
            return
        self.forward()

    def log_message(self, format, *args):
        pass

    def forward(self):
        if self.headers.get("Host") != f"{LOOPBACK}:{self.server.server_port}" or "Origin" in self.headers:
            self.send_error(403)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self.send_error(400)
            return
        if length < 0 or "Transfer-Encoding" in self.headers:
            self.send_error(400)
            return
        # The isolated Ollama listener accepts requests without Codex credentials.
        headers = {
            key: self.headers[key]
            for key in ("Accept", "Content-Type", "Content-Encoding")
            if key in self.headers
        }
        upstream = HTTPConnection(LOOPBACK, self.server.ollama_port, timeout=600)
        response_started = False
        try:
            upstream.request(self.command, self.path, body=self.rfile.read(length), headers=headers)
            with upstream.getresponse() as response:
                media_type = response.headers.get_content_type()
                content_encoding = response.headers.get("Content-Encoding")
                adapt = (
                    self.path.partition("?")[0] == RESPONSE_PATH
                    and response.status == 200
                    and content_encoding in (None, "identity")
                    and os.name == "nt"
                )
                response_started = True
                self.send_response(response.status)
                self.send_header("Content-Type", response.headers.get("Content-Type", media_type))
                if content_encoding:
                    self.send_header("Content-Encoding", content_encoding)
                self.end_headers()
                if media_type == "text/event-stream" and adapt:
                    for chunk in response_chunks(response, self.server.workspace):
                        self.wfile.write(chunk)
                elif media_type == "application/json" and adapt:
                    body = response.read()
                    document = json_object(body)
                    if correct_output(document, self.server.workspace):
                        body = json.dumps(document).encode("utf-8")
                    self.wfile.write(body)
                else:
                    while chunk := response.read1(64 * 1024):
                        self.wfile.write(chunk)
        except (OSError, HTTPException):
            if not response_started:
                self.send_error(502, "Could not reach the local Ollama server")
        finally:
            upstream.close()


@contextmanager
def codex_proxy(port, ollama_port, workspace):
    with ThreadingHTTPServer((LOOPBACK, port), CodexProxyHandler) as server:
        server.ollama_port = ollama_port
        server.workspace = workspace
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            yield
        finally:
            server.shutdown()
            thread.join()
