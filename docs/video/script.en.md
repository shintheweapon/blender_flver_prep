# Normal Maps and Tangent Frames in Elden Ring: video script (English)

<!--
Format, read by docs/video/script.py:
- "## S01 Title" starts a scene.
- "Visual: <kind> <name>" gives the scene's first visual. Kinds: title, figure (an SVG in docs/figures/; several
  joined by " + " are stacked top to bottom), equation (a displayed equation of the paper, by number), table (a table
  of the paper, by Roman numeral),
  screenshot (an image in docs/paper/images/), references (the paper's reference list; such a scene has no segments
  and is held silent for 10 seconds at the end).
- "**S01-02**" starts a segment: one narration file. Its text runs to the next segment or scene.
- "{show: <kind> <name>}" at the start of a segment switches the visual when that segment begins.
The narration is written as it is spoken: "N cross T", "plus V", "W equals minus one".
-->

## S01 The problem

Visual: screenshot ingame_er_tangents.webp

**S01-01**
Custom meshes brought into Elden Ring can show their normal maps shaded in the wrong directions. Raised details look
dented, or look lit from the side.

**S01-02**
On the right, a plane imported the usual way: its two halves carry the same map, yet they disagree. On the left, the
same plane imported with tangents built in the game's own convention: both halves look alike.

**S01-03**
This video follows a paper that sets out that convention, how it was measured on the game's own files and in game,
what the usual import does to it, and two ways to fix it.

## S02 Normal mapping and the tangent frame

Visual: equation 1

**S02-01**
A normal map stores, for each pixel, a tangent-space normal: a direction relative to the surface, rather than to the
world. That lets one map serve a surface in any position, and lets one UV island be reused on several parts.

**S02-02**
To turn it into a shading normal, the renderer needs three vectors at each point: the surface normal N, and two
vectors in the tangent plane, the tangent T and the bitangent B, which give the directions of the image's U and V
axes on the mesh.

**S02-03**
In the common convention, T follows plus U and B follows plus V. The shading normal is then x times T, plus y times B,
plus z times N, normalised, where x, y and z are the components the map stores.

**S02-04**
These vectors are built per vertex from the mesh and its UVs, which is why a mesh carries tangents. If the frame on a
mesh follows a different convention from the one the map was made for, every tangent-space normal is read in the
wrong basis.

## S03 DirectX and OpenGL layouts

Visual: figure paper_normal_map_layout.svg

**S03-01**
Normal maps come in two common layouts. In the DirectX layout, V equals zero at the top row of the image, so plus V
runs down. In the OpenGL layout it runs up. A map converts from one to the other by inverting green.

**S03-02**
Elden Ring's maps use the DirectX layout. Red holds the x component, towards plus U, and green the y component,
towards plus V, with plus V running down the image. On a raised bump, red is high on its plus U side, and green on its
plus V side.

**S03-03**
In the FromSoftware modding community, blue has long been held to store gloss, and alpha other data. That was not
tested here. Reconstructing z from x and y, and normalising, are common real-time practice, but they are unconfirmed
for Elden Ring, because its shaders have not been examined.

## S04 Handedness

Visual: equation 2

**S04-01**
The cross product of two vectors is computed with the same formula in every coordinate system. What the formula does
not fix is which way the result points when drawn. That is the handedness of the axes.

**S04-02**
In a right-handed system the right hand gives the direction, and in a left-handed one the left hand does. Handedness
decides the drawn direction of every cross product, and which side of a triangle is its front face.

**S04-03**
{show: figure paper_axis_swap_animated.svg}
Blender's Front view shows plus X to the right, plus Z up and plus Y into the screen, so Blender's space is
right-handed with Z up.

**S04-04**
The game's model format, FLVER, does not say. One vanilla model answers it. The face part FC_F_0000 stands along plus
Y, faces minus Z and has its left side at plus X. Seen from in front, that is x to the right, y up and z into the
screen: a left-handed system. The winding of its triangles agrees, given normals that point outward.
It was not checked on more models: the modding community has long held that FromSoftware's games use a
left-handed space, and a game is unlikely to use two conventions at once. Neither reason was tested.

**S04-05**
So a Blender scene is carried into FLVER space by swapping Y and Z: a rotation of minus 90 degrees about X, which brings
Blender's up to plus Y, then Z negated, which brings the character's forward direction to minus Z. The swap is a
reflection, which carries the right-handed space into the left-handed one.

**S04-06**
{show: figure paper_axis_swap_animated.svg + paper_axis_swap.svg}
The animation steps through that swap in fixed axes. The three panels below show each stage seen from in front.

## S05 The integrability test

Visual: equation 10

**S05-01**
Which channel holds which component can be read from the maps themselves, without running the game. A map stores the
derivatives of a height field, and the mixed partial derivatives of a height field are equal.

**S05-02**
{show: equation 11}
For small slopes, that means the partial derivative of red along V must match the partial derivative of green along U.
Only the right pairing of channels with UV axes, with the right relative sign, satisfies it.

**S05-03**
Both sides were computed by central differences and compared by their Pearson correlation, over the more detailed
half of each map's pixels. The swapped pairing, red with V and green with U, was compared the same way, and the
pairing with the larger correlation wins.

