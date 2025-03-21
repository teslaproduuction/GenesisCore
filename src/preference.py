# type: ignore
import bpy
from .i18n.translations.zh_HANS import PROP_TCTX, PANEL_TCTX, OPS_TCTX


class AddonPreferences(bpy.types.AddonPreferences):
    bl_idname = __package__.split(".")[0]
    config = {}

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

    def dump_config(self):
        return {
            "provider": self.provider,
            "host": self.host,
            "port": self.port,
            "api_key": self.api_key,
            "base_url": self.base_url,
        }

    def get_model_items(self, context):
        client = self.get_client_by_name(self.provider)
        models = client.get().models if client.get() else []
        return [(m, m, "") for m in models] or [("None", "None", "")]

    model: bpy.props.EnumProperty(items=get_model_items, name="Model", translation_context=PROP_TCTX)

    should_refresh_models: bpy.props.BoolProperty(default=True, name="Should Refresh Models", translation_context=PROP_TCTX)

    def get_client_by_name(self, name):
        from .client import MCPClientBase

        return MCPClientBase.get_client_by_name(name)

    def draw(self, context):
        layout = self.layout
        layout.column().prop(self, "tools", expand=True)
        box = layout.box()
        self.draw_ex(box)

    def draw_ex(self, layout: bpy.types.UILayout):
        row = layout.row()
        row.label(text="API Settings", text_ctxt=PANEL_TCTX)
        row.alert = self.should_refresh_models
        row.operator(RefreshModels.bl_idname, text="", icon="FILE_REFRESH")
        layout.prop(self, "provider")
        provider = self.get_client_by_name(self.provider)
        if not provider:
            return
        provider.draw(layout)


class RefreshModels(bpy.types.Operator):
    bl_idname = "mcp.refresh_models"
    bl_label = "Refresh Models"
    bl_description = "Refresh Models"
    bl_translation_context = OPS_TCTX

    def execute(self, context):
        from .client import MCPClientBase

        pref = get_pref()
        # 先停止所有非当前客户端
        for clientclass in MCPClientBase.get_all_clients():
            cname = clientclass.__name__
            client: MCPClientBase = pref.get_client_by_name(cname)
            if not client:
                continue
            if cname != pref.provider:
                client.stop_client()
                continue
        client = pref.get_client_by_name(pref.provider)
        if not client.get():
            client.try_start_client()
        if not client.get():
            return {"FINISHED"}
        models = client.get().fetch_models(force=True)
        if models:
            pref.should_refresh_models = False
        return {"FINISHED"}


def get_pref() -> AddonPreferences:
    return bpy.context.preferences.addons[AddonPreferences.bl_idname].preferences


def config_checker():
    pref = get_pref()
    config = pref.dump_config()
    if config != pref.config:
        pref.config.update(config)
        pref.should_refresh_models = True
    return 1


clss = [
    RefreshModels,
    AddonPreferences,
]


reg, unreg = bpy.utils.register_classes_factory(clss)


def register():
    reg()
    bpy.app.timers.register(config_checker, first_interval=1, persistent=True)


def unregister():
    unreg()
    bpy.app.timers.unregister(config_checker)
