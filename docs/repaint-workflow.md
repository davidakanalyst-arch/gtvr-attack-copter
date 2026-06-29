# Repaint Workflow

The safe visible path is generated EC135 user repaints, not a geometry patch.

That keeps the stock EC135 cockpit, flight model, systems, and sound loaded. The tactical repaint only replaces exterior color textures and menu previews in local user repaint folders.

## Build And Convert

Build and install the EC135 camo repaint:

```powershell
python tools\build_gtvr_repaint_source.py --variant camo --user-dir tools\vendor\gtvr_repaint_test_user
python tools\run_aerofly_converter.py gtvr_repaint_textures tools\vendor\gtvr_repaint_source\aircraft --userfolder tools\vendor\gtvr_repaint_launch
python tools\install_gtvr_repaint_textures.py --variant camo
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

Build and convert the custom aircraft selection previews:

```powershell
python tools\build_gtvr_menu_preview_source.py
python tools\run_aerofly_converter.py gtvr_menu_preview tools\vendor\gtvr_menu_preview_source\aircraft --userfolder tools\vendor\gtvr_menu_preview_launch
python tools\install_gtvr_repaint_textures.py --repair-previews
```

The preview source plates live in:

```text
assets\menu-previews
```

These plates are transparent PNG cutouts. The builder writes RGB `*_color.png` files plus matching
`*_color_alpha.png` sidecars so the Aerofly converter can preserve transparency in the compiled
menu preview textures.

The converter emits:

```text
tools\vendor\gtvr_menu_preview_user\aircraft\gtvr_menu_preview\black_preview_color.ttx
tools\vendor\gtvr_menu_preview_user\aircraft\gtvr_menu_preview\black_preview_small_color.ttx
tools\vendor\gtvr_menu_preview_user\aircraft\gtvr_menu_preview\camo_preview_color.ttx
tools\vendor\gtvr_menu_preview_user\aircraft\gtvr_menu_preview\camo_preview_small_color.ttx
tools\vendor\gtvr_menu_preview_user\aircraft\gtvr_menu_preview\desert_preview_color.ttx
tools\vendor\gtvr_menu_preview_user\aircraft\gtvr_menu_preview\desert_preview_small_color.ttx
```

## Install

The camo install copies converted textures into this user-side EC135 repaint:

```text
C:\Users\david\Documents\Aerofly FS 4\aircraft\ec135\gtvr_attack_camo
```

The black install copies converted textures into this user-side EC135 repaint:

```text
C:\Users\david\Documents\Aerofly FS 4\aircraft\ec135\gtvr_attack_black
```

The desert install copies converted textures into this user-side EC135 repaint:

```text
C:\Users\david\Documents\Aerofly FS 4\aircraft\ec135\gtvr_attack_desert
```

Each EC135 repaint is created from the stock `german_army` repaint as a local user repaint. The installer does not modify the Steam EC135 folder.

The old standalone `gtvr_attack_copter` package is not installed by this workflow. If it is archived under `local-aircraft-packages\gtvr_attack_copter`, it can be restored manually by dragging that folder into:

```text
C:\Users\david\Documents\Aerofly FS 4\aircraft
```

The repaint texture converter's generated preview files are not installed because that texture-only project uses dummy geometry and produces blank aircraft menu images. The menu preview converter compiles the curated preview plates in `assets\menu-previews` into `.ttx` files, and the installer copies those compiled files into the live `preview.ttx` and `preview_small.ttx` slots. If those custom preview files are missing, the installer falls back to the previous stock/copy behavior.

To repair previews without reinstalling textures:

```powershell
python tools\install_gtvr_repaint_textures.py --repair-previews
```

## Scope

This makes the flyable EC135 visibly different without touching the compiled aircraft model. It does not solve the shell replacement problem; it is the safe interim visual layer while the geometry route is researched.

The EC135 exterior UV layout spreads texture regions across the fuselage, roof, and tail boom in ways that are not obvious from file names alone. Keep repaint art broad and repeated across all three exterior maps. The generated attack camo uses armor-panel blocks, dark red strike marks, sensor circles, fastener grids, and low-visibility `ATTACK COPTER` stencils so the aircraft reads more like a compact military scout without changing the model. The black variant removes the olive base panels and uses neutral charcoal panels instead. The desert variant uses a sand base with darker khaki armor panels.
