import bpy
import blf
import gpu
import hashlib
import importlib
from gpu_extras.batch import batch_for_shader

handler = None
object_select_handler = None
debug_info_lines = []
clickable_objects = []
clicked_object_name = None
debug_panel_x = 15
debug_panel_y = 70
is_dragging = False
drag_offset_x = 0
drag_offset_y = 0
scroll_offset = 0
max_visible_lines = 35
is_scrollbar_dragging = False
scrollbar_drag_start_y = 0
scrollbar_drag_start_offset = 0
update_timer = None
last_material_count = 0
last_material_hash = ""
_collision_materials_cache = None
materials_section_collapsed = False
objects_section_collapsed = False

def get_collision_materials():
    global _collision_materials_cache
    if _collision_materials_cache is None:
        # Liste fournie par l'addon tmunlimiter_blender_plugin (Tomek0055)
        module = importlib.import_module("tmunlimiter_blender_plugin.material_collision.default_collision_materials")
        _collision_materials_cache = module.DEFAULT_COLLISION_MATERIALS
    return _collision_materials_cache

def calculate_materials_hash():
    
    hash_data = []
    
    for material in bpy.data.materials:
        material_data = [material.name]
        if hasattr(material, 'unlimiter_material_collision'):
            collision_props = material.unlimiter_material_collision
            material_data.extend([
                str(collision_props.is_collidable),
                str(collision_props.collision_material)
            ])
        hash_data.append('|'.join(material_data))
    
    for obj in bpy.context.scene.objects:
        if obj.type == 'MESH' and hasattr(obj, 'unlimiter_object_settings'):
            object_settings = obj.unlimiter_object_settings
            try:
                game_mat = object_settings.texture_props.texture_game.game_material
            except Exception:
                game_mat = None
            hash_data.append(f"{obj.name}|{str(object_settings.can_export_collision)}|{game_mat}")
    
    combined_data = '||'.join(sorted(hash_data))
    return hashlib.md5(combined_data.encode()).hexdigest()

def check_for_changes():
    global last_material_count, last_material_hash
    
    current_material_count = len(bpy.data.materials)
    current_hash = calculate_materials_hash()
    
    if (current_material_count != last_material_count or 
        current_hash != last_material_hash):
        
        last_material_count = current_material_count
        last_material_hash = current_hash
        get_debug_info()
        
        for area in bpy.context.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()
        
        return True
    return False

def update_timer_callback():
    if handler is not None:
        check_for_changes()
    return 0.5

def set_clicked_object_hover(object_name):
    global clicked_object_name
    clicked_object_name = object_name
    
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            area.tag_redraw()

