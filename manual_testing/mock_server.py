#!/usr/bin/env python3
"""
OpenAI-compatible MOCK chat server for manual testing of agent.py.

It streams real Server-Sent-Events (SSE) exactly the way agent_answer.py
expects them, but the content is fully configurable and benign.

Run:
    python manual_testing/mock_server.py --port 9090

Then point agent at it (config.json already does by default):
    http://127.0.0.1:9090/v1/chat/completions

Choosing a scenario
--------------------
The scenario that gets served is chosen in this order:
  1. ?scenario=<name>   query param on the request URL  (force one)
  2. keyword match      a scenario whose "keywords" list
                        appears (case-insensitive) in the last user message
  3. default            the scenario named "default"

Editing responses
------------------
Edit scenarios.json in this folder. Each scenario is a declarative description
of what to stream:
{
  "scenario_name": {
    "description": "what this scenario is for",
    "keywords": ["tool", "commands"],   // optional, for auto-selection
    "reasoning": ["thinking", " token"],// optional reasoning deltas
    "content":   ["hello"],             // optional content deltas
    "tool_calls":[                      // optional tool-call deltas
       {"id":"call_1","function":{"name":"powershell",
           "arguments":{"command":"echo one"}}},
       ...
    ],
    "chunks": [                         // optional: exact delta fields per SSE chunk
      {"reasoning_content": "thinking", "content": "answer",
       "tool_calls": [{"index": 0, "id": "call_1", "type": "function",
                       "function": {"name": "powershell", "arguments": "{...}"}}]}
    ],
    "chunk_tool_args": true,            // legacy shorthand: split each tool's args
    "finish_reason": "tool_calls"       // "tool_calls" or "stop"
  }
}

When `chunks` is present, its entries are emitted in order and each entry is
used verbatim as `choices[0].delta`.  It is therefore the preferred way to
exercise combinations of `reasoning_content`, `content`, and `tool_calls` in
the same chunk.  Otherwise the legacy shorthand emits reasoning, content, and
tool calls in that order.  Both forms end with a finish chunk and `[DONE]`.
"""

import argparse
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

HERE = os.path.dirname(os.path.abspath(__file__))
SCENARIOS_PATH = os.path.join(HERE, "scenarios.json")

DEFAULT_SCENARIO = "default"


def load_scenarios():
    try:
        with open(SCENARIOS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"[mock_server] {SCENARIOS_PATH} not found, using empty scenario set")
        return {}
    except json.JSONDecodeError as e:
        print(f"[mock_server] Could not parse {SCENARIOS_PATH}: {e}")
        return {}
    if not isinstance(data, dict):
        print("[mock_server] scenarios.json must be a JSON object of scenarios")
        return {}
    return data


def choose_scenario(scenarios, messages, forced):
    if forced:
        if forced in scenarios:
            return forced
        print(f"[mock_server] forced scenario '{forced}' not found -> using default")
        return DEFAULT_SCENARIO

    # keyword match against the last user (or any non-system) message
    last_text = ""
    for m in reversed(messages):
        role = m.get("role")
        content = m.get("content")
        if role in ("user", "assistant") and isinstance(content, str):
            last_text = content
            break

    lowered = last_text.lower()
    for name, sc in scenarios.items():
        for kw in sc.get("keywords", []):
            if kw.lower() in lowered:
                return name

    if DEFAULT_SCENARIO in scenarios:
        return DEFAULT_SCENARIO
    # fall back to whatever is first
    return next(iter(scenarios), None)


def iter_chunks(scenario, messages, forced):
    """Yield raw SSE 'data: ' lines (str) for the chosen scenario."""
    parts = []

    # `chunks` deliberately maps one-to-one to OpenAI's `delta` object.  Do
    # not split its fields apart: providers may coalesce any of these updates.
    explicit_chunks = scenario.get("chunks")
    if explicit_chunks is not None:
        if not isinstance(explicit_chunks, list):
            raise ValueError("scenario 'chunks' must be a list of delta objects")
        for number, delta in enumerate(explicit_chunks):
            if not isinstance(delta, dict):
                raise ValueError(f"scenario chunk {number} must be an object")
            _validate_delta(delta, number)
            parts.append(_delta_chunk(delta))
    else:
        parts.extend(_legacy_chunks(scenario))

    # A finish reason belongs on a chunk with an empty delta in the standard
    # Chat Completions stream.  Some providers coalesce it with a delta, but
    # keeping it separate makes the default mock usable by strict clients too.
    finish = scenario.get("finish_reason", "stop")
    parts.append(_delta_chunk({}, finish_reason=finish))
    parts.append("data: [DONE]")

    for p in parts:
        yield p
        yield "\n"


