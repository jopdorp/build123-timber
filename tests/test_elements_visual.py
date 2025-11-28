# %%
"""Visual validation for Timber element tests.

Run each cell to visually verify the test case in OCP viewer.
Each cell imports its own creation function so it can be run independently.
"""
from ocp_vscode import show_object, set_defaults, Camera
from build123d import Location, Vector, Edge
from test_utils_visual import show_timber_with_axes

set_defaults(
    reset_camera=Camera.CENTER,
    grid=(True, True, True),  # 0.1mm grid for seeing small differences
)


# %%
# 1. Basic Timber Creation
# Expected: A box 1000×50×100, corner at origin (0,0,0), extending in +X, +Y, +Z.

from test_elements import create_basic_timber

timber = create_basic_timber()
show_timber_with_axes(timber, "1. Basic Timber (1000×50×100)")

# %%
# 2. Timber with Float Dimensions - Comparison
# Expected: Two timbers side by side - integer dims vs float dims.
# The float timber (green) should be visibly slightly larger in all dimensions.

from test_elements import create_timber_with_floats

t_integer, t_float = create_timber_with_floats()

# Place them side by side for comparison
shape_int = t_integer.global_shape
shape_float = t_float.moved(Location((0, 100, 0))).global_shape  # Offset in Y to see both

print("=== 2. Float Precision Comparison ===")
print(f"Integer timber: {t_integer.length} × {t_integer.width} × {t_integer.height}")
print(f"Float timber:   {t_float.length} × {t_float.width} × {t_float.height}")

bbox_int = shape_int.bounding_box()
bbox_float = shape_float.bounding_box()
print(f"\nInteger BBox: X={bbox_int.size.X:.2f}, Y={bbox_int.size.Y:.2f}, Z={bbox_int.size.Z:.2f}")
print(f"Float BBox:   X={bbox_float.size.X:.2f}, Y={bbox_float.size.Y:.2f}, Z={bbox_float.size.Z:.2f}")
print(f"\nDifference:   X={bbox_float.size.X - bbox_int.size.X:.2f}, Y={bbox_float.size.Y - bbox_int.size.Y:.2f}, Z={bbox_float.size.Z - bbox_int.size.Z:.2f}")

show_object(shape_int, name="Integer (1000×50×100)", options={"color": "orange"})
show_object(shape_float, name="Float (1000.5×50.25×100.75)", options={"color": "green"})

# %%
# 3. Factory Methods
# ====================
# Expected orientations by axis:
#
# ALONG X (left-right, primary span):
# - BEAM: Horizontal spanning member - ORANGE
# - JOIST: Floor/ceiling framing - BLUE
#
# ALONG Y (front-back, perpendicular to span):
# - GIRT: Horizontal wall member between posts - PURPLE
# - PURLIN: Roof member perpendicular to rafters - CYAN
# - PLATE: Top/bottom plate in wall framing - PINK
#
# ALONG Z (up-down, vertical):
# - POST: Vertical column - BROWN
# - STUD: Vertical wall framing - GREEN
#
# PITCHED (angled):
# - RAFTER: Roof member at 30° pitch - RED

from test_elements import create_factory_methods_comparison
from ocp_vscode import show_object

timbers = create_factory_methods_comparison()

print("=== 3. Factory Methods Comparison ===")
print("\nALONG X (left-right):")
print(f"  Beam:   {timbers['beam'].length}×{timbers['beam'].width}×{timbers['beam'].height}")
print(f"  Joist:  {timbers['joist'].length}×{timbers['joist'].width}×{timbers['joist'].height}")
print("\nALONG Y (front-back):")
print(f"  Girt:   {timbers['girt'].length}×{timbers['girt'].width}×{timbers['girt'].height}")
print(f"  Purlin: {timbers['purlin'].length}×{timbers['purlin'].width}×{timbers['purlin'].height}")
print(f"  Plate:  {timbers['plate'].length}×{timbers['plate'].width}×{timbers['plate'].height}")
print("\nALONG Z (vertical):")
print(f"  Post:   {timbers['post'].length}×{timbers['post'].width}×{timbers['post'].height}")
print(f"  Stud:   {timbers['stud'].length}×{timbers['stud'].width}×{timbers['stud'].height}")
print("\nPITCHED (30° roof angle):")
print(f"  Rafter: {timbers['rafter'].length}×{timbers['rafter'].width}×{timbers['rafter'].height}")

