"""
Demonstration of rafter pair construction with tongue-and-fork joints.

This example shows just the rafters meeting at a ridge, without the full barn.
It helps visualize how the tongue-and-fork joint works at the peak and
the lap joints at the girt connections.
"""

from build123d import Box, Location, Align, Axis
from ocp_vscode import show_object

from timber_joints.alignment import RafterParams, build_rafter_pair


def main():
    """Create a simple rafter pair demo."""
    # Create simple mock girts as reference (just boxes representing girts)
    girt_length = 3000  # Y dimension
    girt_section = 150  # Width and height
    
    # Span between girts (inner edges)
    span = 4000
    
    # Left girt at negative X
    left_girt = Box(
        girt_section,  # X
        girt_length,   # Y  
        girt_section,  # Z
        align=(Align.MAX, Align.CENTER, Align.MIN),  # Inner edge at X=0
    ).move(Location((-span / 2, 0, 2500)))  # At 2.5m height
    
    # Right girt at positive X
    right_girt = Box(
        girt_section,
        girt_length,
        girt_section,
        align=(Align.MIN, Align.CENTER, Align.MIN),  # Inner edge at X=0
    ).move(Location((span / 2, 0, 2500)))
    
    print("Rafter Pair Demo")
    print("================")
    print(f"Span between girts: {span}mm")
    print(f"Girt section: {girt_section}mm")
    
    # Create rafter parameters
    rafter_params = RafterParams(
        section=100,
        pitch_angle=30,
        overhang=100,  # 10cm overhang past girt
        tongue_width_ratio=0.33,
        lap_depth_ratio=0.5,  # Half-lap joint (half the rafter depth)
    )
    
    print(f"\nRafter parameters:")
    print(f"  Section: {rafter_params.section}mm")
    print(f"  Pitch angle: {rafter_params.pitch_angle}°")
    print(f"  Overhang: {rafter_params.overhang}mm")
    print(f"  Tongue width: {rafter_params.get_tongue_width():.1f}mm")
    print(f"  Lap depth: {rafter_params.get_lap_depth():.1f}mm")
    
    # Build rafter pair at Y=0
    result = build_rafter_pair(
        left_girt=left_girt,
        right_girt=right_girt,
        y_position=0,
        rafter_params=rafter_params,
    )
    
    # Calculate some stats
    left_bbox = result.left_rafter.bounding_box()
    right_bbox = result.right_rafter.bounding_box()
    
    print(f"\nLeft rafter bounding box:")
    print(f"  X: {left_bbox.min.X:.1f} to {left_bbox.max.X:.1f}")
    print(f"  Y: {left_bbox.min.Y:.1f} to {left_bbox.max.Y:.1f}")
    print(f"  Z: {left_bbox.min.Z:.1f} to {left_bbox.max.Z:.1f}")
    
    print(f"\nRight rafter bounding box:")
    print(f"  X: {right_bbox.min.X:.1f} to {right_bbox.max.X:.1f}")
    print(f"  Y: {right_bbox.min.Y:.1f} to {right_bbox.max.Y:.1f}")
    print(f"  Z: {right_bbox.min.Z:.1f} to {right_bbox.max.Z:.1f}")
    
    # Check overlap at peak
    peak_overlap_x = left_bbox.max.X - right_bbox.min.X
    print(f"\nPeak overlap in X: {peak_overlap_x:.1f}mm")
    
    # Calculate expected shoulder position
    import math
    pitch_rad = math.radians(rafter_params.pitch_angle)
    shoulder_depth = rafter_params.section * math.tan(pitch_rad)
    tenon_length = rafter_params.section
    print(f"\nJoint geometry:")
    print(f"  Shoulder depth: {shoulder_depth:.1f}mm")
    print(f"  Tenon length: {tenon_length:.1f}mm")
    print(f"  Total joint extent: {shoulder_depth + tenon_length:.1f}mm")
    print(f"  Right rafter near face (min X at peak): {right_bbox.min.X:.1f}mm")
    print(f"  Left rafter far edge (max X): {left_bbox.max.X:.1f}mm")
    
    # Show the parts
    show_object(left_girt, name="left_girt", options={"color": "gray", "alpha": 0.3})
    show_object(right_girt, name="right_girt", options={"color": "gray", "alpha": 0.3})
    show_object(result.left_rafter, name="left_rafter", options={"color": "orange", "alpha": 0.7})
    show_object(result.right_rafter, name="right_rafter", options={"color": "brown", "alpha": 0.7})


if __name__ == "__main__":
    main()
