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
        client.get().command_queue.put(command)
        return {"FINISHED"}


class SkipCurrentCommand(bpy.types.Operator):
    bl_idname = "mcp.skip_current_command"
    bl_label = "Skip Current Command"
    bl_description = "Skip the current command"
    bl_translation_context = OPS_TCTX

    def execute(self, context):
        pref = get_pref()
        client: MCPClientBase = pref.get_client_by_name(pref.provider)
        if not client:
            self.report({"ERROR"}, "No client selected")
            return {"FINISHED"}
        instance = client.get()
        if instance:
            instance.skip_current_command = True
        return {"FINISHED"}


class MarkCleanMessage(bpy.types.Operator):
    bl_idname = "mcp.mark_clean_message"
    bl_label = "Mark Clean Message"
    bl_description = "Mark the current message as clean"
    bl_translation_context = OPS_TCTX

    def execute(self, context):
        pref = get_pref()
        client: MCPClientBase = pref.get_client_by_name(pref.provider)
        if not client:
            return {"FINISHED"}
        instance = client.get()
        if instance:
            instance.should_clear_messages = True
        return {"FINISHED"}


clss = [
    RunCommand,
    SkipCurrentCommand,
    MarkCleanMessage,
]


reg, unreg = bpy.utils.register_classes_factory(clss)


def register():
    reg()


def unregister():
    unreg()
