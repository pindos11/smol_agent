import json
import sys
import unittest
from unittest.mock import patch, MagicMock

import agent_definitions
from agent_tools import agentToolCall
from agent_tools_runner import agentToolRunner


def make_tool(name="powershell", command="echo test", tool_id="call_1"):
    args = json.dumps({"command": command}) if command else None
    return agentToolCall(index=0, id=tool_id, name=name, args=args)


class TestAgentToolRunnerValidate(unittest.TestCase):
    def test_validate_valid_tool(self):
        runner = agentToolRunner(make_tool())
        self.assertEqual(runner.validateTool(), 0)

    def test_validate_empty_command(self):
        runner = agentToolRunner(make_tool(command=""))
        self.assertEqual(runner.validateTool(), 2)

    def test_validate_none_command(self):
        tool = agentToolCall(index=0, id="call_1", name="powershell", args=None)
        tool.command = None
        runner = agentToolRunner(tool)
        self.assertEqual(runner.validateTool(), 2)

    def test_validate_wrong_tool_name(self):
        runner = agentToolRunner(make_tool(name="bash"))
        self.assertEqual(runner.validateTool(), 3)

    def test_validate_empty_id(self):
        tool = agentToolCall(index=0, id="", name="powershell", args='{"command":"echo test"}')
        runner = agentToolRunner(tool)
        self.assertEqual(runner.validateTool(), 1)

    def test_validate_none_id(self):
        tool = agentToolCall(index=0, id=None, name="powershell", args='{"command":"echo test"}')
        runner = agentToolRunner(tool)
        self.assertEqual(runner.validateTool(), 1)


class TestAgentToolRunnerExecute(unittest.TestCase):
    def _make_runner(self, command="echo test", name="powershell", tool_id="call_1"):
        return agentToolRunner(make_tool(name=name, command=command, tool_id=tool_id))

    @patch("agent_tools_runner.sys.platform", "linux")
    @patch("agent_tools_runner.subprocess.run")
    def test_execute_bash_success(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="hello\n", stderr="")
        runner = self._make_runner(command="echo hello", name="bash", tool_id="call_1")
        rc, out, err = runner.executeTool()
        self.assertEqual(rc, 0)
        self.assertEqual(out, "hello\n")
        self.assertEqual(err, "")
        # bash: command passed directly as string
        self.assertEqual(mock_run.call_args[0][0], "echo hello")

    @patch("agent_tools_runner.sys.platform", "linux")
    @patch("agent_tools_runner.subprocess.run")
    def test_execute_bash_with_error_output(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error message")
        runner = self._make_runner(command="false", name="bash", tool_id="call_2")
        rc, out, err = runner.executeTool()
        self.assertEqual(rc, 1)
        self.assertEqual(out, "")
        self.assertEqual(err, "error message")

    @patch("agent_tools_runner.sys.platform", "linux")
    @patch("agent_tools_runner.subprocess.run")
    def test_execute_bash_nonzero_exit(self, mock_run):
        mock_run.return_value = MagicMock(returncode=3, stdout="partial", stderr="warn")
        runner = self._make_runner(command="exit 3", name="bash", tool_id="call_3")
        rc, out, err = runner.executeTool()
        self.assertEqual(rc, 3)
        self.assertEqual(out, "partial")
        self.assertEqual(err, "warn")

    @patch("agent_tools_runner.subprocess.run")
    def test_execute_powershell_success(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="hello", stderr="")
        runner = self._make_runner(command="echo hello", name="powershell", tool_id="call_1")
        rc, out, err = runner.executeTool()
        self.assertEqual(rc, 0)
        self.assertEqual(out, "hello")
        # powershell: wrapped in powershell.exe -NoProfile -Command ...
        call_cmd = mock_run.call_args[0][0]
        self.assertIsInstance(call_cmd, list)
        self.assertEqual(call_cmd[0], "powershell.exe")
        self.assertIn("echo hello", " ".join(call_cmd))

    @patch("agent_tools_runner.subprocess.run")
    def test_execute_powershell_with_error_output(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="pwsh error")
        runner = self._make_runner(command="exit 1", name="powershell", tool_id="call_2")
        rc, out, err = runner.executeTool()
        self.assertEqual(rc, 1)
        self.assertEqual(out, "")
        self.assertEqual(err, "pwsh error")

    @patch("agent_tools_runner.subprocess.run")
    def test_execute_uses_timeout_and_encoding(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")
        runner = self._make_runner(command="echo ok", name="powershell", tool_id="call_4")
        runner.executeTool()
        kwargs = mock_run.call_args.kwargs
        self.assertEqual(kwargs.get("capture_output"), True)
        self.assertEqual(kwargs.get("text"), True)
        self.assertEqual(kwargs.get("encoding"), "utf-8")
        self.assertEqual(kwargs.get("errors"), "replace")
        self.assertEqual(kwargs.get("timeout"), 5)


class TestAgentToolRunnerCompose(unittest.TestCase):
    def _make_runner(self):
        return agentToolRunner(make_tool())

    def test_compose_self(self):
        runner = self._make_runner()
        runner.result = MagicMock(returncode=0, stdout="done", stderr="")
        result = runner.composeSelf()
        self.assertEqual(result, {"exit_code": 0, "stdout": "done", "stderr": ""})

    def test_compose_self_error(self):
        runner = self._make_runner()
        runner.result = MagicMock(returncode=2, stdout="", stderr="bad")
        result = runner.composeSelf()
        self.assertEqual(result, {"exit_code": 2, "stdout": "", "stderr": "bad"})


if __name__ == "__main__":
    unittest.main()
