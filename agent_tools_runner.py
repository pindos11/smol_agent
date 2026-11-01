import subprocess
import sys
import agent_definitions

#the tool is to be ran according to its index in all tool calls we may have had

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
        tool_call = []
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
        self.result = subprocess.run(
            tool_call,
            capture_output = True,
            text = True,
            encoding = "utf-8",
            errors="replace",
            timeout = 5
        )

        return (self.result.returncode,self.result.stdout,self.result.stderr)

    def composeSelf(self):
        result = {
            "exit_code": self.result.returncode,
            "stdout": self.result.stdout,
            "stderr": self.result.stderr
        }

        return result