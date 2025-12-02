# %%
"""FEA analysis of a single bent frame WITHOUT braces.

A bent is the basic unit of a timber frame:
- 2 posts (vertical)
- 1 beam (horizontal, connecting post tops)
"""

from pathlib import Path
from ocp_vscode import reset_show, show_object

from timber_joints.alignment import build_complete_bent
from timber_joints.fea import TimberFrame, LoadBC, export_fea_combined_gltf

from fea_utils import visualize_frame_with_mesh, run_fea_analysis

reset_show()

# %%
# Build bent frame WITHOUT braces
bent = build_complete_bent(
    post_height=3000,
    post_section=150,
    beam_length=5000,
    brace_params=None,  # No braces
)

left_post = bent.left_post
right_post = bent.right_post
beam = bent.beam

# Create FEA frame
frame = TimberFrame()
frame.add_member("left_post", left_post)
frame.add_member("right_post", right_post)
frame.add_member("beam", beam)

# %%
# Visualize CAD, mesh, and contacts
cad_shapes = [
    (left_post, "Left Post", "sienna"),
    (right_post, "Right Post", "sienna"),
    (beam, "Beam", "burlywood"),
]

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

main_load = LoadBC("main_load", main_load_filter, dof=3, total_load=-50000.0)  # 5 tonne down

output_dir = Path(__file__).parent / "fea_single_bent_output"

print("Loads:")
print("  - Main load: 5000 kg (5 tonne) at beam midspan")
print("  - Self-weight: automatic")
print()

result = run_fea_analysis(
    frame,
    output_dir,
    title="SINGLE BENT FRAME FEA ANALYSIS (NO BRACES)",
    additional_loads=[main_load],
    reference_length=5000.0,  # beam span
)

# %%
# Export FEA results to GLTF with limit-based colormap
# - Displacement limit: 5000/300 = 16.7mm (L/300)
# - Stress limit: 24 MPa (C24 f_m_k)
if result.success:
    export_fea_combined_gltf(
        output_dir=output_dir,
        scale=1.0,
        reference_length=5000.0,
    )
