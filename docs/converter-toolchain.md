# Aerofly Converter Toolchain

The Aerofly FS 4 aircraft converter is now working locally from the ignored SDK/tool folder under `tools/vendor/`.

The reproducible launch contract is:

```powershell
python tools\run_aerofly_converter.py gtvr_attack_shell tools\vendor\gtvr_overlay_source\aircraft --userfolder tools\vendor\gtvr_overlay_launch
```

That wrapper launches `aerofly_fs_4_aircraft_converter.exe` with:

```text
-userfolder='<launch-log-folder>/' model='<source-folder-name>' dir='<source-aircraft-root>/'
```

The converter reads its output paths from `dir\config.tmc`, not from the `-userfolder` directory. Missing `world`, `texture`, or `shader_vulkan` resources can cause the converter to crash; the source generator copies those resource folders into the generated source root when available.

## Overlay Workflow

The current visible-geometry path preserves the EC135-derived cockpit and flight model by using Aerofly's external pilot-object slot as a shell overlay:

```powershell
python tools\build_gtvr_source_project.py --profile pilot-overlay --user-dir tools\vendor\gtvr_overlay_test_user
python tools\run_aerofly_converter.py gtvr_attack_shell tools\vendor\gtvr_overlay_source\aircraft --userfolder tools\vendor\gtvr_overlay_launch
python tools\install_gtvr_overlay_object.py
```

The converter emits:

```text
tools\vendor\gtvr_overlay_test_user\aircraft\gtvr_attack_shell\gtvr_attack_shell.tmb
```

The installer copies that object and its converted textures into:

```text
C:\Users\david\Documents\Aerofly FS 4\objects\gtvr_attack_shell
C:\Users\david\Documents\Aerofly FS 4\aircraft\gtvr_attack_copter\objects\gtvr_attack_shell
```

It also changes the live aircraft metadata from `Pilot[pilot_jason]` to `Pilot[gtvr_attack_shell]`, with a backup beside the live `.tmc`.

## Notes

The full replacement `gtvr_attack_copter.tmb` path is still risky because replacing that compiled model would likely remove the EC135 cockpit geometry. The pilot-slot overlay is the safer current path: it adds a custom tactical shell while leaving `gtvr_attack_copter.tmb`, `gtvr_attack_copter.tmq`, controls, sounds, and cockpit textures intact.
