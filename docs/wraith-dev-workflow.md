# GTVR Wraith Dev Workflow

The stable aircraft is the known-good build:

```text
C:\Users\david\Documents\Aerofly FS 4\aircraft\gtvr_wraith_ec135_core
```

In-game display name: `GTVR Wraith`

The iteration aircraft is:

```text
C:\Users\david\Documents\Aerofly FS 4\aircraft\gtvr_wraith_dev
```

In-game display name: `GTVR Wraith Dev`

Do not edit, rebuild, or reinstall the stable aircraft unless that is the explicit task. Iterate through `tools\build_gtvr_wraith_dev.py`, which retargets the proven EC135-core Wraith pipeline to dev-only names and paths.

## Current Inspection

Checked on 2026-07-05:

- `gtvr_wraith_ec135_core` and `gtvr_wraith_dev` are both installed in the Aerofly FS4 user aircraft folder.
- `gtvr_wraith_heli` is not installed in the Aerofly FS4 user aircraft folder.
- `gtvr_wraith_dev.tmc` uses `DisplayName` and `DisplayNameFull` of `GTVR Wraith Dev`.
- `gtvr_wraith_dev.tmc` uses ICAO `GTWD`.
- `gtvr_wraith_dev.tmc` uses stock pilot `pilot_jason`; switching the EC135-core dev package to `pilot_robert` caused the Aerofly STOP fallback and must not be repeated on this path.
- The installed dev `.tmb` intentionally differs from stable once dev-only geometry experiments, such as the matte black inner shell, are installed.
- Both stable and dev use the proven contact spheres:

```text
( 1.896 1.128 -1.667 0.05)
( 1.896 -1.128 -1.667 0.05)
(-0.876 1.128 -1.668 0.05)
(-0.876 -1.128 -1.668 0.05)
```

## One-Command Dev Iteration

Use this when changing geometry or any source that affects the compiled `.tmb`:

```powershell
python tools\build_gtvr_wraith_dev.py --full --force-install
```

That command:

- prepares Aerofly converter source under `tools\vendor\gtvr_wraith_dev_source\aircraft\gtvr_wraith_dev`;
- shifts the dev visual shell forward around the fixed working EC135 pilot so the pilot sits closer to the side-window area;
- duplicates solid shell faces inward with a matte black material so opaque exterior panels are visible from the cockpit side;
- runs the full Aerofly converter for model `gtvr_wraith_dev`;
- assembles `local-aircraft-packages\gtvr_wraith_dev`;
- installs only to `C:\Users\david\Documents\Aerofly FS 4\aircraft\gtvr_wraith_dev`.

The script refuses to install over `gtvr_wraith_ec135_core`.

## Manual Dev Steps

If you need to inspect converter output between steps:

```powershell
python tools\build_gtvr_wraith_dev.py --prepare-source
python tools\build_gtvr_wraith_dev.py --convert
python tools\build_gtvr_wraith_dev.py --assemble-package --install --force-install
```

The assemble step checks that the converted dev `.tmb` is newer than the prepared dev source stamp. This prevents accidentally repackaging stale converter output after a geometry change.

Only pass `--allow-stale-tmb` for a deliberate metadata/package-only reinstall where the compiled geometry is intentionally unchanged.

## Cockpit-Side Shell Opacity

`tools\build_gtvr_wraith_dev.py` defaults to adding reversed, inward-facing copies of shell triangles before conversion. Those inward faces use the generated `gtvr_inner_matte_black` material, keeping the internal shell matte black while leaving only glass/window/transparent-style materials out of the inward copy pass.

Disable this only for diagnostics:

```powershell
python tools\build_gtvr_wraith_dev.py --full --force-install --no-inner-shell
```

## Pilot Position

Keep the EC135-core dev package on `Pilot[pilot_jason]`. A test that switched `gtvr_wraith_dev.tmc` to `Pilot[pilot_robert]`, copied from the retired plane-flight-model Wraith path, made Aerofly load the STOP fallback. Fix pilot seating relative to the Wraith shell through a safer dev-only shell/pilot alignment path, not by changing the pilot object reference.

The current dev-only correction is `--pilot-alignment-x-delta 0.55`, which shifts the visual shell and rotors forward around the fixed EC135 pilot. Tune this number conservatively if the pilot still needs side-window alignment; keep the pilot object on `pilot_jason`.

## Promotion Rule

Treat `GTVR Wraith Dev` as the workbench. Promote changes to `GTVR Wraith` only after an explicit stable-update request, and then preserve the stable flight model, sounds, landing behavior, and contact spheres unless the requested change specifically says otherwise.
