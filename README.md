# smol agent

Openai compatible agent harness with single tool: bash.

## Set up

### Url
Enter openai compatible endpoint in agent_definitions.py as constant `url`

### API key
Same include, constant `api_secret`

### Model
Same include, constant `MODEL`

## Whats not done yet

### Secret handling
Sure it will end up being not hardcoded

### Tool actual use
Right now it can receive tool call, but does not run it lol

### Display
I think a bit richer display is going to be beneficial too

## Run tests

`python -m unittest discover -s tests -p "test_*.py"`
