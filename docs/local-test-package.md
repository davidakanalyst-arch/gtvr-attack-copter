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

The first installed prototype will still visually resemble the EC135 until the generated shell is refined in Blender and exported through the Aerofly aircraft conversion workflow.

The installer creates one custom repaint folder named `prototype_tactical` from the local EC135 `german_army` repaint, then removes the other stock repaint folders. It keeps `highskids` because that tactical repaint depends on the hidden high-skid option.
