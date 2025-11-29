"""
Full Open-Source Pipeline: Timber Joinery → BIM → FEA → Visualization

This example demonstrates:
1. build123d geometry (your timber joints library)
2. COMPAS geometry conversion
3. compas_fea2 model with orthotropic timber material
4. CalculiX FEA solver
5. ocp/pythonOCC visualization
6. ifcopenshell IFC export

Pipeline:
    build123d (geometry) 
        → compas (structural model)
        → compas_fea2 → CalculiX (FEA)
        → ocp/pythonOCC (visualization)
        → ifcopenshell (BIM/IFC export)

Installation:
    pip install compas compas_fea2 ifcopenshell
    
    # For CalculiX solver (Ubuntu/Debian):
    sudo apt-get install calculix-ccx
    
    # Or via conda:
    conda install -c conda-forge calculix
"""

from dataclasses import dataclass
from typing import Optional, Tuple, List
import numpy as np

# --- Core build123d imports ---
from build123d import Part, Box, Align, Location

# --- Our timber library ---
from timber_joints.beam import Beam
from timber_joints.tenon import Tenon
from timber_joints.alignment import align_beam_on_post


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
    f_t_0_k: float = 14.0   # Tension parallel to grain
    f_t_90_k: float = 0.4   # Tension perpendicular to grain
    f_c_0_k: float = 21.0   # Compression parallel to grain
    f_c_90_k: float = 2.5   # Compression perpendicular to grain
    f_v_k: float = 4.0      # Shear strength
    f_m_k: float = 24.0     # Bending strength


@dataclass
class GLulamMaterial(TimberMaterial):
    """Glued Laminated Timber GL24h properties (EN 14080)."""
    name: str = "GL24h"
    E_L: float = 11500.0
    E_R: float = 300.0
    E_T: float = 300.0
    G_LR: float = 650.0
    G_LT: float = 650.0
    G_RT: float = 65.0
    density: float = 380.0
    f_m_k: float = 24.0
    f_t_0_k: float = 19.2
    f_c_0_k: float = 24.0


# =============================================================================
# CONVERSION TO COMPAS GEOMETRY
# =============================================================================

def beam_to_compas_frame(beam: Beam, origin: Tuple[float, float, float] = (0, 0, 0)):
    """Convert a Beam to a COMPAS Frame representing its local coordinate system.
    
    Args:
        beam: The timber beam
        origin: World position of beam start
        
    Returns:
        compas.geometry.Frame at beam position
    """
    try:
        from compas.geometry import Frame, Point, Vector
    except ImportError:
        raise ImportError("COMPAS not installed. Run: pip install compas")
    
    # Beam local axes: X along length, Y along width, Z along height
    return Frame(
        point=Point(*origin),
        xaxis=Vector(1, 0, 0),  # Along beam length
        yaxis=Vector(0, 1, 0),  # Along beam width
    )


def beam_to_compas_mesh(beam: Beam):
    """Convert a Beam's solid to a COMPAS Mesh.
    
    Uses build123d's tessellation to create a triangulated mesh.
    """
    try:
        from compas.datastructures import Mesh
    except ImportError:
        raise ImportError("COMPAS not installed. Run: pip install compas")
    
    shape = beam.shape
    
    # Get tessellation from build123d/OCC
    # This extracts vertices and triangular faces
    vertices = []
    faces = []
    
    # Use OCC's tessellation
    from OCC.Core.BRepMesh import BRepMesh_IncrementalMesh
    from OCC.Core.TopExp import TopExp_Explorer
    from OCC.Core.TopAbs import TopAbs_FACE
    from OCC.Core.BRep import BRep_Tool
    from OCC.Core.TopLoc import TopLoc_Location
    
    # Mesh the shape
    BRepMesh_IncrementalMesh(shape.wrapped, 1.0, False, 0.5, True)
    
    explorer = TopExp_Explorer(shape.wrapped, TopAbs_FACE)
    vertex_map = {}
    
    while explorer.More():
        face = explorer.Current()
        location = TopLoc_Location()
        triangulation = BRep_Tool.Triangulation(face, location)
        
        if triangulation is not None:
            # Get transformation
            trsf = location.Transformation()
            
            # Add vertices
            for i in range(1, triangulation.NbNodes() + 1):
                pnt = triangulation.Node(i)
                pnt.Transform(trsf)
                v = (pnt.X(), pnt.Y(), pnt.Z())
                if v not in vertex_map:
                    vertex_map[v] = len(vertices)
                    vertices.append(v)
            
            # Add faces (triangles)
            for i in range(1, triangulation.NbTriangles() + 1):
                tri = triangulation.Triangle(i)
                n1, n2, n3 = tri.Get()
                
                p1 = triangulation.Node(n1)
                p2 = triangulation.Node(n2) 
                p3 = triangulation.Node(n3)
                p1.Transform(trsf)
                p2.Transform(trsf)
                p3.Transform(trsf)
                
                v1 = (p1.X(), p1.Y(), p1.Z())
                v2 = (p2.X(), p2.Y(), p2.Z())
                v3 = (p3.X(), p3.Y(), p3.Z())
                
                faces.append([vertex_map[v1], vertex_map[v2], vertex_map[v3]])
        
        explorer.Next()
    
    return Mesh.from_vertices_and_faces(vertices, faces)


