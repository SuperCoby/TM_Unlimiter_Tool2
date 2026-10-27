import bpy


# The 2 boxes exclude each other: combined, the visual would be animated twice
def _on_enabled(self, _context):
    if self.enabled and self.use_map:
        self.use_map = False


def _on_use_map(self, _context):
    if self.use_map and self.enabled:
        self.enabled = False


class TMBLOCKANIM_Instance(bpy.types.PropertyGroup):
    # One instance of the block placed in the map: rank among the instances + grid coordinate
    rank: bpy.props.IntProperty()
    x: bpy.props.IntProperty()
    y: bpy.props.IntProperty()
    z: bpy.props.IntProperty()
    animated: bpy.props.BoolProperty()
    selected: bpy.props.BoolProperty(default=True)


class TMBLOCKANIM_Settings(bpy.types.PropertyGroup):
    instances: bpy.props.CollectionProperty(type=TMBLOCKANIM_Instance)
    list_source: bpy.props.StringProperty()
    map_blocks: bpy.props.StringProperty()  # custom blocks found in the map, for the error message
    use_map: bpy.props.BoolProperty(
        name="In the map + collision", default=False, update=_on_use_map,
        description="Writes the animation as a TMUnlimiter Block Motion into a map (visual + collision)",
    )
    map_path: bpy.props.StringProperty(
        name="Map", subtype="FILE_PATH",
        description=".Challenge.Gbx map where your block is already placed",
    )
    backup: bpy.props.BoolProperty(
        name="Create .bak", default=True,
        description="Copy the map to .bak before writing to it",
    )
    enabled: bpy.props.BoolProperty(
        name="Export the animation in the block", default=True, update=_on_enabled,
        description="Writes this object's keyframes into the .Block.Gbx (the visual moves, the collision stays still)",
    )


classes = (
    TMBLOCKANIM_Instance,
    TMBLOCKANIM_Settings,
)


def register():
    bpy.types.Object.tm_block_animation = bpy.props.PointerProperty(type=TMBLOCKANIM_Settings)


def unregister():
    if hasattr(bpy.types.Object, "tm_block_animation"):
        del bpy.types.Object.tm_block_animation
