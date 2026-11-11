# Normal Maps and Tangent Frames in Elden Ring: Measurement, Analysis and Matching Tangents on Import

**shintheweapon and Claude (Anthropic, Claude Opus 5.5)**

*AI disclosure: see the Acknowledgment.*

**Abstract:** Custom meshes brought into Elden Ring can show their normal maps shaded in the wrong directions. This paper
sets out the convention the game uses and how it was measured: a DirectX-layout map, read with green along the stored
tangent, which points along +V, and red along the bitangent $W(\vec{N}\times\vec{T})$, which points along +U. A slope
test on a vanilla map fixes the layout; vanilla models fix the frame; an in-game test confirms both. Tangents in the
common convention, which the FBX format and the FBX SDK follow, point along +U. Depending on the importer's mirror
setting, the game then turns every authored tilt a quarter turn or reflects it across the diagonal $U = V$. The paper
derives both effects, describes an import option, ER Tangents, that builds the tangents in the game's convention from
the mesh and its UVs, and derives channel changes that match the map to the tangents instead. Every formula is stated
in words as well.

**Index Terms:** normal mapping, tangent space, handedness, Elden Ring, FLVER, FBX import.

## Notation

- $\vec{a}$: a vector, an arrow with a direction and a length. $\hat{a}$: a unit vector, an arrow of length 1.
- $\vec{a}\cdot\vec{b}$: the dot product, a number that is positive when the arrows point the same way and zero when
  they are at right angles.
- $\vec{a}\times\vec{b}$: the cross product, an arrow at right angles to both (Section II-C).
- A number written next to a vector multiplies it: $W\vec{a}$ is $\vec{a}$ scaled by $W$, reversed when $W = -1$.
- $\propto$: proportional to, that is, equal up to a positive factor.
- $\lVert\vec{a}\rVert$: the length of $\vec{a}$.
- $\partial h/\partial u$: the slope of $h$ along +U, with $v$ held fixed; $\partial h/\partial v$ likewise along +V.

## I. Introduction

A normal map stores, for each pixel, a small tilt of the surface. The game turns that tilt into a shading direction
using a frame of three arrows stored on every vertex. When the frame on a mesh follows a different convention from the
one the map was made for, every tilt is read in the wrong direction: raised details look dented, or lit from the side.

Meshes made in Blender reach Elden Ring through an importer that converts FBX files to the game's model format, FLVER
[7]. The importer keeps the tangents of the FBX file, or generates them with the FBX SDK [8], in the common convention.
The game's own models use a different one, so the two disagree. This paper:

- measures the convention of the game's own models (Sections III and IV);
- derives what tangents in the common convention do to it (Section V);
- describes an import option, ER Tangents, that builds tangents in the game's convention (Section VI);
- derives how to match the map to the tangents instead (Section VII).

## II. Background

### A. Normal Mapping and the TBN Frame

Blinn introduced shading with a perturbed normal [1]. A real-time normal map stores the perturbed normal in tangent
space: relative to the surface at that point rather than to the world. One map then serves a surface in any position,
and the same UV island can be reused on several parts. To shade, the renderer needs, at each point, the surface normal
$\vec{N}$ and two arrows in the surface, the tangent $\vec{T}$ and the bitangent $\vec{B}$, which say where the image's
U and V directions lie on the mesh. The three form the TBN frame $[\vec{T}\ \vec{B}\ \vec{N}]$. They are built per vertex
from the mesh and its UVs, which is why a mesh carries tangents. In the common convention, $\vec{T}$ follows +U and
$\vec{B}$ follows +V, and the shading normal is

$$
\vec{n} \propto x\,\vec{T} + y\,\vec{B} + z\,\vec{N} \tag{1}
$$

*In words:* the stored tilt has three parts, x, y and z. The shading normal is x steps along the tangent, plus y steps
along the bitangent, plus z steps along the surface normal, scaled to length 1.

### B. DirectX and OpenGL Layouts

