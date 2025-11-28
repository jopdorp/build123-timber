# %%
from build123d import Compound, Location
from ocp_vscode import show_object, set_defaults, Camera

from build123_timber import (
    Timber,
    Beam,
    LButtJoint,
    TButtJoint,
    LLapJoint,
    TLapJoint,
    XLapJoint,
    LMiterJoint,
    TenonMortiseJoint,
    DovetailJoint,
    HousedDovetailJoint,
    BirdsmouthJoint,
    FrenchRidgeLapJoint,
)

set_defaults(reset_camera=Camera.CENTER)


def create_joint_pair(offset_x: float = 0, offset_y: float = 0):
    main = Beam(
        length=400,
        width=60,
        height=100,
        location=Location((offset_x, offset_y, 0)),
    )
    cross = Beam(
        length=300,
        width=60,
        height=100,
        location=Location((offset_x + 200, offset_y - 150, 0), (0, 0, 90)),
    )
    return main, cross


# %%
shapes = []

main, cross = create_joint_pair(0, 0)
LButtJoint(main=main, cross=cross).apply()
shapes.extend([main.global_shape, cross.global_shape])

main, cross = create_joint_pair(0, 400)
TButtJoint(main=main, cross=cross).apply()
shapes.extend([main.global_shape, cross.global_shape])

main, cross = create_joint_pair(0, 800)
TButtJoint(main=main, cross=cross, mill_depth=10).apply()
shapes.extend([main.global_shape, cross.global_shape])

main, cross = create_joint_pair(600, 0)
LLapJoint(main=main, cross=cross).apply()
shapes.extend([main.global_shape, cross.global_shape])

main, cross = create_joint_pair(600, 400)
TLapJoint(main=main, cross=cross).apply()
shapes.extend([main.global_shape, cross.global_shape])

main, cross = create_joint_pair(600, 800)
XLapJoint(main=main, cross=cross).apply()
shapes.extend([main.global_shape, cross.global_shape])

main, cross = create_joint_pair(1200, 0)
LMiterJoint(main=main, cross=cross).apply()
shapes.extend([main.global_shape, cross.global_shape])

main, cross = create_joint_pair(1200, 400)
TenonMortiseJoint(main=main, cross=cross, tenon_length=40).apply()
shapes.extend([main.global_shape, cross.global_shape])

main, cross = create_joint_pair(1200, 800)
DovetailJoint(main=main, cross=cross, dovetail_length=40, cone_angle=10).apply()
shapes.extend([main.global_shape, cross.global_shape])

main, cross = create_joint_pair(1800, 0)
HousedDovetailJoint(main=main, cross=cross, dovetail_length=40, housing_depth=15).apply()
shapes.extend([main.global_shape, cross.global_shape])

plate = Beam(length=400, width=100, height=50, location=Location((1800, 400, 0)))
rafter = Timber.rafter(
    length=500, width=50, height=150,
    location=Location((2000, 400, 50), (0, 30, 90)),
)
BirdsmouthJoint(main=plate, cross=rafter, rafter_angle=30).apply()
shapes.extend([plate.global_shape, rafter.global_shape])

rafter1 = Timber.rafter(length=400, width=50, height=150, location=Location((1800, 800, 0)))
rafter2 = Timber.rafter(length=400, width=50, height=150, location=Location((2200, 800, 0), (0, 0, 180)))
FrenchRidgeLapJoint(main=rafter1, cross=rafter2).apply()
shapes.extend([rafter1.global_shape, rafter2.global_shape])

# %%
show_object(Compound(shapes), name="joinery_showcase")

# %%
