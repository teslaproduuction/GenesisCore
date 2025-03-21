import json
import bpy
import queue
import asyncio
import requests
from threading import Thread
from dataclasses import dataclass
from typing import Union, Literal
from contextlib import AsyncExitStack
from pathlib import Path
from mcp import ClientSession
from mcp.client.sse import sse_client
from ..timer import Timer
from ..logger import getLogger

logger = getLogger("  BlenderClient")


@dataclass
class ContentEmpty:
    rtype: Literal["empty"]
    text: str
    tool_calls: list
    error: str


@dataclass
class ContentText:
    rtype: Literal["text"]
    text: str


@dataclass
class ContentTool:
    rtype: Literal["tool"]
    tool_calls: list
    arguments: str


ContentType = Union[ContentEmpty, ContentText, ContentTool]


class ResponseParser:
    @staticmethod
    def parse_response(response: str) -> ContentType:
        try:
            data = json.loads(response)
            return data
        except Exception as e:
            print(f"Error parsing response: {e}")
            return None


class MCPClientBase:
    client_pools: dict[object, "MCPClientBase"] = {}
    __clients__: dict[str, "MCPClientBase"] = {}

    def __init__(self, base_url="https://api.deepseek.com", api_key="", model="", stream=True):
        self._base_url = ""
        self.base_url = base_url
        self.api_key = api_key
        self.model = model
        self.stream = stream
        self.session: ClientSession = None
        self.models = []
        self.exit_stack = AsyncExitStack()
        self.should_stop = False
        self.command_queue = queue.Queue()
        self.is_running = False
        self.push_instance(self)
        # self.response_parser = ResponseParser()
        # s = self.response_parser.parse_response("S")

        try:
            from anthropic import Anthropic

            self.anthropic = Anthropic()
        except Exception:
            ...
        self.reset_config()

    @property
    def base_url(self):
        return self._base_url

    @base_url.setter
    def base_url(self, value):
        self._base_url = value[:-1] if value.endswith("/") else value

    def update(self):
        Timer.put(self.reset_config)

    def reset_config(self):
        from ..preference import get_pref

        pref = get_pref()
        self.base_url = pref.base_url
        self.api_key = pref.api_key
        self.model = pref.model

    def get_chat_url(self):
        return ""

    def fetch_models(self, force=False) -> list:
        if self.models and not force:
            return self.models
        logger.info("正在获取模型列表...")
        self.models = sorted(self.fetch_models_ex())
        return self.models

    def fetch_models_ex(self):
        return []

    @classmethod
    def info(cls):
        return {
            "name": "MCPClientBase",
            "description": "A base class for MCP clients",
            "version": "0.1.0",
        }

    @classmethod
    def get(cls):
        return cls.client_pools.get(cls, None)

    @classmethod
    def push_instance(cls, self):
        cls.client_pools[cls] = self

    @classmethod
    def pop_instance(cls):
        return cls.client_pools.pop(cls, None)

    @classmethod
    def get_all_clients(cls):
        clients = []
        for c in cls.__subclasses__():
            clients.append(c)
            clients += c.get_all_clients()
        return clients

    @classmethod
    def get_enum_items(cls):
        return [(c.__name__, c.info()["name"], c.info()["description"]) for c in cls.get_all_clients()]

    @classmethod
    def get_client_by_name(cls, name: str) -> "MCPClientBase":
        if name not in cls.__clients__:
            for c in cls.get_all_clients():
                cls.__clients__[c.__name__] = c
        return cls.__clients__[name]

    @classmethod
    def stop_client(cls):
        if not (instance := cls.pop_instance()):
            return
        instance.should_stop = True

    @classmethod
    def try_start_client(cls):
        instance = cls.get()
        if not instance or instance.should_stop:
            cls.push_instance(cls())
        instance = cls.get()
        if instance.is_running:
            instance.reset_config()
            return
        instance.is_running = True

        def run_client():
            asyncio.run(instance.main())
            logger.info(f"客户端 {cls.__name__} 结束运行!")

        job = Thread(target=run_client, daemon=True)
        job.start()

    @classmethod
    def draw(cls, layout: bpy.types.UILayout):
        from ..preference import get_pref

        pref = get_pref()
        layout.prop(pref, "api_key")
        layout.prop(pref, "base_url")
        layout.prop(pref, "model")

    def system_prompt(self):
        prompt_cn = """
        你擅长对用户的问题进行分析, 并选择合适的工具来解决用户的问题. 
        逐步思考, 每个思考步骤只保留最少的草稿, 最终选择合适的工具来解决问题.
        注意: 仅能选择提供的可用工具
        """
        prompt_en = """
        You are good at analyzing user questions and choosing the appropriate tools to solve user problems.
        Think step by step, but keep only a minimum draft for each thinking step, and finally choose the appropriate tool to solve the problem.
        Note: Only use the tools you have been provided with.
        """
        # prompt_en_path = Path(__file__).parent / "prompt_en.txt"
        # prompt_en = prompt_en_path.read_text(encoding="utf-8")
        return prompt_en.strip()

    async def connect_to_server(self):
        """连接到MCP服务器"""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        stdio_transport = await self.exit_stack.enter_async_context(sse_client(url="http://localhost:45677/sse", headers=headers))
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))

        await self.session.initialize()

    def parse_line(self, line: str) -> dict:
        if not line:
            return {}
        line = line.decode("utf-8").replace("data:", "").strip()
        # print("收到消息:", line)
        if line.endswith(("[DONE]", "PROCESSING")):
            return {}
        if line.endswith("[ERROR]"):
            print(line)
            return {}
        try:
            return json.loads(line)
        except Exception:
            if "PROCESSING" in line:
                return {}
            print("Json解析错误", line)
        return {}

    def response_raise_status(self, response):
        pass

    async def process_query(self, query: str) -> str:
        """Process a query using Claude and available tools"""
        messages = [{"role": "user", "content": query}]

        response = await self.session.list_tools()
        available_tools = [{"name": tool.name, "description": tool.description, "input_schema": tool.inputSchema} for tool in response.tools]
        response = self.anthropic.messages.create(model="claude-3-5-sonnet-20241022", max_tokens=1000, messages=messages, tools=available_tools)

        # Process response and handle tool calls
        final_text = []

        for content in response.content:
            if self.should_stop:
                break
            if content.type == "text":
                final_text.append(content.text)
            elif content.type == "tool_use":
                tool_name = content.name
                tool_args = content.input

                # Execute tool call
                result = await self.session.call_tool(tool_name, tool_args)
                final_text.append(f"[Calling tool {tool_name} with args {tool_args}]")

                # Continue conversation with tool results
                if hasattr(content, "text") and content.text:
                    messages.append({"role": "assistant", "content": content.text})
                messages.append({"role": "user", "content": result.content})

                # Get next response from Claude
                response = self.anthropic.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=1000,
                    messages=messages,
                )

                final_text.append(response.content[0].text)

        return "\n".join(final_text)

    async def main(self):
        try:
            logger.info("尝试连接到创世核心...")
            await self.connect_to_server()
            logger.info("创世核心已连接!")
            while True:
                try:
                    self.update()
                    if self.should_stop:
                        break
                    try:
                        query = self.command_queue.get_nowait()
                    except queue.Empty:
                        await asyncio.sleep(0.2)
                        continue
                    logger.info(f"当前命令: {query}")
                    response = await self.process_query(query)
                    print()
                    logger.info(f"处理完成: {query}")
                    # client.session.call_tool
                    # print(response)
                except requests.exceptions.HTTPError as e:
                    logger.warning(f"HTTP错误(请检查api_key, 模型使用情况或额度): {e}")
                except Exception:
                    import traceback

                    traceback.print_exc()
        except Exception as e:
            logger.error(f"连接失败: {e}")
            logger.error("请尝试改变网络环境(开关代理等)")
        finally:
            await self.cleanup()

    async def cleanup(self):
        """清理资源"""
        await self.exit_stack.aclose()
