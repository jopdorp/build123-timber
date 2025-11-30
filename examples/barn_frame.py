"""Simple barn frame example demonstrating the structural integration."""

from timber_joints import (
    TimberFrame,
    Role,
    simple_bent,
    bay_frame,
    export_frame_to_ifc,
    show_frame,
    export_beam_schedule,
)


def create_simple_barn():
    """Create a simple barn frame structure.
    
    A 2-bay barn with:
    - 6 posts (3 bents)
    - 3 tie beams (connecting posts across width)
    - 4 girts (connecting posts along length)
    - Basic rafter structure
    
    Layout (top view):
    
        ═══════════════════════════
        ║           ║           ║
        ║   Bay 1   ║   Bay 2   ║
        ║           ║           ║
        ═══════════════════════════
    """
    # Dimensions (mm)
    width = 6000       # Barn width
    bay_depth = 4000   # Depth per bay
    post_height = 3000 # Wall height
    roof_peak = 2000   # Additional height to peak
    
    post_section = 200  # Post cross-section
    beam_section = 200  # Beam cross-section
    rafter_section = 150
    
    frame = TimberFrame("Simple Barn")
    ps = post_section
    
    # ==========================================================================
    # POSTS - 6 total (3 bents x 2 posts)
    # ==========================================================================
    for i, z_pos in enumerate([0, bay_depth, bay_depth * 2]):
        frame.add_post(f"post_left_{i}", post_height, ps, ps, x=0, y=z_pos, z=0)
        frame.add_post(f"post_right_{i}", post_height, ps, ps, x=width-ps, y=z_pos, z=0)
    
    # ==========================================================================
    # TIE BEAMS - Connect posts across width (3 total)
    # ==========================================================================
    for i, y_pos in enumerate([0, bay_depth, bay_depth * 2]):
        frame.add_beam(
            f"tie_beam_{i}", width, beam_section, beam_section,
            x=-ps, y=y_pos, z=post_height, role=Role.BEAM
        )
    
    # ==========================================================================
    # GIRTS - Connect posts along length (both sides)
    # ==========================================================================
    frame.add_beam("girt_left_0", bay_depth + ps, beam_section, beam_section,
                   x=-ps, y=0, z=post_height, role=Role.GIRT)
    frame.add_beam("girt_left_1", bay_depth + ps, beam_section, beam_section,
                   x=-ps, y=bay_depth, z=post_height, role=Role.GIRT)
    
    frame.add_beam("girt_right_0", bay_depth + ps, beam_section, beam_section,
                   x=width-2*ps, y=0, z=post_height, role=Role.GIRT)
    frame.add_beam("girt_right_1", bay_depth + ps, beam_section, beam_section,
                   x=width-2*ps, y=bay_depth, z=post_height, role=Role.GIRT)
    
    # ==========================================================================
    # RAFTERS - Simple gable roof (both slopes)
    # ==========================================================================
    rafter_length = 3500  # Approximate slope length
    rs = rafter_section
    
    # TODO: Add rafter rotation for slope
    # For now, using horizontal members as placeholders
    for i, y_pos in enumerate([0, bay_depth, bay_depth * 2]):
        frame.add_beam(
            f"ridge_{i}", rs, rs, rs,  # Ridge beam section (short)
            x=width/2 - rs/2, y=y_pos, z=post_height + roof_peak, role=Role.RAFTER
        )
    
    return frame


def create_bay_module():
    """Create a single bay using the bay_frame template."""
    return bay_frame(
        width=4000,
        depth=3000,
        height=3000,
        post_section=150,
        beam_section=150,
        name="Single Bay",
    )


def main():
    """Build and display barn examples."""
    print("=" * 60)
    print("TIMBER FRAME EXAMPLES")
    print("=" * 60)
    
    # Create simple barn
    barn = create_simple_barn()
    
    # Print schedule (cut list)
    schedule = export_beam_schedule(barn)
    print("\n" + schedule)
    
    # Export to IFC
    export_frame_to_ifc(barn, "simple_barn.ifc", project_name="Simple Barn Example")
    
    # Visualize
    print("\nDisplaying barn in viewer...")
    show_frame(barn)


if __name__ == "__main__":
    main()
