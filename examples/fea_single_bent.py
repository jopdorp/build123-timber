# %%
"""FEA analysis of a single bent frame WITHOUT braces.

A bent is the basic unit of a timber frame:
- 2 posts (vertical)
- 1 beam (horizontal, connecting post tops)

This example uses different materials for posts (weaker C16) and beam (C24)
to demonstrate per-part material stress limits.
"""

from pathlib import Path
from ocp_vscode import reset_show, show_object

from timber_joints.alignment import build_complete_bent
from timber_joints.fea import (
    TimberFrame, 
    LoadBC, 
    export_fea_combined_gltf,
    CustomTimberMaterial,
    ElasticConstants,
    StrengthProperties,
    SoftwoodC24,
)

from fea_utils import visualize_frame_with_mesh, run_fea_analysis

reset_show()

# %%
# Define materials
# C16 softwood (weaker grade) for posts
C16_softwood = CustomTimberMaterial(
    _name="C16_Softwood",
    _elastic=ElasticConstants(
        E_L=8000.0,    # Lower modulus than C24
        E_R=270.0,
        E_T=270.0,
        G_LR=500.0,
        G_LT=500.0,
        G_RT=50.0,
        nu_LR=0.37,
        nu_LT=0.42,
        nu_RT=0.47,
    ),
    _density=310.0,
    _strength=StrengthProperties(
        f_m_k=16.0,    # Lower bending strength (16 MPa vs 24 MPa)
        f_t_0_k=10.0,
        f_t_90_k=0.3,
        f_c_0_k=17.0,
        f_c_90_k=2.2,
        f_v_k=3.2,
    ),
)

# C24 softwood for beam (default)
C24_softwood = SoftwoodC24()

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

# Create FEA frame with different materials
# Posts use weaker C16 softwood, beam uses stronger C24
frame = TimberFrame()
frame.add_member("left_post", left_post, material=C16_softwood)
frame.add_member("right_post", right_post, material=C16_softwood)
frame.add_member("beam", beam, material=C24_softwood)

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
