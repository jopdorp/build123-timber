# %%
"""FEA analysis of a single bent frame WITH braces.

A bent is the basic unit of a timber frame:
- 2 posts (vertical)
- 1 beam (horizontal, connecting post tops)
- 2 knee braces (diagonal, for lateral stability)
"""

from pathlib import Path
from ocp_vscode import reset_show, show_object

from timber_joints.alignment import JointParams, build_complete_bent, BraceParams
from timber_joints.fea import TimberFrame, LoadBC
from timber_joints.fea.frame import MemberType

from fea_utils import visualize_frame_with_mesh, run_fea_analysis, visualize_fea_results

reset_show()

# %%
# Build bent frame WITH braces
bent = build_complete_bent(
    post_height=3000,
    post_section=150,
    beam_length=5000,
    joint_params=JointParams(
        tenon_length=100,
        shoulder_depth=30,
        housing_depth=30,
    ),
    brace_params=BraceParams(
        length=2100,
        section=120,
        tenon_length=90,
        angle=40,
    ),
)

left_post = bent.left_post
right_post = bent.right_post
beam = bent.beam
braces = [b for b in [bent.brace_left, bent.brace_right] if b is not None]

# Create FEA frame
frame = TimberFrame()
frame.add_member("left_post", left_post, MemberType.POST)
frame.add_member("right_post", right_post, MemberType.POST)
frame.add_member("beam", beam, MemberType.BEAM)
for i, brace in enumerate(braces):
    frame.add_member(f"brace_{i}", brace, MemberType.BRACE)

# %%
# Visualize CAD, mesh, and contacts
cad_shapes = [
    (left_post, "Left Post", "sienna"),
    (right_post, "Right Post", "sienna"),
    (beam, "Beam", "burlywood"),
] + [(brace, f"Brace {i}", "orange") for i, brace in enumerate(braces)]

visualize_frame_with_mesh(
    frame, 
    cad_shapes,
    offset_axis="Y",
    cad_offset=0,
    mesh_offset=-500,
    contact_offset=500,
    element_size=100.0,       # Finer mesh for better accuracy
    element_size_fine=30.0,   # Finer contact refinement
)

# %%
# Run FEA analysis with 1 tonne load at beam midspan
beam_bbox = beam.bounding_box()
mid_x = (beam_bbox.min.X + beam_bbox.max.X) / 2
top_z = beam_bbox.max.Z

def main_load_filter(nid, x, y, z, part, mesh):
    # Small area load at beam midspan top - ~50mm x 50mm patch
    return (part == "beam" and 
            abs(x - mid_x) < 25.0 and 
            abs(z - top_z) < 25.0)

main_load = LoadBC("main_load", main_load_filter, dof=3, total_load=-20000.0)  # 2 tonne down

output_dir = Path(__file__).parent / "fea_single_bent_braced_output"

print("Loads:")
print("  - Main load: 2000 kg (2 tonne) at beam midspan")
print("  - Self-weight: automatic")
print()

result = run_fea_analysis(
    frame,
    output_dir,
    title="SINGLE BENT FRAME FEA ANALYSIS (WITH BRACES)",
    additional_loads=[main_load],
    reference_length=5000.0  # beam span
)

# Visualize FEA results with limit-based colormap
# - Displacement limit: 5000/300 = 16.7mm (L/300)
# - Stress limit: 24 MPa (C24 f_m_k)
visualize_fea_results(result, output_dir, cad_shapes, scale=1.0, reference_length=5000.0)

# %%
