# GTVR Wraith Heli Frankenstein Build

`GTVR Wraith Heli` is the first non-EC135 custom military rotorcraft experiment.

It is intentionally not based on the IPACS EC135 helicopter package. The build uses:

- the generated GTVR attack-copter shell from `source-model/gtvr_attack_copter_shell.obj`,
- the open community Bleriot XI package as a readable flight/sound/control donor,
- a generated Aerofly `.tmb` whose geometry names match the donor `.tmd`,
- patched propeller physics that moves the propeller body to the roof and points thrust upward.

This is a prototype, not a polished helicopter. The expected first-test goal is:

1. Aerofly sees `GTVR Wraith Heli` as a selectable aircraft.
2. It loads the custom military helicopter shell instead of the fallback STOP model.
3. It has donor engine sound and basic controllability.
4. The upward rotor-thrust experiment can be tuned after the first in-game result.

## Build

From the project root:

```powershell
python tools\build_gtvr_frankenheli.py --prepare-source
python tools\run_aerofly_converter.py gtvr_wraith_heli tools\vendor\gtvr_frankenheli_source\aircraft --userfolder tools\vendor\gtvr_frankenheli_launch
python tools\build_gtvr_frankenheli.py --assemble-package
```

The assembled package is written to:

```text
C:\Codex\GTVR-Copter\local-aircraft-packages\gtvr_wraith_heli
```

For live testing, copy that folder to:

```text
C:\Users\david\Documents\Aerofly FS 4\aircraft\gtvr_wraith_heli
```

## Notes

- `local-aircraft-packages/` stays ignored because it contains copied third-party aircraft scaffold files and compiled Aerofly binaries.
- The tracked source of truth is the builder script plus the generated OBJ/MTL source model.
- This package is expected to need flight tuning. It is a deliberate Frankenstein path to escape the locked EC135/R22 `.tmq` helicopter core.
