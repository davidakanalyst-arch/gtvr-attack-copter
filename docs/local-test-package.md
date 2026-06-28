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

The installer creates one custom repaint folder named `prototype_tactical` from the local EC135 `german_army` repaint, then removes the other stock repaint folders. It keeps `highskids` because that tactical repaint depends on the hidden high-skid option.
