Quick Start
===========

Basic Joint Creation
--------------------

Create simple timber joints:

.. code-block:: python

   from timber_joints import Beam, Tenon, ShoulderedTenon
   from build123d import export_step
   
   # Create a beam
   beam = Beam(length=4000, width=200, height=150)
   
   # Create a centered tenon
   tenon = Tenon(
       width=120,
       height=80,
       length=100,
       parent_width=200,
       parent_height=150
   )
   
   # Create a shouldered tenon for load bearing
   shouldered = ShoulderedTenon(
       width=120,
       height=80,
       length=100,
       shoulder_depth=20,
       parent_width=200,
       parent_height=150
   )
   
   # Export for CNC
   export_step(tenon.shape, "tenon.step")

Aligning Beams on Posts
------------------------

Use alignment helpers to position beams correctly:

.. code-block:: python

   from timber_joints import Beam, align_beam_on_post
   
   # Create post and beam
   post = Beam(200, 200, 3000)
   beam = Beam(4000, 200, 150)
   
   # Align beam on top of post, centered
   beam_positioned = align_beam_on_post(
       beam=beam,
       post=post,
       offset_x=0,
       offset_y=0,
       beam_role="crossing"
   )

Building a Frame
----------------

Create a complete timber frame structure:

.. code-block:: python

   from timber_joints import TimberFrame, Role, show_frame
   
   # Create frame
   frame = TimberFrame("Simple Bent")
   
   # Add vertical posts
   frame.add_post("left_post", height=3000, width=200, depth=200, 
                  x=0, y=0, z=0)
   frame.add_post("right_post", height=3000, width=200, depth=200, 
                  x=4000, y=0, z=0)
   
   # Add horizontal tie beam
   frame.add_beam("tie_beam", length=4400, width=200, height=200,
                  x=-200, y=0, z=3000, role=Role.BEAM)
   
   # Visualize
   show_frame(frame)

High-Level Barn Frame
---------------------

Use the barn builder for complete structures:

.. code-block:: python

   from timber_joints import BarnConfig, BarnFrame, export_frame_to_ifc
   
   # Configure barn
   config = BarnConfig(
       width=6000,
       length=8000,
       wall_height=3000,
       roof_peak_height=2000,
       num_bents=3,
       post_section=200,
       beam_section=200
   )
   
   # Build barn
   barn = BarnFrame(config)
   
   # Export to IFC
   export_frame_to_ifc(barn.frame, "barn.ifc", project_name="My Barn")

Structural Analysis
-------------------

Run FEA analysis (requires gmsh and CalculiX):

.. code-block:: python

   from timber_joints import (
       analyze_frame, 
       TimberMaterial, 
       AnalysisConfig
   )
   
   # Configure analysis
   config = AnalysisConfig(
       material=TimberMaterial.DOUGLAS_FIR,
       mesh_size=50,
       contact_stiffness=1e6
   )
   
   # Run analysis
   result = analyze_frame(frame, config, loads={
       "tie_beam": ("gravity", 1000)
   })
   
   # Check results
   print(f"Max displacement: {result.max_displacement:.2f} mm")
   print(f"Max stress: {result.max_stress:.2f} MPa")
