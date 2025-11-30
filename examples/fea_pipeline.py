"""
FEA Pipeline: Timber Joinery Analysis

Pipeline:
    build123d (parametric geometry)
        → pythonOCC (tessellation)
        → gmsh (FEA mesh generation)
        → CalculiX (FEA solver)
        → pythonOCC (results visualization)
        → ifcopenshell (BIM/IFC export)

Installation:
    pip install gmsh ifcopenshell
    
    # CalculiX solver (Ubuntu/Debian):
    sudo apt-get install calculix-ccx

Architecture:
    [ PARAMETRIC GEOMETRY ]
                     build123d
                     (timber_joints library)
                          |
        ------------------------------------------------
        |                      |                      |
  [FEA pipeline]        [BIM pipeline]        [Robotics pipeline]
      gmsh                ifcopenshell           COMPAS_fab
    CalculiX               IFC export            (future)
  python post              
 ocp visualization                              

This file: FEA Pipeline
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple, List
import subprocess
import os

import numpy as np

# --- Core build123d imports ---
from build123d import Part, Box, Align, Location, Axis

# --- Our timber library ---
from timber_joints.beam import Beam
from timber_joints.tenon import Tenon


# =============================================================================
# TIMBER MATERIAL PROPERTIES
# =============================================================================

@dataclass
class TimberMaterial:
    """Orthotropic timber material properties.
    
    Wood is anisotropic - different properties in different directions:
    - L: Longitudinal (along grain)
    - R: Radial (across growth rings)  
    - T: Tangential (tangent to growth rings)
    
    Default values are for European Softwood C24 (EN 338).
    """
    name: str = "C24_Softwood"
    
    # Elastic moduli [MPa]
    E_L: float = 11000.0    # Longitudinal (along grain) - highest
    E_R: float = 370.0      # Radial
    E_T: float = 370.0      # Tangential
    
    # Shear moduli [MPa]
    G_LR: float = 690.0     # Longitudinal-Radial
    G_LT: float = 690.0     # Longitudinal-Tangential
    G_RT: float = 50.0      # Radial-Tangential
    
    # Poisson's ratios
    nu_LR: float = 0.37
    nu_LT: float = 0.42
    nu_RT: float = 0.47
    
    # Density [kg/m³]
    density: float = 350.0
    
    # Strength values [MPa] (characteristic values, EN 338)
    f_m_k: float = 24.0     # Bending strength
    f_t_0_k: float = 14.0   # Tension parallel to grain
    f_t_90_k: float = 0.4   # Tension perpendicular to grain
    f_c_0_k: float = 21.0   # Compression parallel to grain
    f_c_90_k: float = 2.5   # Compression perpendicular to grain
    f_v_k: float = 4.0      # Shear strength


# =============================================================================
# BUILD123D → STEP EXPORT (for gmsh)
# =============================================================================

def export_to_step(shape: Part, filename: str):
    """Export build123d shape to STEP file for gmsh import."""
    from OCC.Core.STEPControl import STEPControl_Writer, STEPControl_AsIs
    from OCC.Core.Interface import Interface_Static
    
    writer = STEPControl_Writer()
    Interface_Static.SetCVal("write.step.schema", "AP214")
    writer.Transfer(shape.wrapped, STEPControl_AsIs)
    status = writer.Write(filename)
    
    if status == 1:  # IFSelect_RetDone
        print(f"STEP file written: {filename}")
    else:
        raise RuntimeError(f"Failed to write STEP file: {filename}")


# =============================================================================
# GMSH MESH GENERATION
# =============================================================================

def mesh_step_with_gmsh(
    step_file: str,
    output_dir: str,
    mesh_size: float = 10.0,
    element_order: int = 1,
) -> Tuple[str, List[int], List[int]]:
    """Generate FEA mesh from STEP file using gmsh.
    
    Args:
        step_file: Input STEP file path
        output_dir: Output directory for mesh files
        mesh_size: Target element size [mm]
        element_order: 1 for linear, 2 for quadratic elements
        
    Returns:
        Tuple of (inp_file_path, fixed_node_ids, load_node_ids)
    """
    try:
        import gmsh
    except ImportError:
        raise ImportError("gmsh not installed. Run: pip install gmsh")
    
    gmsh.initialize()
    gmsh.option.setNumber("General.Terminal", 0)  # Suppress output
    gmsh.model.add("timber_beam")
    
    # Import STEP geometry
    gmsh.model.occ.importShapes(step_file)
    gmsh.model.occ.synchronize()
    
    # Set mesh size
    gmsh.option.setNumber("Mesh.CharacteristicLengthMin", mesh_size * 0.5)
    gmsh.option.setNumber("Mesh.CharacteristicLengthMax", mesh_size)
    gmsh.option.setNumber("Mesh.ElementOrder", element_order)
    
    # Generate 3D mesh
    gmsh.model.mesh.generate(3)
    
    # Get nodes and find boundary nodes
    node_tags, node_coords, _ = gmsh.model.mesh.getNodes()
    
    # Find bounding box to identify fixed and load surfaces
    x_coords = node_coords[0::3]
    x_min, x_max = min(x_coords), max(x_coords)
    tol = mesh_size * 0.1
    
    fixed_nodes = []
    load_nodes = []
    
    for i, tag in enumerate(node_tags):
        x = node_coords[3 * i]
        if abs(x - x_min) < tol:
            fixed_nodes.append(int(tag))
        elif abs(x - x_max) < tol:
            load_nodes.append(int(tag))
    
    # Export mesh to CalculiX format
    inp_file = os.path.join(output_dir, "mesh.inp")
    gmsh.write(inp_file)
    
    # Get statistics
    elem_types, elem_tags, _ = gmsh.model.mesh.getElements()
    print(f"Mesh generated: {len(node_tags)} nodes")
    for et, tags in zip(elem_types, elem_tags):
        elem_name = gmsh.model.mesh.getElementProperties(et)[0]
        print(f"  {len(tags)} {elem_name} elements")
    print(f"Fixed nodes (x={x_min:.1f}): {len(fixed_nodes)}")
    print(f"Load nodes (x={x_max:.1f}): {len(load_nodes)}")
    
    gmsh.finalize()
    
    return inp_file, fixed_nodes, load_nodes


def create_beam_mesh(
    beam: Beam,
    output_dir: str,
    mesh_size: float = 10.0,
) -> Tuple[str, List[int], List[int]]:
    """Create FEA mesh for a beam directly using gmsh geometry.
    
    Faster than STEP export for simple shapes.
    Uses named physical groups for CalculiX element sets.
    
    Args:
        beam: Timber beam object
        output_dir: Output directory
        mesh_size: Target element size [mm]
        
    Returns:
        Tuple of (inp_file_path, fixed_node_ids, load_node_ids)
    """
    try:
        import gmsh
    except ImportError:
        raise ImportError("gmsh not installed. Run: pip install gmsh")
    
    os.makedirs(output_dir, exist_ok=True)
    
    gmsh.initialize()
    gmsh.option.setNumber("General.Terminal", 0)
    gmsh.model.add("timber_beam")
    
    # Create box geometry: length along X, width along Y, height along Z
    box = gmsh.model.occ.addBox(0, 0, 0, beam.length, beam.width, beam.height)
    gmsh.model.occ.synchronize()
    
    # Get all volume entities
    volumes = gmsh.model.getEntities(dim=3)
    
    # Create physical group for the timber volume with our name
    # This is the ONLY physical group - no surfaces, which avoids 2D elements
    timber_tag = gmsh.model.addPhysicalGroup(3, [v[1] for v in volumes])
    gmsh.model.setPhysicalName(3, timber_tag, "TIMBER")
    
    # Set mesh size
    gmsh.option.setNumber("Mesh.CharacteristicLengthMax", mesh_size)
    
    # Only save elements belonging to physical groups (3D only)
    gmsh.option.setNumber("Mesh.SaveAll", 0)
    
    # Generate 3D mesh
    gmsh.model.mesh.generate(3)
    
    # Get nodes
    node_tags, node_coords, _ = gmsh.model.mesh.getNodes()
    
    # Find boundary nodes by position
    tol = 1e-3
    fixed_nodes = []
    load_nodes = []
    
    for i, tag in enumerate(node_tags):
        x = node_coords[3 * i]
        if abs(x) < tol:
            fixed_nodes.append(int(tag))
        elif abs(x - beam.length) < tol:
            load_nodes.append(int(tag))
    
    # Export mesh - only 3D elements due to SaveAll=0
    inp_file = os.path.join(output_dir, "mesh.inp")
    gmsh.write(inp_file)
    
    print(f"Mesh: {len(node_tags)} nodes, fixed={len(fixed_nodes)}, load={len(load_nodes)}")
    
    gmsh.finalize()
    
    return inp_file, fixed_nodes, load_nodes


# =============================================================================
# CALCULIX INPUT FILE GENERATION
# =============================================================================

def write_calculix_input(
    mesh_file: str,
    output_file: str,
    material: TimberMaterial,
    fixed_nodes: List[int],
    load_nodes: List[int],
    load_magnitude: float = 1000.0,  # N, total load
):
    """Write complete CalculiX input file for static analysis.
    
    Args:
        mesh_file: Mesh file from gmsh (.inp)
        output_file: Output CalculiX input file
        material: Timber material properties
        fixed_nodes: Node IDs to fix
        load_nodes: Node IDs to apply load
        load_magnitude: Total load in N (distributed among load nodes)
    """
    # Load per node
    load_per_node = load_magnitude / len(load_nodes) if load_nodes else 0
    
    ccx_lines = [
        "** CalculiX Cantilever Beam Analysis",
        "** Timber material with orthotropic properties",
        "**",
        "",
        "** Include mesh from gmsh",
        f"*INCLUDE, INPUT={os.path.basename(mesh_file)}",
        "",
        f"** Material Definition: {material.name}",
        f"*MATERIAL, NAME={material.name}",
        "*ELASTIC, TYPE=ENGINEERING CONSTANTS",
        # E1, E2, E3, nu12, nu13, nu23, G12, G13
        f"{material.E_L}, {material.E_R}, {material.E_T}, "
        f"{material.nu_LR}, {material.nu_LT}, {material.nu_RT}, "
        f"{material.G_LR}, {material.G_LT},",
        # G23, Temperature
        f"{material.G_RT}, 0.0",
        "*DENSITY",
        f"{material.density * 1e-9:.6e}",  # kg/m³ → tonne/mm³
        "",
        "** Assign material to timber elements",
        f"*SOLID SECTION, ELSET=TIMBER, MATERIAL={material.name}",
        "",
        "** Boundary Conditions - Fixed end (all DOFs)",
        "*BOUNDARY",
    ]
    
    # Add fixed boundary conditions
    for node in fixed_nodes:
        ccx_lines.append(f"{node}, 1, 3, 0.0")
    
    ccx_lines.extend([
        "",
        "** Static Analysis Step",
        "*STEP",
        "*STATIC",
        "",
        "** Point loads at free end (distributed)",
        "*CLOAD",
    ])
    
    # Distribute load among load nodes (downward in Z)
    for node in load_nodes:
        ccx_lines.append(f"{node}, 3, {-load_per_node:.6f}")
    
    ccx_lines.extend([
        "",
        "** Output requests",
        "*NODE FILE",
        "U",  # Displacements
        "*EL FILE",
        "S",  # Stresses
        "",
        "*END STEP",
    ])
    
    with open(output_file, 'w') as f:
        f.write('\n'.join(ccx_lines))
    
    print(f"CalculiX input file: {output_file}")
    return output_file


# =============================================================================
# CALCULIX SOLVER
# =============================================================================

def run_calculix(input_file: str, ccx_path: str = "ccx") -> Tuple[bool, str]:
    """Run CalculiX solver.
    
    Args:
        input_file: Path to .inp file
        ccx_path: Path to CalculiX executable
        
    Returns:
        Tuple of (success, message)
    """
    input_path = Path(input_file)
    work_dir = input_path.parent
    job_name = input_path.stem
    
    cmd = [ccx_path, "-i", job_name]
    
    print(f"Running: {' '.join(cmd)} (in {work_dir})")
    
    try:
        result = subprocess.run(
            cmd,
            cwd=work_dir,
            capture_output=True,
            text=True,
            timeout=300,
        )
        
        if result.returncode == 0:
            frd_file = work_dir / f"{job_name}.frd"
            print(f"Analysis complete! Results: {frd_file}")
            return True, str(frd_file)
        else:
            print(f"CalculiX failed: {result.stderr}")
            return False, result.stderr
            
    except FileNotFoundError:
        msg = f"CalculiX not found. Install: sudo apt-get install calculix-ccx"
        print(msg)
        return False, msg
    except subprocess.TimeoutExpired:
        return False, "Analysis timed out"


# =============================================================================
# RESULTS POST-PROCESSING
# =============================================================================

def read_frd_displacements(frd_file: str) -> dict:
    """Read displacement results from CalculiX .frd file.
    
    FRD uses fixed-width format:
    - Column 1-3: record key (e.g., " -1")
    - Column 4-13: node number (10 chars)
    - Column 14-25: value 1 (12 chars)
    - Column 26-37: value 2 (12 chars)
    - Column 38-49: value 3 (12 chars)
    
    Args:
        frd_file: Path to .frd results file
        
    Returns:
        Dict of {node_id: (ux, uy, uz)}
    """
    displacements = {}
    
    with open(frd_file, 'r') as f:
        lines = f.readlines()
    
    in_disp_block = False
    for line in lines:
        # Start of displacement block
        if ' -4  DISP' in line:
            in_disp_block = True
            continue
        
        if in_disp_block:
            # End of block marker
            if line.startswith(' -3'):
                break
            
            # Skip header lines
            if line.startswith(' -4') or line.startswith(' -5'):
                continue
                
            # Data lines start with " -1"
            if line.startswith(' -1'):
                try:
                    # Fixed width parsing
                    node_id = int(line[3:13])
                    ux = float(line[13:25])
                    uy = float(line[25:37])
                    uz = float(line[37:49])
                    displacements[node_id] = (ux, uy, uz)
                except (ValueError, IndexError):
                    pass
    
    return displacements


def analyze_results(frd_file: str) -> dict:
    """Analyze FEA results and return summary statistics.
    
    Args:
        frd_file: Path to .frd results file
        
    Returns:
        Dict with max displacements and their locations
    """
    displacements = read_frd_displacements(frd_file)
    
    if not displacements:
        return {"error": "No displacement data found"}
    
    # Find max displacements
    max_ux = max(displacements.values(), key=lambda d: abs(d[0]))
    max_uy = max(displacements.values(), key=lambda d: abs(d[1]))
    max_uz = max(displacements.values(), key=lambda d: abs(d[2]))
    max_total = max(displacements.values(), 
                    key=lambda d: np.sqrt(d[0]**2 + d[1]**2 + d[2]**2))
    
    return {
        "n_nodes": len(displacements),
        "max_ux": max_ux[0],
        "max_uy": max_uy[1],
        "max_uz": max_uz[2],
        "max_total": np.sqrt(max_total[0]**2 + max_total[1]**2 + max_total[2]**2),
        "displacements": displacements,  # Include raw data for visualization
    }


def read_frd_nodes(frd_file: str) -> dict:
    """Read node coordinates from CalculiX .frd file.
    
    Args:
        frd_file: Path to .frd results file
        
    Returns:
        Dict of {node_id: (x, y, z)}
    """
    nodes = {}
    
    with open(frd_file, 'r') as f:
        lines = f.readlines()
    
    in_node_block = False
    for line in lines:
        # Node block starts with "    2C" line
        if line.startswith('    2C'):
            in_node_block = True
            continue
        
        if in_node_block:
            # End of node block
            if line.startswith(' -3'):
                break
            
            # Data lines start with " -1"
            if line.startswith(' -1'):
                try:
                    node_id = int(line[3:13])
                    x = float(line[13:25])
                    y = float(line[25:37])
                    z = float(line[37:49])
                    nodes[node_id] = (x, y, z)
                except (ValueError, IndexError):
                    pass
    
    return nodes


def visualize_fea_results(
    frd_file: str,
    scale_factor: float = 50.0,
    show_undeformed: bool = True,
):
    """Visualize FEA results with deformed shape and displacement contours.
    
    Uses matplotlib for a standalone visualization of the deformed mesh.
    
    Args:
        frd_file: Path to .frd results file
        scale_factor: Displacement magnification for visibility
        show_undeformed: Show original shape as wireframe
    """
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d import Axes3D
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    
    # Read data
    nodes = read_frd_nodes(frd_file)
    displacements = read_frd_displacements(frd_file)
    
    if not nodes or not displacements:
        print("No data to visualize")
        return
    
    # Calculate total displacement magnitude for coloring
    disp_mag = {}
    for node_id, (ux, uy, uz) in displacements.items():
        disp_mag[node_id] = np.sqrt(ux**2 + uy**2 + uz**2)
    
    max_disp = max(disp_mag.values()) if disp_mag else 1.0
    
    # Prepare coordinates
    orig_x, orig_y, orig_z = [], [], []
    def_x, def_y, def_z = [], [], []
    colors = []
    
    for node_id in sorted(nodes.keys()):
        if node_id not in displacements:
            continue
            
        x, y, z = nodes[node_id]
        ux, uy, uz = displacements[node_id]
        
        orig_x.append(x)
        orig_y.append(y)
        orig_z.append(z)
        
        # Apply scaled displacement
        def_x.append(x + ux * scale_factor)
        def_y.append(y + uy * scale_factor)
        def_z.append(z + uz * scale_factor)
        
        # Color based on displacement magnitude
        colors.append(disp_mag[node_id] / max_disp if max_disp > 0 else 0)
    
    # Create figure
    fig = plt.figure(figsize=(14, 6))
    
    # 3D view
    ax1 = fig.add_subplot(121, projection='3d')
    
    if show_undeformed:
        ax1.scatter(orig_x, orig_y, orig_z, c='gray', alpha=0.3, s=5, label='Original')
    
    scatter = ax1.scatter(def_x, def_y, def_z, c=colors, cmap='jet', s=10, label='Deformed')
    
    ax1.set_xlabel('X [mm]')
    ax1.set_ylabel('Y [mm]')
    ax1.set_zlabel('Z [mm]')
    ax1.set_title(f'Deformed Shape (scale: {scale_factor}x)')
    ax1.legend()
    
    # Add colorbar
    cbar = plt.colorbar(scatter, ax=ax1, shrink=0.5, pad=0.1)
    cbar.set_label('Displacement [mm]')
    # Set colorbar ticks to actual displacement values
    cbar.set_ticks([0, 0.5, 1.0])
    cbar.set_ticklabels([f'{0:.3f}', f'{max_disp/2:.3f}', f'{max_disp:.3f}'])
    
    # Side view (X-Z plane) for cantilever deflection
    ax2 = fig.add_subplot(122)
    
    if show_undeformed:
        ax2.scatter(orig_x, orig_z, c='gray', alpha=0.3, s=5, label='Original')
    
    scatter2 = ax2.scatter(def_x, def_z, c=colors, cmap='jet', s=10, label='Deformed')
    
    ax2.set_xlabel('X [mm] (Length)')
    ax2.set_ylabel('Z [mm] (Height)')
    ax2.set_title(f'Side View - Cantilever Deflection (scale: {scale_factor}x)')
    ax2.legend()
    ax2.set_aspect('equal', adjustable='box')
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    # Save figure
    output_dir = Path(frd_file).parent
    fig_path = output_dir / "fea_results.png"
    plt.savefig(fig_path, dpi=150, bbox_inches='tight')
    print(f"Results visualization saved: {fig_path}")
    
    plt.show()
    
    return fig


def read_mesh_elements(mesh_file: str) -> List[List[int]]:
    """Read tetrahedral elements from gmsh mesh file.
    
    Args:
        mesh_file: Path to mesh.inp file
        
    Returns:
        List of element node connectivity [n1, n2, n3, n4]
    """
    elements = []
    in_element_block = False
    
    with open(mesh_file, 'r') as f:
        for line in f:
            # C3D4 = 4-node tetrahedron
            if '*ELEMENT' in line.upper() and 'C3D4' in line.upper():
                in_element_block = True
                continue
            
            if in_element_block:
                # New keyword ends block
                if line.startswith('*'):
                    in_element_block = False
                    continue
                
                # Parse element: elem_id, n1, n2, n3, n4
                parts = line.strip().split(',')
                if len(parts) >= 5:
                    try:
                        nodes = [int(parts[i].strip()) for i in range(1, 5)]
                        elements.append(nodes)
                    except ValueError:
                        pass
    
    return elements


def visualize_fea_results_ocp(
    frd_file: str,
    mesh_file: str,
    scale_factor: float = 50.0,
    original_beam: Optional[Beam] = None,
):
    """Visualize FEA results in OCP CAD Viewer with deformed mesh.
    
    Creates a tessellated shell of the deformed outer surface.
    
    Args:
        frd_file: Path to .frd results file
        mesh_file: Path to mesh.inp file
        scale_factor: Displacement magnification for visibility
        original_beam: Optional original beam to show for comparison
    """
    try:
        from ocp_vscode import show, show_object
        from OCP.BRepBuilderAPI import BRepBuilderAPI_MakePolygon, BRepBuilderAPI_MakeFace
        from OCP.gp import gp_Pnt
        from OCP.BRep import BRep_Builder
        from OCP.TopoDS import TopoDS_Compound
    except ImportError as e:
        print(f"OCP visualization not available: {e}")
        return
    
    # Read data
    nodes = read_frd_nodes(frd_file)
    displacements = read_frd_displacements(frd_file)
    elements = read_mesh_elements(mesh_file)
    
    if not nodes or not displacements or not elements:
        print("Missing data for OCP visualization")
        return
    
    # Calculate displacement magnitudes for color mapping
    disp_mag = {}
    for node_id, (ux, uy, uz) in displacements.items():
        disp_mag[node_id] = np.sqrt(ux**2 + uy**2 + uz**2)
    
    max_disp = max(disp_mag.values()) if disp_mag else 1.0
    
    # Build deformed coordinates
    deformed_nodes = {}
    for node_id, (x, y, z) in nodes.items():
        if node_id in displacements:
            ux, uy, uz = displacements[node_id]
            deformed_nodes[node_id] = (
                x + ux * scale_factor,
                y + uy * scale_factor,
                z + uz * scale_factor,
            )
        else:
            deformed_nodes[node_id] = (x, y, z)
    
    # Extract outer triangular faces from tetrahedra
    # Each tet has 4 triangular faces
    face_count = {}
    for elem in elements:
        n1, n2, n3, n4 = elem
        # 4 faces of tetrahedron (sorted node tuples for uniqueness)
        faces = [
            tuple(sorted([n1, n2, n3])),
            tuple(sorted([n1, n2, n4])),
            tuple(sorted([n1, n3, n4])),
            tuple(sorted([n2, n3, n4])),
        ]
        for f in faces:
            face_count[f] = face_count.get(f, 0) + 1
    
    # Outer faces appear only once (not shared between elements)
    outer_faces = [f for f, count in face_count.items() if count == 1]
    print(f"Mesh: {len(elements)} tets, {len(outer_faces)} surface triangles")
    
    # Create compound of triangular faces
    builder = BRep_Builder()
    compound = TopoDS_Compound()
    builder.MakeCompound(compound)
    
    # Create faces
    faces_created = 0
    for face_nodes in outer_faces:
        n1, n2, n3 = face_nodes
        
        if n1 not in deformed_nodes or n2 not in deformed_nodes or n3 not in deformed_nodes:
            continue
        
        p1 = gp_Pnt(*deformed_nodes[n1])
        p2 = gp_Pnt(*deformed_nodes[n2])
        p3 = gp_Pnt(*deformed_nodes[n3])
        
        # Create triangular face
        try:
            polygon = BRepBuilderAPI_MakePolygon(p1, p2, p3, True)
            if polygon.IsDone():
                wire = polygon.Wire()
                face_maker = BRepBuilderAPI_MakeFace(wire, True)
                if face_maker.IsDone():
                    builder.Add(compound, face_maker.Face())
                    faces_created += 1
        except Exception:
            pass
    
    print(f"Created {faces_created} triangular faces")
    
    # Show in OCP - show both original and deformed together
    from ocp_vscode import reset_show
    reset_show()  # Clear previous objects
    
    if original_beam is not None:
        show_object(original_beam.shape, name="Original", options={"alpha": 0.3, "color": "gray"})
    
    # Display the compound directly - ocp_vscode can handle TopoDS_Compound
    show_object(compound, name=f"Deformed ({scale_factor}x)", options={"color": "red"})
    
    # Add text annotation with results
    print(f"\nFEA Results displayed in OCP:")
    print(f"  Scale factor: {scale_factor}x")
    print(f"  Max displacement: {max_disp:.4f} mm")
    print(f"  Max scaled: {max_disp * scale_factor:.2f} mm")


# =============================================================================
# IFC EXPORT
# =============================================================================

def export_beam_to_ifc(
    beam: Beam,
    name: str,
    filename: str,
    position: Tuple[float, float, float] = (0, 0, 0),
):
    """Export a single beam to IFC format.
    
    Args:
        beam: Timber beam
        name: Beam name in IFC
        filename: Output IFC file path
        position: (x, y, z) position
    """
    try:
        import ifcopenshell
        import ifcopenshell.api
    except ImportError:
        raise ImportError("ifcopenshell not installed. Run: pip install ifcopenshell")
    
    # Create IFC file
    ifc = ifcopenshell.api.run("project.create_file", version="IFC4")
    
    # Create project structure
    project = ifcopenshell.api.run("root.create_entity", ifc, 
                                    ifc_class="IfcProject", name="Timber FEA")
    
    context = ifcopenshell.api.run("context.add_context", ifc, context_type="Model")
    body_context = ifcopenshell.api.run("context.add_context", ifc,
                                         context_type="Model",
                                         context_identifier="Body",
                                         target_view="MODEL_VIEW",
                                         parent=context)
    
    # Spatial structure
    site = ifcopenshell.api.run("root.create_entity", ifc, 
                                 ifc_class="IfcSite", name="Site")
    building = ifcopenshell.api.run("root.create_entity", ifc,
                                     ifc_class="IfcBuilding", name="Building")
    storey = ifcopenshell.api.run("root.create_entity", ifc,
                                   ifc_class="IfcBuildingStorey", name="Ground")
    
    ifcopenshell.api.run("aggregate.assign_object", ifc, 
                         products=[site], relating_object=project)
    ifcopenshell.api.run("aggregate.assign_object", ifc,
                         products=[building], relating_object=site)
    ifcopenshell.api.run("aggregate.assign_object", ifc,
                         products=[storey], relating_object=building)
    
    # Create beam
    ifc_beam = ifcopenshell.api.run("root.create_entity", ifc,
                                     ifc_class="IfcBeam", name=name)
    
    ifcopenshell.api.run("spatial.assign_container", ifc,
                         relating_structure=storey, products=[ifc_beam])
    
    # Geometry
    profile = ifc.create_entity("IfcRectangleProfileDef",
                                ProfileType="AREA",
                                XDim=beam.width,
                                YDim=beam.height)
    
    direction = ifc.create_entity("IfcDirection", DirectionRatios=[1.0, 0.0, 0.0])
    extruded = ifc.create_entity("IfcExtrudedAreaSolid",
                                  SweptArea=profile,
                                  ExtrudedDirection=direction,
                                  Depth=beam.length)
    
    shape_rep = ifc.create_entity("IfcShapeRepresentation",
                                   ContextOfItems=body_context,
                                   RepresentationIdentifier="Body",
                                   RepresentationType="SweptSolid",
                                   Items=[extruded])
    
    prod_shape = ifc.create_entity("IfcProductDefinitionShape",
                                    Representations=[shape_rep])
    ifc_beam.Representation = prod_shape
    
    # Placement
    x, y, z = position
    ifcopenshell.api.run("geometry.edit_object_placement", ifc,
                         product=ifc_beam,
                         matrix=np.array([
                             [1, 0, 0, x],
                             [0, 1, 0, y],
                             [0, 0, 1, z],
                             [0, 0, 0, 1],
                         ]))
    
    ifc.write(filename)
    print(f"IFC file: {filename}")


# =============================================================================
# VISUALIZATION
# =============================================================================

def visualize_beam(beam: Beam, name: str = "Beam"):
    """Visualize beam using ocp_vscode."""
    try:
        from ocp_vscode import show_object, show
        show_object(beam.shape, name=name)
        show()
    except ImportError:
        print("ocp_vscode not available for visualization")


# =============================================================================
# MAIN PIPELINE
# =============================================================================

def run_fea_pipeline(
    beam: Beam,
    material: TimberMaterial,
    output_dir: str,
    mesh_size: float = 10.0,
    load_magnitude: float = 1000.0,
) -> dict:
    """Run complete FEA pipeline for a timber beam.
    
    Pipeline: build123d → gmsh → CalculiX → post-process
    
    Args:
        beam: Timber beam geometry
        material: Material properties
        output_dir: Output directory for all files
        mesh_size: Target mesh element size [mm]
        load_magnitude: Total load at free end [N]
        
    Returns:
        Dict with results summary
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    results = {
        "beam": f"{beam.length}x{beam.width}x{beam.height} mm",
        "material": material.name,
        "load": f"{load_magnitude} N",
    }
    
    # Step 1: Generate mesh
    print("\n[1/4] Generating mesh with gmsh...")
    try:
        mesh_file, fixed_nodes, load_nodes = create_beam_mesh(
            beam, str(output_path), mesh_size
        )
        results["mesh_file"] = mesh_file
        results["fixed_nodes"] = len(fixed_nodes)
        results["load_nodes"] = len(load_nodes)
    except Exception as e:
        results["error"] = f"Mesh generation failed: {e}"
        return results
    
    # Step 2: Write CalculiX input
    print("\n[2/4] Writing CalculiX input...")
    ccx_file = str(output_path / "analysis.inp")
    write_calculix_input(
        mesh_file, ccx_file, material, fixed_nodes, load_nodes, load_magnitude
    )
    results["ccx_file"] = ccx_file
    
    # Step 3: Run CalculiX
    print("\n[3/4] Running CalculiX analysis...")
    success, frd_file = run_calculix(ccx_file)
    
    if not success:
        results["error"] = f"CalculiX failed: {frd_file}"
        return results
    
    results["frd_file"] = frd_file
    
    # Step 4: Post-process results
    print("\n[4/4] Post-processing results...")
    analysis = analyze_results(frd_file)
    results.update(analysis)
    
    return results


