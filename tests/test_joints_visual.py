# %%
# 1. Basic Timber - verify origin and alignment before testing cuts
# Expected: Corner at (0,0,0), extends to (1000, 50, 100)

from ocp_vscode import show_object
from build123_timber import Timber

timber = Timber.beam(length=1000, width=50, height=100)
bbox = timber.blank.bounding_box()

print("=== 1. Basic Timber (reference) ===")
print(f"BBox: X={bbox.min.X:.0f}-{bbox.max.X:.0f}, Y={bbox.min.Y:.0f}-{bbox.max.Y:.0f}, Z={bbox.min.Z:.0f}-{bbox.max.Z:.0f}")

show_object(timber.blank, name="Timber", options={"color": "orange"})

# %%
# 2. L-lap main cut - single timber with cut, then applied result
# Unit test: test_l_lap_joint_main_cut_position validates X=320-400, Y=0-80, Z=40-80

from ocp_vscode import show_object
from build123d import Location
from test_joints import create_l_lap_joint_main_cut, create_l_lap_joint_applied

# Get the cut geometry (before applying)
main, cut, _ = create_l_lap_joint_main_cut()

# Get the result after applying
main_applied, _, _ = create_l_lap_joint_applied()

cut_bbox = cut.bounding_box()
volume_removed = main_applied.blank.volume - main_applied.shape.volume

print("=== 2. L-lap main cut ===")
print(f"Cut bbox X: {cut_bbox.min.X:.0f}-{cut_bbox.max.X:.0f} (expected: 320-400)")
print(f"Cut bbox Y: {cut_bbox.min.Y:.0f}-{cut_bbox.max.Y:.0f} (expected: 0-80)")
print(f"Cut bbox Z: {cut_bbox.min.Z:.0f}-{cut_bbox.max.Z:.0f} (expected: 40-80)")
print(f"Volume removed: {volume_removed:.0f} (expected: 256000)")

# Left side: uncut blank with cut shape
show_object(main.blank, name="Main blank", options={"color": "orange", "alpha": 0.5})
show_object(cut, name="Main cut", options={"color": "red"})

# Right side: applied result (offset in X)
show_object(main_applied.shape.moved(Location((500, 0, 0))), name="Main result", options={"color": "orange"})

# %%
# 3. LLapJoint - uncut blanks with cuts, then applied result
# Unit tests validate both cuts at END of their respective timbers

from ocp_vscode import show_object
from build123d import Location
from test_joints import create_l_lap_joint_main_cut, create_l_lap_joint_applied

# Get uncut blanks and cut shapes
main, main_cut, joint = create_l_lap_joint_main_cut()
cross = joint.cross
cross_cut = joint.get_cross_feature()

# Get applied result (separate instances)
main_applied, cross_applied, _ = create_l_lap_joint_applied()

main_cut_bbox = main_cut.bounding_box()
cross_cut_bbox = cross_cut.bounding_box()
main_removed = main_applied.blank.volume - main_applied.shape.volume
cross_removed = cross_applied.blank.volume - cross_applied.shape.volume

print("=== 3. LLapJoint ===")
print(f"Main cut X: {main_cut_bbox.min.X:.0f}-{main_cut_bbox.max.X:.0f} (expected: 320-400)")
print(f"Cross cut X: {cross_cut_bbox.min.X:.0f}-{cross_cut_bbox.max.X:.0f} (expected: 220-300)")
print(f"Main volume removed: {main_removed:.0f} (expected: 256000)")
print(f"Cross volume removed: {cross_removed:.0f} (expected: 256000)")

# Left side: uncut blanks with cut shapes (offset in Y)
show_object(main.blank, name="Main blank", options={"color": "orange", "alpha": 0.5})
show_object(cross.blank.moved(Location((0, 150, 0))), name="Cross blank", options={"color": "blue", "alpha": 0.5})
show_object(main_cut, name="Main cut", options={"color": "red"})
show_object(cross_cut.moved(Location((0, 150, 0))), name="Cross cut", options={"color": "darkblue"})

# Right side: applied result (offset in X)
show_object(main_applied.shape.moved(Location((500, 0, 0))), name="Main result", options={"color": "orange"})
show_object(cross_applied.shape.moved(Location((500, 150, 0))), name="Cross result", options={"color": "blue"})

# %%
# 4. TLapJoint - uncut blanks with cuts, then applied result
# Unit tests validate: main cut centered (160-240), cross cut centered (110-190)

