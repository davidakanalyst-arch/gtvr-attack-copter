# Aerofly Converter Toolchain

Aerofly FS 4 is currently loading this compiled visual model:

```text
C:\Users\david\Documents\Aerofly FS 4\aircraft\gtvr_attack_copter\gtvr_attack_copter.tmb
```

That `.tmb` is still a renamed copy of the EC135 model. The custom GTVR shell will not appear in-game until a new Aerofly-compatible `.tmb` is generated.

## What To Find

We need the Aerofly aircraft/content converter executable from the SDK/toolchain. Likely executable names include:

```text
aircraft_converter.exe
aerofly_fs_2_aircraft_converter.exe
aerofly_fs_4_aircraft_converter.exe
content_converter.exe
aerofly_fs_2_content_converter.exe
aerofly_fs_4_content_converter.exe
```

Run:

```powershell
python tools\find_aerofly_converter.py
```

If it finds nothing, the machine does not currently have the converter in a normal location.

The geometry build entrypoint is:

```powershell
python tools\build_aerofly_geometry.py
```

Right now that script fails fast at the missing converter. Once the converter exists locally, this script is where the final command-line invocation should live.

## Current Status

Confirmed working:

- FS4 aircraft folder install.
- Renamed aircraft metadata.
- Startup/state files.
- Single tactical repaint option.
- EC135 cockpit and flight behavior baseline.

Blocked for visible custom geometry:

- Building a new `gtvr_attack_copter.tmb` from the source shell.

## Why This Matters

Dropping `gtvr_attack_copter_shell.obj` beside the aircraft does nothing by itself. Aerofly does not load arbitrary OBJ files from the aircraft folder at runtime; it loads its compiled model bundle.
