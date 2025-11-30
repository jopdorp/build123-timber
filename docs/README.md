# Documentation

This directory contains Sphinx documentation for timber-joints.

## Building Documentation

Install documentation dependencies:

```bash
pip install -e ".[docs]"
```

Build HTML documentation:

```bash
cd docs
make html
```

View the documentation:

```bash
# Open in browser
open _build/html/index.html  # macOS
xdg-open _build/html/index.html  # Linux
```

## Auto-build on Push

Documentation is automatically rebuilt before pushing to the repository via a git hook.

To set up the hooks:

```bash
./.githooks/setup-hooks.sh
```

To skip the hook temporarily:

```bash
git push --no-verify
```

## Documentation Structure

- `index.rst` - Main documentation page
- `installation.rst` - Installation guide
- `quickstart.rst` - Quick start guide
- `api/` - Auto-generated API documentation from docstrings
- `examples.rst` - Usage examples
- `conf.py` - Sphinx configuration

## Adding Documentation

The API documentation is auto-generated from Python docstrings. To add documentation:

1. Write docstrings in your code (Google or NumPy style)
2. Add new modules to the appropriate `api/*.rst` file
3. Rebuild with `make html`

Example docstring:

```python
def my_function(param1: str, param2: int) -> bool:
    """Brief description of the function.
    
    More detailed description here.
    
    Args:
        param1: Description of param1
        param2: Description of param2
        
    Returns:
        Description of return value
        
    Raises:
        ValueError: When something goes wrong
    """
    pass
```
