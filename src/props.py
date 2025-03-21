import bpy
from .i18n.translations.zh_HANS import PROP_TCTX


class McpProps(bpy.types.PropertyGroup):
    command: bpy.props.StringProperty(default="", name="Command", translation_context=PROP_TCTX)


def register():
    bpy.utils.register_class(McpProps)
    bpy.types.Scene.mcp_props = bpy.props.PointerProperty(type=McpProps)


def unregister():
    del bpy.types.Scene.mcp_props
    bpy.utils.unregister_class(McpProps)
