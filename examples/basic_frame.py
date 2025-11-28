from build123d import Location

from build123_timber import (
    Beam,
    Post,
    TimberModel,
    TenonMortiseJoint,
    LLapJoint,
    TLapJoint,
)


def create_simple_frame():
    model = TimberModel(name="SimpleFrame")

    frame_width = 2000
    frame_depth = 1500
    frame_height = 2400
    post_size = 100
    beam_width = 50
    beam_height = 150

    post_positions = [
        (0, 0),
        (frame_width, 0),
        (frame_width, frame_depth),
        (0, frame_depth),
    ]

    for i, (x, y) in enumerate(post_positions):
        post = Post(
            length=frame_height,
            width=post_size,
            height=post_size,
            name=f"post_{i}",
            location=Location((x, y, 0), (0, 90, 0)),
        )
        model.add_element(post)

    beams_config = [
        ("beam_front", frame_width, (0, 0, frame_height - beam_height / 2), (0, 0, 0)),
        ("beam_back", frame_width, (0, frame_depth, frame_height - beam_height / 2), (0, 0, 0)),
        ("beam_left", frame_depth, (0, 0, frame_height - beam_height / 2), (0, 0, 90)),
        ("beam_right", frame_depth, (frame_width, 0, frame_height - beam_height / 2), (0, 0, 90)),
    ]

    for name, length, pos, rot in beams_config:
        beam = Beam(
            length=length,
            width=beam_width,
            height=beam_height,
            name=name,
            location=Location(pos, rot),
        )
        model.add_element(beam)

    print(f"Created model: {model}")
    return model


def create_corner_joint_example():
    beam1 = Beam(length=500, width=50, height=100, name="beam_1")
    beam2 = Beam(
        length=500,
        width=50,
        height=100,
        name="beam_2",
        location=Location((500, 0, 0), (0, 0, 90)),
    )

    joint = LLapJoint(main=beam1, cross=beam2)
    joint.apply()

    print(f"Corner joint: beam1 features={len(beam1._features)}, beam2 features={len(beam2._features)}")
    return beam1, beam2


def create_mortise_tenon_example():
    main = Beam(length=800, width=100, height=150, name="main_beam")
    cross = Beam(
        length=600,
        width=80,
        height=120,
        name="cross_beam",
        location=Location((400, -300, 0), (0, 0, 90)),
    )

    joint = TenonMortiseJoint(
        main=main,
        cross=cross,
        tenon_length=60,
        tenon_width=30,
        tenon_height=80,
    )
    joint.apply()

    print(f"Mortise & tenon: {joint.tenon_length}L x {joint.tenon_width}W x {joint.tenon_height}H")
    return main, cross


def create_t_joint_example():
    main = Beam(length=1000, width=80, height=120, name="main_beam")
    cross = Beam(
        length=500,
        width=80,
        height=120,
        name="cross_beam",
        location=Location((500, -250, 0), (0, 0, 90)),
    )

    joint = TLapJoint(main=main, cross=cross)
    joint.apply()

    print("T-lap joint created")
    return main, cross


if __name__ == "__main__":
    print("=== Build123-Timber Examples ===\n")
    print("1. Creating simple frame...")
    create_simple_frame()
    print()
    print("2. Creating corner joint example...")
    create_corner_joint_example()
    print()
    print("3. Creating mortise and tenon example...")
    create_mortise_tenon_example()
    print()
    print("4. Creating T-joint example...")
    create_t_joint_example()
    print()
    print("=== Examples complete ===")