# =============================================================================
# COMPAS FEA2 MODEL BUILDER
# =============================================================================

def create_fea_model(
    beam: Beam,
    material: TimberMaterial,
    boundary_conditions: str = "cantilever",
    load_magnitude: float = 1000.0,  # N
):
    """Create a compas_fea2 model from a timber beam.
    
    Args:
        beam: The timber beam geometry
        material: Timber material properties
        boundary_conditions: "cantilever", "simply_supported", or "fixed"
        load_magnitude: Point load at free end [N]
        
    Returns:
        compas_fea2 Model ready for analysis
    """
    try:
        from compas_fea2.model import Model, DeformablePart, Node, BeamElement
        from compas_fea2.model import ElasticOrthotropic, RectangularSection
        from compas_fea2.problem import Problem
    except ImportError:
        raise ImportError("compas_fea2 not installed. Run: pip install compas_fea2")
    
    # Create model
    model = Model(name="timber_beam_analysis")
    
    # Create part
    part = DeformablePart(name="beam")
    model.add_part(part)
    
    # Define orthotropic material
    # Note: compas_fea2 ElasticOrthotropic uses engineering constants
    # Mapping from timber conventions: L=x (along grain), R=y, T=z
    timber_mat = ElasticOrthotropic(
        name=material.name,
        Ex=material.E_L,   # Longitudinal (along grain)
        Ey=material.E_R,   # Radial
        Ez=material.E_T,   # Tangential
        vxy=material.nu_LR,
        vyz=material.nu_RT,
        vzx=material.nu_LT,  # vzx required by compas_fea2
        Gxy=material.G_LR,
        Gyz=material.G_RT,
        Gzx=material.G_LT,   # Gzx required by compas_fea2
        density=material.density,
    )
    
    # Define rectangular section
    section = RectangularSection(
        name="beam_section",
        w=beam.width,
        h=beam.height,
        material=timber_mat,
    )
    
    # Create beam elements along length
    n_elements = 20
    dx = beam.length / n_elements
    
    nodes = []
    for i in range(n_elements + 1):
        x = i * dx
        # Beam centerline: Y and Z at center
        node = Node(xyz=(x, beam.width / 2, beam.height / 2))
        part.add_node(node)
        nodes.append(node)
    
    # Create beam elements
    elements = []
    for i in range(n_elements):
        element = BeamElement(
            nodes=[nodes[i], nodes[i + 1]],
            section=section,
        )
        part.add_element(element)
        elements.append(element)
    
    # Apply boundary conditions
    if boundary_conditions == "cantilever":
        # Fixed at start
        model.add_fix_bc(nodes=[nodes[0]])
    elif boundary_conditions == "simply_supported":
        # Pinned at start, roller at end
        model.add_pin_bc(nodes=[nodes[0]])
        model.add_rollerX_bc(nodes=[nodes[-1]])
    elif boundary_conditions == "fixed":
        # Fixed at both ends
        model.add_fix_bc(nodes=[nodes[0]])
        model.add_fix_bc(nodes=[nodes[-1]])
    
    # Create problem and analysis step
    problem = Problem(name="static_analysis")
    model.add_problem(problem)
    
    step = problem.add_static_step()
    
    # Apply point load at free end (downward in Z)
    step.add_node_pattern(nodes=[nodes[-1]], z=-load_magnitude)
    
    return model, problem


def run_calculix_analysis(model, problem, output_dir: str = "./calculix_output"):
    """Run CalculiX analysis and return results.
    
    Args:
        model: compas_fea2 Model
        problem: compas_fea2 Problem
        output_dir: Directory for solver files
        
    Returns:
        Results object with displacements and stresses
    """
    import os
    os.makedirs(output_dir, exist_ok=True)
    
    # Export to CalculiX format
    inp_file = os.path.join(output_dir, "model.inp")
    model.to_calculix(inp_file)
    
    print(f"CalculiX input file written to: {inp_file}")
    print("To run analysis manually:")
    print(f"  ccx -i {os.path.splitext(inp_file)[0]}")
    
    # Try to run CalculiX
    try:
        problem.analyze_and_extract(
            backend="calculix",
            path=output_dir,
        )
        return problem.results
    except Exception as e:
        print(f"CalculiX analysis failed: {e}")
        print("Make sure CalculiX (ccx) is installed and in PATH")
        return None