The two common layouts differ in how the green channel is read. In the DirectX layout the first row of the image is at
the top, so +V runs down the image; in the OpenGL layout it is at the bottom, so +V runs up. A map converts from one
layout to the other by inverting green [5].

### C. Handedness

The cross product of two arrows is computed with one formula in every coordinate system:

$$
\vec{a}\times\vec{b} = (a_y b_z - a_z b_y,\ a_z b_x - a_x b_z,\ a_x b_y - a_y b_x) \tag{2}
$$

*In words:* each part of the result combines the other two parts of the inputs. The result is at right angles to both
arrows, and its length is the area of the parallelogram they span.

The formula fixes the numbers; the handedness of the axes fixes which way the result is drawn. In a right-handed set,
the right hand gives the direction: thumb along $\vec{a}$, index finger along $\vec{b}$, and the middle finger, bent at
right angles to both, along $\vec{a}\times\vec{b}$. In a left-handed set, the left hand does. Handedness decides two
things that matter here:

- the drawn direction of every cross product;
- which side of a triangle is its front, through the order of its corners (the winding).

A mirror, a scale of $-1$ along one axis, swaps both. An FBX file declares its axis system, which may be right-handed or
left-handed: the FBX SDK's presets for Maya, 3ds Max, MotionBuilder and OpenGL are right-handed, and those for DirectX
and Lightwave are left-handed [8]. The SDK describes its 3ds Max preset as x to the right, z up and y into the screen.
Blender's Front view shows the same: +X to the right, +Z up and +Y into the screen, read from the view's rotation in
Blender 4.5. So Blender's 3D space is right-handed with Z up.

## III. Elden Ring's Convention

### A. Layout

Elden Ring's normal maps use the DirectX layout (Fig. 1). Red holds the tilt towards +U and green the tilt towards +V,
with +V running down the image. Blue holds gloss and alpha other data, so neither is part of the normal. With the red
and green values $R$ and $G$ between 0 and 1:

$$
x = 2R - 1, \qquad y = 2G - 1 \tag{3}
$$

*In words:* a channel value of one half means no tilt; values above it tilt the surface towards +U (red) or +V (green),
values below it the other way.

$$
z = \sqrt{1 - x^2 - y^2} \tag{4}
$$

*In words:* the third part is not stored. It is rebuilt so that the tilt has length 1.

Rebuilding $z$ this way is common real-time graphics practice. It is unconfirmed for Elden Ring, because the game's
shaders have not been examined (decompiled) and no in-game test isolates it. For a surface with height $h(u, v)$, the
usual relation between the height and the stored tilt is

$$
x = \frac{-\,\partial h/\partial u}{\sqrt{1 + (\partial h/\partial u)^2 + (\partial h/\partial v)^2}}, \qquad
y = \frac{-\,\partial h/\partial v}{\sqrt{1 + (\partial h/\partial u)^2 + (\partial h/\partial v)^2}} \tag{5}
$$

*In words:* where the surface falls away towards +U, red is high, and where it falls away towards +V, green is high. The
square root scales the tilt to length 1. So on a raised bump, red is high on its +U side and green on its +V side.

![A texture with U running right and V running down from row 0 at the top; red stores the tilt towards +U, green the tilt towards +V](../figures/normal_map_layout.svg)

*Fig. 1. The layout of a normal map. On a raised bump, red is high on its +U side and green on its +V side.*

### B. The Vanilla Tangent Frame

Each vertex of a FLVER mesh stores a tangent $\vec{T}$ and a sign $W$, either $+1$ or $-1$. On the game's own (vanilla)
models, $\vec{T}$ points along +V of the stored UVs, at right angles to $\vec{N}$. The bitangent is not stored; it is

$$
\vec{B} = W\,(\vec{N}\times\vec{T}) \tag{6}
$$

*In words:* the bitangent is the cross product of the normal and the tangent, reversed when W is −1. W is chosen so that
the bitangent points along +U.

