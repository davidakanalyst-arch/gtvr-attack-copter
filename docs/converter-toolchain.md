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

## Failed Overlay Diagnostic

The converter can build the `gtvr_attack_shell` object, but the runtime test showed that the external pilot-object slot is not a safe visible-shell path for this aircraft.

These commands are useful only for reproducing the failed diagnostic:

```powershell
python tools\build_gtvr_source_project.py --profile pilot-overlay --user-dir tools\vendor\gtvr_overlay_test_user
python tools\run_aerofly_converter.py gtvr_attack_shell tools\vendor\gtvr_overlay_source\aircraft --userfolder tools\vendor\gtvr_overlay_launch
python tools\install_gtvr_overlay_object.py --experimental-pilot-slot
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

When forced, the installer changes the live aircraft metadata from `Pilot[pilot_jason]` to `Pilot[gtvr_attack_shell]`, with a backup beside the live `.tmc`.

Do not use that patch as the working mod path. In FS4, the modified aircraft failed to load its main TMD graph and the simulator loaded the fallback STOP model. The log showed missing geometry references:

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

The fallback model has no helicopter dynamics or sound, which is why the sim showed the red STOP object and the aircraft could not fly.

## Notes

The full replacement `gtvr_attack_copter.tmb` path is still risky because replacing that compiled model would likely remove the EC135 cockpit geometry. The next viable route is to find a text-loadable graphics hook or a compiled-model merge path that preserves `gtvr_attack_copter.tmb`, `gtvr_attack_copter.tmq`, controls, sounds, and cockpit textures.

The currently safe converter use is the repaint texture workflow in `docs/repaint-workflow.md`. It converts generated PNGs into the three exterior `.ttx` files used by the `prototype_tactical` repaint and does not patch the aircraft graph.
