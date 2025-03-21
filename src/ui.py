import bpy
from .operator import RunCommand
from .i18n.translations.zh_HANS import PANEL_TCTX

class MCP_PT_Client(bpy.types.Panel):
    bl_label = "Genesis Engine Frontend"
    bl_idname = "MCP_PT_Client"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Genesis Engine"
    bl_translation_context = PANEL_TCTX

    def draw(self, context):
        layout = self.layout
        
        mcp_props = bpy.context.scene.mcp_props
        box = layout.box()
        box.column().prop(mcp_props, "tools", expand=True)
        box.prop(mcp_props, "command")
        col = box.column()
        col.scale_y = 2
        col.operator(RunCommand.bl_idname)
        box = layout.box()
        box.enabled = False
        box.label(text="API Settings", text_ctxt=PANEL_TCTX)
        box.prop(mcp_props, "api_key")
        box.prop(mcp_props, "base_url")
        box.prop(mcp_props, "model")


clss = [
    MCP_PT_Client,
]

register, unregister = bpy.utils.register_classes_factory(clss)