def _legacy_chunks(scenario):
    """Produce the old shorthand format using canonical tool-call fragments."""
    parts = []

    # 1) reasoning deltas
    for tok in scenario.get("reasoning", []):
        parts.append(_delta_chunk({"reasoning_content": tok}))

    # 2) content deltas
    for tok in scenario.get("content", []):
        parts.append(_delta_chunk({"content": tok}))

    # 3) tool-call deltas
    for tc in scenario.get("tool_calls", []):
        args = tc.get("function", {}).get("arguments")
        args_str = json.dumps(args) if args is not None else None
        name = tc.get("function", {}).get("name")
        id_ = tc.get("id")
        index = tc.get("index", 0)

        # OpenAI nests tool calls under delta.tool_calls as a LIST.  The first
        # fragment identifies the call; following fragments only append JSON
        # argument text.  This is the shape emitted by the OpenAI SDK.
        if scenario.get("chunk_tool_args") and id_ is not None and args_str is not None:
            chunks = _split_str(args_str, max(1, len(args_str) // 3 + 1))
            for i, frag in enumerate(chunks):
                call = {"index": index, "function": {"arguments": frag}}
                if i == 0:
                    call.update({"id": id_, "type": "function"})
                    call["function"]["name"] = name
                delta = {"tool_calls": [call]}
                parts.append(_delta_chunk(delta))
        else:
            delta = {"tool_calls": [{"index": index, "id": id_, "type": "function",
                                     "function": {"name": name, "arguments": args_str}}]}
            parts.append(_delta_chunk(delta))

    return parts


def _validate_delta(delta, number):
    allowed = {"role", "content", "reasoning_content", "tool_calls", "refusal"}
    unknown = set(delta) - allowed
    if unknown:
        raise ValueError(f"scenario chunk {number} has unsupported delta field(s): {sorted(unknown)}")
    if "tool_calls" in delta and not isinstance(delta["tool_calls"], list):
        raise ValueError(f"scenario chunk {number} field 'tool_calls' must be a list")


def _split_str(s, n):
    if n <= 0:
        return [s]
    return [s[i:i + n] for i in range(0, len(s), n)]


def _delta_chunk(delta, finish_reason=None):
    obj = {
        "id": "chatcmpl-mock",
        "object": "chat.completion.chunk",
        "created": 0,
        "model": "mock-model",
        "choices": [
            {
                "index": 0,
                "delta": delta,
                "finish_reason": finish_reason,
            }
        ],
    }
    return "data: " + json.dumps(obj)


class Handler(BaseHTTPRequestHandler):
    scenarios = {}

    def log_message(self, fmt, *args):
        sys.stderr.write("[mock_server] " + (fmt % args) + "\n")

    def do_GET(self):
        # OpenAI health/style probe; keep it friendly.
        parsed = urlparse(self.path)
        if parsed.path.rstrip("/") in ("/v1/models", "/models"):
            models = [{"id": "mock-model", "object": "model", "created": 0,
                       "owned_by": "mock"}]
            body = json.dumps({"object": "list", "data": models}).encode()
            self._send(body, "application/json")
        else:
            body = b'{"ok":true,"server":"mock_openai"}'
            self._send(body, "application/json")

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path.rstrip("/") not in ("/v1/chat/completions", "/chat/completions"):
            self._send(b'{"error":"wrong endpoint"}', "application/json", 404)
            return

        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b"{}"
        try:
            req = json.loads(raw)
        except json.JSONDecodeError:
            self._send(b'{"error":"bad json"}', "application/json", 400)
            return

        messages = req.get("messages", [])
        qs = parse_qs(parsed.query)
        forced = qs.get("scenario", [None])[0]

        scenario_name = choose_scenario(self.scenarios, messages, forced)
        if scenario_name is None or scenario_name not in self.scenarios:
            body = json.dumps(
                {"error": f"no scenario '{scenario_name}'",
                 "available": list(self.scenarios)}).encode()
            self._send(body, "application/json", 404)
            return

        scenario = self.scenarios[scenario_name]
        print(f"[mock_server] -> scenario '{scenario_name}' "
              f"(forced={forced!r}) for role={self._last_role(messages)}")

        # Chat Completions returns an ordinary completion unless the caller
        # opted into streaming.  Supporting this is important for compatibility
        # with the OpenAI SDK and other clients, not just agent.py.
        if not req.get("stream", False):
            try:
                body = json.dumps(_completion_response(scenario)).encode("utf-8")
            except ValueError as exc:
                self._send_error(str(exc), 400)
                return
            self._send(body, "application/json")
            return

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        # One completion = one response; close so clients see a clean EOF.
        self.send_header("Connection", "close")
        self.close_connection = True
        self.end_headers()

        try:
            for line in iter_chunks(scenario, messages, forced):
                self.wfile.write(line.encode("utf-8"))
                self.wfile.write(b"\n")
            self.wfile.flush()
        except ValueError as exc:
            # Headers have already been sent, so this can only be logged here.
            # Validate scenarios with --list before using them in a request.
            print(f"[mock_server] invalid scenario '{scenario_name}': {exc}")

    @staticmethod
    def _last_role(messages):
        for m in reversed(messages):
            if m.get("role"):
                return m.get("role")
        return "user"

    def _send(self, body, ctype, code=200):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_error(self, message, code):
        # Match OpenAI's top-level error envelope closely enough for standard
        # client error handling.
        body = json.dumps({"error": {"message": message, "type": "invalid_request_error",
                                     "param": None, "code": None}}).encode("utf-8")
        self._send(body, "application/json", code)


def _completion_response(scenario):
    """Build the non-streaming Chat Completions response for SDK clients."""
    deltas = scenario.get("chunks")
    if deltas is None:
        deltas = []
        for event in _legacy_chunks(scenario):
            deltas.append(json.loads(event[6:])["choices"][0]["delta"])
    else:
        for number, delta in enumerate(deltas):
            if not isinstance(delta, dict):
                raise ValueError(f"scenario chunk {number} must be an object")
            _validate_delta(delta, number)

    content = []
    reasoning = []
    calls = {}
    for delta in deltas:
        if delta.get("content") is not None:
            content.append(delta["content"])
        if delta.get("reasoning_content") is not None:
            reasoning.append(delta["reasoning_content"])
        for call in delta.get("tool_calls", []):
            index = call.get("index")
            if index is None:
                continue
            current = calls.setdefault(index, {"index": index, "id": call.get("id"),
                                               "type": call.get("type", "function"),
                                               "function": {"name": "", "arguments": ""}})
            if call.get("id") is not None:
                current["id"] = call["id"]
            function = call.get("function") or {}
            if function.get("name") is not None:
                current["function"]["name"] += function["name"]
            if function.get("arguments") is not None:
                current["function"]["arguments"] += function["arguments"]

    message = {"role": "assistant", "content": "".join(content) or None}
    if reasoning:
        # Intentional vendor extension; it is never required by the OpenAI SDK.
        message["reasoning_content"] = "".join(reasoning)
    if calls:
        message["tool_calls"] = [calls[index] for index in sorted(calls)]
    return {
        "id": "chatcmpl-mock",
        "object": "chat.completion",
        "created": 0,
        "model": "mock-model",
        "choices": [{"index": 0, "message": message,
                     "finish_reason": scenario.get("finish_reason", "stop")}],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }


def main():
    parser = argparse.ArgumentParser(description="Mock OpenAI streaming server")
    parser.add_argument("--port", type=int, default=9090)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--list", action="store_true",
                        help="list available scenarios and exit")
    args = parser.parse_args()

    Handler.scenarios = load_scenarios()

    if args.list:
        print("Available scenarios:")
        for name, sc in Handler.scenarios.items():
            desc = sc.get("description", "")
            print(f"  - {name}: {desc}")
        return

    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"[mock_server] listening on http://{args.host}:{args.port}/v1/chat/completions")
    print(f"[mock_server] scenarios: {list(Handler.scenarios.keys())}")
    print("[mock_server] force one with ?scenario=<name>; press Ctrl+C to stop")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[mock_server] stopping")
        server.shutdown()


if __name__ == "__main__":
    main()
