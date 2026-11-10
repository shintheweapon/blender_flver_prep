# Normal maps and tangents in Elden Ring

This page records how Elden Ring reads normal maps, and what that means for meshes imported with FbxImporter. It
applies to Elden Ring; Dark Souls 3 and Sekiro were not checked.

## The layout of a normal map

Elden Ring's normal maps (the `_n` textures) use the **DirectX layout**:
- **red** points the surface towards +U;
- **green** points the surface towards +V, where V runs down the image (row 0 is the top);
- a raised detail is encoded as raised;
- **blue** holds gloss, not the normal's third component, and **alpha** holds other data.

A normal map baked in the DirectX layout is therefore in the game's layout as it is. In Blender's bake settings that
is the swizzle +X, -Y, +Z; Blender's default (+X, +Y, +Z) is the OpenGL layout, whose green must be inverted.

## The tangent frame on the game's own models

Each vertex of a FLVER mesh stores a tangent `T` with a fourth component `W`:
- `T` points along **+V** of the stored UVs, at right angles to the normal `N`;
- `W` is +1 or -1, chosen so that `W (N × T)` points along **+U**;
- on mirrored UV islands `W` has the opposite sign, so both halves read the same map the same way.

The game reads green along `T` and red along `W (N × T)`. A mesh whose tangents follow this frame shows a
DirectX-layout map as intended.

## How this was established

- **The layout:** a slope test on a vanilla normal map. For a real height field, the change of the U slope along V
  equals the change of the V slope along U; only the pairing "red with U, green with V, same sign" passes it.
- **The frame:** measured on vanilla body, face and weapon parts (for example BD_M_1730 and BD_M_2110). The stored
  tangent points along +V, and the `W` rule holds, mirrored UV islands included.
- **In game:** a vanilla body part with a test map whose rows alternate two encodings of the same raised shapes,
  DirectX and DirectX with green flipped. Only the DirectX rows look raised, with their bright side towards the light.

## What FbxImporter writes

FbxImporter writes the tangents of the FBX file, or the ones the FBX SDK generates when the file has none. These point
along **+U**, a quarter turn from the game's frame. With a DirectX-layout map:

| FbxImporter Transform | FLVER Prep option | The map reads |
|---|---|---|
| None | Mirror Z on | a quarter turn off |
| Mirror Z | Mirror Z off | with red and green swapped |

## Ways out of Blender

| Route | Tangents in the FBX file | What FbxImporter writes |
|---|---|---|
| FLVER Prep's Prepare and Export (it never adds tangents) | none | FBX SDK tangents along +U |
| Blender's FBX export, **Tangent Space** off (the default) | none | FBX SDK tangents along +U |
| Blender's FBX export, **Tangent Space** on | Blender's tangents along +U, with no `W` | those tangents; `W` is undefined, so mirrored UV halves may also be wrong (not tested) |

FbxImporter keeps tangents that the file already has and only generates missing ones.

## The fix: ER Tangents

A fork of FbxImporter, [shintheweapon/FbxImporter, branch `develop`](https://github.com/shintheweapon/FbxImporter/tree/develop),
adds an **ER Tangents** check box to the mesh import options, ticked by default. It is source only; there is no
release build.

When ticked, the importer ignores the file's tangents and builds them from the mesh after the Transform: for each
vertex it adds up the +V and +U directions of the triangles around it, weighted by area, makes the +V sum
perpendicular to the normal, and takes `W` from the +U side. This works for every Transform setting and every route
above.

It was checked in four ways:
- it reproduces the tangents stored in vanilla parts;
- imports through it follow the game's frame on normal and mirrored UV halves, under Transform None and Mirror Z;
- unticked, it writes exactly what the upstream FbxImporter writes;
- in game, a ticked and an unticked plane side by side with the test map: only the ticked one looks right on both
  halves.

## Without the fix

With the upstream FbxImporter, change the normal map instead (worked out from the frames above; not tested in game):

| FbxImporter Transform | New red | New green |
|---|---|---|
| None (FLVER Prep Mirror Z on) | 1 minus green | red |
| Mirror Z (FLVER Prep Mirror Z off) | green | red |

Blue and alpha stay as they are.
