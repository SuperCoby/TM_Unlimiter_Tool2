import bpy
from ..utils import DebugUnlimiter as dbg


class TMU_OT_debug_drag(bpy.types.Operator):
    bl_idname = "view3d.tmu_debug_drag"
    bl_label = "Debug Panel Drag"
    bl_options = {'REGISTER', 'INTERNAL'}
    
    def modal(self, context, event):
        
        if dbg.handler is None:
            return {'CANCELLED'}
        
        if event.type == 'WHEELUPMOUSE':
            if dbg.debug_info_lines and dbg.is_mouse_in_panel(event.mouse_region_x, event.mouse_region_y):
                total_lines = len(dbg.debug_info_lines)
                if total_lines > dbg.max_visible_lines:
                    dbg.scroll_offset = max(0, dbg.scroll_offset - 3)
                    if context.area:
                        context.area.tag_redraw()
                return {'RUNNING_MODAL'}
        
        elif event.type == 'WHEELDOWNMOUSE':
            if dbg.debug_info_lines and dbg.is_mouse_in_panel(event.mouse_region_x, event.mouse_region_y):
                total_lines = len(dbg.debug_info_lines)
                if total_lines > dbg.max_visible_lines:
                    max_scroll = total_lines - dbg.max_visible_lines
                    dbg.scroll_offset = min(max_scroll, dbg.scroll_offset + 3)
                    if context.area:
                        context.area.tag_redraw()
                return {'RUNNING_MODAL'}
        
        if event.type == 'LEFTMOUSE':
            if event.value == 'PRESS':
                if dbg.debug_info_lines and dbg.is_mouse_in_scrollbar_handle(event.mouse_region_x, event.mouse_region_y):
                    dbg.is_scrollbar_dragging = True
                    dbg.scrollbar_drag_start_y = event.mouse_region_y
                    dbg.scrollbar_drag_start_offset = dbg.scroll_offset
                    return {'RUNNING_MODAL'}
                elif dbg.debug_info_lines and dbg.is_mouse_in_panel(event.mouse_region_x, event.mouse_region_y):
                    clicked_arrow = dbg.get_clicked_arrow(event.mouse_region_x, event.mouse_region_y)
                    if clicked_arrow:
                        old_height = dbg.get_panel_height()
                        if clicked_arrow == "materials":
                            dbg.materials_section_collapsed = not dbg.materials_section_collapsed
                        elif clicked_arrow == "objects":
                            dbg.objects_section_collapsed = not dbg.objects_section_collapsed
                        dbg.get_debug_info()
                        new_height = dbg.get_panel_height()
                        dbg.debug_panel_y += old_height - new_height
                        if context.area:
                            context.area.tag_redraw()
                        return {'RUNNING_MODAL'}
                    
                    clicked_object_name = dbg.get_clicked_object_name(event.mouse_region_x, event.mouse_region_y)
                    if clicked_object_name:
                        if dbg.select_object_by_name(clicked_object_name):
                            for area in context.screen.areas:
                                if area.type in ['VIEW_3D', 'OUTLINER']:
                                    area.tag_redraw()
                        return {'RUNNING_MODAL'}
                    else:
                        dbg.is_dragging = True
                        dbg.drag_offset_x = event.mouse_region_x - dbg.debug_panel_x
                        dbg.drag_offset_y = event.mouse_region_y - dbg.debug_panel_y
                        return {'RUNNING_MODAL'}
            
            elif event.value == 'RELEASE':
                if dbg.is_scrollbar_dragging:
                    dbg.is_scrollbar_dragging = False
                    return {'RUNNING_MODAL'}
                elif dbg.is_dragging:
                    dbg.is_dragging = False
                    return {'RUNNING_MODAL'}
        
        elif event.type == 'MOUSEMOVE':
            if dbg.is_scrollbar_dragging:
                if dbg.debug_info_lines:
                    total_lines = len(dbg.debug_info_lines)
                    if total_lines > dbg.max_visible_lines:
                        LINE_HEIGHT = 16
                        x, y = dbg.debug_panel_x, dbg.debug_panel_y
                        panel_height = (dbg.max_visible_lines + 3) * LINE_HEIGHT + 20
                        scrollbar_height = panel_height - 20
                        handle_height = max(20, scrollbar_height * (dbg.max_visible_lines / total_lines))
                        mouse_delta = dbg.scrollbar_drag_start_y - event.mouse_region_y
                        scroll_range = scrollbar_height - handle_height
                        if scroll_range > 0:
                            scroll_delta = mouse_delta / scroll_range * (total_lines - dbg.max_visible_lines)
                        else:
                            scroll_delta = 0
                        dbg.scroll_offset = max(0, min(total_lines - dbg.max_visible_lines, int(dbg.scrollbar_drag_start_offset + scroll_delta)))
                        if context.area:
                            context.area.tag_redraw()
                return {'RUNNING_MODAL'}
            elif dbg.is_dragging:
                dbg.debug_panel_x = event.mouse_region_x - dbg.drag_offset_x
                dbg.debug_panel_y = event.mouse_region_y - dbg.drag_offset_y
                
                if context.region:
                    dbg.debug_panel_x = max(0, min(dbg.debug_panel_x, context.region.width - 410))
                    dbg.debug_panel_y = max(0, min(dbg.debug_panel_y, context.region.height - 50))
                
                if context.area:
                    context.area.tag_redraw()
                return {'RUNNING_MODAL'}
            
        elif event.type in {'ESC'}:
            dbg.is_dragging = False
            dbg.is_scrollbar_dragging = False
            return {'CANCELLED'}
            
        return {'PASS_THROUGH'}
    
    def invoke(self, context, event):
        if dbg.handler is not None:
            context.window_manager.modal_handler_add(self)
            return {'RUNNING_MODAL'}
        return {'CANCELLED'}

class TMU_OT_toggle_debug(bpy.types.Operator):
    bl_idname = "view3d.tmu_toggle_debug"
    bl_label = "Debug Auto Def"
    bl_description = "Toggle viewport display of materials and collision report with drag support"
    bl_options = {'REGISTER'}

    def execute(self, context):
        try:
            if dbg.handler is None:
                dbg.enable_debug_display()
                if context.area and context.area.type == 'VIEW_3D':
                    try:
                        bpy.ops.view3d.tmu_debug_drag('INVOKE_DEFAULT')
                    except Exception as e:
                        pass
            else:
                dbg.disable_debug_display()
            
            for area in context.screen.areas:
                if area.type == 'VIEW_3D':
                    area.tag_redraw()
        except Exception as e:
            self.report({'ERROR'}, f"Error: {str(e)}")
        
        return {'FINISHED'}


classes = (
    TMU_OT_toggle_debug,
    TMU_OT_debug_drag,
)


def unregister():
    dbg.cleanup()