# =============================================================================
# IFC EXPORT
# =============================================================================

def export_to_ifc(
    beams: List[Tuple[Beam, str, Tuple[float, float, float]]],
    filename: str,
    project_name: str = "Timber Frame Structure",
):
    """Export beams to IFC format using ifcopenshell.
    
    Args:
        beams: List of (Beam, name, position) tuples
        filename: Output IFC file path
        project_name: IFC project name
    """
    try:
        import ifcopenshell
        import ifcopenshell.api
    except ImportError:
        raise ImportError("ifcopenshell not installed. Run: pip install ifcopenshell")
    
    # Create IFC file
    ifc = ifcopenshell.api.run("project.create_file", version="IFC4")
    
    # Create project
    project = ifcopenshell.api.run("root.create_entity", ifc, ifc_class="IfcProject", name=project_name)
    
    # Create context
    context = ifcopenshell.api.run("context.add_context", ifc, context_type="Model")
    body_context = ifcopenshell.api.run(
        "context.add_context", ifc,
        context_type="Model",
        context_identifier="Body",
        target_view="MODEL_VIEW",
        parent=context
    )
    
    # Create site and building
    site = ifcopenshell.api.run("root.create_entity", ifc, ifc_class="IfcSite", name="Site")
    building = ifcopenshell.api.run("root.create_entity", ifc, ifc_class="IfcBuilding", name="Building")
    storey = ifcopenshell.api.run("root.create_entity", ifc, ifc_class="IfcBuildingStorey", name="Ground Floor")
    
    # Aggregate - note: products is a list, relating_object is the parent
    ifcopenshell.api.run("aggregate.assign_object", ifc, products=[site], relating_object=project)
    ifcopenshell.api.run("aggregate.assign_object", ifc, products=[building], relating_object=site)
    ifcopenshell.api.run("aggregate.assign_object", ifc, products=[storey], relating_object=building)
    
    # Create material
    timber_material = ifcopenshell.api.run("material.add_material", ifc, name="C24 Softwood")
    
    # Add beams
    for beam, name, position in beams:
        # Create IfcBeam
        ifc_beam = ifcopenshell.api.run(
            "root.create_entity", ifc,
            ifc_class="IfcBeam",
            name=name
        )
        
        # Assign to storey - products is a list
        ifcopenshell.api.run(
            "spatial.assign_container", ifc,
            relating_structure=storey,
            products=[ifc_beam]
        )
        
        # Assign material - products is a list
        ifcopenshell.api.run(
            "material.assign_material", ifc,
            products=[ifc_beam],
            material=timber_material
        )
        
        # Create geometry (simplified as extruded rectangle)
        # For complex joints, you'd need to tessellate the build123d shape
        profile = ifc.create_entity(
            "IfcRectangleProfileDef",
            ProfileType="AREA",
            XDim=beam.width,
            YDim=beam.height,
        )
        
        # Create extrusion
        direction = ifc.create_entity("IfcDirection", DirectionRatios=[0.0, 0.0, 1.0])
        extruded_solid = ifc.create_entity(
            "IfcExtrudedAreaSolid",
            SweptArea=profile,
            ExtrudedDirection=direction,
            Depth=beam.length,
        )
        
        # Create shape representation
        shape_representation = ifc.create_entity(
            "IfcShapeRepresentation",
            ContextOfItems=body_context,
            RepresentationIdentifier="Body",
            RepresentationType="SweptSolid",
            Items=[extruded_solid],
        )
        
        product_shape = ifc.create_entity(
            "IfcProductDefinitionShape",
            Representations=[shape_representation],
        )
        
        ifc_beam.Representation = product_shape
        
        # Set placement
        x, y, z = position
        placement = ifcopenshell.api.run(
            "geometry.edit_object_placement", ifc,
            product=ifc_beam,
            matrix=np.array([
                [1, 0, 0, x],
                [0, 1, 0, y],
                [0, 0, 1, z],
                [0, 0, 0, 1],
            ])
        )
    
    # Write file
    ifc.write(filename)
    print(f"IFC file written to: {filename}")


# =============================================================================
# VISUALIZATION
# =============================================================================

