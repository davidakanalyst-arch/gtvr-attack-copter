# Local Livery Library

`C:\Codex\GTVR-Copter\Liveries` is the local drag-and-drop library for user aircraft repaints.

The folders inside it are intentionally ignored by Git because they contain converted Aerofly `.ttx` files and may include stock repaint scaffolding copied from the local simulator install. Do not commit or redistribute those compiled aircraft assets.

## Folder Layout

Each aircraft gets its own folder:

```text
Liveries/
  ec135/
  f15e/
  mb339/
```

Each repaint folder is copied directly into the matching Aerofly aircraft folder when testing:

```text
C:\Users\david\Documents\Aerofly FS 4\aircraft\f15e\
C:\Users\david\Documents\Aerofly FS 4\aircraft\mb339\
```

## Current Generated Sets

F-15E:

- `gtvr_strike_black` - `GTVR Strike Black`
- `gtvr_strike_camo` - `GTVR Strike Camo`
- `gtvr_strike_desert` - `GTVR Strike Desert`

MB-339:

- `gtvr_assault_black` - `GTVR Assault Black`
- `gtvr_assault_camo` - `GTVR Assault Camo`
- `gtvr_assault_desert` - `GTVR Assault Desert`

## Rebuild Workflow

Build source PNGs:

```powershell
python tools\build_gtvr_aircraft_liveries.py build-source
```

Run the Aerofly converter:

```powershell
python tools\run_aerofly_converter.py gtvr_aircraft_liveries tools\vendor\gtvr_aircraft_liveries_source\aircraft --userfolder tools\vendor\gtvr_aircraft_liveries_launch --timeout 180
```

Assemble the drag-and-drop livery folders:

```powershell
python tools\build_gtvr_aircraft_liveries.py assemble
```
