# Reads back what tests need from a binary FBX written by Blender, using
# Blender's own FBX parser (io_scene_fbx.parse_fbx)

from dataclasses import dataclass, field
from typing import Dict, List, Tuple

import io_scene_fbx.parse_fbx as parse_fbx


@dataclass
class FbxMesh:
    """One mesh model as stored in the file."""
    name: str
    vertices: List[Tuple[float, float, float]]
    corners: List[int]
    normals: List[Tuple[float, float, float]]
    # Bone name to the number of vertices its skin cluster weights; Blender
    # writes a cluster for every bone, also bones that weight nothing here
    bones: Dict[str, int] = field(default_factory=dict)


def _name(element) -> str:
    """The object name part of an FBX element name (``b'Body\\x00\\x01Model'``)."""
    return element.props[1].split(b'\x00\x01')[0].decode('utf-8')


def _child(element, element_id: bytes):
    """The first child element with this id, or None."""
    return next((child for child in element.elems if child.id == element_id), None)


def _triples(values) -> List[Tuple[float, float, float]]:
    """Group a flat number array into (x, y, z) tuples."""
    return [tuple(values[i:i + 3]) for i in range(0, len(values), 3)]


def _normals(geometry) -> List[Tuple[float, float, float]]:
    """Per-corner normals of a geometry, expanding IndexToDirect references."""
    layer = _child(geometry, b'LayerElementNormal')
    if layer is None:
        return []
    direct = _triples(_child(layer, b'Normals').props[0])
    mapping = _child(layer, b'MappingInformationType').props[0]
    if mapping != b'ByPolygonVertex':
        raise ValueError(f"unexpected normal mapping {mapping!r}")
    if _child(layer, b'ReferenceInformationType').props[0] == b'IndexToDirect':
        return [direct[i] for i in _child(layer, b'NormalsIndex').props[0]]
    return direct


def read_meshes(path: str) -> Dict[str, FbxMesh]:
    """
    Read every mesh model of a binary FBX file.

    Parameters
    ----------
    path : str
        File written by Blender's FBX exporter.

    Returns
    -------
    dict
        Model name to :class:`FbxMesh`: raw vertices, corner order (vertex
        index per corner, the end-of-face markers decoded), per-corner
        normals, and per bone the number of vertices its skin cluster weights.
    """
    root, _ = parse_fbx.parse(path)
    objects = _child(root, b'Objects')
    by_id = {element.props[0]: element for element in objects.elems}
    # Connections: (child id, parent id)
    links = [(c.props[1], c.props[2]) for c in _child(root, b'Connections').elems]

    def parents(child_id):
        return [by_id[p] for c, p in links if c == child_id and p in by_id]

    def children(parent_id):
        return [by_id[c] for c, p in links if p == parent_id and c in by_id]

    meshes = {}
    for geometry in objects.elems:
        if geometry.id != b'Geometry' or geometry.props[2] != b'Mesh':
            continue
        model = next(p for p in parents(geometry.props[0]) if p.id == b'Model')
        corners = [i if i >= 0 else -i - 1 for i in _child(geometry, b'PolygonVertexIndex').props[0]]
        mesh = FbxMesh(_name(model), _triples(_child(geometry, b'Vertices').props[0]),
                       corners, _normals(geometry))
        for skin in children(geometry.props[0]):
            if skin.id != b'Deformer' or skin.props[2] != b'Skin':
                continue
            for cluster in children(skin.props[0]):
                indexes = _child(cluster, b'Indexes')
                weighted = len(indexes.props[0]) if indexes is not None else 0
                for bone in children(cluster.props[0]):
                    if bone.id == b'Model':
                        mesh.bones[_name(bone)] = weighted
        meshes[mesh.name] = mesh
    return meshes
