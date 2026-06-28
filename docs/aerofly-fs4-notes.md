# Aerofly FS 4 Local Notes

Observed on this machine:

- User folder: `C:\Users\david\Documents\Aerofly FS 4`
- User aircraft folder: `C:\Users\david\Documents\Aerofly FS 4\aircraft`
- Steam install: `C:\Program Files (x86)\Steam\steamapps\common\Aerofly FS 4 Flight Simulator`
- Stock aircraft folder: `C:\Program Files (x86)\Steam\steamapps\common\Aerofly FS 4 Flight Simulator\aircraft`
- Stock EC135 folder: `C:\Program Files (x86)\Steam\steamapps\common\Aerofly FS 4 Flight Simulator\aircraft\ec135`

The EC135 folder contains readable `.tmc` and `.tmd` files plus compiled `.tmb`, `.ttx`, and `.tsb` assets. The readable files are useful as local references for:

- aircraft metadata,
- mass and speed ranges,
- tags,
- rotor startup state presets,
- livery folder layout,
- cockpit and systems naming patterns.

Important project rule: stock compiled assets should stay in the Aerofly install. This repository should contain original source files, generated source meshes, notes, scripts, and private local-install helpers only.

## EC135 Reference Values

Useful values from the stock metadata for scale/reference:

- Display name: `EC135`
- Full name: `Eurocopter EC135-T1`
- ICAO: `EC35`
- Maximum takeoff mass: `2835.0 kg`
- Operating empty mass: `1380.0 kg`
- Length: `12.19 m`
- Height: `3.62 m`
- Rotor span reference: `10.2 m`
- Engine count: `2`
- Tags include: `helicopter`, `turboshaft`, `vertical_takeoff`

These values make a good first scale box for the GTVR Attack Copter.

