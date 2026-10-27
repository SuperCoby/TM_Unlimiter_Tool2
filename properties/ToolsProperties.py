import bpy


def register():
    # Ajouter une propriété EnumProperty pour la liste déroulante
    bpy.types.Scene.uv_option = bpy.props.EnumProperty(
        items=[
            ("SROMap", "StadiumRoadO", "StadiumRoadO.dds"),
            ("SRO2Map", "StadiumRoadO2", "StadiumRoadO2.dds"),
            ("SWOmap", "StadiumWarpO", "StadiumWarpO.dds"),
            ("SWO2Map", "StadiumWarpO2", "StadiumWarpO2.dds"),
            ("SGOMap", "StadiumGrassO", "StadiumGrassO.dds"),
            ("SFOMap", "StadiumFabricO", "StadiumFabricO.dds"),
            ("SCOMap", "StadiumControlO", "StadiumControlO.dds"),
            ("SAOMap", "StadiumAirshipO", "StadiumAirshipO.dds"),
        ],
        default="SROMap",  # Option par défaut
        description="Information",
    )

    # Ajouter une deuxième propriété EnumProperty pour le deuxième menu déroulant
    bpy.types.Scene.uv_option_2 = bpy.props.EnumProperty(
        items=[
            ("RedLight", "RedLight", "StadiumStartSignGlow.dds"),
            ("GreenLight", "GreenLight", "StadiumStartSignGlow.dds"),
            ("OrangeLight", "OrangeLight", "StadiumStartSignGlow.dds"),
        ],
        default="RedLight",  # Option par défaut
        description="Information",
    )

    bpy.types.Scene.tmu_manual_auto_menu = bpy.props.EnumProperty(
        items=[
            ("Manual", "Manual", ""),
            ("Auto", "Auto", ""),
        ],
        default="Manual",
    )


def unregister():
    del bpy.types.Scene.uv_option
    del bpy.types.Scene.uv_option_2
    del bpy.types.Scene.tmu_manual_auto_menu
