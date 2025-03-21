import json
import requests

from .base import MCPClientBase


class MCPClientClaude(MCPClientBase):
    @classmethod
    def info(cls):
        return {
            "name": "Claude",
            "description": "Claude is a powerful language model that can be used to generate text.",
            "version": "0.0.1",
        }

    def __init__(self, url="https://api.anthropic.com/v1/messages", api_key="", model="", stream=True):
        self.url = url
        self.api_key = api_key
        self.model = model
        self.stream = stream
        super().__init__()

    async def process_query(self, query: str) -> list:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "x-api-key": self.api_key,
        }

        data = {
            "model": self.model,
            "messages": [],
            "tools": None,
            "stream": True,
        }

        messages = [{"role": "user", "content": query}]
        data["messages"] = messages

        response = await self.session.list_tools()
        tools = []
        for tool in response.tools:
            tool_info = {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    # "parameters": {
                    #     "type": "object",
                    #     "properties": {
                    #         "city": {
                    #             "type": "string",
                    #             "description": "The name of the city",
                    #         },
                    #     },
                    #     "required": ["city"],
                    # },
                },
            }
            parameters = {}
            tool_info["function"]["parameters"] = parameters
            {"properties": {"object_name": {"title": "Object Name", "type": "string"}, "texture_id": {"title": "Texture Id", "type": "string"}}, "required": ["object_name", "texture_id"], "title": "set_textureArguments", "type": "object"}

            for k, v in tool.inputSchema.items():
                parameters[k] = v
            tools.append(tool_info)
        data["tools"] = tools
        response = requests.request("POST", self.url, headers=headers, json=data, stream=data["stream"])
        actions = []
        for line in response.iter_lines():
            if not line:
                continue
            try:
                json_data = json.loads(line)
            except Exception:
                print("Json解析错误", line)
                continue
            {"type": "error", "error": {"type": "invalid_request_error", "message": "Your credit balance is too low to access the Anthropic API. Please go to Plans & Billing to upgrade or purchase credits."}}
            if json_data.get("type", None) == "error":
                print("Error:", json_data.get("error", {}).get("message", ""))
                continue
            choices = json_data.get("choices", [])
            tool_calls = []
            for choice in choices:
                delta = choice.get("delta", {})
                if not delta:
                    continue
                # "choices": [{"index": 0, "delta": {"role": "assistant", "content": ""}}],
                if "content" in delta:
                    print(delta["content"], end="", flush=True)
                # "choices": [{"index": 0, "delta": {"tool_calls": []}},]
                if "tool_calls" in delta:
                    tool_calls += delta.get("tool_calls", [])
            # print(json_data)
            {
                "choices": [
                    {"index": 0, "delta": {"tool_calls": [{"index": 0, "id": "call_0_b5058cfd-47d3-46ba-9f42-3802e8918c81", "type": "function", "function": {"name": "get_scene_info", "arguments": ""}}]}, "logprobs": None, "finish_reason": None}
                ],
            }
            # if content:
            #     messages.append({"role": "assistant", "content": content})
            {
                "id": "6ec394be-6504-46f8-a28d-a6240a4d0248",
                "object": "chat.completion.chunk",
                "created": 1742206922,
                "model": "deepseek-chat",
                "system_fingerprint": "fp_3a5770e1b4_prod0225",
            }

            for tool_call in tool_calls:
                if "function" not in tool_call:
                    continue
                f = tool_call["function"]
                if "name" not in f:
                    continue
                print(f)
                print(f"调用工具: {f['name']} , 参数: {f['arguments']}")
                res = await self.session.call_tool(f["name"], f["arguments"] or {})
                has_json_result = False
                for res_content in res.content:
                    if res_content.type == "text":
                        try:
                            json_content = json.loads(res_content.text)
                            has_json_result = True
                            print("调用工具返回: ", res_content.text)
                            messages.append({"role": "user", "content": json_content})
                        except Exception:
                            ...
                    elif res_content.type == "image":
                        messages.append({"role": "user", "content": res_content.data})
                    elif res_content.type == "resource":
                        messages.append({"role": "user", "content": res_content.resource})
                if has_json_result:
                    response = requests.request("POST", self.url, headers=headers, json=data, stream=data["stream"])
            actions += tool_calls
        print()
        return actions
