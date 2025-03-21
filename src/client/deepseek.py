from .openai import MCPClientOpenAI


class MCPClientDeepSeek(MCPClientOpenAI):
    @classmethod
    def info(cls):
        return {
            "name": "DeepSeek",
            "description": "A client that uses DeepSeek for the rendering.",
            "version": "0.0.1",
        }

    def __init__(self, url="https://api.deepseek.com/chat/completions", api_key="", model="", stream=True):
        super().__init__(url, api_key, model, stream)
        self.url = url