The game reads green along $\vec{T}$ and red along $\vec{B}$, the other way round from (1):

$$
\vec{n} = \frac{x\,\vec{B} + y\,\vec{T} + z\,\vec{N}}{\lVert x\,\vec{B} + y\,\vec{T} + z\,\vec{N}\rVert} \tag{7}
$$

*In words:* the shading normal is x steps along the bitangent (+U), plus y steps along the tangent (+V), plus z steps
along the normal, divided by its own length. Scaling to length 1 is common practice, unconfirmed for Elden Ring for the
reason given in Section III-A.

The value of $W$ an island needs follows from the shape of the mesh. Write $\vec{p}(u, v)$ for the point of the surface
at UV position $(u, v)$, $\vec{a} = \partial\vec{p}/\partial u$ for the surface's direction of +U, and
$\vec{b} = \partial\vec{p}/\partial v$ for its direction of +V. The normal is
$\vec{N} = s\,(\vec{a}\times\vec{b})/\lVert\vec{a}\times\vec{b}\rVert$ with $s = \pm 1$, and
$\vec{T} = \vec{b}/\lVert\vec{b}\rVert$. The identity

$$
(\vec{a}\times\vec{b})\times\vec{b} = (\vec{a}\cdot\vec{b})\,\vec{b} - (\vec{b}\cdot\vec{b})\,\vec{a} \tag{8}
$$

*In words:* crossing $\vec{a}\times\vec{b}$ with $\vec{b}$ again gives an arrow in the surface that points against
$\vec{a}$, apart from a part along $\vec{b}$.

gives $\vec{N}\times\vec{T} \propto -s\,\vec{a}$, apart from a part along $\vec{T}$. For $W(\vec{N}\times\vec{T})$ to
point along +U, $W$ must be $-s$:

$$
W = -\operatorname{sign}\!\left(\vec{N}\cdot\left(\frac{\partial\vec{p}}{\partial u}\times\frac{\partial\vec{p}}{\partial v}\right)\right) \tag{9}
$$

*In words:* W is −1 when the normal points the same way as the cross product of the surface's +U and +V directions,
and +1 when it points the opposite way. A mirrored UV island reverses that cross product, and so has the opposite W.

![Two UV islands lying flat with N up and T along +V towards the viewer; on the unmirrored island W = -1 turns N × T onto +U, on the mirrored island W = +1](../figures/tangent_frame.svg)

*Fig. 2. The tangent frame on an unmirrored and a mirrored island, seen in perspective. The dashed arrow is
$\vec{N}\times\vec{T}$ before $W$ is applied.*

### C. The Handedness of FLVER Space

FLVER files state no handedness. It was found on one vanilla model, the face part FC_F_0000:

- **Anatomy:** the character stands along +Y, faces −Z, and has its left side at +X. Seen from in front, x points to
  the right, y up and z into the screen. In the FBX SDK's terms that is a left-handed set, the same as its DirectX
  preset [8].
- **Winding:** computed with (2), $(\vec{p}_1-\vec{p}_0)\times(\vec{p}_2-\vec{p}_0)$ points against the stored normal on
  almost all LOD0 triangles. Front faces therefore run clockwise under right-handed maths, which is anticlockwise as
  seen in a left-handed space.

The test has limits: one model, LOD0 only, and handedness inferred from anatomy and winding. What follows from it is
that, as seen in game, $\vec{N}\times\vec{T}$ follows the left-hand rule. On an island whose texture looks unmirrored in
game, $\vec{N}\times\vec{T}$ points along −U, and (6) needs $W = -1$. A Blender scene is carried into this space by
swapping its Y and Z axes: a −90° turn about X, which brings Blender's up (+Z) to +Y and its front (−Y) to +Z, then Z
reversed, which brings the front to −Z. The swap is a mirror, which changes handedness, so the character stays the right
way round, with its left side at +X.

## IV. Measurements

