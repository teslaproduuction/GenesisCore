import bpy
import requests
import json
from copy import deepcopy
from .openai import MCPClientOpenAI, logger


class MCPClientLocalOllama(MCPClientOpenAI):
    @classmethod
    def info(cls):
        return {
            "name": "LocalOllama",
            "description": "Local Ollama client",
            "version": "1.0.0",
        }

    @classmethod
    def default_config(cls):
        return {
            "base_url": "http://localhost:11434",
            "host": "localhost",
            "port": 11434,
            "api_key": "",
            "model": "llama3.2:3b",
        }

    def __init__(self, base_url="http://localhost:11434", api_key="ollama", model="", stream=True):
        super().__init__(base_url, api_key=api_key, model=model, stream=stream)

    def get_chat_url(self):
        res = f"{self.base_url}/v1/chat/completions"
        if not res.startswith("http"):
            res = f"http://{res}"
        return res

    def fetch_models_ex(self):
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        model_url = f"{self.base_url}/v1/models"
        if not model_url.startswith("http"):
            model_url = f"http://{model_url}"
        try:
            response = requests.get(model_url, headers=headers)
            models = response.json().get("data", [])
            self.models = [model["id"] for model in models]
        except Exception:
            logger.error("获取模型列表失败, 请检查大模型服务商, API密钥及base url是否正确")
        return self.models

    @classmethod
    def draw(cls, layout: bpy.types.UILayout):
        from ..preference import get_pref

        pref = get_pref()
        layout.prop(pref, "host")
        layout.prop(pref, "port")
        layout.prop(pref, "api_key")
        layout.prop(pref, "model")

    def reset_config(self):
        from ..preference import get_pref

        pref = get_pref()
        self.base_url = f"{pref.host}:{pref.port}"
        self.api_key = pref.api_key
        self.model = pref.model

    def response_raise_status(self, response: requests.Response):
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError:
            try:
                json_data = response.json()
                error = json_data.get("error", "")
                if message := error.get("message", ""):
                    if "does not support tools" in message:
                        logger.error("当前模型不支持工具调用, 请更换模型")
                    raise Exception(message)
                print(json_data)
            except json.JSONDecodeError:
                raise
