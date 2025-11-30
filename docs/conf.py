"""Sphinx configuration for timber-joints documentation."""

import os
import sys

# Add source to path
sys.path.insert(0, os.path.abspath("../src"))

# Project information
project = "timber-joints"
copyright = "2025, timber-joints contributors"
author = "timber-joints contributors"
release = "0.1.0"

# General configuration
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
    "sphinx_rtd_theme",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# HTML output
html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]

# Napoleon settings (for Google/NumPy style docstrings)
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = True
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = True
napoleon_use_admonition_for_notes = True
napoleon_use_admonition_for_references = False
napoleon_use_ivar = False
napoleon_use_param = True
napoleon_use_rtype = True
napoleon_type_aliases = None

# Autodoc settings
autodoc_default_options = {
    "members": True,
    "member-order": "bysource",
    "special-members": "__init__",
    "undoc-members": True,
    "exclude-members": "__weakref__",
    "imported-members": False,
}
autodoc_mock_imports = ["build123d", "ocp_vscode", "gmsh", "OCP"]

# Suppress duplicate/ambiguous reference warnings from re-exported symbols  
suppress_warnings = ["autodoc.import_cycle", "ref.python", "autodoc", "app.add_node"]

# Ignore duplicate object descriptions (common with re-exported symbols)
def setup(app):
    app.registry.source_suffix = {'.rst': 'restructuredtext'}
    
    # Suppress duplicate warnings
    import logging
    class DuplicateFilter(logging.Filter):
        def filter(self, record):
            return "duplicate object description" not in record.getMessage()
    
    logging.getLogger('sphinx').addFilter(DuplicateFilter())
    logging.getLogger('sphinx.domains.python').addFilter(DuplicateFilter())

# Don't document imported members (prevents duplicates)
autodoc_inherit_docstrings = False

# Intersphinx mapping
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "build123d": ("https://build123d.readthedocs.io/en/latest/", None),
}
