import bpy
from .operator import RunCommand, SkipCurrentCommand, MarkCleanMessage
from .i18n.translations.zh_HANS import PANEL_TCTX, OPS_TCTX, PROP_TCTX
from .preference import get_pref


class MCP_PT_Client(bpy.types.Panel):
    bl_label = "Genesis Core"
    bl_idname = "MCP_PT_Client"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Genesis Core"
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
            col.scale_x = 1.5
            col.enabled = bool(bpy.context.scene.mcp_props.command)
            row = col.row(align=True)
            row.operator(RunCommand.bl_idname, text_ctxt=OPS_TCTX)
            row.operator(SkipCurrentCommand.bl_idname, icon="PAUSE", text="", text_ctxt=OPS_TCTX)
            row.prop(pref, "use_history_message", text="", icon="WORDWRAP_ON", text_ctxt=PROP_TCTX)
            row.operator(MarkCleanMessage.bl_idname, icon="TRASH", text="", text_ctxt=OPS_TCTX)

            box = layout.box()
            pref.draw_ex(box)
        except Exception as e:
            print(e)


clss = [
    MCP_PT_Client,
]

register, unregister = bpy.utils.register_classes_factory(clss)