def get_debug_info():
    global debug_info_lines, materials_section_collapsed, objects_section_collapsed
    global objects_no_export_collision, objects_warning_export_collision
    debug_info_lines = []
    
    try:
        collision_materials = get_collision_materials()
        collision_materials_dict = {item[0]: item[1] for item in collision_materials}
        materials_info = {}
        
        for material in bpy.data.materials:
            is_collidable = False
            collision_material_name = None
            
            if hasattr(material, 'unlimiter_material_collision'):
                collision_props = material.unlimiter_material_collision
                is_collidable = collision_props.is_collidable
                
                if is_collidable:
                    collision_material_name = collision_materials_dict.get(
                        collision_props.collision_material, 
                        f"Material #{collision_props.collision_material} (Unknown)"
                    )
            
            materials_info[material.name] = {
                'name': material.name,
                'is_collidable': is_collidable,
                'collision_material_name': collision_material_name
            }
        
        objects_no_export_collision = []
        objects_warning_export_collision = []
        for obj in bpy.context.scene.objects:
            if obj.type == 'MESH' and hasattr(obj, 'unlimiter_object_settings'):
                settings = obj.unlimiter_object_settings
                try:
                    game_mat = obj.unlimiter_object_settings.texture_props.texture_game.game_material
                except Exception:
                    game_mat = None
                if not settings.can_export_collision:
                    objects_no_export_collision.append(obj.name)
                elif settings.can_export_collision and game_mat in [
                    'StadiumStartSignGlow.Material.Gbx',
                    'StadiumFan.Material.Gbx',
                    'StadiumWarpSpotsGlow.Material.Gbx',
                    'StadiumWarpSpotsGlowBack.Material.Gbx']:
                    objects_warning_export_collision.append(obj.name)
        
        debug_info_lines.append("═" * 28)
        
        arrow_icon = "▼" if not materials_section_collapsed else "►"
        debug_info_lines.append(f"{arrow_icon} MATERIALS AND COLLISIONS REPORT")
        
        debug_info_lines.append("═" * 28)
        debug_info_lines.append("")
        
        if not materials_section_collapsed:
            debug_info_lines.append(f"TOTAL: {len(materials_info)} material(s) found")
            debug_info_lines.append("")
            
            sorted_materials = sorted(materials_info.items())
            
            for material_name, info in sorted_materials:
                collision_icon = "[ENABLED]" if info['is_collidable'] else "[DISABLED]"
                debug_info_lines.append(f"{collision_icon} MATERIAL: {material_name}")
                
                if info['is_collidable']:
                    collision_name = info['collision_material_name'] or "Not defined"
                    debug_info_lines.append(f"   └─ Is Collide: ENABLED ({collision_name})")
                else:
                    debug_info_lines.append(f"   └─ Is Collide: DISABLED")
                debug_info_lines.append("")
        
        if objects_no_export_collision or objects_warning_export_collision:
            debug_info_lines.append("─" * 33)
            arrow_icon = "▼" if not objects_section_collapsed else "►"
            debug_info_lines.append(f"{arrow_icon} OBJECTS WITH 'EXPORT COLLISION' UNCHECKED:")
            debug_info_lines.append("─" * 33)
            if not objects_section_collapsed:
                idx = 1
                for obj_name in objects_no_export_collision:
                    debug_info_lines.append(f"  {idx}. {obj_name}")
                    idx += 1
                for obj_name in objects_warning_export_collision:
                    debug_info_lines.append(f"  {idx}. {obj_name} [Warning]")
                    idx += 1
                debug_info_lines.append("")
        
        debug_info_lines.append("═" * 28)
        
    except Exception as e:
        debug_info_lines = [
            "═══ DEBUG ERROR ═══",
            f"Error: {str(e)}",
            "Check console for details",
            "═" * 30
        ]

def get_panel_height():
    global debug_info_lines
    LINE_HEIGHT = 16
    BORDER_OFFSET = 10
    total_lines = len(debug_info_lines)
    max_lines = min(total_lines, max_visible_lines)
    return (max_lines + 3) * LINE_HEIGHT + 20