### A. The Slope Test

For any smooth height field, the order of two slopes does not matter:

$$
\frac{\partial}{\partial v}\!\left(\frac{\partial h}{\partial u}\right) = \frac{\partial}{\partial u}\!\left(\frac{\partial h}{\partial v}\right) \tag{10}
$$

*In words:* how the U slope changes as you move along V equals how the V slope changes as you move along U.

For small tilts, (3) and (5) give $x \approx -\partial h/\partial u$ and $y \approx -\partial h/\partial v$, so a map in
the assumed layout must satisfy

$$
\frac{\partial R}{\partial v} \approx \frac{\partial G}{\partial u} \tag{11}
$$

*In words:* the change of red down the image matches the change of green across it.

The two sides were correlated over the more detailed half of the pixels of a vanilla normal map, and tile by tile. Only
the pairing "red with U, green with V, same sign", with V running down, gives a strong positive correlation. That
pairing is the DirectX layout.

### B. Vanilla Frames

On vanilla body and weapon parts, the stored tangent points along +V, and (9) holds on almost all triangles of each part
checked, mirrored islands included. On the weapon checked, whose UVs are mostly unmirrored, most vertices carry
$W = -1$.

### C. The In-Game Test

A vanilla body part was given a test map whose rows alternate two encodings of the same raised shapes: DirectX, and
DirectX with green inverted. In game, only the DirectX rows look raised, with their bright side towards the light. This
confirms the layout and the frame together.

### D. Import Measurements

A test plane with one unmirrored and one mirrored UV half was imported twice, once without a mirror and once with Z
mirrored. Without a mirror, the tangent points along +U, $W = -1$ on the unmirrored half, and red is read along −V.
With Z mirrored, red is read along +V.

## V. Tangents in the Common Convention

The tangents an FBX file carries, and those the FBX SDK generates for a file without them [8], point along +U, as
measured in Section IV-D. The importer keeps them as they are. With the frames measured there, the arrows the game uses
become

$$
\vec{T}' = \hat{u}, \qquad
\vec{B}' = W'\,(\vec{N}\times\hat{u}) = \begin{cases} -\hat{v} & \text{without a mirror} \\ +\hat{v} & \text{with Z mirrored} \end{cases} \tag{12}
$$

*In words:* $\hat{u}$ and $\hat{v}$ are the unit arrows along +U and +V on the surface. With tangents along +U, green is
read along +U, and red along −V (without a mirror) or +V (with Z mirrored).

An authored tilt $(a, b)$, $a$ towards +U and $b$ towards +V, is meant as the direction $a\,\hat{u} + b\,\hat{v}$. By (7)
the game reads it as $a\,\vec{B}' + b\,\vec{T}'$, which in $(U, V)$ parts is

$$
\begin{pmatrix} b \\ -a \end{pmatrix} = \begin{pmatrix} 0 & 1 \\ -1 & 0 \end{pmatrix}\begin{pmatrix} a \\ b \end{pmatrix} \ \text{(without a mirror)}, \qquad
\begin{pmatrix} b \\ a \end{pmatrix} = \begin{pmatrix} 0 & 1 \\ 1 & 0 \end{pmatrix}\begin{pmatrix} a \\ b \end{pmatrix} \ \text{(with Z mirrored)} \tag{13}
$$

*In words:* without a mirror every tilt is turned a quarter turn; with Z mirrored every tilt is reflected across the
diagonal U = V. A raised dome then reads lit from the side, or raised on one diagonal and dented on the other (Fig. 4).

![Three sheets with N up: vanilla tangents read green along +V and red along +U; tangents along +U read green along +U, with red along -V (without a mirror) or +V (with Z mirrored)](../figures/paper_tangent_directions.svg)

*Fig. 3. The directions in which the game reads green and red, for vanilla tangents and for tangents along +U.*

