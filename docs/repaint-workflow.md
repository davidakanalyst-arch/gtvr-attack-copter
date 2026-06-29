# Repaint Workflow

The safe visible prototype path is a generated repaint, not a geometry patch.

The live aircraft must stay on:

```text
<[string8][Pilot][pilot_jason]>
```

That keeps the EC135-derived cockpit, flight model, systems, and sound loaded. The tactical repaint only replaces the exterior color textures inside the `prototype_tactical` repaint folder.

## Build And Convert

Build and install the GTVR camo repaint:

```powershell
python tools\build_gtvr_repaint_source.py --variant olive --user-dir tools\vendor\gtvr_repaint_test_user
python tools\run_aerofly_converter.py gtvr_repaint_textures tools\vendor\gtvr_repaint_source\aircraft --userfolder tools\vendor\gtvr_repaint_launch
python tools\install_gtvr_repaint_textures.py --variant olive
```

Build and install the black repaint:

```powershell
python tools\build_gtvr_repaint_source.py --variant black --user-dir tools\vendor\gtvr_repaint_test_user
python tools\run_aerofly_converter.py gtvr_repaint_textures tools\vendor\gtvr_repaint_source\aircraft --userfolder tools\vendor\gtvr_repaint_launch
python tools\install_gtvr_repaint_textures.py --variant black
```

Build and install the desert repaint:

```powershell
python tools\build_gtvr_repaint_source.py --variant desert --user-dir tools\vendor\gtvr_repaint_test_user
python tools\run_aerofly_converter.py gtvr_repaint_textures tools\vendor\gtvr_repaint_source\aircraft --userfolder tools\vendor\gtvr_repaint_launch
python tools\install_gtvr_repaint_textures.py --variant desert
```

Each converter run emits:

```text
tools\vendor\gtvr_repaint_test_user\aircraft\gtvr_repaint_textures\ext01_fuselage_color.ttx
tools\vendor\gtvr_repaint_test_user\aircraft\gtvr_repaint_textures\ext02_fuselage_color.ttx
tools\vendor\gtvr_repaint_test_user\aircraft\gtvr_repaint_textures\ext03_fuselage_color.ttx
```

## Install

The olive install copies converted textures into:

```text
C:\Users\david\Documents\Aerofly FS 4\aircraft\gtvr_attack_copter\prototype_tactical
```

It renames that repaint option to `GTVR Attack Camo` and backs up the previous files beside the repaint folder:

```text
C:\Users\david\Documents\Aerofly FS 4\aircraft\gtvr_attack_copter\_prototype_tactical_pre_gtvr_generated_repaint
```

The black install copies converted textures into the GTVR aircraft root and into this user-side EC135 repaint:

```text
C:\Users\david\Documents\Aerofly FS 4\aircraft\ec135\gtvr_attack_black
```

The desert install copies converted textures into these repaint folders:

```text
C:\Users\david\Documents\Aerofly FS 4\aircraft\gtvr_attack_copter\prototype_desert
C:\Users\david\Documents\Aerofly FS 4\aircraft\ec135\gtvr_attack_desert
```

The EC135 repaint is created from the stock `german_army` repaint as a local user repaint. The installer does not modify the Steam EC135 folder.

The converter's generated preview files are not installed because this texture-only converter project uses dummy geometry and produces blank aircraft menu images. GTVR preview files are restored from the live package backups, and the EC135 user repaint preview is copied from the stock `german_army` repaint.

To repair previews without reinstalling textures:

```powershell
python tools\install_gtvr_repaint_textures.py --repair-previews
```

## Scope

This makes the flyable EC135-derived prototype visibly different without touching the compiled aircraft model. It does not solve the shell replacement problem; it is the safe interim visual layer while the geometry route is researched.

The EC135 exterior UV layout spreads texture regions across the fuselage, roof, and tail boom in ways that are not obvious from file names alone. Keep repaint art broad and repeated across all three exterior maps. The generated attack camo uses armor-panel blocks, dark red strike marks, sensor circles, fastener grids, and low-visibility `ATTACK COPTER` stencils so the aircraft reads more like a compact military scout without changing the model. The black variant removes the olive base panels and uses neutral charcoal panels instead. The desert variant uses a sand base with darker khaki armor panels.
