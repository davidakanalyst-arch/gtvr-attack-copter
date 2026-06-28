# Modeling Roadmap

The generated OBJ is a source concept, not the final Aerofly model. Its job is to define scale, part names, and the tactical exterior direction before the real Blender pass.

## Current Shell Parts

The OBJ exports named objects for:

- fuselage and tail boom,
- glass cockpit block,
- canopy armor rails,
- nose armor plate,
- engine doghouse,
- intake guards,
- exhaust covers,
- stub wings,
- rocket pods,
- chin sensor,
- skids and struts,
- rotor reference bars,
- flare boxes,
- belly mission pack,
- tail antenna spine.

## Why Named Parts Matter

Named parts make the next steps less painful:

- Blender can select and replace each object independently.
- Aerofly animation mapping can later target known object names.
- We can keep cockpit/glass visibility intact while replacing exterior bodywork.
- Placeholder geometry can be swapped piece-by-piece instead of rebuilt as one lump.

## Next Modeling Pass

1. Import `source-model/gtvr_attack_copter_shell.obj` into Blender.
2. Keep the cockpit/glass block as the no-go volume.
3. Replace boxy placeholders with real low-poly surfaces.
4. Keep rotor references aligned to the EC135-class dimensions.
5. Split visual stores from the fuselage so they can be hidden or replaced later.