show_object(timbers["beam"].global_shape, name="Beam", options={"color": "orange"})
show_object(timbers["joist"].global_shape, name="Joist", options={"color": "blue"})
show_object(timbers["girt"].global_shape, name="Girt", options={"color": "purple"})
show_object(timbers["purlin"].global_shape, name="Purlin", options={"color": "cyan"})
show_object(timbers["plate"].global_shape, name="Plate", options={"color": "pink"})
show_object(timbers["post"].global_shape, name="Post", options={"color": "brown"})
show_object(timbers["stud"].global_shape, name="Stud", options={"color": "green"})
show_object(timbers["rafter"].global_shape, name="Rafter", options={"color": "red"})

# %%
# 4. Timber at Origin (Default Location)
# Expected: Position: (0, 0, 0), BBox X: 0-1000, Y: 0-50, Z: 0-100

from test_elements import create_timber_at_origin
from test_utils_visual import show_timber_with_axes

timber = create_timber_at_origin()
show_timber_with_axes(timber, "4. Timber at Origin")

# %%
# 5. Timber Translated
# Expected: Position: (100, 200, 300), BBox shifted accordingly

from test_elements import create_timber_translated
from test_utils_visual import show_timber_with_axes

timber = create_timber_translated()
show_timber_with_axes(timber, "5. Timber Translated to (100, 200, 300)")

# %%
# 6. Timber Rotated 90° around Z
# Expected: Local X→World Y, Local Y→World -X, BBox size: X=50, Y=1000, Z=100

from test_elements import create_timber_rotated_z90
from test_utils_visual import show_timber_with_axes

timber = create_timber_rotated_z90()
show_timber_with_axes(timber, "6. Timber Rotated 90° Z")

# %%
# 7. Timber Rotated 90° around X
# Expected: Local Y→World Z, Local Z→World -Y, BBox size: X=1000, Y=100, Z=50

from test_elements import create_timber_rotated_x90
from test_utils_visual import show_timber_with_axes

timber = create_timber_rotated_x90()
show_timber_with_axes(timber, "7. Timber Rotated 90° X")

# %%
# 8. Timber Rotated 90° around Y
# Expected: Local X→World -Z, Local Z→World X, BBox size: X=100, Y=50, Z=1000

from test_elements import create_timber_rotated_y90
from test_utils_visual import show_timber_with_axes

timber = create_timber_rotated_y90()
show_timber_with_axes(timber, "8. Timber Rotated 90° Y")

# %%
# 9. Timber with Arbitrary Rotation
# Expected: Rotated (45°, 30°, 60°) - verify axes show correct orientation.

from test_elements import create_timber_rotated_arbitrary
from test_utils_visual import show_timber_with_axes

timber = create_timber_rotated_arbitrary()
show_timber_with_axes(timber, "9. Timber Rotated (45°, 30°, 60°)")

# %%
# 10. Timber Rotated and Translated
# Expected: First rotated 90° Z, then translated to (100, 200, 0)

from test_elements import create_timber_rotated_and_translated
from test_utils_visual import show_timber_with_axes

timber = create_timber_rotated_and_translated()
show_timber_with_axes(timber, "10. Timber Rotated 90° Z then Translated")

# %%
# 11. Timber with Cut Feature
# Expected: Timber 1000×50×100 with a 100×50×50 notch cut at origin corner.
# World-space validation:
# - Original volume: 1000×50×100 = 5,000,000 mm³
# - Cut volume: 100×50×50 = 250,000 mm³
# - Remaining volume: 4,750,000 mm³
# - Cut is full width (50) but only half height (50 of 100)
# - BBox unchanged: X: 0-1000, Y: 0-50, Z: 0-100 (material remains above cut)

from test_elements import create_timber_with_cut
from ocp_vscode import show_object

timber = create_timber_with_cut()

# World-space volume check
original_vol = timber.blank.volume
cut_vol = timber.blank.volume - timber.shape.volume
remaining_vol = timber.shape.volume
expected_cut_vol = 100 * 50 * 50  # 250,000

print("=== 11. Timber with Cut ===")
print(f"Original volume: {original_vol:.0f} mm³")
print(f"Cut volume: {cut_vol:.0f} mm³ (expected: {expected_cut_vol})")
print(f"Remaining volume: {remaining_vol:.0f} mm³")
print(f"Volume check: {'✓ PASS' if abs(cut_vol - expected_cut_vol) < 1 else '✗ FAIL'}")

# World-space bounding box (unchanged since cut doesn't remove full cross-section)
bbox = timber.shape.bounding_box()
print(f"\nBBox: X={bbox.min.X:.0f}-{bbox.max.X:.0f}, Y={bbox.min.Y:.0f}-{bbox.max.Y:.0f}, Z={bbox.min.Z:.0f}-{bbox.max.Z:.0f}")

show_object(timber.shape, name="Timber with cut", options={"color": "orange"})

# %%