def draw_debug_info():
    global debug_panel_x, debug_panel_y, scroll_offset, clickable_objects
    
    if not debug_info_lines:
        return
    
    clickable_objects = []
    x, y = debug_panel_x, debug_panel_y
    
    LINE_HEIGHT = 16
    PANEL_WIDTH = 420
    SCROLLBAR_WIDTH = 10
    BORDER_OFFSET = 10
    
    total_lines = len(debug_info_lines)
    max_lines = min(total_lines, max_visible_lines)
    start_line = max(0, min(scroll_offset, total_lines - max_lines))
    end_line = min(start_line + max_lines, total_lines)
    
    panel_height = get_panel_height()
    
    vertices = [
        (x - BORDER_OFFSET, y - BORDER_OFFSET), (x + PANEL_WIDTH, y - BORDER_OFFSET),
        (x + PANEL_WIDTH, y + panel_height), (x - BORDER_OFFSET, y + panel_height)
    ]
    
    shader = gpu.shader.from_builtin('UNIFORM_COLOR')
    batch = batch_for_shader(shader, 'TRI_FAN', {"pos": vertices})
    
    shader.bind()
    shader.uniform_float("color", (0.1, 0.1, 0.15, 0.85))
    batch.draw(shader)
    
    border_vertices = [
        (x - BORDER_OFFSET, y - BORDER_OFFSET), (x + PANEL_WIDTH, y - BORDER_OFFSET),
        (x + PANEL_WIDTH, y + panel_height), (x - BORDER_OFFSET, y + panel_height)
    ]
    border_batch = batch_for_shader(shader, 'LINE_LOOP', {"pos": border_vertices})
    shader.uniform_float("color", (0.3, 0.6, 1.0, 0.8))
    border_batch.draw(shader)
    
    if total_lines > max_visible_lines:
        scrollbar_x = x + PANEL_WIDTH - 20
        scrollbar_y = y
        scrollbar_width = SCROLLBAR_WIDTH
        scrollbar_height = panel_height - 20
        
        scrollbar_bg_vertices = [
            (scrollbar_x, scrollbar_y), (scrollbar_x + scrollbar_width, scrollbar_y),
            (scrollbar_x + scrollbar_width, scrollbar_y + scrollbar_height), (scrollbar_x, scrollbar_y + scrollbar_height)
        ]
        scrollbar_bg_batch = batch_for_shader(shader, 'TRI_FAN', {"pos": scrollbar_bg_vertices})
        shader.uniform_float("color", (0.2, 0.2, 0.2, 0.8))
        scrollbar_bg_batch.draw(shader)
        
        scroll_ratio = start_line / max(1, total_lines - max_visible_lines)
        handle_height = max(20, scrollbar_height * (max_visible_lines / total_lines))
        handle_y = scrollbar_y + scrollbar_height - handle_height - scroll_ratio * (scrollbar_height - handle_height)
        
        handle_vertices = [
            (scrollbar_x + 1, handle_y), (scrollbar_x + scrollbar_width - 1, handle_y),
            (scrollbar_x + scrollbar_width - 1, handle_y + handle_height), (scrollbar_x + 1, handle_y + handle_height)
        ]
        handle_batch = batch_for_shader(shader, 'TRI_FAN', {"pos": handle_vertices})
        shader.uniform_float("color", (0.5, 0.7, 1.0, 0.9))
        handle_batch.draw(shader)
    
    for i in range(end_line - start_line):
        line_index = start_line + i
        line = debug_info_lines[line_index]
        current_y = y + panel_height - 30 - (i * LINE_HEIGHT)
        blf.position(0, x, current_y, 0)
        

        is_object_line = False
        object_name = None
        is_arrow_line = False
        arrow_type = None
        warning_text = None

        if line.strip().startswith(tuple("0123456789")):
            parts = line.strip().split('. ', 1)
            if len(parts) > 1:
                if "[Warning]" in parts[1]:
                    object_name = parts[1].replace(" [Warning]", "")
                    is_object_line = True
                    is_warning = True
                    warning_text = "[Warning]"
                else:
                    object_name = parts[1]
                    is_object_line = True
                    is_warning = False
        elif line.startswith("▼") or line.startswith("►"):
            is_arrow_line = True
            if "MATERIALS AND COLLISIONS REPORT" in line:
                arrow_type = "materials"
            elif "OBJECTS WITH 'EXPORT COLLISION' UNCHECKED" in line:
                arrow_type = "objects"

        if is_object_line and object_name:
            blf.size(0, 11)
            if object_name == clicked_object_name:
                blf.color(0, 1.0, 1.0, 0.0, 1.0)
            else:
                blf.color(0, 0.3, 1.0, 0.8, 1.0)
            blf.position(0, x, current_y, 0)
            blf.draw(0, f"{line.strip().split('. ', 1)[0]}. {object_name}")

            text_width = blf.dimensions(0, f"{line.strip().split('. ', 1)[0]}. {object_name}")[0]
            text_height = LINE_HEIGHT
            clickable_objects.append({
                'name': object_name,
                'x': x,
                'y': current_y,
                'x_end': x + text_width,
                'y_end': current_y + text_height
            })

            if warning_text:
                warning_x = x + text_width + 5
                blf.size(0, 11)
                blf.color(0, 1.0, 0.6, 0.0, 1.0)
                blf.position(0, warning_x, current_y, 0)
                blf.draw(0, warning_text)
        else:
            if line.startswith("═"):
                blf.size(0, 14)
                blf.color(0, 0.2, 0.8, 1.0, 1.0)
            elif line.startswith("TOTAL:"):
                blf.size(0, 13)
                blf.color(0, 0.9, 0.9, 0.2, 1.0)
            elif line.startswith("[ENABLED]"):
                blf.size(0, 12)
                blf.color(0, 0.2, 0.9, 0.3, 1.0)
            elif line.startswith("[DISABLED]"):
                blf.size(0, 12)
                blf.color(0, 1.0, 0.4, 0.3, 1.0)
            elif "Is Collide: ENABLED" in line:
                blf.size(0, 11)
                blf.color(0, 0.5, 0.9, 0.5, 1.0)
            elif "Is Collide: DISABLED" in line:
                blf.size(0, 11)
                blf.color(0, 1.0, 0.6, 0.4, 1.0)
            elif line.startswith("   │") or line.startswith("   ├") or line.startswith("   └"):
                blf.size(0, 10)
                blf.color(0, 0.8, 0.8, 0.8, 1.0)
            elif line.startswith("─"):
                blf.size(0, 12)
                blf.color(0, 0.6, 0.6, 0.9, 1.0)
            elif "OBJECTS WITH 'EXPORT COLLISION' UNCHECKED" in line:
                blf.size(0, 13)
                blf.color(0, 1.0, 0.3, 0.3, 1.0)
            else:
                blf.size(0, 11)
                blf.color(0, 0.9, 0.9, 0.9, 1.0)
            blf.position(0, x, current_y, 0)
            blf.draw(0, line)

        if is_arrow_line and arrow_type:
            arrow_width = blf.dimensions(0, "▼ ")[0]
            text_height = LINE_HEIGHT
            clickable_objects.append({
                'is_arrow': True,
                'arrow_type': arrow_type,
                'x': x,
                'y': current_y,
                'x_end': x + arrow_width,
                'y_end': current_y + text_height
            })
    
    if total_lines > max_visible_lines:
        blf.position(0, x, y + 5, 0)
        blf.size(0, 11)
        blf.color(0, 1.0, 0.8, 0.0, 1.0)
        blf.draw(0, f"Lines {start_line + 1}-{end_line} of {total_lines}")
    
    if total_lines > max_visible_lines and total_lines - end_line > 0:
        blf.position(0, x + PANEL_WIDTH - 200, y + 5, 0)
        blf.size(0, 10)
        blf.color(0, 0.8, 0.8, 0.8, 1.0)
        blf.draw(0, f"↓ {total_lines - end_line} more lines below")