from ocp_vscode import show_object
from build123d import Location
from test_joints import create_t_lap_joint_cuts, create_t_lap_joint_applied

# Get uncut blanks and cut shapes
main, cross, main_cut, cross_cut, _ = create_t_lap_joint_cuts()

# Get applied result (separate instances)
main_applied, cross_applied, _ = create_t_lap_joint_applied()

main_bbox = main_cut.bounding_box()
cross_bbox = cross_cut.bounding_box()
main_removed = main_applied.blank.volume - main_applied.shape.volume
cross_removed = cross_applied.blank.volume - cross_applied.shape.volume

print("=== 4. TLapJoint ===")
print(f"Main cut X: {main_bbox.min.X:.0f}-{main_bbox.max.X:.0f} (expected: 160-240)")
print(f"Cross cut X: {cross_bbox.min.X:.0f}-{cross_bbox.max.X:.0f} (expected: 220-300)")
print(f"Main volume removed: {main_removed:.0f}")
print(f"Cross volume removed: {cross_removed:.0f}")

# Left side: uncut blanks with cut shapes (offset in Y)
show_object(main.blank, name="Main blank", options={"color": "orange", "alpha": 0.5})
show_object(cross.blank.moved(Location((0, 150, 0))), name="Cross blank", options={"color": "blue", "alpha": 0.5})
show_object(main_cut, name="Main cut", options={"color": "red"})
show_object(cross_cut.moved(Location((0, 150, 0))), name="Cross cut", options={"color": "darkblue"})

# Right side: applied result (offset in X)
show_object(main_applied.shape.moved(Location((500, 0, 0))), name="Main result", options={"color": "orange"})
show_object(cross_applied.shape.moved(Location((500, 150, 0))), name="Cross result", options={"color": "blue"})

# %%
# 5. XLapJoint - uncut blanks with cuts, then applied result
# Unit tests validate: both cuts centered (160-240)

from ocp_vscode import show_object
from build123d import Location
from test_joints import create_x_lap_joint_cuts, create_x_lap_joint_applied

# Get uncut blanks and cut shapes
main, cross, main_cut, cross_cut, _ = create_x_lap_joint_cuts()

# Get applied result (separate instances)
main_applied, cross_applied, _ = create_x_lap_joint_applied()

main_bbox = main_cut.bounding_box()
cross_bbox = cross_cut.bounding_box()
main_removed = main_applied.blank.volume - main_applied.shape.volume
cross_removed = cross_applied.blank.volume - cross_applied.shape.volume

print("=== 5. XLapJoint ===")
print(f"Main cut X: {main_bbox.min.X:.0f}-{main_bbox.max.X:.0f} (expected: 160-240)")
print(f"Cross cut X: {cross_bbox.min.X:.0f}-{cross_bbox.max.X:.0f} (expected: 160-240)")
print(f"Main volume removed: {main_removed:.0f}")
print(f"Cross volume removed: {cross_removed:.0f}")

# Left side: uncut blanks with cut shapes (offset in Y)
show_object(main.blank, name="Main blank", options={"color": "orange", "alpha": 0.5})
show_object(cross.blank.moved(Location((0, 150, 0))), name="Cross blank", options={"color": "blue", "alpha": 0.5})
show_object(main_cut, name="Main cut", options={"color": "red"})
show_object(cross_cut.moved(Location((0, 150, 0))), name="Cross cut", options={"color": "darkblue"})

# Right side: applied result (offset in X)
show_object(main_applied.shape.moved(Location((500, 0, 0))), name="Main result", options={"color": "orange"})
show_object(cross_applied.shape.moved(Location((500, 150, 0))), name="Cross result", options={"color": "blue"})

# %%
# 6. TenonMortiseJoint (basic) - mortise in main, tenon is full cross-section (no shoulders)
# Main gets mortise (rectangular hole), cross timber end IS the tenon

from ocp_vscode import show_object
from build123d import Location
from test_joints import create_tenon_mortise_joint_cuts, create_tenon_mortise_joint_applied

# Get uncut blanks and cut shapes
main, cross, main_cut, cross_cut, joint = create_tenon_mortise_joint_cuts()

# Get applied result (separate instances)
main_applied, cross_applied, _ = create_tenon_mortise_joint_applied()

main_bbox = main_cut.bounding_box()
main_removed = main_applied.blank.volume - main_applied.shape.volume
cross_removed = cross_applied.blank.volume - cross_applied.shape.volume

