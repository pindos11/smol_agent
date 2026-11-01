import os
import sys
from datetime import date

url = "http://127.0.0.1:9090/v1/chat/completions"

SYS_MESSAGE = f'''
You are a tiny but powerful agent. 
Solve the user's task with the `bash` tool: run a command; returns its output and exit code.

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
                "name": "bash",
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