def enable_debug_display():
    global handler, update_timer, last_material_count, last_material_hash
    global object_select_handler
    if handler is None:
        get_debug_info()
        handler = bpy.types.SpaceView3D.draw_handler_add(draw_debug_info, (), 'WINDOW', 'POST_PIXEL')
        last_material_count = len(bpy.data.materials)
        last_material_hash = calculate_materials_hash()
        if update_timer is None:
            update_timer = bpy.app.timers.register(update_timer_callback, persistent=True)

    if object_select_handler is None:
        object_select_handler = bpy.msgbus.subscribe_rna(
            key=(bpy.types.LayerObjects, "active"),
            owner=__name__,
            args=(),
            notify=on_object_selected
        )

def disable_debug_display():
    global handler, is_dragging, is_scrollbar_dragging, update_timer, clickable_objects
    global clicked_object_name
    global object_select_handler
    
    if handler is not None:
        bpy.types.SpaceView3D.draw_handler_remove(handler, 'WINDOW')
        handler = None
    
    if update_timer is not None:
        if bpy.app.timers.is_registered(update_timer_callback):
            bpy.app.timers.unregister(update_timer_callback)
        update_timer = None

    if object_select_handler is not None:
        bpy.msgbus.clear_by_owner(__name__)
        object_select_handler = None
