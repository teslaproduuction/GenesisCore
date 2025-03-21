# type: ignore
import bpy
from .i18n.translations.zh_HANS import PROP_TCTX, PANEL_TCTX


class AddonPreferences(bpy.types.AddonPreferences):
    bl_idname = __package__.split(".")[0]

    def get_tools_items(self, context):
        from .server.tools import ToolsPackageBase

        return ToolsPackageBase.get_enum_items()

    tools: bpy.props.EnumProperty(
        items=get_tools_items,
        name="ToolPackage",
        options={"ENUM_FLAG"},
        default=0b10111,
        translation_context=PROP_TCTX,
    )

    def get_provider_items(self, context):
        from .client import MCPClientBase

        return MCPClientBase.get_enum_items()

    provider: bpy.props.EnumProperty(
        items=get_provider_items,
        name="LLM Provider",
        translation_context=PROP_TCTX,
    )

    host: bpy.props.StringProperty(default="localhost", name="Host", translation_context=PROP_TCTX)
    port: bpy.props.IntProperty(default=11434, name="Port", translation_context=PROP_TCTX)
    api_key: bpy.props.StringProperty(default="", name="API Key", translation_context=PROP_TCTX)

    base_url: bpy.props.StringProperty(
        default="https://api.deepseek.com",
        name="Base URL",
        translation_context=PROP_TCTX,
    )

    model: bpy.props.StringProperty(default="Qwen/QwQ-32B", name="Model", translation_context=PROP_TCTX)

    def get_client_by_name(self, name):
        from .client import MCPClientBase

        return MCPClientBase.get_client_by_name(name)

    def draw(self, context):
        layout = self.layout
        layout.column().prop(self, "tools", expand=True)
        box = layout.box()
        self.draw_ex(box)

    def draw_ex(self, layout: bpy.types.UILayout):
        layout.label(text="API Settings", text_ctxt=PANEL_TCTX)
        layout.prop(self, "provider")
        provider = self.get_client_by_name(self.provider)
        if not provider:
            return
        provider.draw(layout)


def get_pref() -> AddonPreferences:
    return bpy.context.preferences.addons[AddonPreferences.bl_idname].preferences


def register():
    bpy.utils.register_class(AddonPreferences)


def unregister():
    bpy.utils.unregister_class(AddonPreferences)
