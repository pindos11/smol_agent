import json
import unittest

from agent_tools import agentToolCall, agentToolsChunkParser


class TestAgentToolCall(unittest.TestCase):
    def test_init_without_args(self):
        tool = agentToolCall(index=0, id="call_1")
        self.assertEqual(tool.index, 0)
        self.assertEqual(tool.id, "call_1")
        self.assertIsNone(tool.name)
        self.assertIsNone(tool.args)
        self.assertEqual(tool.command, "")
        self.assertEqual(tool.partName, "")
        self.assertEqual(tool.partArgs, "")

    def test_init_with_args(self):
        args = json.dumps({"command": "ls", "path": "/"})
        tool = agentToolCall(index=0, id="call_1", name="bash", args=args)
        self.assertEqual(tool.name, "bash")
        self.assertEqual(tool.args, args)
        self.assertEqual(tool.command, "ls")

    def test_set_args_valid_json(self):
        tool = agentToolCall(index=0, id="call_1")
        args = json.dumps({"command": "echo", "text": "hi"})
        tool.setArgs(args)
        self.assertEqual(tool.args, args)
        self.assertEqual(tool.command, "echo")

    def test_set_args_none(self):
        tool = agentToolCall(index=0, id="call_1")
        tool.setArgs(None)
        self.assertIsNone(tool.args)
        self.assertEqual(tool.command, "")

    def test_set_args_invalid_json(self):
        tool = agentToolCall(index=0, id="call_1")
        with self.assertRaises(json.JSONDecodeError):
            tool.setArgs("not json")

    def test_finalize(self):
        tool = agentToolCall(index=0, id="call_1")
        tool.partName = "bash"
        tool.partArgs = json.dumps({"command": "pwd"})
        tool.finalize()
        self.assertEqual(tool.name, "bash")
        self.assertEqual(tool.args, tool.partArgs)
        self.assertEqual(tool.command, "pwd")

    def test_finalize_invalid_json(self):
        tool = agentToolCall(index=0, id="call_1")
        tool.partName = "bash"
        tool.partArgs = "not json"
        with self.assertRaises(json.JSONDecodeError):
            tool.finalize()

    def test_compose_self(self):
        tool = agentToolCall(index=0, id="call_1", name="bash", args='{"command":"ls"}')
        result = tool.composeSelf()
        expected = {
            "id": "call_1",
            "type": "function",
            "function": {
                "name": "bash",
                "arguments": '{"command":"ls"}',
            },
        }
        self.assertEqual(result, expected)


class TestAgentToolsChunkParser(unittest.TestCase):
    def setUp(self):
        self.parser = agentToolsChunkParser()

    def test_process_chunks_new_tool(self):
        chunks = [
            [
                {"index": 0, "id": "call_1", "function": {"name": "bash", "arguments": '{"command":"ls"}'}},
            ]
        ]
        tools = self.parser.processChunks(chunks)
        self.assertEqual(len(tools), 1)
        self.assertEqual(tools[0].id, "call_1")
        self.assertEqual(tools[0].name, "bash")
        self.assertEqual(tools[0].command, "ls")

    def test_process_chunks_missing_index(self):
        chunks = [[{"function": {"name": "bash"}}]]
        tools = self.parser.processChunks(chunks)
        self.assertEqual(len(tools), 0)

    def test_process_chunks_new_tool_missing_id(self):
        chunks = [
            [
                {"index": 0, "function": {"name": "bash", "arguments": '{}'}},
            ]
        ]
        tools = self.parser.processChunks(chunks)
        self.assertEqual(len(tools), 0)

    def test_process_chunks_append_to_existing(self):
        # simulates streaming JSON arguments that concatenate into valid JSON
        chunks = [
            [
                {"index": 0, "id": "call_1", "function": {"name": "ba", "arguments": '{"command"'}},
            ],
            [
                {"index": 0, "function": {"name": "sh", "arguments": ': "ls"}'}},
            ],
        ]
        tools = self.parser.processChunks(chunks)
        self.assertEqual(len(tools), 1)
        self.assertEqual(tools[0].name, "bash")
        self.assertEqual(tools[0].args, '{"command": "ls"}')
        parsed = json.loads(tools[0].args)
        self.assertEqual(parsed["command"], "ls")

    def test_process_chunks_multiple_tools(self):
        chunks = [
            [
                {"index": 0, "id": "call_1", "function": {"name": "bash", "arguments": '{"command":"ls"}'}},
                {"index": 1, "id": "call_2", "function": {"name": "bash", "arguments": '{"command":"pwd"}'}},
            ]
        ]
        tools = self.parser.processChunks(chunks)
        self.assertEqual(len(tools), 2)
        self.assertEqual(tools[0].id, "call_1")
        self.assertEqual(tools[0].command, "ls")
        self.assertEqual(tools[1].id, "call_2")
        self.assertEqual(tools[1].command, "pwd")


if __name__ == "__main__":
    unittest.main()
