from build123d import Location

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


def demo_butt_joints():
    print("\n=== Butt Joints ===")

    main, cross = create_joint_pair(0, 0)
    LButtJoint(main=main, cross=cross).apply()
    print(f"L-Butt: {len(main._features)} + {len(cross._features)} features")

    main2, cross2 = create_joint_pair(0, 300)
    TButtJoint(main=main2, cross=cross2).apply()
    print(f"T-Butt: {len(main2._features)} + {len(cross2._features)} features")

    main3, cross3 = create_joint_pair(0, 600)
    TButtJoint(main=main3, cross=cross3, mill_depth=10).apply()
    print(f"T-Butt (milled): {len(main3._features)} + {len(cross3._features)} features")


def demo_lap_joints():
    print("\n=== Lap Joints ===")

    joints = [
        ("L-Lap", LLapJoint, {}),
        ("T-Lap", TLapJoint, {}),
        ("X-Lap", XLapJoint, {}),
        ("L-Lap (flipped)", LLapJoint, {"flip_lap_side": True}),
        ("L-Lap (biased)", LLapJoint, {"cut_plane_bias": 0.7}),
    ]

    for i, (name, joint_cls, kwargs) in enumerate(joints):
        main, cross = create_joint_pair(500, i * 300)
        joint_cls(main=main, cross=cross, **kwargs).apply()
        print(f"{name}: {len(main._features)} + {len(cross._features)} features")


def demo_miter_joints():
    print("\n=== Miter Joints ===")

    main, cross = create_joint_pair(1000, 0)
    LMiterJoint(main=main, cross=cross).apply()
    print(f"L-Miter: {len(main._features)} + {len(cross._features)} features")


def demo_mortise_tenon():
    print("\n=== Mortise and Tenon Joints ===")

    main, cross = create_joint_pair(1500, 0)
    joint = TenonMortiseJoint(main=main, cross=cross, tenon_length=40)
    joint.apply()
    print(f"M&T (auto): {joint.tenon_width}W x {joint.tenon_height}H x {joint.tenon_length}L")

    main2, cross2 = create_joint_pair(1500, 300)
    joint2 = TenonMortiseJoint(
        main=main2, cross=cross2,
        tenon_length=50, tenon_width=25, tenon_height=60,
    )
    joint2.apply()
    print(f"M&T (custom): {joint2.tenon_width}W x {joint2.tenon_height}H x {joint2.tenon_length}L")

    main3, cross3 = create_joint_pair(1500, 600)
    joint3 = TenonMortiseJoint(main=main3, cross=cross3, tenon_length=70, through_tenon=True)
    joint3.apply()
    print(f"M&T (through): through={joint3.through_tenon}")


def demo_dovetail_joints():
    print("\n=== Dovetail Joints ===")

    main, cross = create_joint_pair(2000, 0)
    joint = DovetailJoint(main=main, cross=cross, dovetail_length=40, cone_angle=10)
    joint.apply()
    print(f"Dovetail: angle={joint.cone_angle}°, length={joint.dovetail_length}")

    main2, cross2 = create_joint_pair(2000, 300)
    joint2 = HousedDovetailJoint(main=main2, cross=cross2, dovetail_length=40, housing_depth=15)
    joint2.apply()
    print(f"Housed dovetail: housing_depth={joint2.housing_depth}")


def demo_specialty_joints():
    print("\n=== Specialty Joints ===")

    plate = Beam(length=400, width=100, height=50)
    rafter = Timber.rafter(
        length=500, width=50, height=150,
        location=Location((200, 0, 50), (0, 30, 90)),
    )
    joint = BirdsmouthJoint(main=plate, cross=rafter, rafter_angle=30)
    joint.apply()
    print(f"Birdsmouth: seat_depth={joint.seat_depth}, angle={joint.rafter_angle}°")

    rafter1 = Timber.rafter(length=400, width=50, height=150, location=Location((2500, 0, 0)))
    rafter2 = Timber.rafter(length=400, width=50, height=150, location=Location((2900, 0, 0), (0, 0, 180)))
    FrenchRidgeLapJoint(main=rafter1, cross=rafter2).apply()
    print("French Ridge Lap: applied to ridge rafters")


def main():
    print("=" * 50)
    print("BUILD123-TIMBER JOINERY DEMONSTRATION")
    print("=" * 50)

    demo_butt_joints()
    demo_lap_joints()
    demo_miter_joints()
    demo_mortise_tenon()
    demo_dovetail_joints()
    demo_specialty_joints()

    print("\n" + "=" * 50)
    print("All joint demonstrations complete!")
    print("=" * 50)


if __name__ == "__main__":
    main()
