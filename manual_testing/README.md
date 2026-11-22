# mock_server.py — OpenAI-compatible test server for agent.py

Streams real Server-Sent-Events (SSE) that `agent_answer.py` parses exactly like a
real OpenAI streaming endpoint, but the content is fully configurable and benign.

## Run

    python mock_server.py --port 9090

Set `openai_api.api_url` in `config.json` to this server's Chat Completions
endpoint on the selected port, then run `agent.py` normally.

List scenarios: `python mock_server.py --list`

## Choosing a scenario

1. `?scenario=<name>` query param — force one (e.g. `.../chat/completions?scenario=many_tools`)
2. keyword match — a scenario whose `keywords` appear in the last user message
3. `default` — used if neither matches

## Test scenarios (edit scenarios.json to change)

| scenario              | what it exercises                                             |
|-----------------------|---------------------------------------------------------------|
| default               | reasoning -> content, no tools                                |
| single_chunk_content  | reasoning streamed, then ALL content in ONE content delta     |
| token_streaming       | content in many small tokens                                  |
| mixed_delta           | reasoning, content, and multiple tool-call deltas coalesced   |
| many_tools            | many tool calls emitted at once                               |
| incremental_tool_args | one tool call whose args arrive across many deltas            |
| multi_turn_tool       | a tool call (then you feed a tool result back)                |
| malformed_tool        | a tool chunk missing `id` (tests parser skip)                 |
| no_reasoning          | content only, no reasoning_content                            |

## Editing responses

Edit `scenarios.json`. Each scenario is a declarative streaming description:

    {
      "name": {
        "keywords": ["tool", "commands"],       // optional auto-selection
        "reasoning": ["thinking", " token"],    // optional reasoning deltas
        "content":   ["hello"],                 // optional content deltas
        "chunks": [                              // preferred: exact mixed deltas
          {"reasoning_content":"thinking", "content":"hello",
           "tool_calls":[{"index":0,"id":"call_1","type":"function",
                           "function":{"name":"powershell","arguments":"{...}"}}]}
        ],
        "tool_calls": [
          {"id":"call_1","function":{"name":"powershell","arguments":{"command":"echo 1"}}}
        ],
        "chunk_tool_args": true,                // split args across many deltas
        "finish_reason": "tool_calls"           // "tool_calls" or "stop"
      }
    }

If `chunks` is supplied, every object is emitted as one `choices[0].delta` in
the listed order. This supports any combination of `reasoning_content`,
`content`, and `tool_calls` in a single chunk, including several tool calls.
Otherwise the legacy shorthand emits reasoning tokens, content deltas, then
tool calls. Both forms end with a finish chunk and `[DONE]`.

`content` and `tool_calls` follow the OpenAI Chat Completions streaming shape.
`reasoning_content` is deliberately a non-standard provider extension (used by
reasoning-compatible OpenAI-style APIs); official OpenAI Chat Completions
clients should ignore unknown delta fields. Tool-call fragments use an initial
`id`/`type`/function-name delta followed by argument-only deltas, as OpenAI
streaming clients expect.

The endpoint also honors `"stream": false` and returns a normal
`chat.completion` JSON response. This lets standard OpenAI SDK clients use the
mock without depending on this repository's streaming parser.
