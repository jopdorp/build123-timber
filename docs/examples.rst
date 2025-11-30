Examples
========

Complete examples demonstrating library usage.

Barn Frame Assembly
-------------------

See ``examples/barn_frame.py`` for a complete barn frame example:

.. literalinclude:: ../examples/barn_frame.py
   :language: python
   :linenos:

FEA Pipeline
------------

See ``examples/fea_pipeline.py`` for structural analysis workflow:

.. code-block:: python

   # Example: Running FEA on a timber frame
   from timber_joints import (
       TimberFrame,
       analyze_frame,
       TimberMaterial,
       AnalysisConfig
   )
   
   # Build frame
   frame = TimberFrame("Test Frame")
   # ... add elements ...
   
   # Configure analysis
   config = AnalysisConfig(
       material=TimberMaterial.DOUGLAS_FIR,
       mesh_size=50
   )
   
   # Run analysis
   result = analyze_frame(frame, config)
   print(f"Max displacement: {result.max_displacement:.2f} mm")

More Examples
-------------

Additional examples can be found in the ``examples/`` directory:

* ``barn_frame.py`` - Complete barn frame assembly
* ``fea_pipeline.py`` - FEA workflow with contact surfaces
* ``compas_pipeline_example.py`` - COMPAS integration
