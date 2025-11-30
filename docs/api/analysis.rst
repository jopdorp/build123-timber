Analysis Module
===============

FEA integration for structural analysis (requires gmsh and CalculiX).

.. automodule:: timber_joints.analysis
   :members:
   :undoc-members:
   :show-inheritance:

Materials
---------

.. autoclass:: timber_joints.analysis.TimberMaterial
   :members:
   :undoc-members:

Configuration
-------------

.. autoclass:: timber_joints.analysis.AnalysisConfig
   :members:
   :undoc-members:

Results
-------

.. autoclass:: timber_joints.analysis.AnalysisResult
   :members:
   :undoc-members:

Analysis Functions
------------------

.. autofunction:: timber_joints.analysis.analyze_element
.. autofunction:: timber_joints.analysis.analyze_frame
.. autofunction:: timber_joints.analysis.print_analysis_summary

Contact Surface Utilities
--------------------------

.. autofunction:: timber_joints.analysis.get_bbox_solid
.. autofunction:: timber_joints.analysis.scale_shape_in_place
.. autofunction:: timber_joints.analysis.expand_shape_by_margin
.. autofunction:: timber_joints.analysis.find_contact_surface
.. autofunction:: timber_joints.analysis.find_joint_contact_surfaces
.. autofunction:: timber_joints.analysis.find_mesh_contact_faces
.. autofunction:: timber_joints.analysis.find_mesh_faces_on_surface
.. autofunction:: timber_joints.analysis.build_mesh_faces_compound
