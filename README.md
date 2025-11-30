# Timber Joints

A comprehensive timber joinery and structural framing library for [build123d](https://github.com/gumyr/build123d). Design parametric timber structures with traditional joinery, automatic joint creation, and optional finite element analysis (FEA).

## Features

### 🪵 Core Joinery
- **Parametric joint geometry** - All joints are fully configurable inserting parts
- **Traditional timber joints** - Tenons, dovetails, lap joints, braces with shoulders
- **Automatic alignment** - Helper functions to position beams on posts with proper offsets
- **Contact surface detection** - For compression analysis at joint interfaces

### 🏗️ Structural Framing
- **TimberFrame system** - Declarative frame assembly with automatic joint detection
- **Role-based elements** - Posts, beams, girts, rafters, braces with proper connections
- **Barn frame builder** - High-level API for common timber frame structures
- **Smart positioning** - Automatic brace angle calculation and alignment

### 📊 Analysis & Export
- **FEA integration** - Structural analysis via gmsh + CalculiX (optional)
- **Material modeling** - Orthotropic timber material properties
- **Contact surfaces** - Automatic compression-only contact at joints
- **IFC export** - Building Information Modeling integration
- **Beam schedules** - Automatic cut lists and bill of materials

## Installation

```bash
pip install timber-joints
```

For development:

```bash
git clone https://github.com/jopdorp/build123-timber.git
cd build123-timber
pip install -e ".[dev]"
```

### Optional Dependencies

For finite element analysis:
```bash
# Install gmsh and CalculiX
sudo apt-get install gmsh calculix-ccx  # Linux
# or
brew install gmsh  # macOS
```

## Quick Start

### Basic Joint Creation

```python
from timber_joints import Beam, Tenon, ShoulderedTenon, align_beam_on_post
from build123d import export_step

# Create a post and beam
post = Beam(200, 200, 3000)
beam = Beam(200, 150, 4000)

# Align beam on top of post
beam_positioned = align_beam_on_post(
    beam=beam,
    post=post,
    offset_x=0,
    offset_y=100,
    beam_role="crossing"
)

# Create tenon at beam end
tenon = Tenon(
    width=120,
    height=80,
    length=100,
    parent_width=200,
    parent_height=150
)

# Export for CNC
export_step(beam_positioned, "beam.step")
export_step(tenon, "tenon.step")
```

### Building a Frame

```python
from timber_joints import TimberFrame, Role, show_frame

# Create a timber frame structure
frame = TimberFrame("Simple Bent")

# Add posts
frame.add_post("left_post", height=3000, width=200, depth=200, x=0, y=0, z=0)
frame.add_post("right_post", height=3000, width=200, depth=200, x=4000, y=0, z=0)

# Add tie beam connecting posts
frame.add_beam(
    "tie_beam",
    length=4400,
    width=200,
    height=200,
    x=-200,
    y=0,
    z=3000,
    role=Role.BEAM
)

# Visualize
show_frame(frame)
```

### High-Level Barn Frame

```python
from timber_joints import BarnConfig, BarnFrame, export_frame_to_ifc

# Configure barn dimensions
config = BarnConfig(
    width=6000,
    length=8000,  # 2 bays @ 4000mm each
    wall_height=3000,
    roof_peak_height=2000,
    num_bents=3,
    post_section=200,
    beam_section=200
)

# Build complete barn frame
barn = BarnFrame(config)

# Export to IFC for BIM software
export_frame_to_ifc(barn.frame, "barn.ifc", project_name="My Barn")
```

## Joint Types

| Joint | Description | Use Case |
|-------|-------------|----------|
| **Tenon** | Centered projection at beam end | Mortise and tenon connections |
| **ShoulderedTenon** | Tenon with bearing shoulder | Load-bearing beam-to-post |
| **BraceTenon** | Angled tenon for braces | Diagonal bracing with shoulders |
| **LapJoint** | Half-depth cut at beam end | Simple lap connections |
| **LapXSection** | Cross-halving joint | Beam crossings |
| **DovetailInsert** | Tapered dovetail projection | Sliding dovetails |
| **HalfDovetail** | Single-sided dovetail | Edge connections |

All joints represent the **inserting part only** - create mortises/housings with `create_receiving_cut()`.

## Frame Assembly Workflow

1. **Define structure** - Create `TimberFrame` and add elements
2. **Automatic joints** - Frame detects intersections and creates joints
3. **Apply cuts** - Generate receiving cuts (mortises) in elements
4. **Export** - Generate IFC, STEP files, or beam schedules
5. **Analyze** (optional) - Run FEA to verify structural integrity

## Analysis Example

```python
from timber_joints import analyze_frame, TimberMaterial, AnalysisConfig

# Configure analysis
config = AnalysisConfig(
    material=TimberMaterial.DOUGLAS_FIR,
    mesh_size=50,
    contact_stiffness=1e6
)

# Run FEA (requires gmsh + CalculiX)
result = analyze_frame(frame, config, loads={
    "tie_beam": ("gravity", 1000)  # 1000N distributed load
})

# Check results
print(f"Max displacement: {result.max_displacement:.2f} mm")
print(f"Max stress: {result.max_stress:.2f} MPa")
```

## Architecture

```
timber_joints/
├── beam.py              # Base Beam class
├── base_joint.py        # Joint base class
├── tenon.py            # Tenon joints
├── shouldered_tenon.py # Shouldered tenons
├── brace_tenon.py      # Angled brace tenons
├── dovetail.py         # Dovetail joints
├── lap_joint.py        # Lap joints
├── alignment.py        # Beam positioning utilities
├── frame.py            # TimberFrame assembly system
├── barn.py             # High-level barn builder
├── analysis.py         # FEA integration
├── export.py           # IFC/schedule export
└── utils.py            # Helper functions
```

## Documentation

**📚 [Read the full documentation on GitHub Pages →](https://jopdorp.github.io/build123-timber/)**

Full API documentation is available in the `docs/` directory. Build it locally:

```bash
pip install -e ".[docs]"
cd docs
make html
# Open docs/_build/html/index.html in browser
```

Documentation is automatically rebuilt and deployed to GitHub Pages on push to main.

To build locally, documentation is also automatically rebuilt before each git push via pre-push hook. Set up hooks:

```bash
./.githooks/setup-hooks.sh
```

## Examples

See the `examples/` directory:
- `barn_frame.py` - Complete barn frame assembly
- `fea_pipeline.py` - Structural analysis workflow
- `compas_pipeline_example.py` - COMPAS integration

## Contributing

Contributions welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT License - see [LICENSE](LICENSE) file.

## Acknowledgments

- [COMPAS Timber](https://github.com/gramaziokohler/compas_timber) - Inspiration for joinery concepts
- [build123d](https://github.com/gumyr/build123d) - Powerful CAD kernel
- [gmsh](https://gmsh.info/) + [CalculiX](http://www.calculix.de/) - FEA tools
