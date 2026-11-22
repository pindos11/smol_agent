# smol agent

OpenAI-compatible agent harness. One tool: run a shell command, get output and exit code.

## Set up

`config.json`: api_key, api_url, model live there now - not hardcoded in agent_definitions.py. use `config_example.json` as a template and make own copy named `config.json`.

## State

### Tool
Actually runs commands now. Windows -> powershell, posix -> shell. 5s timeout, hard char cap, kills the process tree on timeout.

### Secrets
Moved out of the code into config.json. Still not encrypted.

### Display
Colored printer. Zen mode, service info (tokens, context estimate). Tool output line-limited for the screen.

### Context
Compaction not yet done.

## Manual testing

manual_testing has a mock server and scenarios for running the loop without a real model. There is more in its README.

## Run tests

`python -m unittest discover -s tests -p "test_*.py"`
