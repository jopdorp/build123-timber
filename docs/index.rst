Timber Joints Documentation
===========================

A comprehensive timber joinery and structural framing library for build123d.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   installation
   quickstart
   api/index
   examples

Features
--------

* **Parametric Joinery** - Traditional timber joints (tenons, dovetails, laps)
* **Structural Framing** - TimberFrame system for complete structures
* **FEA Analysis** - Optional finite element analysis integration
* **Export Tools** - IFC export and beam schedules

Installation
------------

.. code-block:: bash

   pip install timber-joints

Quick Example
-------------

.. code-block:: python

   from timber_joints import Beam, Tenon
   
   # Create a beam
   beam = Beam(length=4000, width=200, height=150)
   
   # Create a tenon at the end
   tenon = Tenon(
       width=120,
       height=80,
       length=100,
       parent_width=200,
       parent_height=150
   )

Indices and Tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
