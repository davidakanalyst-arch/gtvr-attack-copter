# GTVR Wraith Heli Frankenstein Build

`GTVR Wraith Heli` is the first non-EC135 custom military rotorcraft experiment.

It is intentionally not based on the IPACS EC135 helicopter package.

The current v2 build is stable-first. It uses:

- the generated GTVR attack-copter shell from `source-model/gtvr_attack_copter_shell.obj`,
- the open community Edgley Optica package as a readable slow-flight, runway, sound, gear, and control donor,
- a generated Aerofly `.tmb` whose geometry names match the donor `.tmd`,
- patched propeller graphics that move the visible rotor to the roof while retaining the donor's stable forward prop physics.

The archived v1 Bleriot build proved that a non-EC135 custom package could be selected and loaded from an in-air continuation, but it was not useful: fresh runway starts could black-screen and the vertical-thrust hack was not meaningfully controllable.

This is a prototype, not a polished helicopter. The expected first-test goal is:

1. Aerofly sees `GTVR Wraith Heli` as a selectable aircraft.
2. It loads the custom military helicopter shell instead of the fallback STOP model.
3. It starts from the runway without a black screen.
4. It has donor engine sound and basic Optica-like controllability.
5. It can then be tuned toward more rotorcraft-like behavior without sacrificing fresh-spawn stability.

## Build

From the project root:

```powershell
python tools\build_gtvr_wraith_optica.py --prepare-source
python tools\run_aerofly_converter.py gtvr_wraith_heli tools\vendor\gtvr_wraith_optica_source\aircraft --userfolder tools\vendor\gtvr_wraith_optica_launch
python tools\build_gtvr_wraith_optica.py --assemble-package
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
- `tools/build_gtvr_frankenheli.py` remains as a record of the failed Bleriot vertical-thrust experiment.
- This package is expected to need flight tuning. It is a deliberate Frankenstein path to escape the locked EC135/R22 `.tmq` helicopter core.
