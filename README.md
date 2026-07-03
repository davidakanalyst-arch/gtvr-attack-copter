# GTVR Attack Copter

Fictional Aerofly FS 4 helicopter project.

Goal: keep the enjoyable EC135-style glass-cockpit flying experience, then dress the exterior in a compact military attack/scout shell.

## Direction

- Preserve a modern glass cockpit feel.
- Keep the aircraft compact and agile rather than heavy-transport sized.
- Build an original exterior: angular fuselage, armored canopy framing, sensor turret, stub wings, pylons, rocket pods, intake guards, exhaust covers, and tactical paint.
- Treat the stock Aerofly FS 4 EC135 as a local handling and package-structure reference only.
- Do not commit or redistribute IPACS stock aircraft assets.

## Current Contents

- `docs/design-brief.md` - visual and simulation target.
- `docs/aerofly-fs4-notes.md` - local FS4 paths and package notes from this machine.
- `docs/local-test-package.md` - how to install the private local FS4 prototype.
- `docs/manual-install.md` - manual copy/rename steps for learning the Aerofly aircraft layout.
- `docs/modeling-roadmap.md` - how the generated shell is intended to become a real exterior model.
- `docs/geometry-replacement.md` - geometry replacement findings, including the failed pilot-slot overlay diagnostic.
- `docs/converter-toolchain.md` - verified Aerofly converter launch contract and current cautions.
- `docs/repaint-workflow.md` - safe tactical repaint conversion and install workflow.
- `docs/livery-library.md` - local drag-and-drop livery library notes for EC135, F-15E, MB-339, and future aircraft.
- `docs/frankenheli.md` - non-EC135 Frankenstein rotorcraft build notes for `GTVR Wraith Heli`.
- `blender/create_gtvr_attack_copter_scene.py` - builds a Blender source scene from the named OBJ.
- `tools/generate_attack_copter_obj.py` - source generator for the first exterior shell concept.
- `tools/build_blender_source.py` - runs Blender in background to create the `.blend` source scene when Blender is installed.
- `tools/find_aerofly_converter.py` - searches this machine for the Aerofly aircraft/content converter.
- `tools/build_aerofly_geometry.py` - future one-command geometry build; currently fails fast if the converter is missing.
- `tools/build_gtvr_source_project.py` - generates Aerofly source files for the full shell or diagnostic pilot-slot overlay.
- `tools/build_gtvr_repaint_source.py` - generates source PNGs for the camo, black, and desert attack repaints.
- `tools/build_gtvr_menu_preview_source.py` - builds converter source files for custom aircraft selection preview images.
- `tools/build_gtvr_aircraft_liveries.py` - generates and assembles F-15E Strike and MB-339 Assault repaint packages.
- `tools/build_gtvr_frankenheli.py` - builds a non-EC135 experimental custom military rotorcraft package from the generated shell plus an open donor aircraft graph.
- `tools/run_aerofly_converter.py` - drives the Aerofly converter GUI using the discovered launch contract.
- `tools/install_gtvr_repaint_textures.py` - installs converted attack repaint textures and previews with backups.
- `tools/install_gtvr_overlay_object.py` - diagnostic-only pilot-slot installer; refuses to patch live aircraft by default.
- `tools/install_local_test_package.py` - creates a private local FS4 working aircraft from your installed EC135.
- `source-model/gtvr_attack_copter_shell.obj` - generated low-poly concept mesh.
- `source-model/gtvr_attack_copter_shell.mtl` - generated material palette.

## Next Build Steps

1. Test `GTVR Wraith Heli` as the non-EC135 Frankenstein path.
2. Use `GTVR Attack Black`, `GTVR Attack Camo`, and `GTVR Attack Desert` as the safe EC135 repaint path.
3. Treat the standalone EC135-derived `gtvr_attack_copter` aircraft as a drag-copy archive only.
4. Treat the `gtvr_attack_shell` pilot-slot overlay as a failed diagnostic: it triggered the FS4 fallback STOP model and removed helicopter sound/dynamics.
5. Tune the Wraith's donor flight graph after the first in-game load/fly test.