# Expected mortise position: centered at X=200, Y from 0 to ~50.5 (depth), Z centered
expected_mortise_width = joint.tenon_width + joint.clearance
expected_x_min = 200 - expected_mortise_width / 2
expected_x_max = 200 + expected_mortise_width / 2

print("=== 6. TenonMortiseJoint (basic - no shoulders) ===")
print(f"Mortise X: {main_bbox.min.X:.1f}-{main_bbox.max.X:.1f} (expected: {expected_x_min:.1f}-{expected_x_max:.1f})")
print(f"Mortise Y: {main_bbox.min.Y:.1f}-{main_bbox.max.Y:.1f} (depth into timber)")
print(f"Main volume removed (mortise): {main_removed:.0f}")
print(f"Cross volume removed: {cross_removed:.0f} (expected: 0 - no shoulders)")
print(f"Tenon: {joint.tenon_length}L × {joint.tenon_width:.0f}W × {joint.tenon_height:.0f}H (full cross-section)")
print(f"Cross cut: {cross_cut}")  # Should be None

# Left side: uncut blanks with cut shape (offset in Y)
show_object(main.blank, name="Main blank", options={"color": "orange", "alpha": 0.5})
show_object(cross.blank.moved(Location((0, 150, 0))), name="Cross blank (=tenon)", options={"color": "blue", "alpha": 0.5})
show_object(main_cut, name="Main cut (mortise)", options={"color": "red"})

# Right side: applied result (offset in X)
show_object(main_applied.shape.moved(Location((500, 0, 0))), name="Main result", options={"color": "orange"})
show_object(cross_applied.shape.moved(Location((500, 150, 0))), name="Cross result (unchanged)", options={"color": "blue"})

# %%
# 7. HousedTenonMortiseJoint - housing + mortise in main, shoulder + tenon on cross
# Main gets housing (shallow recess) + mortise (deeper hole)
# Cross gets shoulder (step) + tenon (projecting piece)

from ocp_vscode import show_object
from build123d import Location
from test_joints import create_housed_tenon_mortise_joint_cuts, create_housed_tenon_mortise_joint_applied

# Get uncut blanks and cut shapes
main, cross, main_cut, cross_cut, joint = create_housed_tenon_mortise_joint_cuts()

# Get applied result (separate instances)
main_applied, cross_applied, _ = create_housed_tenon_mortise_joint_applied()

main_bbox = main_cut.bounding_box()
cross_bbox = cross_cut.bounding_box()
main_removed = main_applied.blank.volume - main_applied.shape.volume
cross_removed = cross_applied.blank.volume - cross_applied.shape.volume

print("=== 7. HousedTenonMortiseJoint ===")
print(f"Housing+Mortise X: {main_bbox.min.X:.1f}-{main_bbox.max.X:.1f}")
print(f"Housing+Mortise Y: {main_bbox.min.Y:.1f}-{main_bbox.max.Y:.1f} (depth into main)")
print(f"Housing+Mortise Z: {main_bbox.min.Z:.1f}-{main_bbox.max.Z:.1f}")
print(f"Main volume removed: {main_removed:.0f}")
print(f"Shoulder+Tenon X: {cross_bbox.min.X:.1f}-{cross_bbox.max.X:.1f}")
print(f"Cross volume removed: {cross_removed:.0f}")
print(f"Tenon: {joint.tenon_length}L × {joint.tenon_width:.1f}W × {joint.tenon_height:.1f}H")
print(f"Housing depth: {joint.housing_depth}mm")

# Left side: uncut blanks with cut shapes (offset in Y)
show_object(main.blank, name="Main blank (yellow)", options={"color": "yellow", "alpha": 0.5})
show_object(cross.blank.moved(Location((0, 200, 0))), name="Cross blank", options={"color": "blue", "alpha": 0.5})
show_object(main_cut, name="Main cut (housing+mortise)", options={"color": "red"})
show_object(cross_cut.moved(Location((0, 200, 0))), name="Cross cut (shoulder+tenon)", options={"color": "darkblue"})

# Right side: applied result (offset in X)
show_object(main_applied.shape.moved(Location((500, 0, 0))), name="Main result", options={"color": "yellow"})
show_object(cross_applied.shape.moved(Location((500, 200, 0))), name="Cross result", options={"color": "blue"})

# %%
