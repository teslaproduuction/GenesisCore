import bpy
from .server.tools import ToolsPackageBase


class McpProps(bpy.types.PropertyGroup):
    command: bpy.props.StringProperty(default="", name="Command")

    def get_tools_items(self, context):
        return ToolsPackageBase.get_enum_items()

    tools: bpy.props.EnumProperty(items=get_tools_items, name="ToolPackage", options={"ENUM_FLAG"}, default=0b10111)

    api_key: bpy.props.StringProperty(default="", name="API Key")
    base_url: bpy.props.StringProperty(default="https://api.deepseek.com", name="Base URL")
    model: bpy.props.StringProperty(default="Qwen/QwQ-32B", name="Model")


def register():
    bpy.utils.register_class(McpProps)
    bpy.types.Scene.mcp_props = bpy.props.PointerProperty(type=McpProps)


def unregister():
    del bpy.types.Scene.mcp_props
    bpy.utils.unregister_class(McpProps)