def on_object_selected():
    global clicked_object_name, objects_no_export_collision, objects_warning_export_collision
    obj = bpy.context.view_layer.objects.active
    get_debug_info()
    if obj and obj.type == 'MESH':
        name = obj.name
        if name in objects_no_export_collision or name in objects_warning_export_collision:
            set_clicked_object_hover(name)
        else:
            set_clicked_object_hover(None)
    else:
        set_clicked_object_hover(None)

def is_mouse_in_panel(mouse_x, mouse_y):
    global debug_panel_x, debug_panel_y
    
    if not debug_info_lines:
        return False
    
    PANEL_WIDTH = 420
    BORDER_OFFSET = 10
    LINE_HEIGHT = 16
    
    panel_height = get_panel_height()
    
    return (debug_panel_x - BORDER_OFFSET <= mouse_x <= debug_panel_x + PANEL_WIDTH and
            debug_panel_y - BORDER_OFFSET <= mouse_y <= debug_panel_y + panel_height)

def is_mouse_in_scrollbar_handle(mouse_x, mouse_y):
    global debug_panel_x, debug_panel_y, scroll_offset
    
    if not debug_info_lines:
        return False
    
    total_lines = len(debug_info_lines)
    if total_lines <= max_visible_lines:
        return False
    
    PANEL_WIDTH = 420
    SCROLLBAR_WIDTH = 10
    LINE_HEIGHT = 16
    
    x, y = debug_panel_x, debug_panel_y
    panel_height = (max_visible_lines + 3) * LINE_HEIGHT + 20
    
    scrollbar_x = x + PANEL_WIDTH - 20
    scrollbar_y = y
    scrollbar_height = panel_height - 20
    
    start_line = max(0, min(scroll_offset, total_lines - max_visible_lines))
    scroll_ratio = start_line / max(1, total_lines - max_visible_lines)
    handle_height = max(20, scrollbar_height * (max_visible_lines / total_lines))
    handle_y = scrollbar_y + scrollbar_height - handle_height - scroll_ratio * (scrollbar_height - handle_height)
    
    return (scrollbar_x <= mouse_x <= scrollbar_x + SCROLLBAR_WIDTH and
            handle_y <= mouse_y <= handle_y + handle_height)

def get_clicked_object_name(mouse_x, mouse_y):
    for obj_info in clickable_objects:
        if (obj_info['x'] <= mouse_x <= obj_info['x_end'] and 
            obj_info['y'] <= mouse_y <= obj_info['y_end']):
            return obj_info['name']
    return None

def get_clicked_arrow(mouse_x, mouse_y):
    for obj_info in clickable_objects:
        if (obj_info.get('is_arrow') and
            obj_info['x'] <= mouse_x <= obj_info['x_end'] and 
            obj_info['y'] <= mouse_y <= obj_info['y_end']):
            return obj_info['arrow_type']
    return None

def select_object_by_name(object_name):
    try:
        bpy.ops.object.select_all(action='DESELECT')
        
        obj = bpy.data.objects.get(object_name)
        if obj:
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj
            
            set_clicked_object_hover(object_name)
            
            return True
        else:
            return False
    except Exception as e:
        return False


def cleanup():
    global update_timer
    disable_debug_display()
    if update_timer is not None:
        if bpy.app.timers.is_registered(update_timer_callback):
            bpy.app.timers.unregister(update_timer_callback)
        update_timer = None
