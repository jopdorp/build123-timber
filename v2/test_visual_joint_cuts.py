# %%
# 1. Plain Beam (reference)
# Expected: Box at origin extending in +X, +Y, +Z

from ocp_vscode import show_object
from build123d import Location
from timber_joints.beam import Beam

beam = Beam(length=300, width=100, height=100)
bbox = beam.shape.bounding_box()

print("=== 1. Plain Beam (reference) ===")
print(f"BBox: X={bbox.min.X:.0f}-{bbox.max.X:.0f}, Y={bbox.min.Y:.0f}-{bbox.max.Y:.0f}, Z={bbox.min.Z:.0f}-{bbox.max.Z:.0f}")

show_object(beam.shape.move(Location((0, 0, 300))), name="Plain Beam", options={"color": "orange"})

# %%
# 2. Lap Joint - positive/inserting end
# Beam with half-depth cut at the end, ready to insert into matching cut

from ocp_vscode import show_object
from build123d import Align, Box, Location
from timber_joints.beam import Beam
from timber_joints.lap_joint import LapJoint

beam = Beam(length=300, width=100, height=100)
lap = LapJoint(
    beam=beam,
    cut_depth=50,  # Half the height
    cut_length=100,
    from_top=True
)

print("=== 2. Lap Joint (inserting end) ===")
print(f"Cut depth: {lap.cut_depth}mm (from top)")
print(f"Cut length: {lap.cut_length}mm")

# Show cut shape on left, result on right
show_object(beam.shape, name="Beam blank", options={"color": "orange", "alpha": 0.3})
show_object(lap.shape.move(Location((400, 0, 0))), name="Lap Joint result", options={"color": "green"})

# %%
# 3. Basic Tenon - centered projection at beam end
# Classic mortise-tenon proportions: 1/3 width, 2/3 height

from ocp_vscode import show_object
from build123d import Location
from timber_joints.beam import Beam
from timber_joints.tenon import Tenon

beam = Beam(length=300, width=100, height=100)
tenon = Tenon(
    beam=beam,
    tenon_width=100 / 3,   # ~33mm (classic 1/3 width)
    tenon_height=100 * 2 / 3,  # ~67mm (classic 2/3 height)
    tenon_length=50,
    at_start=False
)

print("=== 3. Basic Tenon ===")
print(f"Tenon: {tenon.tenon_length}L × {tenon.tenon_width:.1f}W × {tenon.tenon_height:.1f}H")

show_object(beam.shape.move(Location((0, -300, 0))), name="Beam blank", options={"color": "orange", "alpha": 0.3})
show_object(tenon.shape.move(Location((400, -300, 0))), name="Tenon result", options={"color": "blue"})

# %%
# 4. Shouldered Tenon - tenon with angled/triangular shoulder
# The angled shoulder creates a wedge-shaped bearing surface

from ocp_vscode import show_object
from build123d import Location
from timber_joints.beam import Beam
from timber_joints.shouldered_tenon import ShoulderedTenon

beam = Beam(length=300, width=100, height=100)
shouldered = ShoulderedTenon(
    beam=beam,
    tenon_width=100 / 3,
    tenon_height=100 * 2 / 3,
    tenon_length=40,
    shoulder_depth=20,
    at_start=False
)

print("=== 4. Shouldered Tenon (angled) ===")
print(f"Tenon: {shouldered.tenon_length}L × {shouldered.tenon_width:.1f}W × {shouldered.tenon_height:.1f}H")
print(f"Shoulder depth: {shouldered.shoulder_depth}mm")

show_object(beam.shape.move(Location((0, -600, 0))), name="Beam blank", options={"color": "orange", "alpha": 0.3})
show_object(shouldered.shape.move(Location((400, -600, 0))), name="Shouldered Tenon result", options={"color": "purple"})

# %%
# 5. Dovetail Insert - tapered projection
# Widens toward the base for mechanical locking

from ocp_vscode import show_object
from build123d import Location
from timber_joints.beam import Beam
from timber_joints.dovetail import DovetailInsert

beam = Beam(length=300, width=100, height=100)
dovetail = DovetailInsert(
    beam=beam,
    dovetail_width=100 / 3,
    dovetail_height=50,
    dovetail_length=50,
    cone_angle=10.0,
    at_start=False
)

narrow, wide = dovetail._get_widths()

print("=== 5. Dovetail Insert ===")
print(f"Dovetail: {dovetail.dovetail_length}L × {dovetail.dovetail_height}H")
print(f"Width: {narrow:.1f}mm (tip) → {wide:.1f}mm (base)")
print(f"Cone angle: {dovetail.cone_angle}°")

show_object(beam.shape.move(Location((0, 300, 0))), name="Beam blank", options={"color": "orange", "alpha": 0.3})
show_object(dovetail.shape.move(Location((400, 300, 0))), name="Dovetail Insert result", options={"color": "red"})

# %%
# 6. Lap X-Section - lap cut at a cross-section point along the beam
# Used for cross-lap joints where two beams intersect

from ocp_vscode import show_object
from build123d import Location
from timber_joints.beam import Beam
from timber_joints.lap_x_section import LapXSection

beam = Beam(length=300, width=100, height=100)
lap_x = LapXSection(
    beam=beam,
    cut_depth=50,  # Half depth
    cut_length=100,  # Width of intersecting beam
    x_position=150,  # Center of beam
    from_top=True
)

print("=== 6. Lap X-Section (cross lap) ===")
print(f"Cut depth: {lap_x.cut_depth}mm (from top)")
print(f"Cut length: {lap_x.cut_length}mm at X={lap_x.x_position}mm")

show_object(beam.shape.move(Location((0, 600, 0))), name="Beam blank", options={"color": "orange", "alpha": 0.3})
show_object(lap_x.shape.move(Location((400, 600, 0))), name="Lap X-Section result", options={"color": "cyan"})

# %%
# 7. Half-Dovetail - dovetail insert at top or bottom of beam
# Same as dovetail insert but positioned at top/bottom instead of centered

from ocp_vscode import show_object
from build123d import Location
from timber_joints.beam import Beam
from timber_joints.half_dovetail import HalfDovetail

beam = Beam(length=300, width=100, height=100)
half_dt = HalfDovetail(
    beam=beam,
    dovetail_width=40,
    dovetail_height=50,
    dovetail_length=70,
    dovetail_angle=20.0,
    at_start=False,
    at_top=True
)

print("=== 7. Half-Dovetail ===")
print(f"Dovetail: {half_dt.dovetail_length}L × {half_dt.dovetail_height}H at top")

show_object(beam.shape.move(Location((0, 900, 0))), name="Beam blank", options={"color": "orange", "alpha": 0.3})
show_object(half_dt.shape.move(Location((400, 900, 0))), name="Half-Dovetail result", options={"color": "magenta"})

# %%
