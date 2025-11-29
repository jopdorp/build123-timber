"""Export adapters for timber frames (IFC, visualization)."""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import numpy as np

from timber_joints.frame import TimberFrame, Element, Role


# Role to IFC class mapping
ROLE_TO_IFC = {
    Role.POST: "IfcColumn",
    Role.BEAM: "IfcBeam",
    Role.GIRT: "IfcBeam",
    Role.RAFTER: "IfcBeam",
    Role.STUD: "IfcColumn",
    Role.BRACE: "IfcMember",
    Role.PLATE: "IfcBeam",
    Role.SILL: "IfcBeam",
    Role.PEG: "IfcMechanicalFastener",
    Role.WEDGE: "IfcMechanicalFastener",
}


def export_frame_to_ifc(
    frame: TimberFrame,
    filename: str,
    project_name: str = "Timber Frame",
):
    """Export a timber frame to IFC format.
    
    Args:
        frame: The timber frame assembly
        filename: Output IFC file path
        project_name: Name for the IFC project
    """
    try:
        import ifcopenshell
        import ifcopenshell.api
    except ImportError:
        raise ImportError("ifcopenshell not installed. Run: pip install ifcopenshell")
    
    # Create IFC file
    ifc = ifcopenshell.api.run("project.create_file", version="IFC4")
    
    # Project structure
    project = ifcopenshell.api.run("root.create_entity", ifc,
                                    ifc_class="IfcProject", name=project_name)
    
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
    
    # Export each element
    for name, element in frame.elements.items():
        ifc_class = ROLE_TO_IFC.get(element.role, "IfcMember")
        
        ifc_elem = ifcopenshell.api.run("root.create_entity", ifc,
                                         ifc_class=ifc_class, name=name)
        
        ifcopenshell.api.run("spatial.assign_container", ifc,
                             relating_structure=storey, products=[ifc_elem])
        
        # Simple extruded geometry
        beam = element.beam
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
        ifc_elem.Representation = prod_shape
        
        # Placement from element location
        loc = element.location
        x, y, z = loc.position.X, loc.position.Y, loc.position.Z
        
        # Build transformation matrix
        matrix = np.eye(4)
        matrix[0:3, 3] = [x, y, z]
        
        # Apply rotation if present
        if element.rotation:
            axis, angle = element.rotation
            rad = np.radians(angle)
            c, s = np.cos(rad), np.sin(rad)
            if axis.direction.Z == 1:  # Z axis
                rot = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])
            elif axis.direction.Y == 1:  # Y axis
                rot = np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
            else:  # X axis
                rot = np.array([[1, 0, 0], [0, c, -s], [0, s, c]])
            matrix[0:3, 0:3] = rot
        
        ifcopenshell.api.run("geometry.edit_object_placement", ifc,
                             product=ifc_elem, matrix=matrix)
    
    ifc.write(filename)
    print(f"IFC exported: {filename}")
    print(f"  {len(frame.elements)} elements")


def show_frame(
    frame: TimberFrame,
    colors: dict[Role, str] = None,
):
    """Display a timber frame in OCP CAD Viewer.
    
    Args:
        frame: The timber frame to display
        colors: Optional dict mapping roles to colors
    """
    try:
        from ocp_vscode import show
    except ImportError:
        print("ocp_vscode not available for visualization")
        return
    
    # Default colors by role
    default_colors = {
        Role.POST: "saddlebrown",
        Role.BEAM: "peru",
        Role.GIRT: "burlywood",
        Role.RAFTER: "tan",
        Role.STUD: "wheat",
        Role.BRACE: "orange",
        Role.PLATE: "chocolate",
        Role.SILL: "sienna",
        Role.PEG: "darkgoldenrod",
        Role.WEDGE: "goldenrod",
    }
    colors = colors or default_colors
    
    # Build list of (shape, name, color) for display
    parts = []
    for name, element in frame.elements.items():
        color = colors.get(element.role, "gray")
        parts.append((element.shape, name, color))
    
    # Show combined shape
    show(frame.shape)
    print(f"Displayed {len(frame.elements)} elements")


def export_beam_schedule(frame: TimberFrame, filename: str = None) -> str:
    """Generate a beam schedule (cut list) for the frame.
    
    Args:
        frame: The timber frame
        filename: Optional file to write schedule to
        
    Returns:
        Schedule as formatted string
    """
    lines = [
        "TIMBER FRAME SCHEDULE",
        "=" * 60,
        f"Frame: {frame.name}",
        "",
        f"{'Name':<15} {'Role':<10} {'L':>8} {'W':>6} {'H':>6}  {'Volume':>10}",
        "-" * 60,
    ]
    
    total_volume = 0
    for name, elem in sorted(frame.elements.items()):
        b = elem.beam
        vol = b.length * b.width * b.height / 1e9  # mm³ to m³
        total_volume += vol
        lines.append(
            f"{name:<15} {elem.role.name:<10} {b.length:>8.0f} {b.width:>6.0f} {b.height:>6.0f}  {vol:>10.4f} m³"
        )
    
    lines.extend([
        "-" * 60,
        f"{'TOTAL':<15} {'':<10} {'':>8} {'':>6} {'':>6}  {total_volume:>10.4f} m³",
        f"Elements: {len(frame.elements)}",
    ])
    
    schedule = "\n".join(lines)
    
    if filename:
        Path(filename).write_text(schedule)
        print(f"Schedule written: {filename}")
    
    return schedule