**S05-04**
{show: figure paper_layout_test.svg}
The test ran on 1,437 normal maps from the game's part files; 50 of them have too little detail to test. On 1,347 of
the remaining 1,387, or 97 percent, the DirectX pairing wins with a positive correlation.

**S05-05**
{show: table I}
The correlation is moderate, not strong: its median is 0.53, against 0.24 for the swapped pairing. Of the 40 other
maps, the test picks green inverted on 32 and the swapped pairing on 8. Four of them were viewed shaded, and looked
raised when read as DirectX, so the test likely misreads those maps.

**S05-06**
The test has two limits. A map with both red and green inverted gives the same correlations, so it cannot fix the
overall sign. And it tests how the maps were authored, not how the game reads them. The in-game test settles both.

## S06 The vanilla tangent frame

Visual: equation 6

**S06-01**
Each vertex of a FLVER mesh stores a tangent T and a bitangent sign W, either plus one or minus one. On the game's own
models, T points along plus V of the stored UVs. The bitangent is not stored: it is W times N cross T.

**S06-02**
{show: equation 7}
W is chosen so that the bitangent points along plus U. The game reads green along T and red along B. So the roles are
swapped from the common convention: there, T follows plus U and B follows plus V.

**S06-03**
{show: equation 9}
Which W an island needs follows from the shape of the mesh. W is minus the sign of N dotted with the cross product of
the partial derivatives of position along plus U and plus V.

**S06-04**
{show: figure tangent_frame.svg}
A mirrored UV island reverses that cross product, and so has the opposite W. Because FLVER space is left-handed, an
island whose texture looks unmirrored in game has N cross T pointing along minus U, and needs W equals minus one.

## S07 The frame survey and cloth meshes

Visual: table II

**S07-01**
To check this on more than a few models, 1,515 part models were read with SoulsFormatsNEXT, the community
continuation of TKGP's SoulsFormats, and every triangle corner's stored frame was compared with the one its positions
and UVs imply.

**S07-02**
On all 1,515 parts, W is exactly plus or minus one, and T has unit length to within the stored precision. T is
orthogonal to N to within about two degrees on 99 percent of the corners of every part, and follows the plus V
direction.

**S07-03**
The UV orientation of a triangle is the sign of d, the determinant of its UV differences. The cross product of a
triangle's two edges equals d times the cross product of its partial derivatives. So with the game's winding, d is
positive on mirrored islands and negative on unmirrored ones.

**S07-04**
{show: table III}
Equation 9 holds on both orientations, except on one kind of mesh: those whose material name contains cloth. On those,
W is minus one on every vertex, whatever the UV orientation, so equation 9 holds on only 1.39 percent of their mirrored
corners.

**S07-05**
In the modding community, these materials are known to mark meshes moved by cloth simulation rather than by bones.
Why they keep W at minus one was not investigated, and whether the game uses W on them was not tested.

**S07-06**
{show: table IV}
An importer sees the material file a mesh uses, not its material name. By material file, meshes with cloth in it keep
W at minus one on 96.0 percent of meshes and 98.1 percent of mirrored corners. The rule has exceptions, such as one
large cloth mesh on FC_M_0105 that follows equation 9 throughout.

## S08 The in-game test

Visual: screenshot ingame_layout_test.webp

**S08-01**
The files only show how the maps were authored and how the frames are stored. The game shows how it reads them.

**S08-02**
A vanilla body part, BD_M_1730, was given a test map whose rows alternate two encodings of the same raised shapes:
DirectX, tinted warm, and DirectX with green inverted, tinted cool.

**S08-03**
With the light from above, only the DirectX rows look raised, with their bright side towards the light. The
green-inverted rows look dented.

**S08-04**
The two encodings differ only in green, so this fixes the overall sign of green read along T. Together with the
pairing from the integrability test, it confirms the layout and the frame.

## S09 Tangents along plus U

Visual: figure paper_tangent_directions.svg

**S09-01**
Tangents in the common convention point along plus U. The FBX SDK generates them that way, as measured on a test
import. The tangents an FBX file carries, such as Blender's, follow the same convention, though those were not
measured here.

**S09-02**
{show: equation 12}
With such tangents, the game reads green along plus U. Without a mirror, red is read along minus V. With Z mirrored,
red is read along plus V. The mirror turns red around because a reflection reverses every cross product, while W stays
as it was generated.

**S09-03**
{show: equation 13}
So without a mirror, a stored normal with components a and b is read as b and minus a: rotated by 90 degrees
anticlockwise on the map, from plus U towards minus V. With Z mirrored, it is read as b and a: reflected about the
line U equals V.

**S09-04**
{show: figure paper_dome_tilts.svg}
On a raised dome, the rotation makes the normals run round the dome, so it reads lit from the side. The reflection
leaves the dome raised on the U equals V diagonal, dented on the other diagonal, and lit from the side along U and V.

## S10 Both halves of the test plane

Visual: screenshot ingame_er_tangents.webp

