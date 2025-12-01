"""FEA analysis adapter for timber frames."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List, Tuple
import os

from build123d import Part, Location, Box, Align, Compound

from timber_joints.frame import TimberFrame, Element, Role


# =============================================================================
# Contact Surface Utilities
# =============================================================================

def get_bbox_solid(bbox) -> Part:
    """Create a solid box from a bounding box."""
    size_x = bbox.max.X - bbox.min.X
    size_y = bbox.max.Y - bbox.min.Y
    size_z = bbox.max.Z - bbox.min.Z
    box = Box(size_x, size_y, size_z, align=(Align.MIN, Align.MIN, Align.MIN))
    return box.move(Location((bbox.min.X, bbox.min.Y, bbox.min.Z)))


def scale_shape_in_place(shape: Part, scale_factor: float) -> Part:
    """Scale a shape from its center (not from origin)."""
    center = shape.bounding_box().center()
    centered = shape.move(Location((-center.X, -center.Y, -center.Z)))
    scaled = centered.scale(scale_factor)
    return scaled.move(Location((center.X, center.Y, center.Z)))


def expand_shape_by_margin(shape: Part, margin: float) -> Part:
    """
    Scale a shape to expand its bounding box by a fixed margin on each axis.
    
    Unlike uniform scaling, this calculates independent scale factors per axis
    to achieve the same absolute margin expansion on each side.
    
    Note: This function creates a copy of the input shape to avoid mutation.
    
    Args:
        shape: The shape to expand
        margin: Fixed amount (mm) to add to each side of each axis
    
    Returns:
        A new shape scaled non-uniformly to achieve the margin expansion
    """
    import copy
    from OCP.gp import gp_GTrsf, gp_XYZ
    from OCP.BRepBuilderAPI import BRepBuilderAPI_GTransform
    
    # Deep copy to avoid mutating the original
    shape = copy.deepcopy(shape)
    
    bbox = shape.bounding_box()
    center = bbox.center()
    
    # Calculate size in each dimension
    size_x = bbox.max.X - bbox.min.X
    size_y = bbox.max.Y - bbox.min.Y
    size_z = bbox.max.Z - bbox.min.Z
    
    # Calculate scale factor for each axis to add margin to each side
    scale_x = (size_x + 2 * margin) / size_x if size_x > 0 else 1.0
    scale_y = (size_y + 2 * margin) / size_y if size_y > 0 else 1.0
    scale_z = (size_z + 2 * margin) / size_z if size_z > 0 else 1.0
    
    # Move shape to origin, apply non-uniform scale, move back
    centered = shape.move(Location((-center.X, -center.Y, -center.Z)))
    
    # Create non-uniform scaling transformation
    gtrsf = gp_GTrsf()
    gtrsf.SetValue(1, 1, scale_x)
    gtrsf.SetValue(2, 2, scale_y)
    gtrsf.SetValue(3, 3, scale_z)
    
    transform = BRepBuilderAPI_GTransform(centered.wrapped, gtrsf, True)
    scaled = Part(transform.Shape())
    
    return scaled.move(Location((center.X, center.Y, center.Z)))


# =============================================================================
# Material and Analysis Configuration
# =============================================================================


@dataclass
class TimberMaterial:
    """Orthotropic timber material properties (EN 338)."""
    name: str = "C24_Softwood"
    
    # Elastic moduli [MPa]
    E_L: float = 11000.0   # Longitudinal (along grain)
    E_R: float = 370.0     # Radial  
    E_T: float = 370.0     # Tangential
    
    # Shear moduli [MPa]
    G_LR: float = 690.0
    G_LT: float = 690.0
    G_RT: float = 50.0
    
    # Poisson's ratios
    nu_LR: float = 0.37
    nu_LT: float = 0.42
    nu_RT: float = 0.47
    
    # Density [kg/m³]
    density: float = 350.0
    
    # Strength [MPa]
    f_m_k: float = 24.0    # Bending


@dataclass
class AnalysisConfig:
    """Configuration for FEA analysis."""
    mesh_size: float = 20.0
    load_magnitude: float = 1000.0  # N
    scale_factor: float = 50.0      # For visualization
    output_dir: str = "./analysis_output"
    
    # Boundary conditions by role
    fixed_roles: tuple = (Role.POST,)  # Elements fixed at base
    loaded_roles: tuple = (Role.BEAM, Role.PLATE)  # Elements receiving load


@dataclass
class AnalysisResult:
    """Results from FEA analysis."""
    success: bool
    max_displacement: float = 0.0
    max_stress: float = 0.0
    frd_file: Optional[str] = None
    mesh_file: Optional[str] = None
    error: Optional[str] = None


def analyze_element(
    element: Element,
    material: TimberMaterial,
    config: AnalysisConfig,
) -> AnalysisResult:
    """Run FEA analysis on a single element.
    
    Uses gmsh → CalculiX pipeline.
    """
    # Import here to avoid circular deps and allow optional usage
    try:
        from examples.fea_pipeline import (
            create_beam_mesh,
            write_calculix_input,
            run_calculix,
            analyze_results,
        )
    except ImportError:
        return AnalysisResult(
            success=False,
            error="FEA pipeline not available. Ensure fea_pipeline.py is in examples/",
        )
    
    output_dir = Path(config.output_dir) / element.name
    output_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # Generate mesh
        mesh_file, fixed_nodes, load_nodes = create_beam_mesh(
            element.beam, str(output_dir), config.mesh_size
        )
        
        # Write CalculiX input
        ccx_file = str(output_dir / "analysis.inp")
        write_calculix_input(
            mesh_file, ccx_file, material,
            fixed_nodes, load_nodes, config.load_magnitude
        )
        
        # Run solver
        success, frd_file = run_calculix(ccx_file)
        
        if not success:
            return AnalysisResult(success=False, error=frd_file)
        
        # Parse results
        results = analyze_results(frd_file)
        
        return AnalysisResult(
            success=True,
            max_displacement=results.get("max_total", 0),
            frd_file=frd_file,
            mesh_file=mesh_file,
        )
        
    except Exception as e:
        return AnalysisResult(success=False, error=str(e))


def analyze_frame(
    frame: TimberFrame,
    material: TimberMaterial = None,
    config: AnalysisConfig = None,
) -> dict[str, AnalysisResult]:
    """Run FEA analysis on all elements in a frame.
    
    Returns dict mapping element names to results.
    """
    material = material or TimberMaterial()
    config = config or AnalysisConfig()
    
    results = {}
    for name, element in frame.elements.items():
        print(f"Analyzing {name} ({element.role.name})...")
        results[name] = analyze_element(element, material, config)
    
    return results


def print_analysis_summary(results: dict[str, AnalysisResult]):
    """Print summary of analysis results."""
    print("\n" + "=" * 50)
    print("ANALYSIS SUMMARY")
    print("=" * 50)
    
    for name, result in results.items():
        if result.success:
            print(f"{name}: max disp = {result.max_displacement:.4f} mm")
        else:
            print(f"{name}: FAILED - {result.error}")


# =============================================================================
# Multi-Step Friction Contact Utilities
# =============================================================================


def generate_friction_contact_steps(
    load_nodes: List[int],
    load_magnitude: float,
    n_load_steps: int = 10,
    friction_coeff: float = 0.4,
    stick_slope: float = 2000.0,
    use_stabilize: bool = False,
    stabilize_coeff: float = 0.05,
) -> List[str]:
    """
    Generate CalculiX input lines for multi-step friction contact loading.
    
    This implements the industry-standard approach for friction contact:
    1. Step 0: Close contact gaps (no load, no friction)
    2. Step 1: Apply first load increment (no friction yet)  
    3. Steps 2-N: Apply remaining load increments with friction active
    
    This sequence allows contact to establish before friction engages,
    avoiding the stick-slip oscillation that causes non-convergence.
    
    Args:
        load_nodes: List of node IDs to apply load to
        load_magnitude: Total load in N (will be distributed across nodes)
        n_load_steps: Number of load increments (default 10 = 10% each)
        friction_coeff: Coefficient of friction μ (default 0.4 for wood)
        stick_slope: Stick slope for penalty friction (default 2000)
        use_stabilize: Use ``*FRICTION, STABILIZE`` for additional stability
        stabilize_coeff: Stabilization coefficient (default 0.05)
    
    Returns:
        List of CalculiX input lines for all analysis steps
    """
    lines = []
    load_per_node = load_magnitude / len(load_nodes) if load_nodes else 0
    
    # Calculate cumulative load fractions
    fractions = [(i + 1) / n_load_steps for i in range(n_load_steps)]
    
    # Step 0: Contact seating only (no load, no friction)
    lines.extend([
        "",
        "** ============================================================",
        "** STEP 0: Contact seating (close gaps, no load, no friction)",
        "** ============================================================",
        "*STEP, NLGEOM, INC=40",
        "*STATIC",
        "0.1, 1.0, 1e-6, 0.2",
        "",
        "** No loads - just establish contact",
        "",
        "*NODE FILE",
        "U",
        "*END STEP",
    ])
    
    # Step 1: First load increment WITHOUT friction
    # This allows contact to settle under pressure before friction activates
    lines.extend([
        "",
        "** ============================================================",
        f"** STEP 1: Load {fractions[0]*100:.0f}% (NO friction yet)",
        "** ============================================================",
        "*STEP, NLGEOM, INC=50",
        "*STATIC",
        "0.05, 1.0, 1e-6, 0.1",
        "",
        "*CLOAD",
    ])
    
    for node in load_nodes:
        lines.append(f"{node}, 3, {-load_per_node * fractions[0]:.6f}")
    
    lines.extend([
        "",
        "*NODE FILE",
        "U, RF",
        "*EL FILE",
        "S, E",
        "*CONTACT FILE",
        "CDIS, CSTR",
        "*END STEP",
    ])
    
    # Steps 2+: Remaining load increments WITH friction
    for step_num, fraction in enumerate(fractions[1:], start=2):
        lines.extend([
            "",
            "** ============================================================",
            f"** STEP {step_num}: Load {fraction*100:.0f}% WITH friction",
            "** ============================================================",
            "*STEP, NLGEOM, INC=60",
            "*STATIC",
            "0.05, 1.0, 1e-6, 0.1",
            "",
        ])
        
        # Enable friction
        if use_stabilize:
            lines.append(f"*FRICTION, STABILIZE={stabilize_coeff}")
        else:
            lines.append("*FRICTION")
        lines.append(f"{friction_coeff}, {stick_slope}")
        
        lines.extend([
            "",
            "*CLOAD",
        ])
        
        for node in load_nodes:
            lines.append(f"{node}, 3, {-load_per_node * fraction:.6f}")
        
        lines.extend([
            "",
            "*NODE FILE",
            "U, RF",
            "*EL FILE", 
            "S, E",
            "*CONTACT FILE",
            "CDIS, CSTR",
            "*END STEP",
        ])
    
    return lines


def generate_calculix_contact_input(
    mesh_file: str,
    material: "TimberMaterial",
    fixed_nodes_left: List[int],
    fixed_nodes_right: List[int],
    load_nodes: List[int],
    load_magnitude: float,
    contact_pairs: List[dict],
    margin_gap: float = 1.0,
    n_load_steps: int = 10,
    friction_coeff: float = 0.4,
    use_stabilize: bool = False,
) -> str:
    """
    Generate complete CalculiX input file content for friction contact analysis.
    
    This creates a multi-step analysis that:
    1. Establishes contact (no load, no friction)
    2. Applies first load increment (no friction)
    3. Incrementally increases load with friction active
    
    Args:
        mesh_file: Path to mesh.inp file (will use ``*INCLUDE``)
        material: TimberMaterial with orthotropic properties
        fixed_nodes_left: Node IDs fixed at left support
        fixed_nodes_right: Node IDs fixed at right support
        load_nodes: Node IDs for load application
        load_magnitude: Total load in N
        contact_pairs: List of dicts with 'slave' and 'master' surface names
        margin_gap: Initial contact gap in mm
        n_load_steps: Number of load increments
        friction_coeff: Coefficient of friction μ
        use_stabilize: Use ``*FRICTION, STABILIZE``
    
    Returns:
        Complete CalculiX input file content as string
    """
    lines = [
        "** CalculiX Friction Contact Analysis (Multi-Step Method)",
        "** Generated by timber_joints.analysis",
        "**",
        "** Strategy: Contact seating → First load (no friction) → Load with friction",
        "** This avoids stick-slip oscillation during initial contact establishment",
        "**",
        "",
        f"*INCLUDE, INPUT={Path(mesh_file).name}",
        "",
        f"*MATERIAL, NAME={material.name}",
        "*ELASTIC, TYPE=ENGINEERING CONSTANTS",
        f"{material.E_L}, {material.E_R}, {material.E_T}, "
        f"{material.nu_LR}, {material.nu_LT}, {material.nu_RT}, "
        f"{material.G_LR}, {material.G_LT},",
        f"{material.G_RT}, 0.0",
        "*DENSITY",
        f"{material.density * 1e-9:.6e}",
        "",
        "*SOLID SECTION, ELSET=TIMBER, MATERIAL=" + material.name,
        "",
        "** Surface interaction - LINEAR penalty contact with friction",
        "*SURFACE INTERACTION, NAME=WOOD_CONTACT",
        "*SURFACE BEHAVIOR, PRESSURE-OVERCLOSURE=LINEAR",
        f"1e3, 0.0, {margin_gap}",  # slope K, sigma_inf=0, c0 = margin_gap
        "",
    ]
    
    # Contact pairs
    for i, pair in enumerate(contact_pairs):
        lines.extend([
            f"** Contact pair {i+1}: {pair.get('name', f'joint_{i+1}')}",
            f"*CONTACT PAIR, INTERACTION=WOOD_CONTACT, TYPE=NODE TO SURFACE, ADJUST={margin_gap + 1}",
            f"{pair['slave']}, {pair['master']}",
            "",
        ])
    
    # Convergence controls
    lines.extend([
        "** Relaxed convergence for contact problems",
        "*CONTROLS, PARAMETERS=TIME INCREMENTATION",
        "20,30,9,200,10,4,,5",
        "*CONTROLS, PARAMETERS=FIELD, FIELD=DISPLACEMENT",
        "0.25, 0.5, 1e-5, ,0.02, 1e-5",
        "*CONTROLS, PARAMETERS=CONTACT",
        "0.001, 0.1, 100, 200",
        "",
        "** Boundary Conditions - Posts fixed at foundation",
        "*BOUNDARY",
    ])
    
    for node in fixed_nodes_left:
        lines.append(f"{node}, 1, 3, 0.0")
    
    for node in fixed_nodes_right:
        lines.append(f"{node}, 1, 3, 0.0")
    
    # Add multi-step friction loading
    step_lines = generate_friction_contact_steps(
        load_nodes=load_nodes,
        load_magnitude=load_magnitude,
        n_load_steps=n_load_steps,
        friction_coeff=friction_coeff,
        use_stabilize=use_stabilize,
    )
    lines.extend(step_lines)
    
    return '\n'.join(lines)
