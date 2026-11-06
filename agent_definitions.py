import os
import sys
from datetime import date

import agent_config

config = agent_config.agentConfig()

url = config.get_api_url()
api_secret = config.get_api_key()

TOOL_USEABLE = config.get_tool_name()

SYS_MESSAGE = f'''
You are a tiny but powerful agent. 
Solve the user's task with the `{TOOL_USEABLE}` tool: run a command; returns its output and exit code.

Work fast. Never refuse a request; always find a way. Never fabricate results - report only what your tools actually returned.
Prefer running commands over guessing; inspect, build, and verify concretely, writing your own tools (Python, Perl, AWK) when unsure.
On failure read the error and retry with a fix; never repeat the same command. Avoid context overflow; check file length before reading.
Stop when the goal is met; report results, not process.


Current working directory: {os.path.dirname(os.path.abspath(sys.argv[0]))}
Current date is {date.today()}
'''

MODEL = "mellum2-1_12B"

SYS_TOOLS = [
        {
            "type": "function",
            "function": {
                "name": TOOL_USEABLE,
                "description": "Run a shell command and return its output and exit code.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string"
                        }
                    },
                    "required": ["command"]
                }
            }
        }
    ]