**S10-01**
What happens on mirrored islands? A test plane with one unmirrored and one mirrored UV half was imported twice,
without a mirror and with Z mirrored, from a file without tangents, and the stored frames were read back.

**S10-02**
In both imports, the tangent points along plus U on both halves, and W is minus one on one half and plus one on the
other. W follows the island, so in each import both halves are read alike.

**S10-03**
The mirror also swaps every island between mirrored and unmirrored, while each vertex keeps its W. So the half with W
equals minus one is the unmirrored one without a mirror, and the mirrored one with Z mirrored. That is one test plane,
with generated tangents.

## S11 ER Tangents

Visual: equation 14

**S11-01**
The first fix is an import step, ER Tangents. It builds the tangents from the mesh after the importer's axis change,
in place of the file's. It is adapted from Lengyel's method, with the tangent following plus V instead of plus U.

**S11-02**
For each triangle, each edge is a combination of the partial derivatives along plus U and plus V, weighted by its UV
differences. Solving the two edges together gives both partial derivatives, divided by d.

**S11-03**
{show: equation 17}
Each vertex adds up, over the triangles around it, the plus U and plus V directions, each weighted by the triangle's
area, so larger triangles count for more.

**S11-04**
{show: equation 18}
The tangent is the accumulated plus V direction, with its component along the normal removed and normalised.

**S11-05**
{show: equation 19}
W is plus one when N cross T points the same way as the accumulated plus U direction, and minus one otherwise. So W
times N cross T always points along plus U, and either winding gives the same result.

**S11-06**
{show: figure paper_uv_triangle.svg}
A worked example. A triangle with corners at the origin, at 2 along x and at 1 along z, with UVs of zero, a half along
U and a quarter along V, and a normal of minus Y.

**S11-07**
{show: table V}
d is 0.125. The partial derivatives are 4 along x and 4 along z. T points along z, N cross T along minus x, and W is
minus one, so the bitangent points along plus x, which is plus U. This triangle winds the other way from the game's,
so d is positive here although the island is unmirrored.

## S12 Validation

Visual: screenshot ingame_er_tangents.webp

**S12-01**
ER Tangents was checked four ways. On vanilla parts, the recomputed tangents point almost the same way as the stored
ones.

**S12-02**
Imports with it follow the game's frame on both UV halves, without a mirror and with Z mirrored. Without it, the
importer writes exactly what it wrote before.

**S12-03**
And in game, the plane imported with it looks alike on both halves, while the one imported without it does not. Which
mirror setting that import used was not recorded.

**S12-04**
Blender itself computes tangents with MikkTSpace. They follow plus U and carry no W, so they follow the common
convention too. ER Tangents ignores them and builds its own.

## S13 Matching the map instead

Visual: equation 20

**S13-01**
The second fix changes the map instead of the tangents. Without a mirror, the new red is one minus the old green, and
the new green is the old red. On 8-bit channels, one minus green is 255 minus green.

**S13-02**
{show: equation 21}
With Z mirrored, red and green simply swap. Blue and alpha stay as they are.

**S13-03**
{show: figure paper_channel_changes.svg}
After the change, the dome's normals point outward again. Both changes are worked out from the measured frames, not
tested in game.

**S13-04**
{show: table VI}
Where the FBX SDK generates the tangents, they apply to mirrored islands too, since both halves are read alike. With
Blender's Tangent Space option on, W is undefined, and mirrored islands are not covered.

## S14 Ways out of Blender

Visual: figure paper_ways_out_of_blender.svg

**S14-01**
There are two ways out of Blender. Its FBX export with Tangent Space off writes no tangents. With Tangent Space on, it
writes tangents along plus U, with no W.

**S14-02**
Without ER Tangents, both routes end with tangents along plus U, since the importer generates them when the file has
none. With it, both give a model in the game's convention, apart from vertices with no usable UV area, which keep the
file's tangent.

## S15 Limitations

Visual: title Limitations

**S15-01**
The paper states its limits. Reconstructing z, normalising, and the height relation are common practice, unconfirmed
for Elden Ring. What blue and alpha hold was not tested.

**S15-02**
The handedness of FLVER space was inferred from one model, for the reasons given earlier. Cloth meshes keep W at minus one, and the cause and the
effect in game were not tested.

**S15-03**
The layout test's correlation is moderate, and four of its 40 disagreeing maps were viewed. The game version was not
recorded, the two halves were read back from one test plane, and only Elden Ring was checked.

## S16 Conclusion

Visual: title Conclusion

**S16-01**
Elden Ring reads a DirectX-layout map with green along a tangent that follows plus V, and red along W times N cross T,
which follows plus U.

**S16-02**
Tangents in the common convention follow plus U, so every tangent-space normal is rotated by 90 degrees anticlockwise
on the map, or reflected about U equals V, depending on the mirror setting.

**S16-03**
Building the tangents from the mesh in the game's convention gives the game's frame for both ways out of Blender.
Where that step is not available, swapping or inverting channels matches the map to the tangents instead.

**S16-04**
The paper, its measurements and its scripts are in the blender_flver_prep repository on GitHub, and the import step is
in a fork of FbxImporter. The paper and this video were made with Claude, by Anthropic.

## S17 References

Visual: references