def visualize_with_ocp(shapes: List[Part], colors: Optional[List] = None):
    """Visualize shapes using ocp_vscode (OCP CAD Viewer).
    
    Args:
        shapes: List of build123d Part objects
        colors: Optional list of colors for each shape
    """
    try:
        from ocp_vscode import show, show_object
    except ImportError:
        print("ocp_vscode not installed. Using basic OCC display.")
        visualize_with_occ(shapes)
        return
    
    for i, shape in enumerate(shapes):
        name = f"shape_{i}"
        color = colors[i] if colors and i < len(colors) else None
        show_object(shape, name=name, options={"color": color} if color else {})
    
    show()


def visualize_with_occ(shapes: List[Part]):
    """Fallback visualization using pythonOCC display."""
    try:
        from OCC.Display.SimpleGui import init_display
    except ImportError:
        print("pythonOCC display not available.")
        return
    
    display, start_display, add_menu, add_function_to_menu = init_display()
    
    for shape in shapes:
        display.DisplayShape(shape.wrapped, update=True)
    
    display.FitAll()
    start_display()


# =============================================================================
# MAIN EXAMPLE
# =============================================================================

def main():
    """Complete pipeline example: Mortise-Tenon joint → FEA → IFC."""
    
    print("=" * 60)
    print("Timber Joinery FEA Pipeline Example")
    print("=" * 60)
    
    # 1. CREATE GEOMETRY
    print("\n1. Creating timber geometry...")
    
    # Create a horizontal beam with tenon
    beam = Beam(length=600, width=80, height=120)
    tenon = Tenon(
        beam=beam,
        tenon_width=beam.width / 3,
        tenon_height=beam.height * 2 / 3,
        tenon_length=60,
        at_start=True,
    )
    beam_with_tenon = tenon.shape
    
    # Create a post (vertical)
    post = Beam(length=400, width=100, height=100)
    
    print(f"   Beam: {beam.length} x {beam.width} x {beam.height} mm")
    print(f"   Post: {post.length} x {post.width} x {post.height} mm")
    print(f"   Tenon: {tenon.tenon_width:.1f} x {tenon.tenon_height:.1f} x {tenon.tenon_length} mm")
    
    # 2. DEFINE MATERIAL
    print("\n2. Defining timber material (C24 Softwood)...")
    material = TimberMaterial()
    print(f"   E_longitudinal: {material.E_L} MPa")
    print(f"   E_radial: {material.E_R} MPa")
    print(f"   Density: {material.density} kg/m³")
    print(f"   Bending strength: {material.f_m_k} MPa")
    
    # 3. CONVERT TO COMPAS (if available)
    print("\n3. Converting to COMPAS geometry...")
    try:
        frame = beam_to_compas_frame(beam)
        print(f"   Frame origin: {frame.point}")
        print(f"   Frame X-axis: {frame.xaxis}")
    except ImportError as e:
        print(f"   Skipped: {e}")
    
    # 4. CREATE FEA MODEL (if available)
    print("\n4. Creating FEA model...")
    try:
        model, problem = create_fea_model(
            beam=beam,
            material=material,
            boundary_conditions="cantilever",
            load_magnitude=1000.0,  # 1 kN point load
        )
        print(f"   Model: {model.name}")
        print(f"   Elements: beam elements along length")
        print(f"   BC: Cantilever (fixed at start)")
        print(f"   Load: 1000 N downward at free end")
        
        # 5. RUN ANALYSIS
        print("\n5. Running CalculiX analysis...")
        results = run_calculix_analysis(model, problem)
        if results:
            print("   Analysis complete!")
            # Extract max displacement
            displacements = results.get_nodal_displacements()
            print(f"   Max displacement: {max(d[2] for d in displacements):.3f} mm")
    except ImportError as e:
        print(f"   Skipped: {e}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # 6. EXPORT TO IFC
    print("\n6. Exporting to IFC...")
    try:
        export_to_ifc(
            beams=[
                (beam, "Horizontal_Beam", (0, 0, 300)),
                (post, "Vertical_Post", (0, 0, 0)),
            ],
            filename="timber_frame.ifc",
            project_name="Timber Joint Example",
        )
    except ImportError as e:
        print(f"   Skipped: {e}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # 7. VISUALIZE
    print("\n7. Visualizing geometry...")
    try:
        # Position post vertically using build123d Axis
        from build123d import Axis
        vertical_post = post.shape.rotate(Axis.Y, 90)
        
        visualize_with_ocp([beam_with_tenon, vertical_post])
    except Exception as e:
        print(f"   Visualization error: {e}")
        print("   Run in VS Code with OCP CAD Viewer extension for visualization")
    
    print("\n" + "=" * 60)
    print("Pipeline complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
