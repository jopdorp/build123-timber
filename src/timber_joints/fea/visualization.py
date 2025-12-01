"""FEA visualization utilities for OCP CAD Viewer."""

from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import numpy as np

from OCP.BRepBuilderAPI import BRepBuilderAPI_MakePolygon, BRepBuilderAPI_MakeFace
from OCP.gp import gp_Pnt
from OCP.BRep import BRep_Builder
from OCP.TopoDS import TopoDS_Compound

from build123d import Compound

from .backends.calculix import read_frd_nodes, read_frd_displacements


# C3D4 tetrahedron face definitions (0-indexed into node list)
C3D4_FACE_INDICES = [(0, 1, 2), (0, 1, 3), (1, 2, 3), (0, 2, 3)]


def read_mesh_elements(mesh_file: str) -> List[List[int]]:
    """Read tetrahedral element connectivity from CalculiX mesh file.
    
    Args:
        mesh_file: Path to mesh.inp file
        
    Returns:
        List of [n1, n2, n3, n4] node lists for each C3D4 element
    """
    elements = []
    in_elements = False
    
    with open(mesh_file, 'r') as f:
        for line in f:
            if '*ELEMENT' in line.upper() and 'C3D4' in line.upper():
                in_elements = True
                continue
            if in_elements:
                if line.startswith('*'):
                    in_elements = False
                    continue
                parts = line.strip().split(',')
                if len(parts) >= 5:
                    try:
                        nodes = [int(parts[i].strip()) for i in range(1, 5)]
                        elements.append(nodes)
                    except ValueError:
                        pass
    return elements


def get_outer_faces(elements: List[List[int]]) -> List[Tuple[int, int, int]]:
    """Extract boundary triangular faces from tetrahedral mesh.
    
    Boundary faces appear exactly once (not shared between elements).
    
    Args:
        elements: List of [n1, n2, n3, n4] element connectivity
        
    Returns:
        List of (n1, n2, n3) node tuples for boundary faces
    """
    face_count = {}
    
    for elem in elements:
        for i, j, k in C3D4_FACE_INDICES:
            face_key = tuple(sorted([elem[i], elem[j], elem[k]]))
            face_count[face_key] = face_count.get(face_key, 0) + 1
    
    return [f for f, count in face_count.items() if count == 1]


def build_triangle_compound(
    triangles: List[Tuple[int, int, int]],
    nodes: Dict[int, Tuple[float, float, float]],
) -> Compound:
    """Build a build123d Compound from triangular faces.
    
    Args:
        triangles: List of (n1, n2, n3) node ID tuples
        nodes: Dict mapping node_id to (x, y, z) coordinates
        
    Returns:
        build123d Compound of triangular faces
    """
    builder = BRep_Builder()
    compound = TopoDS_Compound()
    builder.MakeCompound(compound)
    
    for n1, n2, n3 in triangles:
        if n1 not in nodes or n2 not in nodes or n3 not in nodes:
            continue
        
        p1, p2, p3 = gp_Pnt(*nodes[n1]), gp_Pnt(*nodes[n2]), gp_Pnt(*nodes[n3])
        
        try:
            polygon = BRepBuilderAPI_MakePolygon(p1, p2, p3, True)
            if polygon.IsDone():
                face_maker = BRepBuilderAPI_MakeFace(polygon.Wire(), True)
                if face_maker.IsDone():
                    builder.Add(compound, face_maker.Face())
        except Exception:
            pass
    
    return Compound(compound)


def apply_displacements(
    nodes: Dict[int, Tuple[float, float, float]],
    displacements: Dict[int, Tuple[float, float, float]],
    scale: float = 1.0,
) -> Dict[int, Tuple[float, float, float]]:
    """Apply scaled displacements to node coordinates.
    
    Args:
        nodes: Original node coordinates
        displacements: Node displacements (ux, uy, uz)
        scale: Displacement scale factor for visualization
        
    Returns:
        New dict with deformed coordinates
    """
    deformed = {}
    for nid, (x, y, z) in nodes.items():
        if nid in displacements:
            ux, uy, uz = displacements[nid]
            deformed[nid] = (x + ux * scale, y + uy * scale, z + uz * scale)
        else:
            deformed[nid] = (x, y, z)
    return deformed


def build_deformed_mesh(
    mesh_file: str,
    frd_file: str,
    scale: float = 10.0,
) -> Tuple[Compound, Dict]:
    """Build deformed mesh visualization from FEA results.
    
    Args:
        mesh_file: Path to mesh.inp file
        frd_file: Path to .frd results file
        scale: Displacement magnification factor
        
    Returns:
        Tuple of (deformed_compound, info_dict)
        info_dict contains: nodes, displacements, max_disp, elements
    """
    nodes = read_frd_nodes(frd_file)
    displacements = read_frd_displacements(frd_file)
    elements = read_mesh_elements(mesh_file)
    
    if not nodes or not displacements or not elements:
        raise ValueError("Missing mesh or results data")
    
    # Calculate max displacement
    max_disp = 0.0
    for ux, uy, uz in displacements.values():
        mag = np.sqrt(ux**2 + uy**2 + uz**2)
        if mag > max_disp:
            max_disp = mag
    
    # Build deformed coordinates
    deformed_nodes = apply_displacements(nodes, displacements, scale)
    
    # Get boundary faces and build compound
    outer_faces = get_outer_faces(elements)
    deformed_compound = build_triangle_compound(outer_faces, deformed_nodes)
    
    info = {
        "nodes": nodes,
        "displacements": displacements,
        "max_displacement": max_disp,
        "num_elements": len(elements),
        "num_surface_faces": len(outer_faces),
        "scale_factor": scale,
    }
    
    return deformed_compound, info


def show_fea_results(
    mesh_file: str,
    frd_file: str,
    scale: float = 10.0,
    original_shapes: Optional[List[Tuple[Any, str, str]]] = None,
    deformed_color: str = "red",
    original_alpha: float = 0.3,
):
    """Visualize FEA results in OCP CAD Viewer.
    
    Args:
        mesh_file: Path to mesh.inp file
        frd_file: Path to .frd results file  
        scale: Displacement magnification factor
        original_shapes: List of (shape, name, color) tuples to show
        deformed_color: Color for deformed mesh
        original_alpha: Transparency for original shapes
    """
    from ocp_vscode import show_object, reset_show
    
    deformed, info = build_deformed_mesh(mesh_file, frd_file, scale)
    
    print(f"\nFEA Visualization:")
    print(f"  Elements: {info['num_elements']}")
    print(f"  Surface faces: {info['num_surface_faces']}")
    print(f"  Max displacement: {info['max_displacement']:.4f} mm")
    print(f"  Scale factor: {scale}x")
    print(f"  Scaled max: {info['max_displacement'] * scale:.2f} mm")
    
    reset_show()
    
    # Show original geometry
    if original_shapes:
        for shape, name, color in original_shapes:
            show_object(shape, name=name, options={"color": color, "alpha": original_alpha})
    
    # Show deformed mesh
    show_object(deformed, name=f"Deformed ({scale}x)", options={"color": deformed_color})
    
    return info
