# Manual Install Notes

The installer script does this automatically, but the manual process is useful to understand.

## Basic Aircraft Copy

Copy the stock EC135 folder:

```text
C:\Program Files (x86)\Steam\steamapps\common\Aerofly FS 4 Flight Simulator\aircraft\ec135
```

Into:

```text
C:\Users\david\Documents\Aerofly FS 4\aircraft
```

Rename the copied folder:

```text
ec135 -> gtvr_attack_copter
```

## Rename Main Files

Inside `gtvr_attack_copter`, rename:

```text
ec135.tmc                  -> gtvr_attack_copter.tmc
ec135.tmb                  -> gtvr_attack_copter.tmb
ec135.tmq                  -> gtvr_attack_copter.tmq
ec135_clean.tmd            -> gtvr_attack_copter_clean.tmd
ec135_cold.tmd             -> gtvr_attack_copter_cold.tmd
ec135_landing.tmd          -> gtvr_attack_copter_landing.tmd
ec135_start.tmd            -> gtvr_attack_copter_start.tmd
ec135_takeoff.tmd          -> gtvr_attack_copter_takeoff.tmd
```

## Edit Metadata

Open:

```text
C:\Users\david\Documents\Aerofly FS 4\aircraft\gtvr_attack_copter\gtvr_attack_copter.tmc
```

Change:

```text
<[stringt8c][ICAO][EC35]>
<[string8][DisplayName][EC135]>
<[string8][DisplayNameFull][Eurocopter EC135-T1]>
```

To:

```text
<[stringt8c][ICAO][GTAC]>
<[string8][DisplayName][GTVR Attack Copter]>
<[string8][DisplayNameFull][GTVR Attack Copter Prototype]>
```

## Reduce Stock Livery Clutter

The EC135 livery choices come from repaint folders. To give the GTVR prototype an immediate tactical baseline, first copy all files except `option.tmc` from:

```text
german_army
```

Into the root of:

```text
gtvr_attack_copter
```

That overwrites the base exterior texture files with the local military repaint files. Then remove these copied folders from the local prototype:

```text
adac
drf
german_army
highskids
police
sheriff
```

Keep:

```text
lowskids
```

The base `option.tmc` currently depends on `lowskids`, so removing that folder can stop the selected option from working correctly.
