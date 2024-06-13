import bpy
import webbrowser
import bpy.utils.previews
import os

addon_keymaps = {}
_icons = None

# Main sidebar panel to parent others to
class SNA_PT_main(bpy.types.Panel):
    bl_label = "Main"
    bl_idname = "SNA_PT_main"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "TM"

    @classmethod
    def poll(cls, context):
        return not (False)

    def draw_header(self, context):
        layout = self.layout

    def draw(self, context):
        global _icons
        layout = self.layout
        row = layout.row(align=True)
        
        # Ajout d'un espace entre chaque icône
        row.separator(factor=2)
        
        if not True: row.operator_context = "EXEC_DEFAULT"
        op = row.operator('sna.open_discord', text='', icon_value=_icons['DISCORD'].icon_id, emboss=True, depress=False)
        row.separator(factor=0.5)
        
        op = row.operator('sna.open_documentation', text='', icon_value=_icons['documentation'].icon_id, emboss=True, depress=False)
        row.separator(factor=0.5)
        
        op = row.operator('wm.popup_message', text='', icon_value=_icons['info'].icon_id, emboss=True, depress=False)        
        row.separator(factor=0.5)
        
        op = row.operator('sna.open_github', text='', icon_value=_icons['github'].icon_id, emboss=True, depress=False)
        row.separator(factor=0.5)
        
        op = row.operator('sna.open_web', text='', icon_value=_icons['web'].icon_id, emboss=True, depress=False)
        row.separator(factor=0.5)        


# Operator for the popup message
class SimpleOperator(bpy.types.Operator):
    bl_idname = "wm.popup_message"
    bl_label = "Popup Message"

    def execute(self, context):
        wm = bpy.context.window_manager
        return wm.invoke_popup(self)

    def draw(self, context):
        layout = self.layout
        layout.label(text="In case of problem :")
        layout.label(text="-Avoid Blendermania as I use the same classes.")
        layout.label(text="-UV Occ: not functional for night mode borders.")
        layout.label(text="-Add light: requires no other StartLight in the map.")
        layout.label(text="-Material: set image path in Edit Preferences.")
        layout.label(text="-Import: ensure Dotnet is added to Utils folder for errors.")
        layout.label(text="-Detected Objets: can take 10 seconds.")
        layout.label(text="-TextureCustom: an object must be selected.")
        layout.label(text="-Auto: must have the same name as GameTexture")


# Operator to open documentation
class SNA_OT_OpenDocumentation(bpy.types.Operator):
    bl_idname = "sna.open_documentation"
    bl_label = "Documentation"
    bl_description = ""
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        webbrowser.open('https://docs.google.com/document/d/1NPc3UE9vzHdGh73wqbt_pFpTByCeFQFgEFyGJ88DiCs/edit')
        return {"FINISHED"}
        
# Operator to open github
class SNA_OT_OpenGithub(bpy.types.Operator):
    bl_idname = "sna.open_github"
    bl_label = "github"
    bl_description = ""
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        webbrowser.open('https://github.com/SuperCoby/')
        return {"FINISHED"}
        
# Operator to open web
class SNA_OT_OpenWeb(bpy.types.Operator):
    bl_idname = "sna.open_web"
    bl_label = "web"
    bl_description = ""
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        webbrowser.open('https://github.com/SuperCoby/')
        return {"FINISHED"}


# Operator to open Discord
class SNA_OT_OpenDiscord(bpy.types.Operator):
    bl_idname = "sna.open_discord"
    bl_label = "Discord"
    bl_description = ""
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        webbrowser.open('https://discord.gg/n8mW58Uq')
        return {"FINISHED"}


# Registration and unregistration
def register():
    bpy.utils.register_class(SNA_PT_main)
    bpy.utils.register_class(SimpleOperator)
    bpy.utils.register_class(SNA_OT_OpenDocumentation)
    bpy.utils.register_class(SNA_OT_OpenGithub)
    bpy.utils.register_class(SNA_OT_OpenWeb)    
    bpy.utils.register_class(SNA_OT_OpenDiscord)
    global _icons
    _icons = bpy.utils.previews.new()
    # Ajuster les chemins pour correspondre à votre structure de dossier
    icons_dir = os.path.join(os.path.dirname(__file__), '..', 'Icons')
    if not 'DISCORD' in _icons: _icons.load('DISCORD', os.path.join(icons_dir, 'DISCORD.png'), "IMAGE")
    if not 'documentation' in _icons: _icons.load('documentation', os.path.join(icons_dir, 'documentation.png'), "IMAGE")
    if not 'github' in _icons: _icons.load('github', os.path.join(icons_dir, 'github.png'), "IMAGE")
    if not 'web' in _icons: _icons.load('web', os.path.join(icons_dir, 'web.png'), "IMAGE")    
    if not 'info' in _icons: _icons.load('info', os.path.join(icons_dir, 'info.png'), "IMAGE")


def unregister():
    bpy.utils.unregister_class(SimpleOperator)
    bpy.utils.unregister_class(SNA_OT_OpenDocumentation)
    bpy.utils.unregister_class(SNA_OT_OpenGithub)
    bpy.utils.unregister_class(SNA_OT_OpenDiscord)
    bpy.utils.unregister_class(SNA_OT_OpenWeb)    
    global _icons
    bpy.utils.previews.remove(_icons)
    bpy.utils.unregister_class(SNA_PT_main)


if __name__ == "__main__":
    register()
