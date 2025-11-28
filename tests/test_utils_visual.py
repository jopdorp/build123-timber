"""Visual test utilities for displaying timber elements in OCP viewer."""

from ocp_vscode import show_object


def show_timber_with_axes(timber, title=""):
    """Display timber with local coordinate axes for orientation verification.
    
    Shows the timber shape along with its local coordinate system:
    - Red: X axis (along length)
    - Green: Y axis (along width)  
    - Blue: Z axis (along height)
    
    Prints dimensions, position, rotation, and bounding box info.
    """
    from build123_timber.alignment import show_lcs
    
    shape = timber.global_shape
    x_axis, y_axis, z_axis = show_lcs(timber, size=200)
    
    print(f"=== {title} ===")
    print(f"Dimensions: L={timber.length}, W={timber.width}, H={timber.height}")
    print(f"Position: {timber.location.position}")
    print(f"Rotation: {tuple(timber.location.orientation)}")
    
    bbox = shape.bounding_box()
    print(f"BBox size: X={bbox.size.X:.1f}, Y={bbox.size.Y:.1f}, Z={bbox.size.Z:.1f}")
    print(f"BBox min: ({bbox.min.X:.1f}, {bbox.min.Y:.1f}, {bbox.min.Z:.1f})")
    print(f"BBox max: ({bbox.max.X:.1f}, {bbox.max.Y:.1f}, {bbox.max.Z:.1f})")
    
    show_object(shape, name="timber", options={"color": "orange"})
    show_object(x_axis, name="X (red)", options={"color": "red"})
    show_object(y_axis, name="Y (green)", options={"color": "green"})
    show_object(z_axis, name="Z (blue)", options={"color": "blue"})
