import bpy
import requests
import json
from copy import deepcopy
from .base import MCPClientBase


class MCPClientLocalOllama(MCPClientBase):
    @classmethod
    def info(cls):
        return {
            "name": "LocalOllama",
            "description": "Local Ollama client",
            "version": "1.0.0",
        }

    def __init__(self, url="http://localhost:11434/api/chat", model="", stream=True):
        self.url = url
        self.model = model
        self.stream = stream
        super().__init__()

    @classmethod
    def draw(cls, layout: bpy.types.UILayout):
        from ..preference import get_pref

        pref = get_pref()
        layout.prop(pref, "host")
        layout.prop(pref, "port")
        layout.prop(pref, "model")

    def init_config(self):
        from ..preference import get_pref

        pref = get_pref()
        self.url = f"{pref.host}:{pref.port}/api/chat"
        self.model = pref.model

    async def prepare_tools(self):
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
            parameters = deepcopy(tool.inputSchema)
            parameters.pop("title", None)
            for info in parameters["properties"].values():
                info.pop("title", None)
            tool_info["function"]["parameters"] = parameters
            tools.append(tool_info)
        return tools

    async def process_query(self, query: str) -> list:
        # TODO: ollama支持str 的枚举类型 https://github.com/ollama/ollama/blob/main/docs/api.md#chat-request-with-tools
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        data = {
            "model": self.model,
            "messages": [{"role": "system", "content": self.system_prompt()}, {"role": "user", "content": query}],
            "tools": await self.prepare_tools(),
            "stream": self.stream,
        }

        messages = data["messages"]
        response = requests.request("POST", self.url, headers=headers, json=data, stream=self.stream)

        if not self.stream:
            while True:
                try:
                    json_data = response.json()
                except Exception:
                    break
                self.tool_called = False

                resp_messages = json_data.get("message", {})
                if content := resp_messages.get("content"):
                    print(content)
                    messages.append({"role": "assistant", "content": content})
                tool_calls = resp_messages.get("tool_calls", [{}])
                for tool in tool_calls:
                    if not (f := tool.get("function")):
                        continue
                    if not (fn_name := f.get("name")):
                        continue
                    if not (arguments := f.get("arguments")):
                        arguments = {}
                    messages.append({"role": "assistant", "content": "", "tool_calls": [tool]})
                    print(messages)
                    print(f"调用工具: {fn_name} , 参数: {arguments}")
                    res = await self.session.call_tool(fn_name, arguments)
                    self.tool_called = True
                    for res_content in res.content:
                        tool_call_result = {"role": "tool", "content": "", "name": fn_name}
                        messages.append(tool_call_result)
                        if res_content.type == "text":
                            tool_call_result["content"] = res_content.text
                        if res_content.type == "image":
                            tool_call_result["images"] = [res_content.data]
                        if res_content.type == "resource":
                            tool_call_result["content"] = res_content.resource
                        result = tool_call_result["content"]
                        if isinstance(result, str) and result.startswith("Error"):
                            print(result)
                            return ""
                        if isinstance(result, str) and result:
                            print("调用工具结果: ", result)
                if not self.tool_called:
                    break
                response = requests.request("POST", self.url, headers=headers, json=data, stream=self.stream)
            return
        actions = []
        while True:
            self.tool_called = False
            for line in response.iter_lines():
                if not line:
                    continue
                # print(line)
                json_data = json.loads(line.decode("utf-8"))
                if "error" in json_data:
                    print("错误", json_data["error"])
                    continue
                resp_messages = json_data.get("message", {})
                if content := resp_messages.get("content"):
                    print(content, end="", flush=True)
                    messages.append({"role": "assistant", "content": content})
                # "message": {"role": "assistant", "tool_calls": [{"function": {"name": "xxx", "arguments": {}}}]
                tool_calls = resp_messages.get("tool_calls", [])
                for tool in tool_calls:
                    if not (f := tool.get("function")):
                        continue
                    if not (fn_name := f.get("name")):
                        continue
                    if not (arguments := f.get("arguments")):
                        arguments = {}
                    messages.append({"role": "assistant", "content": "", "tool_calls": [tool]})
                    print(messages)
                    print(f"调用工具: {fn_name} , 参数: {arguments}")
                    res = await self.session.call_tool(fn_name, arguments)
                    self.tool_called = True
                    for res_content in res.content:
                        tool_call_result = {"role": "tool", "content": "", "name": fn_name}
                        messages.append(tool_call_result)
                        if res_content.type == "text":
                            tool_call_result["content"] = res_content.text
                        if res_content.type == "image":
                            tool_call_result["images"] = [res_content.data]
                        if res_content.type == "resource":
                            tool_call_result["content"] = res_content.resource
                        result = tool_call_result["content"]
                        if isinstance(result, str) and result.startswith("Error"):
                            print(result)
                        if isinstance(result, str) and result:
                            print("调用工具结果: ", result)
                actions += tool_calls
            if not self.tool_called:
                break
            response = requests.request("POST", self.url, headers=headers, json=data, stream=self.stream)
        return actions
