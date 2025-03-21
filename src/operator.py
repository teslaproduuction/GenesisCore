import queue
import bpy
import json
import asyncio
from queue import Queue
from threading import Thread
from pathlib import Path
from .client import MCPClientBase
from .server.server import Server
from .server.tools import ToolsPackageBase
from .i18n.translations.zh_HANS import OPS_TCTX
from .logger import logger
from .preference import get_pref


test_config_path = Path(__file__).parent.parent / "test_config.json"
test_config = {}
if test_config_path.exists():
    test_config.update(json.loads(test_config_path.read_text(encoding="utf-8")))


class RunCommand(bpy.types.Operator):
    bl_idname = "mcp.run"
    bl_label = "Run"
    bl_description = "Run the command"
    bl_translation_context = OPS_TCTX

    def execute(self, context):
        pref = get_pref()
        for tname in ToolsPackageBase.get_all_tool_packages_names():
            tp = ToolsPackageBase.get_package(tname)
            if not tp:
                continue
            tools = tp.get_all_tools()
            if tname in pref.tools:
                # 注册工具
                Server.register_tools(tools)
            else:
                # 注销工具
                Server.unregister_tools(tools)
        selected_client = pref.provider
        for clientclass in MCPClientBase.get_all_clients():
            cname = clientclass.__name__
            client: MCPClientBase = pref.get_client_by_name(cname)
            if not client:
                continue
            if cname != selected_client:
                client.stop_client()
                continue

        client: MCPClientBase = pref.get_client_by_name(selected_client)
        if not client:
            self.report({"ERROR"}, "No client selected")
            return {"FINISHED"}
        client.try_start_client()
        # print(all_clients)
        command = bpy.context.scene.mcp_props.command
        if not command:
            return {"FINISHED"}
        client.instance.command_queue.put(command)
        return {"FINISHED"}


def get_client():
    # OpenAI
    # api_key = test_config.get("OpenAI", {}).get("api_key", "")
    # base_url = test_config.get("OpenAI", {}).get("base_url", "")
    # model = "gpt-3.5-turbo"
    # OpenRouter
    # api_key = test_config.get("OpenRouter", {}).get("api_key", "")
    # base_url = test_config.get("OpenRouter", {}).get("base_url", "")
    # model = "anthropic/claude-3.7-sonnet"
    # model = "openai/gpt-4o"
    # client = MCPClientOpenAI(url=base_url, api_key=api_key, model=model)

    # Ollama
    # host = test_config.get("LocalOllama", {}).get("host", "localhost")
    # port = test_config.get("LocalOllama", {}).get("port", 11434)
    # base_url = f"http://{host}:{port}/api/chat"
    # model = "deepseek-r1:32b"
    # model = "qwq"
    # model = "llama3.2:3b"
    # client = MCPClientLocalOllama(base_url, model=model)

    # DeepSeek
    # api_key = test_config.get("DeepSeek", {}).get("api_key", "")
    # base_url = test_config.get("DeepSeek", {}).get("base_url", "")
    # model = "deepseek-chat"
    # client = MCPClientDeepSeek(url=base_url, api_key=api_key, model=model)

    # Claude
    # api_key = test_config.get("Claude", {}).get("api_key", "")
    # base_url = test_config.get("Claude", {}).get("base_url", "")
    # model = "claude-3-7-sonnet"
    # client = MCPClientClaude(url=base_url, api_key=api_key, model=model)

    # SiliconFlow
    api_key = test_config.get("SiliconFlow", {}).get("api_key", "")
    base_url = test_config.get("SiliconFlow", {}).get("base_url", "")
    model = "Pro/Qwen/Qwen2.5-7B-Instruct"
    model = "Pro/deepseek-ai/DeepSeek-R1"
    model = "deepseek-ai/DeepSeek-V3"
    model = "Qwen/QwQ-32B"
    if not api_key:
        api_key = test_config.get("api_key", "xxx")
        base_url = test_config.get("base_url", "xxx")
    print(api_key, base_url, model)
    model = test_config.get("model", model)
    client = MCPClientSiliconflow(url=base_url, api_key=api_key, model=model)
    return client


clss = [
    RunCommand,
]


reg, unreg = bpy.utils.register_classes_factory(clss)


def register():
    reg()


def unregister():
    unreg()
