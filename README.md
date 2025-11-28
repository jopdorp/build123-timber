# build123-timber

A timber framing library for [build123d](https://github.com/gumyr/build123d) - parametric design of timber structures with traditional joinery.

Inspired by [COMPAS Timber](https://github.com/gramaziokohler/compas_timber) and [compas_wood](https://github.com/petrasvestartas/compas_wood) Grasshopper plugins.

## Features

- **Timber Elements**: Beam and Post classes for creating rectangular cross-section timber members
- **Traditional Joinery**: Support for common timber frame joints including:
  - Mortise and Tenon
  - Dovetail (including housed dovetail)
  - Half Lap joints (L, T, and X configurations)
  - Butt joints
  - Miter joints
  - Birdsmouth joints
- **Joint Topologies**: Automatic detection and handling of L, T, and X joint configurations
- **Parametric Design**: All dimensions and parameters are configurable

## Installation

```bash
pip install build123-timber
```

Or for development:

```bash
git clone https://github.com/yourusername/build123-timber.git
cd build123-timber
pip install -e ".[dev]"
```

## Quick Start

```python
from build123_timber import Beam, TenonMortiseJoint
from build123d import Pos

# Create two beams
main_beam = Beam(length=1000, width=100, height=150)
cross_beam = Beam(length=800, width=100, height=150)

# Position the cross beam
cross_beam = cross_beam.move(Pos(500, 0, 75))
cross_beam = cross_beam.rotate((0, 0, 1), 90)

# Create a tenon and mortise joint
joint = TenonMortiseJoint(
    main_beam=main_beam,
    cross_beam=cross_beam,
    tenon_length=50,
    tenon_width=40,
    tenon_height=100
)

# Get the modified beams with the joint cut
main_with_mortise, cross_with_tenon = joint.apply()
```

## Joint Types

### Butt Joints
Simple joints where one beam is cut to meet another:
- `LButtJoint`: Corner (L) butt joint
- `TButtJoint`: T-intersection butt joint

### Lap Joints
Half-lap style joints where material is removed from both beams:
- `LLapJoint`: Corner lap joint
- `TLapJoint`: T-intersection lap joint
- `XLapJoint`: Cross lap joint (X-intersection)

### Miter Joints
- `LMiterJoint`: Corner miter joint at bisector angle

### Mortise and Tenon
- `TenonMortiseJoint`: Traditional mortise and tenon for L and T topologies

### Dovetail Joints
- `DovetailJoint`: Sliding dovetail for T-intersections
- `HousedDovetailJoint`: Housed/stopped dovetail

### Specialty Joints
- `BirdsmouthJoint`: Rafter seat cut for T-intersections
- `FrenchRidgeLapJoint`: Ridge lap with angled cut for L-intersections

## API Reference

See the [API documentation](docs/api.md) for detailed information on all classes and methods.

## Contributing

Contributions are welcome! Please read our [Contributing Guide](CONTRIBUTING.md) for details.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [COMPAS Timber](https://github.com/gramaziokohler/compas_timber) - Inspiration for the API design and joint types
- [compas_wood](https://github.com/petrasvestartas/compas_wood) - Inspiration for joinery generation concepts
- [build123d](https://github.com/gumyr/build123d) - The underlying CAD kernel
