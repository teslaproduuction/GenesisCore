import bpy
from .operator import RunCommand
from .i18n.translations.zh_HANS import PANEL_TCTX
from .preference import get_pref


class MCP_PT_Client(bpy.types.Panel):
    bl_label = "Genesis Engine Frontend"
    bl_idname = "MCP_PT_Client"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Genesis Engine"
    bl_translation_context = PANEL_TCTX

    def draw(self, context):
        try:
            layout = self.layout
            pref = get_pref()
            mcp_props = bpy.context.scene.mcp_props
            box = layout.box()
            box.column().prop(pref, "tools", expand=True)
            box.prop(mcp_props, "command")
            col = box.column()
            col.scale_y = 2
            col.enabled = bool(bpy.context.scene.mcp_props.command)
            col.operator(RunCommand.bl_idname)
            box = layout.box()
            pref.draw_ex(box)
        except Exception as e:
            print(e)


clss = [
    MCP_PT_Client,
]

register, unregister = bpy.utils.register_classes_factory(clss)
