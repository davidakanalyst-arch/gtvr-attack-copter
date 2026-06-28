# Repaint Workflow

The safe visible prototype path is a generated repaint, not a geometry patch.

The live aircraft must stay on:

```text
<[string8][Pilot][pilot_jason]>
```

That keeps the EC135-derived cockpit, flight model, systems, and sound loaded. The tactical repaint only replaces the exterior color textures inside the `prototype_tactical` repaint folder.

## Build And Convert

```powershell
python tools\build_gtvr_repaint_source.py --user-dir tools\vendor\gtvr_repaint_test_user
python tools\run_aerofly_converter.py gtvr_repaint_textures tools\vendor\gtvr_repaint_source\aircraft --userfolder tools\vendor\gtvr_repaint_launch
```

The converter emits:

```text
tools\vendor\gtvr_repaint_test_user\aircraft\gtvr_repaint_textures\ext01_fuselage_color.ttx
tools\vendor\gtvr_repaint_test_user\aircraft\gtvr_repaint_textures\ext02_fuselage_color.ttx
tools\vendor\gtvr_repaint_test_user\aircraft\gtvr_repaint_textures\ext03_fuselage_color.ttx
```

## Install

```powershell
python tools\install_gtvr_repaint_textures.py
```

The installer copies those three converted textures into:

```text
C:\Users\david\Documents\Aerofly FS 4\aircraft\gtvr_attack_copter\prototype_tactical
```

It renames the repaint option to `GTVR Tactical Black` and backs up the previous files beside the repaint folder:

```text
C:\Users\david\Documents\Aerofly FS 4\aircraft\gtvr_attack_copter\_prototype_tactical_pre_gtvr_generated_repaint
```

## Scope

This makes the flyable EC135-derived prototype visibly different without touching the compiled aircraft model. It does not solve the shell replacement problem; it is the safe interim visual layer while the geometry route is researched.

The EC135 exterior UV layout spreads texture regions across the fuselage, roof, and tail boom in ways that are not obvious from file names alone. Keep repaint art broad and repeated across all three exterior maps; avoid long readable labels because they can land on the tail or wrap across unexpected panels.
