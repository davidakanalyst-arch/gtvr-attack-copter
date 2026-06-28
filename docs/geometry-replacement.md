# Geometry Replacement

The current in-game prototype still uses the EC135 compiled model:

```text
gtvr_attack_copter.tmb
```

That file is the visual geometry bundle Aerofly FS 4 loads. Repaints and option folders can change textures and menu variants, but they do not replace the actual helicopter shape.

## What We Have Now

- A working selectable FS4 aircraft folder.
- EC135-style cockpit and handling preserved.
- A real tactical repaint option.
- A named source shell at `source-model/gtvr_attack_copter_shell.obj`.
- A Blender scene builder at `blender/create_gtvr_attack_copter_scene.py`.

## What Must Happen To See The New Shell In-Game

1. Build/refine the exterior model in Blender.
2. Keep the glass cockpit volume and rotor reference axes aligned.
3. Export through the Aerofly aircraft/content conversion workflow.
4. Replace the local prototype's compiled model bundle with a GTVR-generated `.tmb`.
5. Test in FS4, then iterate object names, origins, animations, and materials.

## Current Machine State

At the time this note was written, neither Blender nor an Aerofly content converter executable was found in the usual install locations on this machine. The source pipeline is ready, but the compiled in-game model cannot be produced locally until those tools are available.

Run this after Blender is installed:

```powershell
python tools\build_blender_source.py
```

