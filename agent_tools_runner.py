import subprocess
import sys
from types import SimpleNamespace

import agent_definitions

#the tool is to be ran according to its index in all tool calls we may have had

#Absolute safety cap so a runaway command can never overflow context/memory.
#Line count is deliberately not capped: the configured tool-output setting is
#a presentation concern, not a limit on data returned to the model.
_HARD_CHAR_LIMIT = 120000


def _cap_output(text, char_limit):
    """Preserve tool output except for the absolute character safety cap."""
    if text is None:
        text = ""
    if len(text) > char_limit:
        text = text[:char_limit] + f"\n...[truncated {len(text) - char_limit} chars]"
    return text


class agentToolRunner:
    def __init__(self,tool):
        self.toolCall = tool
        self.result = None

    def validateTool(self):
        result = 0 #other than 0 is bad

        if self.toolCall == None:
            result = 1 #internal error

        if self.toolCall.command == None or self.toolCall.command == "":
            result = 2 #command is malformed

        if self.toolCall.name != agent_definitions.TOOL_USEABLE:
            result = 3 #wrong tool called

        if self.toolCall.id == None or self.toolCall.id == "":
            result = 1 #well, its kinda server error? id is not given, or maybe we did not parse it right

        return result

    def executeTool(self):
        if sys.platform == "win32":
            tool_call = [
                "powershell.exe",
                "-NoProfile",
                "-Command",
                "$OutputEncoding = [System.Text.UTF8Encoding]::new($false); "
                "[Console]::OutputEncoding = $OutputEncoding; "
                +self.toolCall.command
            ]
        else:
            tool_call = self.toolCall.command

        #start_new_session on posix -> our own process group we can kill wholesale
        proc = subprocess.Popen(
            tool_call,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            start_new_session=(sys.platform != "win32"),
        )

        try:
            out, err = proc.communicate(timeout=5) #i think its reasonable
            self.result = SimpleNamespace(returncode=proc.returncode, stdout=out, stderr=err)
        except subprocess.TimeoutExpired:
            #kill the whole process tree, then grab whatever was buffered
            self._terminate(proc)
            try:
                out, err = proc.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                out, err = "", ""
            self.result = SimpleNamespace(
                returncode=-1,
                stdout=out or "",
                stderr=(err or "") + "\n[command terminated: exceeded 5s timeout]"
            )

        #Cap only characters before data reaches the context. Display-specific
        #line limiting belongs in the UI, not in the model's tool result.
        self.result.stdout = _cap_output(self.result.stdout, _HARD_CHAR_LIMIT)
        self.result.stderr = _cap_output(self.result.stderr, _HARD_CHAR_LIMIT)

        return (self.result.returncode, self.result.stdout, self.result.stderr)

    def _terminate(self, proc):
        #windows: taskkill /T reliably terminates the process AND its children
        if sys.platform == "win32":
            try:
                subprocess.run(
                    ["taskkill", "/pid", str(proc.pid), "/T", "/F"],
                    capture_output=True, text=True, timeout=5
                )
            except subprocess.SubprocessError:
                pass
        else:
            #posix: kill the whole session/group we started
            import os, signal
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                try:
                    proc.kill()
                except ProcessLookupError:
                    pass
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            pass

    def composeSelf(self):
        result = {
            "exit_code": self.result.returncode,
            "stdout": self.result.stdout,
            "stderr": self.result.stderr
        }

        return result

