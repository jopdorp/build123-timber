Installation
============

Basic Installation
------------------

Install via pip:

.. code-block:: bash

   pip install timber-joints

Development Installation
------------------------

For development, clone the repository and install in editable mode:

.. code-block:: bash

   git clone https://github.com/jopdorp/build123-timber.git
   cd build123-timber
   pip install -e ".[dev]"

Optional Dependencies
---------------------

For Finite Element Analysis
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To use the FEA features, install gmsh and CalculiX:

**Linux:**

.. code-block:: bash

   sudo apt-get install gmsh calculix-ccx

**macOS:**

.. code-block:: bash

   brew install gmsh

For Documentation
~~~~~~~~~~~~~~~~~

To build documentation locally:

.. code-block:: bash

   pip install sphinx sphinx-rtd-theme

Then build:

.. code-block:: bash

   cd docs
   make html

Requirements
------------

* Python >= 3.10
* build123d >= 0.5.0
* ocp-vscode >= 2.0.0
