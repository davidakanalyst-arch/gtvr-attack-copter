# Geometry Replacement

The live prototype still keeps the original EC135-derived compiled aircraft model:

```text
C:\Users\david\Documents\Aerofly FS 4\aircraft\gtvr_attack_copter\gtvr_attack_copter.tmb
```

That is intentional for now. The EC135 cockpit and most of the flight/graphics glue appear to live inside the compiled `.tmb`/`.tmq` pair, so replacing the whole file with a minimal custom shell would likely remove the glass cockpit we want to preserve.

## Current Approach

The first visible custom-geometry path is an overlay object loaded through Aerofly's external pilot model slot.

Evidence from the converter log:

```text
geometry 'objects/pilot_jason/pilot_jason.tmb' not found
geometry 'PilotBody' not found
geometry 'PilotHead' not found
geometry 'HeadsetLower' not found
geometry 'HeadsetUpper' not found
```

So the GTVR shell is compiled as `gtvr_attack_shell.tmb`, with geometry groups named:

```text
PilotBody
PilotHead
HeadsetLower
HeadsetUpper
```

The live `gtvr_attack_copter.tmc` now points `Pilot` at `gtvr_attack_shell`. This keeps the aircraft package flyable while adding a tactical shell through a loader path Aerofly already supports.

## Build Commands

```powershell
python tools\build_gtvr_source_project.py --profile pilot-overlay --user-dir tools\vendor\gtvr_overlay_test_user
python tools\run_aerofly_converter.py gtvr_attack_shell tools\vendor\gtvr_overlay_source\aircraft --userfolder tools\vendor\gtvr_overlay_launch
python tools\install_gtvr_overlay_object.py
```

## Open Risk

The next manual FS4 test decides whether the pilot-slot object is positioned and shown the way we need. If it appears only in external views, that is probably acceptable. If it is offset, hidden, or only visible in cockpit views, the fallback is to refine the object coordinates or find another text-loadable graphics hook.
