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
- `docs/geometry-replacement.md` - current pilot-slot overlay strategy for visible custom geometry.
- `docs/converter-toolchain.md` - verified Aerofly converter launch and overlay workflow.
- `blender/create_gtvr_attack_copter_scene.py` - builds a Blender source scene from the named OBJ.
- `tools/generate_attack_copter_obj.py` - source generator for the first exterior shell concept.
- `tools/build_blender_source.py` - runs Blender in background to create the `.blend` source scene when Blender is installed.
- `tools/find_aerofly_converter.py` - searches this machine for the Aerofly aircraft/content converter.
- `tools/build_aerofly_geometry.py` - future one-command geometry build; currently fails fast if the converter is missing.
- `tools/build_gtvr_source_project.py` - generates Aerofly source files for the full shell or pilot-slot overlay.
- `tools/run_aerofly_converter.py` - drives the Aerofly converter GUI using the discovered launch contract.
- `tools/install_gtvr_overlay_object.py` - installs the compiled overlay object and patches the live `Pilot` pointer.
- `tools/install_local_test_package.py` - creates a private local FS4 working aircraft from your installed EC135.
- `source-model/gtvr_attack_copter_shell.obj` - generated low-poly concept mesh.
- `source-model/gtvr_attack_copter_shell.mtl` - generated material palette.

## Next Build Steps

1. Test the installed `gtvr_attack_shell` pilot-slot overlay in FS4.
2. If the overlay is visible but offset, refine the source OBJ coordinates and rebuild.
3. If the overlay is hidden by the pilot-view rules, find another text-loadable graphics hook.
4. Keep the original EC135-derived `.tmb` in place until the cockpit can be preserved another way.
