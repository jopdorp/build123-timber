"""Visual test for brace tenon cuts."""

import sys
sys.path.insert(0, "src")

from build123d import Part, Axis, Location, Box, export_step
from timber_joints.beam import Beam
from timber_joints.brace_tenon import BraceTenon
from timber_joints.alignment import (
    make_post_vertical,
    build_complete_bent,
    create_brace_for_bent,
)
from pathlib import Path
from ocp_vscode import reset_show, show_object

reset_show()

# Create output directory
output_dir = Path("brace_tenon_test_output")
output_dir.mkdir(exist_ok=True)


def test_brace_tenon_45_degrees():
    """Test brace tenon for 45 degree brace."""
    brace_length = 500
    brace_section = 100
    
    brace = Beam(length=brace_length, width=brace_section, height=brace_section)
    
    tenon_width = brace_section / 3
    tenon_length = 60
    
    brace_with_tenon = BraceTenon(
        brace=brace.shape,
        tenon_width=tenon_width,
        tenon_length=tenon_length,
        brace_angle=45,
        at_start=False,
    )
    
    result = brace_with_tenon.shape
    show_object(result, name="Brace Tenon 45°", options={"color": "orange"})
    export_step(result, str(output_dir / "brace_tenon_45.step"))
    
    print(f"✓ Brace tenon 45°: {brace_with_tenon}")
    return result


def test_brace_tenon_30_degrees():
    """Test brace tenon for 30 degree brace."""
    brace_length = 500
    brace_section = 100
    
    brace = Beam(length=brace_length, width=brace_section, height=brace_section)
    
    tenon_width = brace_section / 3
    tenon_length = 60
    
    brace_with_tenon = BraceTenon(
        brace=brace.shape,
        tenon_width=tenon_width,
        tenon_length=tenon_length,
        brace_angle=30,
        at_start=False,
    )
    
    result = brace_with_tenon.shape
    result = result.move(Location((0, 150, 0)))
    show_object(result, name="Brace Tenon 30°", options={"color": "darkorange"})
    export_step(result, str(output_dir / "brace_tenon_30.step"))
    
    print(f"✓ Brace tenon 30°: {brace_with_tenon}")
    return result


def test_brace_tenon_60_degrees():
    """Test brace tenon for 60 degree brace."""
    brace_length = 500
    brace_section = 100
    
    brace = Beam(length=brace_length, width=brace_section, height=brace_section)
    
    tenon_width = brace_section / 3
    tenon_length = 60
    
    brace_with_tenon = BraceTenon(
        brace=brace.shape,
        tenon_width=tenon_width,
        tenon_length=tenon_length,
        brace_angle=60,
        at_start=True,
    )
    
    result = brace_with_tenon.shape
    result = result.move(Location((0, 300, 0)))
    show_object(result, name="Brace Tenon 60°", options={"color": "chocolate"})
    export_step(result, str(output_dir / "brace_tenon_60.step"))
    
    print(f"✓ Brace tenon 60°: {brace_with_tenon}")
    return result


def test_brace_tenon_at_start():
    """Test brace tenon at start (post end)."""
    brace_length = 500
    brace_section = 100
    
    brace = Beam(length=brace_length, width=brace_section, height=brace_section)
    
    tenon_width = brace_section / 3
    tenon_length = 60
    
    brace_with_tenon = BraceTenon(
        brace=brace.shape,
        tenon_width=tenon_width,
        tenon_length=tenon_length,
        brace_angle=45,
        at_start=True,
    )
    
    result = brace_with_tenon.shape
    result = result.move(Location((0, 450, 0)))
    show_object(result, name="Brace Tenon at Start", options={"color": "sienna"})
    export_step(result, str(output_dir / "brace_tenon_at_start.step"))
    
    print(f"✓ Brace tenon at start: {brace_with_tenon}")
    return result


def test_brace_both_tenons():
    """Test brace with tenons at both ends."""
    brace_length = 500
    brace_section = 100
    
    brace = Beam(length=brace_length, width=brace_section, height=brace_section)
    
    tenon_width = brace_section / 3
    tenon_length = 60
    
    # First apply bottom tenon (post end)
    brace_with_bottom = BraceTenon(
        brace=brace.shape,
        tenon_width=tenon_width,
        tenon_length=tenon_length,
        brace_angle=45,
        at_start=True,
    )
    
    # Then apply top tenon (beam end)
    brace_with_both = BraceTenon(
        brace=brace_with_bottom.shape,
        tenon_width=tenon_width,
        tenon_length=tenon_length,
        brace_angle=45,
        at_start=False,
    )
    
    result = brace_with_both.shape
    result = result.move(Location((0, 600, 0)))
    show_object(result, name="Both Tenons", options={"color": "peru"})
    export_step(result, str(output_dir / "brace_both_tenons.step"))
    
    print("✓ Brace with both tenons created")
    return result


if __name__ == "__main__":
    test_brace_tenon_45_degrees()
    test_brace_tenon_30_degrees()
    test_brace_tenon_60_degrees()
    test_brace_tenon_at_start()
    test_brace_both_tenons()
    
    print("\n✅ Brace tenon tests complete - check the OCP viewer!")
