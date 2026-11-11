// Dumps each FLVER2 mesh as JSON: material, MTD, per-vertex position, normal, tangents (xyzw), UVs, LOD0 triangles.
using System.Globalization;
using System.Text;
using SoulsFormats;

var flver = FLVER2.Read(args[0]);
var sb = new StringBuilder();
string F(float v) => v.ToString("R", CultureInfo.InvariantCulture);
sb.Append("[");
for (int m = 0; m < flver.Meshes.Count; m++)
{
    var mesh = flver.Meshes[m];
    var mat = flver.Materials[mesh.MaterialIndex];
    if (m > 0) sb.Append(",");
    sb.Append("{\"index\":").Append(m).Append(",\"material\":\"").Append(mat.Name.Replace("\\", "\\\\").Replace("\"", "'"))
      .Append("\",\"mtd\":\"").Append(mat.MTD.Replace("\\", "\\\\")).Append("\",\"node\":\"")
      .Append(mesh.NodeIndex >= 0 && mesh.NodeIndex < flver.Nodes.Count ? flver.Nodes[mesh.NodeIndex].Name : "").Append("\",\"vertices\":[");
    for (int i = 0; i < mesh.Vertices.Count; i++)
    {
        var v = mesh.Vertices[i];
        if (i > 0) sb.Append(",");
        sb.Append("{\"p\":[").Append(F(v.Position.X)).Append(",").Append(F(v.Position.Y)).Append(",").Append(F(v.Position.Z))
          .Append("],\"n\":[").Append(F(v.Normal.X)).Append(",").Append(F(v.Normal.Y)).Append(",").Append(F(v.Normal.Z)).Append("],\"t\":[");
        sb.Append(string.Join(",", v.Tangents.Select(t => $"[{F(t.X)},{F(t.Y)},{F(t.Z)},{F(t.W)}]")));
        sb.Append("],\"uv\":[").Append(string.Join(",", v.UVs.Select(u => $"[{F(u.X)},{F(u.Y)}]"))).Append("]}");
    }
    var fs = mesh.FaceSets.FirstOrDefault(f => (f.Flags & (FLVER2.FaceSet.FSFlags.LodLevel1 | FLVER2.FaceSet.FSFlags.LodLevel2 | FLVER2.FaceSet.FSFlags.MotionBlur)) == 0);
    var tris = fs == null ? new List<int>() : fs.Triangulate(mesh.Vertices.Count < ushort.MaxValue);
    sb.Append("],\"triangles\":[").Append(string.Join(",", tris)).Append("]}");
}
sb.Append("]");
File.WriteAllText(args[1], sb.ToString());
Console.WriteLine($"meshes {flver.Meshes.Count} -> {args[1]}");
