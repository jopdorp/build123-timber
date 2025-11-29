"""FEA analysis adapter for timber frames."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import os

from timber_joints.frame import TimberFrame, Element, Role


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
