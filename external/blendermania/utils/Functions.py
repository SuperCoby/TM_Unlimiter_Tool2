from datetime import datetime
import subprocess
import bpy
import os
import re
import math
import pprint
from inspect import currentframe, getframeinfo


from .Constants import *
from .. import ADDON_ROOT_PATH


def fix_slash(filepath: str) -> str:
    """convert \\\+ to /"""
    filepath = re.sub(r"\\+", "/", filepath)
    filepath = re.sub(r"\/+", "/", filepath)
    return filepath


def is_file_existing(filepath: str) -> bool:
    return os.path.isfile(filepath)


def get_addon_path() -> str:
    return fix_slash(ADDON_ROOT_PATH + "/")


def get_addon_assets_path() -> str:
    return get_addon_path() + "assets/"


def radians(v, reverse=False) -> float:
    """return math.radians, example: some_blender_object.rotation_euler=(radian, radian, radian)"""
    return math.radians(v) if reverse is False else math.degrees(v)


def radian_list(*rads) -> list:
    """return math.radians as list"""
    return [radians(rad) for rad in rads]


def get_path_filename(filepath: str, remove_extension=False) -> str:
    filepath = fix_slash(filepath).split("/")[-1]

    if remove_extension:
        filepath = re.sub(r"\.\w+$", "", filepath, flags=re.IGNORECASE)

    return filepath


def select_obj(obj) -> bool:
    """selects object, no error during view_layer=scene.view_layers[0]"""
    if obj.hide_get() is False:
        obj.select_set(True)
        return True

    return False


def deselect_all_objects() -> None:
    """deselects all objects in the scene, works only for visible ones"""
    bpy.ops.object.select_all(action="DESELECT")


def set_active_object(obj) -> None:
    """set active object"""
    if obj.name in bpy.context.view_layer.objects:
        bpy.context.view_layer.objects.active = obj
        select_obj(obj)


def unset_active_object() -> None:
    """unset active object, deselect all"""
    bpy.context.view_layer.objects.active = None
    deselect_all_objects()


debug_list = ""


def debug(
    *args,
    pp=False,
    raw=False,
    add_to_list=False,
    save_list_to=None,
    clear_list=False,
    open_file=False,
) -> None:
    """better printer, adds line and filename as prefix"""
    global debug_list
    frameinfo = getframeinfo(currentframe().f_back)
    line = str(frameinfo.lineno)
    name = str(frameinfo.filename).split("\\")[-1]
    time = datetime.now().strftime("%H:%M:%S")

    line = line if int(line) > 10 else line + " "
    line = line if int(line) > 100 else line + " "
    line = line if int(line) > 1000 else line + " "
    line = line if int(line) > 10000 else line + " "
    # line = line if int(line) > 100000   else line + " "

    base = f"{line}, {time}, {name}"
    baseLen = len(base)
    dashesToAdd = 40 - baseLen

    # make sure base is 40 chars long, better reading between different files
    if dashesToAdd > 0:
        base += "-" * dashesToAdd

    if raw:
        base = ""

    print(base, end="")
    if add_to_list:
        debug_list += base

    if pp is True:
        for arg in args:
            pprint.pprint(arg, width=160)
            if add_to_list:
                debug_list += pprint.pformat(arg)
    else:
        for arg in args:

            text = " " + str(arg)
            print(text, end="")
            if add_to_list:
                debug_list += text

    print()
    if add_to_list:
        debug_list += "\n"

    if save_list_to is not None:
        with open(fix_slash(save_list_to), "w") as f:
            f.write(debug_list)
        if open_file:
            p = subprocess.Popen(f"notepad {save_list_to}")

    if clear_list:
        debug_list = ""


def redraw_panels(self, context):
    try:
        context.area.tag_redraw()
    except AttributeError:
        pass  # works fine but spams console full of errors... yes


def show_report_popup(
    title=str("some error occured"), infos: tuple = (), icon: str = "INFO"
):
    """create a small info(text) popup in blender, write infos to a file on desktop"""
    frameinfo = getframeinfo(currentframe().f_back)
    line = str(frameinfo.lineno)
    name = str(frameinfo.filename).split("\\")[-1]
    pyinfos = f"\n\nLINE: {line}\nFILE: {name}"

    title = str(title)

    def draw(self, context):
        # self.layout.label(text=f"This report is saved at: {desktopPath} as {fileName}.txt", icon="FILE_TEXT")
        for info in infos:
            self.layout.label(text=str(info))

    bpy.context.window_manager.popup_menu(draw, title=title, icon=icon)


def get_global_props() -> object:
    return bpy.context.scene.tm_props


def is_obj_visible_by_name(name: str) -> bool:
    """check if object will be visible ingame"""
    name = name.lower()
    return not name.startswith("_") or name.startswith(
        SPECIAL_NAME_PREFIX_NOTCOLLIDABLE
    )


def load_image_into_blender(texpath: str) -> tuple:
    """load image texture into blender, return tuple(bool(success), texNAME)"""
    imgs = bpy.data.images
    texpath = fix_slash(texpath)
    texName = get_path_filename(texpath)

    if not texpath:
        return False, ""

    debug(f"try to load texture into blender: {texpath}")

    if is_file_existing(filepath=texpath):

        if texName not in imgs:
            imgs.load(texpath)
            debug(f"texture loaded: { texName }")

        else:
            debug(f"texture already loaded: { texName }")

        return True, texName

    else:
        debug(f"failed to find file: {texName}")
        return False, texName


def add_indents(text: str, tab_count: int = 1) -> str:
    prefix = "    " * tab_count
    return prefix + text.replace("\n", "\n" + prefix)
