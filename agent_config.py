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