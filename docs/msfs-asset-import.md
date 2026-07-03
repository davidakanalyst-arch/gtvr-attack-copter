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
- emitting transparent dummy geometry for every other Optica geometry reference,
- retaining the existing Wraith animated main-rotor placeholder,
- assembling a local test package at `local-aircraft-packages\gtvr_wraith_heli`.

The currently installed live test build used:

```powershell
python tools\build_gtvr_wraith_msfs.py --prepare-source --preset uh60 --max-faces 100000 --max-texture-size 1024
python tools\run_aerofly_converter.py gtvr_wraith_heli tools\vendor\gtvr_wraith_msfs_source\aircraft --userfolder tools\vendor\gtvr_wraith_msfs_launch
python tools\build_gtvr_wraith_msfs.py --assemble-package --preset uh60 --max-faces 100000 --max-texture-size 1024
```

and was copied to:

```text
C:\Users\david\Documents\Aerofly FS 4\aircraft\gtvr_wraith_heli
```

## Current Limits

This improves the exterior shell path only. It does not solve the helicopter flight model because the package still uses the Optica donor graph. Controls, ground behavior, sound semantics, and cockpit camera behavior remain inherited from Optica unless a real Aerofly helicopter graph is found or built.

The MSFS source archives and generated converter output stay local-only. Do not commit or redistribute imported MSFS assets.

