import json
import unittest

from agent_messages import modelMessage, modelTextContext
from agent_tools import agentToolCall


class TestModelMessage(unittest.TestCase):
    def test_init_basic(self):
        msg = modelMessage(role="user", content="hi")
        self.assertEqual(msg.role, "user")
        self.assertEqual(msg.content, "hi")
        self.assertIsNone(msg.reasoning)
        self.assertIsNone(msg.toolCalls)
        self.assertIsNone(msg.toolResults)
        self.assertIsNone(msg.toolCallId)

    def test_compose_self_content_only(self):
        msg = modelMessage(role="user", content="hi")
        result = msg.composeSelf()
        self.assertEqual(result, {"role": "user", "content": "hi"})

    def test_compose_self_with_reasoning(self):
        msg = modelMessage(role="assistant", content="hi", reasoning="thinking")
        result = msg.composeSelf()
        self.assertEqual(result, {"role": "assistant", "content": "hi", "reasoning_content": "thinking"})

    def test_compose_self_reasoning_empty(self):
        msg = modelMessage(role="assistant", reasoning="")
        result = msg.composeSelf()
        self.assertEqual(result, {"role": "assistant", "reasoning_content": ""})

    def test_compose_self_reasoning_want_reasoning_false(self):
        # want_reasoning=False has no effect when reasoning is not None
        msg = modelMessage(role="assistant", reasoning="thinking")
        result = msg.composeSelf(want_reasoning=False)
        self.assertEqual(result, {"role": "assistant", "reasoning_content": "thinking"})

    def test_compose_self_all_none(self):
        msg = modelMessage(role="user")
        result = msg.composeSelf()
        self.assertIsNone(result)

    def test_compose_self_tool_calls(self):
        tool = agentToolCall(index=0, id="call_1", name="bash", args='{"command":"ls"}')
        msg = modelMessage(role="assistant", toolCalls=[tool])
        result = msg.composeSelf()
        expected = {
            "role": "assistant",
            "tool_calls": [
                {
                    "id": "call_1",
                    "type": "function",
                    "function": {"name": "bash", "arguments": '{"command":"ls"}'},
                }
            ],
        }
        self.assertEqual(result, expected)

    def test_compose_self_tool_results(self):
        msg = modelMessage(role="tool", toolResults={"output": "done"}, tRID="call_1")
        result = msg.composeSelf()
        expected = {
            "role": "tool",
            "tool_call_id": "call_1",
            "content": json.dumps({"output": "done"}),
        }
        self.assertEqual(result, expected)


class TestModelTextContext(unittest.TestCase):
    def setUp(self):
        self.ctx = modelTextContext()

    def test_add_message(self):
        msg = modelMessage(role="user", content="hi")
        self.ctx.add_message(msg)
        self.assertEqual(len(self.ctx.messages), 1)
        self.assertIs(self.ctx.messages[0], msg)

    def test_compose_self(self):
        self.ctx.add_message(modelMessage(role="user", content="hi"))
        self.ctx.add_message(modelMessage(role="assistant", content="bye"))
        result = self.ctx.composeSelf()
        self.assertEqual(
            result,
            [
                {"role": "user", "content": "hi"},
                {"role": "assistant", "content": "bye"},
            ],
        )

    def test_compose_self_with_reasoning(self):
        self.ctx.add_message(modelMessage(role="assistant", content="hi", reasoning="thinking"))
        result = self.ctx.composeSelf()
        self.assertEqual(
            result,
            [{"role": "assistant", "content": "hi", "reasoning_content": "thinking"}],
        )


if __name__ == "__main__":
    unittest.main()
