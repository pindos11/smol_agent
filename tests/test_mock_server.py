import importlib.util
import json
from pathlib import Path
import threading
import unittest
from http.server import ThreadingHTTPServer
from urllib.request import Request, urlopen


MODULE_PATH = Path(__file__).parents[1] / "manual_testing" / "mock_server.py"
SPEC = importlib.util.spec_from_file_location("mock_server", MODULE_PATH)
mock_server = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mock_server)


def streamed_deltas(scenario):
    lines = list(mock_server.iter_chunks(scenario, [], None))
    data_lines = [line for line in lines if line.startswith("data: {")]
    return [json.loads(line[6:])["choices"][0] for line in data_lines]


class TestMockServerChunks(unittest.TestCase):
    def test_explicit_chunk_keeps_all_mixed_delta_fields_together(self):
        scenario = {
            "chunks": [{
                "reasoning_content": "reason",
                "content": "answer",
                "tool_calls": [{"index": 0, "id": "call_1", "type": "function",
                                "function": {"name": "powershell", "arguments": "{}"}}],
            }],
            "finish_reason": "tool_calls",
        }

        choices = streamed_deltas(scenario)
        self.assertEqual(choices[0]["delta"], scenario["chunks"][0])
        self.assertEqual(choices[1]["delta"], {})
        self.assertEqual(choices[1]["finish_reason"], "tool_calls")

    def test_legacy_fragment_has_openai_tool_call_start_then_argument_updates(self):
        scenario = {
            "tool_calls": [{"index": 0, "id": "call_1",
                            "function": {"name": "powershell", "arguments": {"command": "echo hi"}}}],
            "chunk_tool_args": True,
        }

        calls = [choice["delta"]["tool_calls"][0]
                 for choice in streamed_deltas(scenario)
                 if "tool_calls" in choice["delta"]]
        self.assertEqual(calls[0]["id"], "call_1")
        self.assertEqual(calls[0]["type"], "function")
        self.assertEqual(calls[0]["function"]["name"], "powershell")
        self.assertTrue(all("id" not in call for call in calls[1:]))
        self.assertEqual("".join(call["function"]["arguments"] for call in calls),
                         '{"command": "echo hi"}')

    def test_invalid_explicit_chunk_fails_with_a_useful_error(self):
        with self.assertRaisesRegex(ValueError, "tool_calls"):
            list(mock_server.iter_chunks({"chunks": [{"tool_calls": {}}]}, [], None))

    def test_non_streaming_response_uses_chat_completions_shape(self):
        response = mock_server._completion_response({
            "content": ["hello"],
            "tool_calls": [{"index": 0, "id": "call_1",
                            "function": {"name": "powershell", "arguments": {"command": "echo hi"}}}],
            "finish_reason": "tool_calls",
        })
        self.assertEqual(response["object"], "chat.completion")
        choice = response["choices"][0]
        self.assertEqual(choice["message"]["role"], "assistant")
        self.assertEqual(choice["message"]["content"], "hello")
        self.assertEqual(choice["message"]["tool_calls"][0]["function"]["arguments"],
                         '{"command": "echo hi"}')

    def test_http_non_streaming_request_returns_json_not_sse(self):
        original = mock_server.Handler.scenarios
        mock_server.Handler.scenarios = {"default": {"content": ["hello"]}}
        server = ThreadingHTTPServer(("127.0.0.1", 0), mock_server.Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            request = Request(
                f"http://127.0.0.1:{server.server_port}/v1/chat/completions",
                data=b'{"model":"mock-model","messages":[]}',
                headers={"Content-Type": "application/json"}, method="POST")
            with urlopen(request) as response:
                self.assertEqual(response.headers.get_content_type(), "application/json")
                payload = json.load(response)
            self.assertEqual(payload["object"], "chat.completion")
            self.assertEqual(payload["choices"][0]["message"]["content"], "hello")
        finally:
            server.shutdown()
            server.server_close()
            thread.join()
            mock_server.Handler.scenarios = original


if __name__ == "__main__":
    unittest.main()
