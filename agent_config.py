import json

class agentConfig:
    def __init__(self):
        # i will just assume config is just to be in the same folder for now
        f = open("config.json", encoding="utf-8")
        config_data = json.load(f)
        f.close()

        self.api = config_data.get("openai_api",{})
        self.processing = config_data.get("model_process",{})
        self.agent = config_data.get("agent",{})
        self.display = config_data.get("presentation",{})

    def get_api_url(self):
        return self.api.get("api_url","")

    def get_api_key(self):
        return self.api.get("api_key","")

    def get_tool_name(self):
        return self.agent.get("tool","")

    def get_model_name(self):
        return self.api.get("model_name","")

    def get_text_colors(self):
        return self.display.get("text",{})

    def get_zen_params(self):
        return self.display.get("messages",{})

    def get_tool_output_limits(self):
        #returns (size_limit_enabled, line_limit). line_limit<=0 means "no line cap".
        tool_calls = self.display.get("tool_calls",{})
        size_limit = bool(tool_calls.get("limit_tool_output_size", False))
        line_limit = tool_calls.get("limit_tool_output_lines", 0)
        try:
            line_limit = int(line_limit)
        except (TypeError, ValueError):
            line_limit = 0
        return size_limit, line_limit
