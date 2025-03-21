import bpy
from .operator import RunCommand


class MCP_PT_Client(bpy.types.Panel):
    bl_label = "MCP Client"
    bl_idname = "MCP_PT_Client"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "MCP"

    def draw(self, context):
        layout = self.layout
        mcp_props = bpy.context.scene.mcp_props
        layout.column().prop(mcp_props, "tools", expand=True)
        layout.prop(mcp_props, "command")
        layout.operator(RunCommand.bl_idname)
        box = layout.box()
        box.prop(mcp_props, "api_key")
        box.prop(mcp_props, "base_url")
        box.prop(mcp_props, "model")


clss = [
    MCP_PT_Client,
]

register, unregister = bpy.utils.register_classes_factory(clss)
