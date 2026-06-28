from __future__ import annotations

import math
from pathlib import Path

import bpy


ROOT = Path(__file__).resolve().parents[1]
OBJ_PATH = ROOT / "source-model" / "gtvr_attack_copter_shell.obj"
BLEND_PATH = ROOT / "blender" / "gtvr_attack_copter_shell.blend"
EXPORT_DIR = ROOT / "exports"


def clear_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()


def configure_scene() -> None:
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0
    scene.render.engine = "BLENDER_EEVEE_NEXT"


def import_shell() -> list[bpy.types.Object]:
    bpy.ops.wm.obj_import(filepath=str(OBJ_PATH), forward_axis="Y", up_axis="Z")
    objects = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    for obj in objects:
        obj.name = f"gtvr_{obj.name}"
        obj.data.name = obj.name
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)
        bpy.ops.object.shade_flat()
        obj.select_set(False)
    return objects


def add_empty(name: str, location: tuple[float, float, float], rotation: tuple[float, float, float] = (0.0, 0.0, 0.0)) -> None:
    bpy.ops.object.empty_add(type="ARROWS", location=location, rotation=rotation)
    empty = bpy.context.object
    empty.name = name
    empty.empty_display_size = 0.45


def add_reference_empties() -> None:
    add_empty("gtvr_ref_main_rotor_axis", (0.2, 0.0, 2.55))
    add_empty("gtvr_ref_tail_rotor_axis", (-5.9, 0.0, 0.58), (math.radians(90.0), 0.0, 0.0))
    add_empty("gtvr_ref_cockpit_eye_line", (3.15, 0.0, 1.28))
    add_empty("gtvr_ref_fuselage_origin", (0.0, 0.0, 0.0))


def add_camera_and_light() -> None:
    bpy.ops.object.light_add(type="AREA", location=(2.8, -6.0, 5.0))
    light = bpy.context.object
    light.name = "gtvr_key_light"
    light.data.energy = 450
    light.data.size = 5

    bpy.ops.object.camera_add(location=(7.5, -8.5, 3.7), rotation=(math.radians(66.0), 0.0, math.radians(42.0)))
    bpy.context.scene.camera = bpy.context.object


def organize_collections(objects: list[bpy.types.Object]) -> None:
    collection = bpy.data.collections.new("GTVR_Attack_Copter_Source")
    bpy.context.scene.collection.children.link(collection)
    for obj in objects:
        for existing in obj.users_collection:
            existing.objects.unlink(obj)
        collection.objects.link(obj)


def export_interchange() -> None:
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.obj_export(filepath=str(EXPORT_DIR / "gtvr_attack_copter_shell_named.obj"), export_materials=True)


def main() -> None:
    clear_scene()
    configure_scene()
    objects = import_shell()
    organize_collections(objects)
    add_reference_empties()
    add_camera_and_light()
    export_interchange()
    BLEND_PATH.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH))


if __name__ == "__main__":
    main()

