import json
from dataclasses import dataclass
from typing import Union, Literal
from contextlib import AsyncExitStack
from pathlib import Path
from mcp import ClientSession
from mcp.client.sse import sse_client
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
    current_client: "MCPClientBase" = None

    @classmethod
    def info(cls):
        return {
            "name": "MCPClientBase",
            "description": "A base class for MCP clients",
            "version": "0.1.0",
        }

    def __init__(self):
        self.session: ClientSession = None
        self.exit_stack = AsyncExitStack()
        self.tool_called = False
        self.should_stop = False
        self.__class__.current_client = self
        # self.response_parser = ResponseParser()
        # s = self.response_parser.parse_response("S")

        try:
            from anthropic import Anthropic

            self.anthropic = Anthropic()
        except Exception:
            ...

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

    async def process_query(self, query: str) -> str:
        """Process a query using Claude and available tools"""
        messages = [{"role": "user", "content": query}]

        response = await self.session.list_tools()
        available_tools = [{"name": tool.name, "description": tool.description, "input_schema": tool.inputSchema} for tool in response.tools]
        response = self.anthropic.messages.create(model="claude-3-5-sonnet-20241022", max_tokens=1000, messages=messages, tools=available_tools)

        # Process response and handle tool calls
        final_text = []

        for content in response.content:
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

    async def command_loop(self):
        """运行一个可交互的命令循环"""
        print("\nMCP 客户端运行中...")
        print("输入命令或quit退出.\n")

        while True:
            try:
                query = input(">>>").strip()
                if query.lower() == "quit":
                    break
                response = await self.process_query(query)
                # print("\n" + response)
            except Exception as e:
                print(f"\n错误: {str(e)}")

    async def cleanup(self):
        """清理资源"""
        await self.exit_stack.aclose()
