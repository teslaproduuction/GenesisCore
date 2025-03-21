import json
import bpy
import requests
import re
from copy import deepcopy

from .base import MCPClientBase, logger


class MCPClientOpenAI(MCPClientBase):
    @classmethod
    def info(cls):
        return {
            "name": "OpenAI Compatible",
            "description": "A client that uses OpenAI for the rendering.",
            "version": "0.0.1",
        }

    def __init__(self, base_url="https://api.openai.com", api_key="", model="", stream=True):
        super().__init__(base_url, api_key, model, stream)

    def get_chat_url(self):
        return f"{self.base_url}/v1/chat/completions"

    def fetch_models_ex(self):
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        model_url = f"{self.base_url}/v1/models"
        try:
            response = requests.get(model_url, headers=headers)
            models = response.json().get("data", [])
            self.models = [model["id"] for model in models]
        except Exception:
            logger.error("获取模型列表失败, 请检查大模型服务商, API密钥及base url是否正确")
        return self.models

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
            tool_info["function"]["parameters"] = parameters
            # region 简化函数描述
            description = tool.description
            description = description.replace("Args:", "")
            for name, info in parameters.get("properties", {}).items():
                find_description = re.search(f"- {name}: (.*)\n", description)
                if not find_description:
                    continue
                description = description.replace(find_description.group(0), "")
            description = description.replace("\n", "").strip()
            while "  " in description:
                description = description.replace("  ", " ")
            # endregion 简化函数描述
            tool_info["function"]["description"] = description
            tools.append(tool_info)
        return tools

    def parse_arguments(self, arguments: str):
        arguments = arguments.strip()
        try:
            try:
                return json.loads(arguments)
            except Exception:
                pass
            if not arguments.startswith("{") or not arguments.endswith("}"):
                raise Exception("Json 解析错误")
            return eval(arguments)
            # if arguments.startswith("<tool_call>"):
            #     arguments = arguments[len("<tool_call>") :]
            # if arguments.endswith("</tool_call>"):
            #     arguments = arguments[: -len("</tool_call>")]
            # # AI大模型可能导致最后多花括号
            # for i in range(5):
            #     try:
            #         return json.loads(arguments)
            #     except Exception:
            #         ...
            #     try:
            #         return json.loads(arguments.replace("\\", ""))
            #     except Exception:
            #         ...
            #     try:
            #         return json.loads(arguments.replace("\\", "").replace("'", '"'))
            #     except Exception:
            #         ...
            #     print(f"Json 解析错误，尝试去掉最后一个字符: {arguments}")
            #     import base64
            #     print(base64.b64encode(arguments.encode()).decode())
            #     arguments = arguments[:-1].strip()
            # else:
            #     raise Exception("Json 解析错误")
        except Exception as e:
            logger.info(f"错误参数:\n{arguments}\n")
            raise e

    async def call_tool(self, fn_name: str, arguments: str | dict, tool_id: str = ""):
        print()  # 每次调用工具时，打印一个空行，方便查看日志
        logger.info(f"尝试工具: {fn_name} 参数: {arguments}")
        if isinstance(arguments, str):
            arguments = self.parse_arguments(arguments)

        res = await self.session.call_tool(fn_name, arguments)
        results = []
        for res_content in res.content:
            tool_call_result = {"role": "tool", "content": "", "tool_call_id": tool_id, "name": fn_name}
            result = ""
            if res_content.type == "text":
                result = res_content.text
            elif res_content.type == "image":
                result = res_content.data
            elif res_content.type == "resource":
                result = res_content.resource
            if isinstance(result, str) and result.startswith("Error"):
                logger.error(result)
            tool_call_result["content"] = f"Selected tool: {fn_name}\nResult: {result}"
            results.append(tool_call_result)
        return results

    def response_raise_status(self, response: requests.Response):
        try:
            json_data = response.json()
            error = json_data.get("error", {})
            if message := error.get("message"):
                if "tools is not supported" in message:
                    logger.error("此模型不支持工具调用")
                raise Exception(message)
            print(json_data)
        except json.JSONDecodeError:
            ...
        response.raise_for_status()

    async def process_query(self, query: str) -> list:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        data = {
            "model": self.model,
            "messages": [],
            "tools": None,
            "stream": self.stream,
        }

        messages = data["messages"]
        # messages.append({"role": "system", "content": self.system_prompt()})
        messages.append({"role": "user", "content": query})
        data["tools"] = await self.prepare_tools()
        response_text = ""
        while True:
            last_call_index = -1
            tool_calls = {}
            response = requests.request("POST", self.get_chat_url(), headers=headers, json=data, stream=self.stream)
            self.response_raise_status(response)
            response.encoding = "utf-8"
            # print("---------------------------------------START---------------------------------------")

            for line in response.iter_lines():
                if not line:
                    continue
                if self.should_stop:
                    break
                # print("原始数据:", line)
                if not (json_data := self.parse_line(line)):
                    # print("无法解析原始数据:", line)
                    continue
                choice = json_data.get("choices", [{}])[0]
                delta = choice.get("delta", {})
                if not delta and choice.get("finish_reason") == "stop":
                    print("无delta原始数据:", line)
                    continue
                # print("delta原始数据:", delta)
                # ---------------------------1.文本输出---------------------------
                # 原始数据 {"choices": [{"index": 0, "delta": {"role": "assistant", "content": ""}}]}
                if (content := delta.get("content")) or (content := delta.get("reasoning_content")):
                    response_text += content
                    print(content, end="", flush=True)

                # ---------------------------2.工具调用---------------------------
                # 原始数据 {"choices": [{"index": 0, "delta": {"role": "assistant", "tool_calls": [{"index": 0, "id": "XXX", "type": "function", "function": {"name": "get_scene_info", "arguments": ""}}]}}]}
                if not (rtool_call := delta.get("tool_calls", [{}])[0]):
                    continue
                if not (f := rtool_call.get("function")):
                    continue

                rindex = rtool_call["index"]

                if fn_name := f.get("name", ""):
                    # fn_name最先发送, 所以仅当fn_name存在时, 才添加到tool_calls
                    last_call_index = rindex
                    tool_calls[rindex] = {"id": "", "type": "function", "function": {"name": "", "arguments": ""}}
                    tc = tool_calls[rindex]
                    tc["function"]["name"] = fn_name

                    if tool_id := rtool_call.get("id"):
                        tc["id"] = tool_id

                if rindex not in tool_calls:
                    continue

                tc = tool_calls[rindex]
                if arguments := f.get("arguments", ""):
                    tc["function"]["arguments"] += arguments.strip()
                # 每轮只允许一个工具调用( 当存在连续调用时, 每当tryjson 成功时就调用)
                try:
                    parsed_arguments = json.loads(tc["function"]["arguments"])
                    messages.append({"role": "assistant", "content": "", "tool_calls": [tc]})
                    messages += await self.call_tool(tc["function"]["name"], parsed_arguments, tc["id"])
                    tool_calls.pop(rindex)
                except json.JSONDecodeError:
                    continue
            # print("----------------------------------------END-----------------------------------------")
            if self.should_stop:
                break
            if last_call_index == -1:
                break
            # 保证执行最后一个工具调用
            for tc in tool_calls.values():
                messages.append({"role": "assistant", "content": "", "tool_calls": [tc]})
                tc["function"]["arguments"] = tc["function"]["arguments"].strip() or "{}"
                messages += await self.call_tool(tc["function"]["name"], tc["function"]["arguments"], tc["id"])
        return ""
