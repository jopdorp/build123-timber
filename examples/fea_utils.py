"""Shared utilities for FEA examples.

This module provides common functionality for:
- Visualizing CAD geometry, mesh, and contact surfaces
- Running and displaying FEA analysis results
"""

from pathlib import Path
from typing import List, Tuple, Optional, Callable

from build123d import Location, Part
from ocp_vscode import show

from timber_joints.fea import (
    TimberFrame, LoadBC, show_fea_results,
    get_boundary_faces, build_mesh_faces_compound,
)


def visualize_frame_with_mesh(
    frame: TimberFrame,
    cad_shapes: List[Tuple[Part, str, str]],
    offset_axis: str = "X",
    cad_offset: float = 0,
    mesh_offset: float = 6000,
    contact_offset: float = 12000,
    element_size: float = 150.0,
    element_size_fine: float = 40.0,
    refinement_margin: float = 20.0,
    verbose: bool = True,
):
    """Visualize CAD geometry, mesh, and contact surfaces side by side.
    
    Args:
        frame: TimberFrame with members added
        cad_shapes: List of (shape, name, color) tuples for CAD visualization
        offset_axis: "X" or "Y" - axis to offset mesh/contacts along
        cad_offset: Offset for CAD geometry
        mesh_offset: Offset for mesh visualization  
        contact_offset: Offset for contact surface visualization
        element_size: Base mesh element size
        element_size_fine: Fine mesh size at contacts
        refinement_margin: Margin around contact regions
        verbose: Print progress
        
    Returns:
        MeshingResult from frame.mesh()
    """
    # Collect all objects to show at once (avoids O(n²) re-rendering)
    objects_to_show = []
    
    # 1. Collect CAD geometry
    if verbose:
        print(f"CAD geometry at {offset_axis}={cad_offset}")
    
    for shape, name, color in cad_shapes:
        if offset_axis == "X":
            offset_shape = shape.move(Location((cad_offset, 0, 0)))
        else:
            offset_shape = shape.move(Location((0, cad_offset, 0)))
        objects_to_show.append((offset_shape, f"CAD: {name}", {"color": color, "alpha": 0.5}))
    
    # 2. Generate mesh with contact detection (cached for later analysis)
    if verbose:
        print("Generating refined mesh with contact detection...")
    
    meshing_result = frame.mesh(
        element_size=element_size,
        element_size_fine=element_size_fine,
        refinement_margin=refinement_margin,
        verbose=verbose,
    )
    
    # 3. Collect mesh boundaries
    if verbose:
        print(f"\nRefined mesh: {meshing_result.total_nodes} nodes, {meshing_result.total_elements} elements")
    
    for part_name, mesh in meshing_result.meshes.items():
        elems = [(i + 1, e) for i, e in enumerate(mesh.elements)]
        boundary_faces = get_boundary_faces(elems)
        mesh_compound = build_mesh_faces_compound(boundary_faces, elems, mesh.nodes)
        
        if offset_axis == "X":
            mesh_vis = mesh_compound.move(Location((mesh_offset, 0, 0)))
        else:
            mesh_vis = mesh_compound.move(Location((0, mesh_offset, 0)))
        
        objects_to_show.append((mesh_vis, f"Mesh: {part_name}", {"color": "lightgray", "alpha": 0.7}))
        
        if verbose:
            print(f"  {part_name}: {mesh.num_nodes} nodes, {mesh.num_elements} elements, {len(boundary_faces)} boundary faces")
    
    # 4. Collect contact surfaces with tenon/mortise distinction
    if verbose:
        print(f"\nContact surfaces:")
    
    for surf_name, faces in meshing_result.contact_surfaces.items():
        if not faces:
            continue
        
        mesh_compound = build_mesh_faces_compound(
            faces, 
            meshing_result.combined.elements, 
            meshing_result.combined.nodes
        )
        
        # Determine if this is a mortise (receiving) or tenon (inserted) surface
        # Posts and beams have mortises (blue), braces have tenons (red)
        part_name = surf_name.replace("_SURF", "").split("_")[-1]  # e.g., "left_post" from "contact_0_left_post_SURF"
        # Reconstruct part name (handles underscores in names)
        parts = surf_name.replace("_SURF", "").split("_")[1:]  # Remove "contact" and "N"
        if len(parts) >= 2:
            part_name = "_".join(parts[1:])  # Skip the contact number
        
        is_mortise = "post" in part_name or "beam" in part_name or "girt" in part_name
        color = "blue" if is_mortise else "red"
        
        if offset_axis == "X":
            surface_vis = mesh_compound.move(Location((contact_offset, 0, 0)))
        else:
            surface_vis = mesh_compound.move(Location((0, contact_offset, 0)))
        
        label = "mortise" if is_mortise else "tenon"
        objects_to_show.append((surface_vis, f"Contact: {surf_name} ({label})", {"color": color}))
        
        if verbose:
            print(f"  {surf_name} ({label}): {len(faces)} faces")
    
    # 5. Show all objects at once (single render, not O(n²))
    if verbose:
        print(f"\nShowing {len(objects_to_show)} objects...")
    
    # Unpack into format that show() expects: show(*objects, names=[...], colors=[...])
    shapes = [obj for obj, name, opts in objects_to_show]
    names = [name for obj, name, opts in objects_to_show]
    colors = [opts.get("color", "gray") for obj, name, opts in objects_to_show]
    alphas = [opts.get("alpha", 1.0) for obj, name, opts in objects_to_show]
    
    show(*shapes, names=names, colors=colors, alphas=alphas)
    
    if verbose:
        print(f"\nVisualization offsets ({offset_axis} axis):")
        print(f"  CAD geometry at {cad_offset}")
        print(f"  Mesh geometry at {mesh_offset}")
        print(f"  Contact surfaces at {contact_offset}")
    
    return meshing_result


