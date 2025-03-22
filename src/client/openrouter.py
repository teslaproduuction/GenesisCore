import requests
from .base import logger
from .openai import MCPClientOpenAI


class MCPClientOpenRouter(MCPClientOpenAI):
    @classmethod
    def info(cls):
        return {
            "name": "OpenRouter",
            "description": "OpenRouter API",
            "version": "0.0.1",
        }

    @classmethod
    def default_config(cls):
        return {
            "base_url": "https://openrouter.ai",
            "api_key": "",
            "model": "anthropic/claude-3.5-haiku",
        }

    def __init__(self, base_url="https://openrouter.ai", api_key="", model="", stream=True):
        super().__init__(base_url, api_key, model, stream)

    def get_chat_url(self):
        return f"{self.base_url}/api/v1/chat/completions"

    def fetch_models_ex(self):
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        model_url = f"{self.base_url}/api/v1/models"
        try:
            response = requests.get(model_url, headers=headers)
            models = response.json().get("data", [])
            self.models = [model["id"] for model in models]
        except Exception:
            logger.error("获取模型列表失败, 请检查大模型服务商, API密钥及base url是否正确")
        return self.models
