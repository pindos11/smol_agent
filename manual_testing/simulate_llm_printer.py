"""Replay a representative streamed LLM exchange through ``cliPrinter``.

This is deliberately offline: it neither calls a model nor runs the displayed
command. It is intended for quick visual checks of reasoning hiding/tool-call
animation, tool-result, and final-answer rendering.

Run from the repository root:
    python manual_testing/simulate_llm_printer.py

Use ``--delay 0`` for an instant replay.
"""

import argparse
import os
import sys
import time
from pathlib import Path


# Executing this file directly makes manual_testing the first import location.
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

os.chdir(REPOSITORY_ROOT)

from agent_config import agentConfig
from agent_messages import modelMessage
from agent_printer import cliPrinter


def stream(printer, text, kind, delay):
    """Send word-sized streamed chunks through the printer's proxy method."""
    for word in text.split(" "):
        printer.printAnimatedText(kind, word + " ")
        time.sleep(delay)


def pause(seconds, delay):
    time.sleep(seconds if delay else 0)


def run(delay, color):
    # agentConfig reads config.json from the working directory.
    printer = cliPrinter(agentConfig())
    if color == "always":
        printer.use_color = True
    elif color == "never":
        printer.use_color = False

    # Zen mode needs its labels selected before the first streamed chunk.
    printer.pick_random_texts()
    printer.printSysMessage("LLM printer simulation - no command will run")

    stream(
        printer,
        "I need to inspect the project before I can answer accurately.",
        "reasoning",
        delay,
    )
    pause(0.7, delay)

    stream(
        printer,
        "\n\nTool calling: powershell {\"command\": \"Get-ChildItem\"}\n",
        "tool",
        delay,
    )
    pause(1.0, delay)

    # This uses the same message-shaped object as a real tool result.
    tool_result = modelMessage(
        "tool",
        "Directory: D:\\smol_agent\nFiles: agent.py, agent_printer.py, README.md",
    )
    printer.printMessage(tool_result)
    pause(0.8, delay)

    # Keep the tool result intact before Zen's carriage-return animation starts.
    printer.printAnimatedText("answer", "\n")
    stream(
        printer,
        "The requested files are present, so I can provide a concise result.",
        "reasoning",
        delay,
    )
    pause(0.7, delay)

    printer.printAnimatedText("answer", "\n\n")
    stream(
        printer,
        "Done. I inspected the directory and found the relevant agent files.",
        "answer",
        delay,
    )
    printer.printEndMessage("Simulation complete")


def parse_args():
    parser = argparse.ArgumentParser(description="Replay LLM output through cliPrinter.")
    parser.add_argument(
        "--delay",
        type=float,
        default=0.10,
        help="seconds between streamed words (default: 0.10; use 0 for instant replay)",
    )
    parser.add_argument(
        "--color",
        choices=("auto", "always", "never"),
        default="auto",
        help="ANSI color mode (default: auto; use always to test escape sequences)",
    )
    args = parser.parse_args()
    if args.delay < 0:
        parser.error("--delay must be zero or positive")
    return args


if __name__ == "__main__":
    arguments = parse_args()
    run(arguments.delay, arguments.color)