![Animated: the frame and the decoded tilts around a raised dome; vanilla tilts point outward, without a mirror every tilt turns a quarter, with Z mirrored every tilt flips across the U = V diagonal](../figures/paper_dome_tilts.svg)

*Fig. 4. Animated: the decoded tilts around a raised dome under each setting.*

## VI. ER Tangents

ER Tangents is an import option [6] that builds tangents in the game's convention. When it is ticked, the importer
builds the tangents from the mesh after the importer's axis change, in place of the file's. It is adapted from
Lengyel's method [2], which computes per-triangle tangents, averages them per vertex, makes them perpendicular to the
normal (Gram-Schmidt) and stores the handedness as ±1. Here the tangent follows +V instead of +U, and each triangle adds
unit directions weighted by its size. The steps run as follows.

**Per triangle.** Triangles with a repeated corner are skipped. For corners $\vec{p}_0, \vec{p}_1, \vec{p}_2$ with UVs
$(u_i, v_i)$, the edges are $\vec{e}_1 = \vec{p}_1 - \vec{p}_0$ and $\vec{e}_2 = \vec{p}_2 - \vec{p}_0$, with UV steps
$\Delta u_1 = u_1 - u_0$, $\Delta v_1 = v_1 - v_0$, and likewise $\Delta u_2$, $\Delta v_2$. Across a flat triangle,
position changes evenly with UV:

$$
\vec{e}_1 = \Delta u_1\,\frac{\partial\vec{p}}{\partial u} + \Delta v_1\,\frac{\partial\vec{p}}{\partial v}, \qquad
\vec{e}_2 = \Delta u_2\,\frac{\partial\vec{p}}{\partial u} + \Delta v_2\,\frac{\partial\vec{p}}{\partial v} \tag{14}
$$

*In words:* each edge is made of so many steps along the surface's +U direction plus so many along its +V direction.

$$
d = \Delta u_1\,\Delta v_2 - \Delta u_2\,\Delta v_1 \tag{15}
$$

*In words:* d is the signed area spanned by the two UV steps, doubled. When d is zero, or nearly, the triangle has no UV
area and is skipped.

$$
\frac{\partial\vec{p}}{\partial u} = \frac{\Delta v_2\,\vec{e}_1 - \Delta v_1\,\vec{e}_2}{d}, \qquad
\frac{\partial\vec{p}}{\partial v} = \frac{\Delta u_1\,\vec{e}_2 - \Delta u_2\,\vec{e}_1}{d} \tag{16}
$$

*In words:* solving (14) for the two directions gives the arrows along which U and V increase on this triangle.

**Per vertex.** Each triangle adds both directions, scaled to length 1 and then by $\lVert\vec{e}_1\times\vec{e}_2\rVert$
(twice its area), to each of its three corners:

$$
\vec{s}_u = \sum \lVert\vec{e}_1\times\vec{e}_2\rVert\,\frac{\partial\vec{p}/\partial u}{\lVert\partial\vec{p}/\partial u\rVert}, \qquad
\vec{s}_v = \sum \lVert\vec{e}_1\times\vec{e}_2\rVert\,\frac{\partial\vec{p}/\partial v}{\lVert\partial\vec{p}/\partial v\rVert} \tag{17}
$$

*In words:* each vertex collects a vote for +U and a vote for +V from every triangle around it; larger triangles count
for more.

$$
\vec{T} = \frac{\vec{s}_v - \vec{N}\,(\vec{N}\cdot\vec{s}_v)}{\lVert\vec{s}_v - \vec{N}\,(\vec{N}\cdot\vec{s}_v)\rVert} \tag{18}
$$

*In words:* the +V vote, with its part along the normal removed (Gram-Schmidt) and scaled to length 1, is the tangent.

$$
W = \begin{cases} +1 & \text{if } (\vec{N}\times\vec{T})\cdot\vec{s}_u \ge 0 \\ -1 & \text{otherwise} \end{cases} \tag{19}
$$