def main():
    """Main example: Cantilever beam FEA analysis."""
    
    print("=" * 60)
    print("FEA Pipeline: build123d → gmsh → CalculiX")
    print("=" * 60)
    
    # Output directory
    output_dir = Path(__file__).parent / "calculix_output"
    
    # Create beam geometry
    print("\nCreating beam geometry...")
    beam = Beam(length=600, width=80, height=120)
    print(f"  Beam: {beam.length} x {beam.width} x {beam.height} mm")
    
    # Define material
    print("\nDefining material...")
    material = TimberMaterial()
    print(f"  Material: {material.name}")
    print(f"  E_longitudinal: {material.E_L} MPa")
    print(f"  Density: {material.density} kg/m³")
    
    # Run FEA pipeline
    print("\n" + "-" * 60)
    results = run_fea_pipeline(
        beam=beam,
        material=material,
        output_dir=str(output_dir),
        mesh_size=15.0,
        load_magnitude=1000.0,  # 1 kN
    )
    print("-" * 60)
    
    # Print results
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    
    if "error" in results:
        print(f"ERROR: {results['error']}")
    else:
        print(f"Max Z-displacement: {results.get('max_uz', 'N/A'):.4f} mm")
        print(f"Max total displacement: {results.get('max_total', 'N/A'):.4f} mm")
        print(f"Output directory: {output_dir}")
        
        # Visualize FEA results in OCP
        print("\nVisualizing FEA results in OCP...")
        try:
            frd_file = results.get("frd_file")
            mesh_file = results.get("mesh_file")
            if frd_file and mesh_file:
                visualize_fea_results_ocp(
                    frd_file, 
                    mesh_file, 
                    scale_factor=50.0,
                    original_beam=beam,
                )
        except Exception as e:
            print(f"  OCP visualization error: {e}")
            # Fallback to matplotlib
            print("  Falling back to matplotlib...")
            try:
                visualize_fea_results(frd_file, scale_factor=50.0)
            except Exception as e2:
                print(f"  Matplotlib error: {e2}")
    
    # Export to IFC
    print("\nExporting to IFC...")
    try:
        ifc_file = str(output_dir / "beam.ifc")
        export_beam_to_ifc(beam, "Cantilever_Beam", ifc_file)
    except ImportError as e:
        print(f"  Skipped: {e}")
    
    print("\n" + "=" * 60)
    print("Pipeline complete!")
    print("=" * 60)
    
    return results


if __name__ == "__main__":
    main()
