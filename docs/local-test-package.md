# Local Aerofly Test Package

The fastest way to get a selectable aircraft is to create a private local working copy of the installed EC135, then rename its metadata to `GTVR Attack Copter`. This gives us a safe baseline for menu visibility, cockpit feel, and handling while the original exterior model is developed.

This is a local prototype only:

- It copies stock Aerofly files into `Documents/Aerofly FS 4/aircraft/gtvr_attack_copter`.
- It does not commit or redistribute stock assets.
- It keeps the copied aircraft outside the repository.
- It also places the generated `source-model` OBJ/MTL beside the local prototype for reference.

Run:

```powershell
python tools\install_local_test_package.py --force
```

Then start Aerofly FS 4 and look for:

```text
GTVR Attack Copter
```

The first installed prototype will still visually resemble the EC135 until a safe custom-geometry route is found.

The external pilot-object slot was tested as a possible non-destructive overlay:

```powershell
python tools\build_gtvr_source_project.py --profile pilot-overlay --user-dir tools\vendor\gtvr_overlay_test_user
python tools\run_aerofly_converter.py gtvr_attack_shell tools\vendor\gtvr_overlay_source\aircraft --userfolder tools\vendor\gtvr_overlay_launch
python tools\install_gtvr_overlay_object.py --experimental-pilot-slot
```

That route failed in FS4: the aircraft loaded the fallback STOP model, with no helicopter sound or flight dynamics. Keep the local test package on `Pilot[pilot_jason]` until a different graphics hook or compiled-model merge route is proven.

The safe interim visual path is the generated attack-wrap repaint pair:

```powershell
python tools\build_gtvr_repaint_source.py --variant olive --user-dir tools\vendor\gtvr_repaint_test_user
python tools\run_aerofly_converter.py gtvr_repaint_textures tools\vendor\gtvr_repaint_source\aircraft --userfolder tools\vendor\gtvr_repaint_launch
python tools\install_gtvr_repaint_textures.py --variant olive

python tools\build_gtvr_repaint_source.py --variant black --user-dir tools\vendor\gtvr_repaint_test_user
python tools\run_aerofly_converter.py gtvr_repaint_textures tools\vendor\gtvr_repaint_source\aircraft --userfolder tools\vendor\gtvr_repaint_launch
python tools\install_gtvr_repaint_textures.py --variant black
```

That updates the GTVR prototype to two visible attack-wrap choices: root `GTVR Attack Black` and `prototype_tactical` `GTVR Attack Wrap`. The black variant is also installed as a user-side EC135 repaint named `GTVR Attack Black` without touching the stock Steam aircraft folder.

The installer creates one custom repaint folder named `prototype_tactical` from the local EC135 `german_army` repaint, then removes the other stock repaint folders. It keeps `highskids` because that tactical repaint depends on the hidden high-skid option.