*In words:* W is +1 when $\vec{N}\times\vec{T}$ already points along the +U vote, and −1 when it points against it, so
that $W(\vec{N}\times\vec{T})$ always points along +U.

**Fallback.** A vertex with no usable normal, no +V vote, or a +V vote almost along its normal keeps the tangent the
file or the FBX SDK gave it, with W set to +1 or −1 from its sign.

**Winding.** Swapping corners 1 and 2 swaps the edges and the UV steps, which reverses the sign of $d$ and of both
numerators in (16). The directions and $\lVert\vec{e}_1\times\vec{e}_2\rVert$ stay the same, so the result is the same
for either winding.

**Worked example.** One triangle: $\vec{p}_0 = (0, 0, 0)$, $\vec{p}_1 = (2, 0, 0)$, $\vec{p}_2 = (0, 0, 1)$; UVs
$(0, 0)$, $(0.5, 0)$, $(0, 0.25)$; normal $\vec{N} = (0, -1, 0)$ at every corner.

| Quantity | Value |
|---|---|
| $\vec{e}_1$, $\vec{e}_2$ | $(2, 0, 0)$, $(0, 0, 1)$ |
| $d$ by (15) | $0.125$ |
| $\partial\vec{p}/\partial u$ by (16) | $(4, 0, 0)$ |
| $\partial\vec{p}/\partial v$ by (16) | $(0, 0, 4)$ |
| $\vec{T}$ by (18) | $(0, 0, 1)$ |
| $\vec{N}\times\vec{T}$ by (2) | $(-1, 0, 0)$ |
| $W$ by (19), and by (9) | $-1$ |
| $\vec{B}$ by (6) | $(1, 0, 0)$, along +U |

**Validation.** ER Tangents was checked in four ways [6]:

- on vanilla parts, the rebuilt tangents point almost the same way as the stored ones;
- imports through it follow the game's frame on both UV halves, without a mirror and with Z mirrored;
- unticked, the importer writes exactly what the upstream release writes;
- in game, a ticked and an unticked plane side by side with the test map: only the ticked one looks right on both
  halves.

It starts ticked for Elden Ring FLVERs only, and is offered upstream as a pull request [6].

**Relation to MikkTSpace.** MikkTSpace [3], [4] is the tangent method Blender uses: its `Mesh.calc_tangents` runs it
[4], and Blender's FBX exporter calls `calc_tangents` when Tangent Space is on. These tangents follow +U and the
exporter writes no W, so they follow the common convention, like the FBX SDK's. ER Tangents builds its own tangents
from the mesh, so every route out of Blender gives the same result.

## VII. Matching the Map Instead of the Tangents

Without ER Tangents, the map can be changed so that (13) reads it as authored. Without a mirror a stored tilt
$(a', b')$ is read as $(b', -a')$, so storing $a' = -b$, $b' = a$ gives back $(a, b)$. With (3):

$$
R' = 1 - G, \qquad G' = R \tag{20}
$$

*In words:* without a mirror, the new red is one minus the old green, and the new green is the old red.

$$
R' = G, \qquad G' = R \tag{21}
$$

*In words:* with Z mirrored, red and green swap.

Blue and alpha stay as they are. Both changes are worked out from the measured frames, not tested in game. They assume
that every island is unmirrored, or that mirrored islands read the same way.

| Import | New red | New green |
|---|---|---|
| Without a mirror | 1 − green | red |
| With Z mirrored | green | red |

## VIII. Practical Use

There are two ways out of Blender (Fig. 5): its FBX export with Tangent Space off, which writes no tangents, and with
Tangent Space on, which writes tangents along +U with no W. Without ER Tangents, both give tangents along +U, since the
importer generates them when the file has none. With it, both give a FLVER in the game's convention. With Tangent Space
on and without ER Tangents, W is undefined, so mirrored UV halves may also read wrong; this has not been tested.

![Two routes into the importer: Blender's FBX export with Tangent Space off, with no tangents, and with Tangent Space on, with +U tangents and no W; with ER Tangents ticked, both give a FLVER in the game's frame](../figures/paper_ways_out_of_blender.svg)

