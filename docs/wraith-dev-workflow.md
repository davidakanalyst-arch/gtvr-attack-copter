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
- adds the generated cockpit kit: raised textured upholstered front seats, animated floor-mounted matte-black cyclics, left-side collectives, forward rounded pedals, a forward dashboard without lower shelf/brace tubes, and left/middle/right glass-style panels;
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

The current dev-only correction is `--pilot-alignment-x-delta 0.40`, which shifts the visual shell and rotors forward around the fixed EC135 pilot. Tune this number conservatively if the pilot still needs side-window alignment; keep the pilot object on `pilot_jason`.

## Generated Cockpit Kit

The dev wrapper adds a generated cockpit kit directly into the compiled dev `.tmb`. It includes two raised textured upholstered front seats, animated floor-mounted matte-black cyclics, left-side collective/throttle levers, forward rounded pedal bars, a forward framed dashboard, and left/middle/right glass-style panels. The current side panels are accepted runtime display receivers: left and right screens populate `DisplayPFDL`/`DisplayPFDR` with independent inset PFD-only atlas windows that place live speed, altitude, attitude and heading-tape data inside the Wraith side screen bezels while excluding the duplicate side strips and allowing lower ND/compass remnants to overflow downward. The centre panel populates `DisplayNDL` with a separate `gtvr_cockpit_map` texture; the generated dev text TMD is packaged alongside the EC135 `.tmq` and hosts an AN2/DR400-style `texture_animation_map_display` renderer for that texture so the centre can behave as a borderless floating moving-map surface without changing the accepted side PFD crops. The dev package also forces the PFD/ND display state inputs on by default and reduces inherited visible stick/collective/pedal click handles in `controls.tmd`, leaving the generated Wraith controls as the visible cockpit controls. Cyclics, collectives and pedals are separate animated geometry groups; cyclics use cyclic pitch/roll only, while collectives use collective travel only.

There is intentionally no dash hood/shelf over the panel. The current dashboard/panel group uses `--dash-forward-x-delta 0.55` to hold the dash toward the front of the cockpit without touching the pilot, seats, cyclics, collectives, pedals, or shell/pilot alignment. The seat/control cluster uses `--interior-forward-x-delta 0.32` so those parts sit closer to the side-window/pilot area while the dash stays anchored forward.

Disable it only for diagnostics:

```powershell
python tools\build_gtvr_wraith_dev.py --full --force-install --no-cockpit-kit
```

Use `--interior-forward-x-delta` for seat, cyclic, collective, pedal and floor fore/aft fit tuning. Use `--dash-forward-x-delta` for dashboard-only tuning. Use `--cockpit-x-delta` only when the whole generated cockpit kit needs a small fore/aft correction; none of these options changes the shell/pilot alignment.

## Promotion Rule

Treat `GTVR Wraith Dev` as the workbench. Promote changes to `GTVR Wraith` only after an explicit stable-update request, and then preserve the stable flight model, sounds, landing behavior, and contact spheres unless the requested change specifically says otherwise.

When stable promotion is explicitly authorized, use:

```powershell
python tools\promote_wraith_dev_to_stable.py --force-local --install --force-install
```

That command copies the current `gtvr_wraith_dev` package to `gtvr_wraith_ec135_core`, renames the aircraft files, restores stable identity strings (`GTWE`, `GTVR Wraith`), validates the proven contact spheres and `pilot_jason`, then installs only to the stable Aerofly FS4 aircraft folder.
