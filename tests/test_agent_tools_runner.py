import json
import subprocess
import sys
import unittest
from unittest.mock import patch, MagicMock

import agent_definitions
from agent_tools import agentToolCall
from agent_tools_runner import agentToolRunner, _cap_output


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
    @patch("agent_tools_runner.subprocess.Popen")
    def test_execute_bash_success(self, mock_popen):
        proc = MagicMock()
        proc.returncode = 0
        proc.communicate.return_value = ("hello\n", "")
        mock_popen.return_value = proc

        runner = self._make_runner(command="echo hello", name="bash", tool_id="call_1")
        rc, out, err = runner.executeTool()

        self.assertEqual(rc, 0)
        self.assertEqual(out, "hello\n")
        self.assertEqual(err, "")
        mock_popen.assert_called_once_with(
            "echo hello",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            start_new_session=True,
        )
        proc.communicate.assert_called_once_with(timeout=5)

    @patch("agent_tools_runner.sys.platform", "linux")
    @patch("agent_tools_runner.subprocess.Popen")
    def test_execute_bash_with_error_output(self, mock_popen):
        proc = MagicMock()
        proc.returncode = 1
        proc.communicate.return_value = ("", "error message")
        mock_popen.return_value = proc

        runner = self._make_runner(command="false", name="bash", tool_id="call_2")
        rc, out, err = runner.executeTool()

        self.assertEqual(rc, 1)
        self.assertEqual(out, "")
        self.assertEqual(err, "error message")

    @patch("agent_tools_runner.sys.platform", "linux")
    @patch("agent_tools_runner.subprocess.Popen")
    def test_execute_bash_nonzero_exit(self, mock_popen):
        proc = MagicMock()
        proc.returncode = 3
        proc.communicate.return_value = ("partial", "warn")
        mock_popen.return_value = proc

        runner = self._make_runner(command="exit 3", name="bash", tool_id="call_3")
        rc, out, err = runner.executeTool()

        self.assertEqual(rc, 3)
        self.assertEqual(out, "partial")
        self.assertEqual(err, "warn")

    @patch("agent_tools_runner.sys.platform", "win32")
    @patch("agent_tools_runner.subprocess.Popen")
    def test_execute_powershell_success(self, mock_popen):
        proc = MagicMock()
        proc.returncode = 0
        proc.communicate.return_value = ("hello", "")
        mock_popen.return_value = proc

        runner = self._make_runner(command="echo hello", name="powershell", tool_id="call_1")
        rc, out, err = runner.executeTool()

        self.assertEqual(rc, 0)
        self.assertEqual(out, "hello")
        call_cmd = mock_popen.call_args.args[0]
        self.assertIsInstance(call_cmd, list)
        self.assertEqual(call_cmd[0], "powershell.exe")
        self.assertIn("echo hello", " ".join(call_cmd))
        self.assertFalse(mock_popen.call_args.kwargs["start_new_session"])

    @patch("agent_tools_runner.sys.platform", "win32")
    @patch("agent_tools_runner.subprocess.Popen")
    def test_execute_powershell_with_error_output(self, mock_popen):
        proc = MagicMock()
        proc.returncode = 1
        proc.communicate.return_value = ("", "pwsh error")
        mock_popen.return_value = proc

        runner = self._make_runner(command="exit 1", name="powershell", tool_id="call_2")
        rc, out, err = runner.executeTool()

        self.assertEqual(rc, 1)
        self.assertEqual(out, "")
        self.assertEqual(err, "pwsh error")

    @patch("agent_tools_runner.sys.platform", "win32")
    @patch("agent_tools_runner.subprocess.Popen")
    def test_execute_uses_communicate_timeout_and_encoding(self, mock_popen):
        proc = MagicMock()
        proc.returncode = 0
        proc.communicate.return_value = ("ok", "")
        mock_popen.return_value = proc

        runner = self._make_runner(command="echo ok", name="powershell", tool_id="call_4")
        runner.executeTool()

        kwargs = mock_popen.call_args.kwargs
        self.assertEqual(kwargs["stdout"], subprocess.PIPE)
        self.assertEqual(kwargs["stderr"], subprocess.PIPE)
        self.assertTrue(kwargs["text"])
        self.assertEqual(kwargs["encoding"], "utf-8")
        self.assertEqual(kwargs["errors"], "replace")
        proc.communicate.assert_called_once_with(timeout=5)

    @patch.object(agentToolRunner, "_terminate")
    @patch("agent_tools_runner.sys.platform", "linux")
    @patch("agent_tools_runner.subprocess.Popen")
    def test_timeout_terminates_process_and_returns_partial_output(self, mock_popen, mock_terminate):
        proc = MagicMock()
        proc.communicate.side_effect = [
            subprocess.TimeoutExpired("echo test", 5),
            ("partial output", ""),
        ]
        mock_popen.return_value = proc

        runner = self._make_runner()
        rc, out, err = runner.executeTool()

        self.assertEqual(rc, -1)
        self.assertEqual(out, "partial output")
        self.assertIn("exceeded 5s timeout", err)
        mock_terminate.assert_called_once_with(proc)
        self.assertEqual(proc.communicate.call_count, 2)

    @patch("agent_tools_runner.sys.platform", "win32")
    @patch("agent_tools_runner.subprocess.run")
    def test_windows_terminate_uses_taskkill_for_process_tree(self, mock_run):
        proc = MagicMock(pid=1234)
        runner = self._make_runner()

        runner._terminate(proc)

        mock_run.assert_called_once_with(
            ["taskkill", "/pid", "1234", "/T", "/F"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        proc.wait.assert_called_once_with(timeout=5)


class TestToolOutputCap(unittest.TestCase):
    def test_short_output_is_preserved_exactly(self):
        self.assertEqual(_cap_output("one\ntwo\n", 100), "one\ntwo\n")

    def test_many_lines_are_not_limited(self):
        output = "\n".join(f"line {number}" for number in range(500))
        self.assertEqual(_cap_output(output, 120000), output)

    def test_character_limit_adds_truncation_marker(self):
        self.assertEqual(
            _cap_output("abcdef", 3),
            "abc\n...[truncated 3 chars]",
        )

    def test_none_output_becomes_empty_string(self):
        self.assertEqual(_cap_output(None, 100), "")


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