*Fig. 5. The ways out of Blender, and the tangents each one gives.*

## IX. Limitations

- Rebuilding z (4), scaling to length 1 (7) and the height relation (5) are common real-time graphics practice. They are
  unconfirmed for Elden Ring, because its shaders have not been examined and no in-game test isolates them.
- The handedness of FLVER space was inferred from one model, LOD0 only.
- Only Elden Ring was checked; Dark Souls 3, Sekiro, Armored Core 6 and Nightreign were not.

## X. Conclusion

Elden Ring reads a DirectX-layout map with green along a tangent that follows +V, and red along $W(\vec{N}\times\vec{T})$,
which follows +U. Tangents in the common convention follow +U, so every tilt is turned a quarter turn or reflected across
the diagonal, depending on the mirror setting. Building the tangents from the mesh and its UVs in the game's convention
gives the intended shading for every route out of Blender. Where that option is not available, swapping or inverting
channels matches the map to the tangents instead.

## Acknowledgment

This paper was written with Claude Opus 5.5 by Anthropic. Claude drafted the text and equations and generated the
figures. Claude wrote the code and the analysis: the measurement scripts, ER Tangents, the figure generator and its
tests. shintheweapon carried out the in-game tests and the test imports, and made the visual judgements.

## References

[1] J. F. Blinn, "Simulation of wrinkled surfaces," *ACM SIGGRAPH Comput. Graph.*, vol. 12, no. 3, pp. 286-292,
Aug. 1978, doi: 10.1145/965139.507101.

[2] E. Lengyel, "Computing tangent space basis vectors for an arbitrary mesh," Terathon Software, Mar. 15, 2004.
[Online]. Available: https://terathon.com/code/tangent.php. Accessed: Nov. 11, 2026.

[3] M. Mikkelsen, "Simulation of wrinkled surfaces revisited," M.S. thesis, Dept. Comput. Sci. (DIKU), Univ.
Copenhagen, Copenhagen, Denmark, Mar. 2008. [Online]. Available:
http://image.diku.dk/projects/media/morten.mikkelsen.08.pdf. Accessed: Nov. 11, 2026.

[4] M. S. Mikkelsen, "MikkTSpace," GitHub repository, 2011. [Online]. Available: https://github.com/mmikk/MikkTSpace.
Blender's port: `intern/mikktspace` and `source/blender/blenkernel/intern/mesh_tangent.cc`, Blender 4.5, [Online].
Available: https://github.com/blender/blender. Accessed: Nov. 11, 2026.

[5] Adobe, "What is the difference between the OpenGL and DirectX normal format?," Substance 3D Bakers documentation,
May 1, 2026. [Online]. Available:
https://experienceleague.adobe.com/en/docs/substance-3d/bakers/common-questions/what-is-the-difference-between-the-opengl-and-directx-normal-format.
Accessed: Nov. 11, 2026.

[6] shintheweapon, "FbxImporter," fork, branch develop; and "Add an ER Tangents import option," pull request #10.
[Online]. Available: https://github.com/shintheweapon/FbxImporter/tree/develop and
https://github.com/The12thAvenger/FbxImporter/pull/10. Accessed: Nov. 11, 2026.

[7] soulsmods, "SoulsFormatsNEXT," GitHub repository. [Online]. Available: https://github.com/soulsmods/SoulsFormatsNEXT.
Accessed: Nov. 11, 2026.

[8] Autodesk, *FBX SDK 2020.2.1*, header files `fbxsdk/scene/fbxaxissystem.h` (`FbxAxisSystem`) and
`fbxsdk/scene/geometry/fbxmesh.h` (`FbxMesh::GenerateTangentsDataForAllUVSets`). [Online]. Available:
https://help.autodesk.com/view/FBX/2020/ENU/. Accessed: Nov. 11, 2026.