def run_fea_analysis(
    frame: TimberFrame,
    output_dir: Path,
    title: str,
    additional_loads: Optional[List[LoadBC]] = None,
    mesh_size: float = 150.0,
    mesh_size_fine: float = 40.0,
    reference_length: Optional[float] = None,
    verbose: bool = True,
):
    """Run FEA analysis and print results.
    
    Args:
        frame: TimberFrame with members added (and optionally pre-meshed)
        output_dir: Directory for output files
        title: Title for the analysis printout
        additional_loads: Optional list of LoadBC objects
        mesh_size: Base mesh element size
        mesh_size_fine: Fine mesh size at contacts
        reference_length: Reference length for L/300 check (e.g., beam span)
        verbose: Print progress
        
    Returns:
        AssemblyResult from frame.analyze()
    """
    if verbose:
        print("=" * 60)
        print(title)
        print("=" * 60)
        print()
    
    result = frame.analyze(
        additional_loads=additional_loads or [],
        output_dir=output_dir,
        mesh_size=mesh_size,
        mesh_size_fine=mesh_size_fine,
        verbose=verbose,
    )
    
    if verbose:
        print("\n" + "=" * 60)
        print("ANALYSIS SUMMARY")
        print("=" * 60)
        print(f"Success: {result.success}")
        print(f"Mesh: {result.num_nodes} nodes, {result.num_elements} elements")
        
        if result.success:
            print(f"\nDeflection Results:")
            print(f"  Max total: {result.fea_results.max_displacement:.4f} mm")
            print(f"  Max Z: {result.fea_results.max_uz:.4f} mm")
            
            if reference_length:
                limit = reference_length / 300  # L/300
                status = "PASS ✓" if abs(result.fea_results.max_uz) < limit else "FAIL ✗"
                print(f"  Limit (L/300): {limit:.2f} mm")
                print(f"  Status: {status}")
        
        print("=" * 60)
    
    return result


def visualize_fea_results(
    result,
    output_dir: Path,
    original_shapes: List[Tuple[Part, str, str]],
    scale: float = 5.0,
):
    """Visualize FEA results with deformed shape.
    
    Args:
        result: AssemblyResult from frame.analyze()
        output_dir: Directory containing mesh.inp and analysis.frd
        original_shapes: List of (shape, name, color) tuples
        scale: Displacement scale factor for visualization
    """
    if result.success:
        show_fea_results(
            mesh_file=str(output_dir / "mesh.inp"),
            frd_file=str(output_dir / "analysis.frd"),
            scale=scale,
            original_shapes=original_shapes,
            deformed_color="red",
            original_alpha=0.3,
        )
