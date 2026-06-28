# Geometry Replacement

The live prototype still keeps the original EC135-derived compiled aircraft model:

```text
C:\Users\david\Documents\Aerofly FS 4\aircraft\gtvr_attack_copter\gtvr_attack_copter.tmb
```

That is intentional for now. The EC135 cockpit and most of the flight/graphics glue appear to live inside the compiled `.tmb`/`.tmq` pair, so replacing the whole file with a minimal custom shell would likely remove the glass cockpit we want to preserve.

## Failed Pilot-Slot Approach

The first visible custom-geometry path tried to load an overlay object through Aerofly's external pilot model slot.

The initial clue came from converter output for the stock pilot object:

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

The compiled object was then installed as `gtvr_attack_shell` and the live `gtvr_attack_copter.tmc` was pointed at it with:

```text
<[string8][Pilot][gtvr_attack_shell]>
```

That failed in FS4. The simulator did not load the helicopter; it loaded the fallback STOP model instead. The runtime log showed:

```text
geometry 'PilotBody' not found
object 'PilotBody' not found
geometry 'PilotHead' not found
object 'PilotHead' not found
geometry 'HeadsetLower' not found
object 'HeadsetLower' not found
geometry 'HeadsetUpper' not found
object 'HeadsetUpper' not found
tmd error ( hint 'GeometryList HeadsetUpper' )
error loading tmd file 'gtvr_attack_copter'
loading fallback model...
```

The fallback model has no helicopter sound or flight dynamics, so this explains the red STOP object, silence, and no-flying behavior.

The live test aircraft has been rolled back to:

```text
<[string8][Pilot][pilot_jason]>
```

## Diagnostic Build Commands

These commands are retained only for reproducing or studying the failed path:

```powershell
python tools\build_gtvr_source_project.py --profile pilot-overlay --user-dir tools\vendor\gtvr_overlay_test_user
python tools\run_aerofly_converter.py gtvr_attack_shell tools\vendor\gtvr_overlay_source\aircraft --userfolder tools\vendor\gtvr_overlay_launch
python tools\install_gtvr_overlay_object.py --experimental-pilot-slot
```

## Current Direction

The pilot object slot cannot be used as the working exterior-shell mechanism for this aircraft. The next investigation needs to find either:

- a text-loadable graphics hook that can add a separate visual object while the EC135-derived compiled aircraft remains intact, or
- a compiled-model merge path that preserves the cockpit, controls, sounds, and systems from the original `.tmb`/`.tmq` pair.
