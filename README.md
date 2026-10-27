<h1 align="center">
  TM_Unlimiter_Tool 2.0
</h1>

<p align="center">
  <a href="https://unlimiter.net/download" target="_blank">
    <img src="https://img.shields.io/badge/Unlimiter-2.0-2" alt="Trackmania Unlimiter" />
  </a>
  <a href="https://discord.gg/uD4UAJr" target="_blank">
    <img src="https://img.shields.io/badge/Discord%20-official-brightgreen" alt="Discord Unlimiter"/>
  </a>
  <img src="https://img.shields.io/badge/Trackmania-Nation%20Forever-brightgreen" alt="Trackmania"/>
  <img src="https://img.shields.io/badge/Blender-5.1.1%2B-orange" alt="Blender 5.1.1+"/>
</p>


TM Unlimiter Tool for Unlimiter 2.0: a Blender add-on to build custom TrackMania Nations/United Forever blocks.


## Requirements

- **Blender 5.1.1** or newer
- Optional: [TrackMania Unlimiter: Custom Block exporter](https://github.com/tomek0055/tmunlimiter_blender_plugin) (`tmunlimiter_blender_plugin`), needed for the block export features. Without it, those features are hidden and the rest of the add-on works normally.

## Installation

1. Download `TM_Unlimiter_Tool-main.zip` from the [latest release](https://github.com/SuperCoby/TM_Unlimiter_Tool2/releases/latest)
2. In Blender: **Edit > Preferences > Add-ons > Install from Disk** and select the .zip
3. Enable **TM_Unlimiter_Tool**
4. In the add-on preferences, set your **TMNF / TM² / TM2020 texture folders** and your **Block Author** name

The tools are in the 3D View sidebar (**N**), **TM** tab.


## Features

### Import
- **.Item.Gbx** (ManiaPlanet / TM2020 items)
- **.Solid.Gbx** (TMNF/TMUF meshes): TMNF material names, UVs, checkpoint/finish triggers
- **.Block.Gbx** (TMUnlimiter custom blocks): full object hierarchy, Ground/Air variations, spawns, block units and tmunlimiter settings, ready to be re-exported
- Import a single file or a whole folder
- **Shift+A > Edge Base**: ready-made Stadium edge meshes

### Materials
- Browse your game textures with previews
- Add a texture to a material, or create a material from a texture, named like the TMUnlimiter material (e.g. `StadiumGrass1.dds` → `StadiumGrass`)

### Tool 2.0
- Separate by material + modifiers, merge duplicated materials
- Occlusion / fake light UV maps
- **Game material**: sets the TMUnlimiter game material and collision material automatically

### Detection Units
- Generate a block unit grid (Stadium, Coast, Island, Snow, Desert, Rally, Bay)
- **Detected Objects**: exact detection of the block units used by a mesh

### Render Icon
- 64×64 block icon render, transparent background by default

### Block Animation
- Animate an object with keyframes: a rotation on one axis **or** a translation (the game loops between the first and last keyframe)
- **In the block (fake collision)**: exported into the .Block.Gbx with tmunlimiter, only the visual moves
- **In the map + collision**: written as a TMUnlimiter **Block Motion** onto the blocks already placed in a .Challenge.Gbx map (visual and collision move), with an optional .bak backup

### With tmunlimiter_blender_plugin
- **Auto Block Definition**: creates a block definition from the selected collection (Ground/Grass/Air models, triggers, spawns, waypoint type, block units)
- **Export Multiple**, with collection/subfolder entries to sort the exported files into folders (indented, foldable list)
- **Custom Texture** panel, collision controls and **Debug** report in the 3D View header
- Works on Blender 5 out of the box (built-in replacement for the `python-lzo` module tmunlimiter needs)
