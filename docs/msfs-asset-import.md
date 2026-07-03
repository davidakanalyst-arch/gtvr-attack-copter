# MSFS Asset Import

The local folder:

```text
C:\Users\david\Downloads\MSFS Helis
```

contains useful helicopter visual sources, but they are not direct Aerofly aircraft conversions. MSFS packages provide glTF meshes, DDS textures, animation names, and flight-model reference values. Aerofly FS 4 still needs an Aerofly `.tmd`/`.tmq` control graph, matching geometry names, sounds, state files, and menu metadata.

## What Worked

`tools/build_msfs_shell_source.py` can read a local MSFS ZIP, resolve glTF mesh buffers, find DDS textures stored elsewhere in the archive, convert those textures to PNG source files, cap triangle count, and emit an Aerofly converter source project.

Verified on:

```powershell
python tools\build_msfs_shell_source.py --preset uh60 --max-faces 6000 --max-texture-size 512
python tools\run_aerofly_converter.py gtvr_msfs_uh60_shell tools\vendor\gtvr_msfs_shell_source\aircraft --userfolder tools\vendor\gtvr_msfs_shell_launch
```

The Aerofly converter completed and produced a compiled shell model.

`tools/build_gtvr_wraith_msfs.py` then bridges the imported MSFS exterior into the existing Optica-based `GTVR Wraith Heli` package by:

- importing the MSFS body into the Optica `Cabin` geometry name,
- emitting empty geometry slots for every other Optica geometry reference,
- retaining the existing Wraith animated main-rotor placeholder,
- assembling a local test package at `local-aircraft-packages\gtvr_wraith_heli`.

Do not use tiny placeholder triangles for unused donor geometry names. Aerofly still applies each donor object's transform, so visible placeholders turn into a cloud of scattered fragments around the aircraft. Empty patch lists are accepted by the converter and keep those donor geometry names invisible.

Also do not triangle-sample the MSFS body by keeping every Nth face. That makes the source model compile, but it shreds the visible aircraft into disconnected fragments. The current UH-60 Wraith test imports the full body mesh, rotates it 180 degrees around the vertical axis so the visual nose matches the Optica flight graph, keeps the UH-60 tail rotor visible, and filters out non-aircraft accessory nodes such as the firefighting bambi bucket, cargo hook, hoist, sling/load helpers, water effects, and baked MSFS main-rotor nodes.

The currently installed live test build used:

```powershell
python tools\build_gtvr_wraith_msfs.py --prepare-source --preset uh60 --max-faces 700000 --max-texture-size 1024
python tools\run_aerofly_converter.py gtvr_wraith_heli tools\vendor\gtvr_wraith_msfs_source\aircraft --userfolder tools\vendor\gtvr_wraith_msfs_launch
python tools\build_gtvr_wraith_msfs.py --assemble-package --preset uh60 --max-faces 700000 --max-texture-size 1024
```

and was copied to:

```text
C:\Users\david\Documents\Aerofly FS 4\aircraft\gtvr_wraith_heli
```

## Current Limits

This improves the exterior shell path only. It does not solve the helicopter flight model because the package still uses the Optica donor graph. Controls, ground behavior, sound semantics, and cockpit camera behavior remain inherited from Optica unless a real Aerofly helicopter graph is found or built.

The MSFS source archives and generated converter output stay local-only. Do not commit or redistribute imported MSFS assets.
