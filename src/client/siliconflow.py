from .openai import MCPClientOpenAI


class MCPClientSiliconflow(MCPClientOpenAI):
    @classmethod
    def info(cls):
        return {
            "name": "Siliconflow",
            "description": "Siliconflow API client",
            "version": "0.0.1",
        }

    def __init__(self, url="https://api.siliconflow.cn/v1/chat/completions", api_key="", model="", stream=True):
        super().__init__(url, api_key, model, stream)
        self.url = url
