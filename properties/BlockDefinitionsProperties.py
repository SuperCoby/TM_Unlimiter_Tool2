import bpy

# Propriétés ajoutées à TMUnlimiter_BlockDefinition (classe de tmunlimiter_blender_plugin) par
# utils/TMUnlimiterPatches.py. Mêmes noms qu'avant, pour retrouver les données déjà
# enregistrées dans les .blend.


def extra_props():
    return {
        # Propriété pour la sélection d'export multiple
        "selected_for_export": bpy.props.BoolProperty(name="Export", default=False, description="Select this block for multiple export"),
        # Propriété pour changer l'icône (MATCUBE ou OUTLINER_COLLECTION)
        "use_collection_icon": bpy.props.BoolProperty(name="Use Collection Icon", default=False, description="Use collection icon instead of material cube icon"),
        # Propriété pour créer un sous-dossier
        "use_subfolder_icon": bpy.props.BoolProperty(name="Use Subfolder Icon", default=False, description="Create a subfolder in the current collection"),
        # Dossier (collection / sous-dossier) plié dans la liste
        "tmu_collapsed": bpy.props.BoolProperty(name="Collapsed", default=False, description="Fold or unfold this folder in the list"),
    }
