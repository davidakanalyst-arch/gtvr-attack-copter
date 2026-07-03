from __future__ import annotations

import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "source-model"
OBJ_PATH = OUT_DIR / "gtvr_attack_copter_shell.obj"
MTL_PATH = OUT_DIR / "gtvr_attack_copter_shell.mtl"


class ObjBuilder:
    def __init__(self) -> None:
        self.vertices: list[tuple[float, float, float]] = []
        self.faces: list[tuple[str, str, tuple[int, ...]]] = []

    def add_face(self, name: str, material: str, face: tuple[int, ...]) -> None:
        self.faces.append((name, material, face))

    def add_box(
        self,
        name: str,
        center: tuple[float, float, float],
        size: tuple[float, float, float],
        material: str,
    ) -> None:
        cx, cy, cz = center
        sx, sy, sz = (v / 2.0 for v in size)
        base = len(self.vertices) + 1
        points = [
            (cx - sx, cy - sy, cz - sz),
            (cx + sx, cy - sy, cz - sz),
            (cx + sx, cy + sy, cz - sz),
            (cx - sx, cy + sy, cz - sz),
            (cx - sx, cy - sy, cz + sz),
            (cx + sx, cy - sy, cz + sz),
            (cx + sx, cy + sy, cz + sz),
            (cx - sx, cy + sy, cz + sz),
        ]
        self.vertices.extend(points)
        quads = [
            (base + 0, base + 1, base + 2, base + 3),
            (base + 4, base + 7, base + 6, base + 5),
            (base + 0, base + 4, base + 5, base + 1),
            (base + 1, base + 5, base + 6, base + 2),
            (base + 2, base + 6, base + 7, base + 3),
            (base + 3, base + 7, base + 4, base + 0),
        ]
        for face in quads:
            self.add_face(name, material, face)

    def add_wedge(
        self,
        name: str,
        x_front: float,
        x_back: float,
        y_half_front: float,
        y_half_back: float,
        z_low_front: float,
        z_low_back: float,
        z_high_front: float,
        z_high_back: float,
        material: str,
    ) -> None:
        base = len(self.vertices) + 1
        self.vertices.extend(
            [
                (x_front, -y_half_front, z_low_front),
                (x_front, y_half_front, z_low_front),
                (x_front, -y_half_front, z_high_front),
                (x_front, y_half_front, z_high_front),
                (x_back, -y_half_back, z_low_back),
                (x_back, y_half_back, z_low_back),
                (x_back, -y_half_back, z_high_back),
                (x_back, y_half_back, z_high_back),
            ]
        )
        for face in [
            (base + 0, base + 1, base + 3, base + 2),
            (base + 4, base + 6, base + 7, base + 5),
            (base + 0, base + 2, base + 6, base + 4),
            (base + 1, base + 5, base + 7, base + 3),
            (base + 2, base + 3, base + 7, base + 6),
            (base + 0, base + 4, base + 5, base + 1),
        ]:
            self.add_face(name, material, face)

    def add_cylinder(
        self,
        name: str,
        center: tuple[float, float, float],
        radius: float,
        length: float,
        axis: str,
        segments: int,
        material: str,
    ) -> None:
        cx, cy, cz = center
        base = len(self.vertices) + 1
        for end in (-0.5, 0.5):
            for i in range(segments):
                a = (math.tau * i) / segments
                p = radius * math.cos(a)
                q = radius * math.sin(a)
                if axis == "x":
                    self.vertices.append((cx + end * length, cy + p, cz + q))
                elif axis == "y":
                    self.vertices.append((cx + p, cy + end * length, cz + q))
                else:
                    self.vertices.append((cx + p, cy + q, cz + end * length))
        for i in range(segments):
            j = (i + 1) % segments
            self.add_face(name, material, (base + i, base + j, base + segments + j, base + segments + i))
        self.add_face(name, material, tuple(base + i for i in range(segments - 1, -1, -1)))
        self.add_face(name, material, tuple(base + segments + i for i in range(segments)))

    def add_cylinder_between(
        self,
        name: str,
        p0: tuple[float, float, float],
        p1: tuple[float, float, float],
        radius: float,
        segments: int,
        material: str,
    ) -> None:
        def sub(a: tuple[float, float, float], b: tuple[float, float, float]) -> tuple[float, float, float]:
            return (a[0] - b[0], a[1] - b[1], a[2] - b[2])

        def dot(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
            return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]

        def cross(a: tuple[float, float, float], b: tuple[float, float, float]) -> tuple[float, float, float]:
            return (
                a[1] * b[2] - a[2] * b[1],
                a[2] * b[0] - a[0] * b[2],
                a[0] * b[1] - a[1] * b[0],
            )

        def scale(a: tuple[float, float, float], s: float) -> tuple[float, float, float]:
            return (a[0] * s, a[1] * s, a[2] * s)

        def add(a: tuple[float, float, float], b: tuple[float, float, float]) -> tuple[float, float, float]:
            return (a[0] + b[0], a[1] + b[1], a[2] + b[2])

        def normalize(a: tuple[float, float, float]) -> tuple[float, float, float]:
            length = math.sqrt(dot(a, a))
            if length <= 1e-9:
                return (1.0, 0.0, 0.0)
            return (a[0] / length, a[1] / length, a[2] / length)

        axis = normalize(sub(p1, p0))
        guide = (0.0, 0.0, 1.0)
        if abs(dot(axis, guide)) > 0.9:
            guide = (0.0, 1.0, 0.0)
        side = normalize(cross(axis, guide))
        up = normalize(cross(side, axis))

        base = len(self.vertices) + 1
        for end_point in (p0, p1):
            for i in range(segments):
                angle = (math.tau * i) / segments
                offset = add(scale(side, math.cos(angle) * radius), scale(up, math.sin(angle) * radius))
                self.vertices.append(add(end_point, offset))
        for i in range(segments):
            j = (i + 1) % segments
            self.add_face(name, material, (base + i, base + j, base + segments + j, base + segments + i))
        self.add_face(name, material, tuple(base + i for i in range(segments - 1, -1, -1)))
        self.add_face(name, material, tuple(base + segments + i for i in range(segments)))

    def add_elliptic_sections(
        self,
        name: str,
        stations: list[tuple[float, float, float, float]],
        segments: int,
        material: str,
    ) -> None:
        """Add a smooth aircraft body from x/y-radius/z-radius/z-center stations."""
        base = len(self.vertices) + 1
        for x, y_radius, z_radius, z_center in stations:
            for i in range(segments):
                angle = (math.tau * i) / segments
                self.vertices.append(
                    (
                        x,
                        math.cos(angle) * y_radius,
                        z_center + math.sin(angle) * z_radius,
                    )
                )
        for ring in range(len(stations) - 1):
            ring_base = base + ring * segments
            next_base = ring_base + segments
            for i in range(segments):
                j = (i + 1) % segments
                self.add_face(name, material, (ring_base + i, ring_base + j, next_base + j, next_base + i))
        self.add_face(name, material, tuple(base + i for i in range(segments - 1, -1, -1)))
        cap_base = base + (len(stations) - 1) * segments
        self.add_face(name, material, tuple(cap_base + i for i in range(segments)))

    def add_tapered_blade_pair(
        self,
        name: str,
        center: tuple[float, float, float],
        length: float,
        root_width: float,
        tip_width: float,
        thickness: float,
        angle: float,
        material: str,
    ) -> None:
        cx, cy, cz = center
        ca = math.cos(angle)
        sa = math.sin(angle)

        def transform(x: float, y: float, z: float) -> tuple[float, float, float]:
            return (cx + x * ca - y * sa, cy + x * sa + y * ca, cz + z)

        half = length / 2.0
        root = 0.24
        plan = [
            (-half, -tip_width / 2.0),
            (-root, -root_width / 2.0),
            (root, -root_width / 2.0),
            (half, -tip_width / 2.0),
            (half, tip_width / 2.0),
            (root, root_width / 2.0),
            (-root, root_width / 2.0),
            (-half, tip_width / 2.0),
        ]
        base = len(self.vertices) + 1
        for z in (-thickness / 2.0, thickness / 2.0):
            for x, y in plan:
                self.vertices.append(transform(x, y, z))
        self.add_face(name, material, tuple(base + i for i in range(len(plan) - 1, -1, -1)))
        self.add_face(name, material, tuple(base + len(plan) + i for i in range(len(plan))))
        for i in range(len(plan)):
            j = (i + 1) % len(plan)
            self.add_face(name, material, (base + i, base + j, base + len(plan) + j, base + len(plan) + i))

    def write(self, obj_path: Path) -> None:
        lines = [
            "# GTVR Attack Copter low-poly exterior shell concept",
            "mtllib gtvr_attack_copter_shell.mtl",
        ]
        for vertex in self.vertices:
            lines.append(f"v {vertex[0]:.4f} {vertex[1]:.4f} {vertex[2]:.4f}")
        current_object = None
        current_material = None
        for object_name, material, face in self.faces:
            if object_name != current_object:
                lines.append(f"o {object_name}")
                current_object = object_name
                current_material = None
            if material != current_material:
                lines.append(f"usemtl {material}")
                current_material = material
            lines.append("f " + " ".join(str(index) for index in face))
        obj_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_materials(path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                "newmtl matte_graphite",
                "Kd 0.055 0.060 0.060",
                "Ks 0.100 0.100 0.095",
                "Ns 18",
                "",
                "newmtl canopy_glass",
                "Kd 0.080 0.150 0.180",
                "Ks 0.600 0.750 0.800",
                "Ns 90",
                "d 0.45",
                "",
                "newmtl dark_metal",
                "Kd 0.018 0.020 0.020",
                "Ks 0.250 0.250 0.240",
                "Ns 35",
                "",
                "newmtl olive_panel",
                "Kd 0.170 0.205 0.145",
                "Ks 0.080 0.090 0.075",
                "Ns 12",
                "",
                "newmtl warning_red",
                "Kd 0.550 0.030 0.020",
                "Ks 0.100 0.020 0.020",
                "Ns 8",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def build_model() -> ObjBuilder:
    obj = ObjBuilder()

    # Length and height are intentionally EC135-class, but the second-pass mesh is
    # rounded and aircraft-like enough to avoid the toy-block silhouette.
    obj.add_elliptic_sections(
        "faceted_nose",
        [
            (5.35, 0.08, 0.10, -0.03),
            (4.85, 0.42, 0.42, 0.00),
            (4.25, 0.72, 0.66, 0.04),
            (3.55, 0.94, 0.82, 0.05),
            (2.80, 1.08, 0.92, 0.02),
        ],
        24,
        "matte_graphite",
    )
    obj.add_elliptic_sections(
        "center_fuselage",
        [
            (2.85, 1.08, 0.94, 0.02),
            (1.75, 1.16, 1.02, 0.00),
            (0.45, 1.14, 1.00, -0.02),
            (-0.85, 0.98, 0.86, -0.01),
            (-1.85, 0.72, 0.62, 0.08),
        ],
        24,
        "matte_graphite",
    )
    obj.add_elliptic_sections(
        "tail_boom",
        [
            (-1.78, 0.62, 0.42, 0.18),
            (-2.85, 0.46, 0.34, 0.22),
            (-4.20, 0.30, 0.25, 0.26),
            (-5.80, 0.20, 0.18, 0.31),
        ],
        18,
        "matte_graphite",
    )
    obj.add_elliptic_sections(
        "glass_cockpit",
        [
            (4.80, 0.34, 0.20, 0.78),
            (4.15, 0.68, 0.38, 0.93),
            (3.25, 0.86, 0.46, 1.02),
            (2.45, 0.78, 0.36, 0.96),
        ],
        20,
        "canopy_glass",
    )
    obj.add_elliptic_sections(
        "engine_doghouse",
        [
            (1.70, 0.56, 0.25, 1.28),
            (0.80, 0.76, 0.34, 1.38),
            (-0.25, 0.66, 0.30, 1.33),
        ],
        18,
        "olive_panel",
    )
    obj.add_cylinder_between("left_intake_guard", (1.35, -1.06, 1.30), (-0.10, -1.06, 1.30), 0.10, 14, "dark_metal")
    obj.add_cylinder_between("right_intake_guard", (1.35, 1.06, 1.30), (-0.10, 1.06, 1.30), 0.10, 14, "dark_metal")
    obj.add_cylinder_between("left_exhaust_cover", (-0.45, -1.12, 0.98), (-1.40, -1.12, 0.92), 0.12, 14, "dark_metal")
    obj.add_cylinder_between("right_exhaust_cover", (-0.45, 1.12, 0.98), (-1.40, 1.12, 0.92), 0.12, 14, "dark_metal")

    obj.add_box("left_stub_wing", (0.35, -1.60, -0.06), (1.80, 1.05, 0.16), "olive_panel")
    obj.add_box("right_stub_wing", (0.35, 1.60, -0.06), (1.80, 1.05, 0.16), "olive_panel")
    obj.add_cylinder_between("left_rocket_pod", (1.12, -2.36, -0.30), (-0.78, -2.36, -0.30), 0.20, 18, "dark_metal")
    obj.add_cylinder_between("right_rocket_pod", (1.12, 2.36, -0.30), (-0.78, 2.36, -0.30), 0.20, 18, "dark_metal")
    obj.add_cylinder("chin_sensor", (3.95, 0.0, -0.84), 0.30, 0.36, "z", 20, "dark_metal")

    obj.add_cylinder_between("left_skid", (3.10, -1.18, -1.45), (-2.55, -1.18, -1.45), 0.055, 16, "dark_metal")
    obj.add_cylinder_between("right_skid", (3.10, 1.18, -1.45), (-2.55, 1.18, -1.45), 0.055, 16, "dark_metal")
    obj.add_cylinder_between("front_left_skid_strut", (2.55, -1.18, -1.42), (2.25, -0.74, -0.68), 0.040, 12, "dark_metal")
    obj.add_cylinder_between("rear_left_skid_strut", (-1.20, -1.18, -1.42), (-1.05, -0.74, -0.58), 0.040, 12, "dark_metal")
    obj.add_cylinder_between("front_right_skid_strut", (2.55, 1.18, -1.42), (2.25, 0.74, -0.68), 0.040, 12, "dark_metal")
    obj.add_cylinder_between("rear_right_skid_strut", (-1.20, 1.18, -1.42), (-1.05, 0.74, -0.58), 0.040, 12, "dark_metal")

    obj.add_cylinder_between("rotor_mast_placeholder", (0.20, 0.0, 1.62), (0.20, 0.0, 2.42), 0.11, 18, "dark_metal")
    obj.add_tapered_blade_pair("main_rotor_disc_reference", (0.20, 0.0, 2.55), 9.8, 0.24, 0.09, 0.035, 0.0, "dark_metal")
    obj.add_tapered_blade_pair("main_rotor_cross_reference", (0.20, 0.0, 2.55), 9.8, 0.24, 0.09, 0.035, math.pi / 2.0, "dark_metal")
    obj.add_wedge("tail_fin", -5.15, -5.95, 0.10, 0.16, 0.25, 0.08, 1.70, 1.20, "matte_graphite")
    obj.add_box("tail_rotor_reference", (-5.92, 0.0, 0.55), (0.045, 1.65, 0.08), "dark_metal")
    obj.add_box("tail_rotor_cross_reference", (-5.92, 0.0, 0.55), (0.045, 0.08, 1.65), "dark_metal")

    obj.add_box("left_flare_box", (-1.55, -1.03, 0.24), (0.46, 0.12, 0.30), "warning_red")
    obj.add_box("right_flare_box", (-1.55, 1.03, 0.24), (0.46, 0.12, 0.30), "warning_red")
    obj.add_cylinder_between("left_canopy_armor_rail", (4.35, -0.72, 1.13), (2.50, -0.82, 1.32), 0.045, 10, "dark_metal")
    obj.add_cylinder_between("right_canopy_armor_rail", (4.35, 0.72, 1.13), (2.50, 0.82, 1.32), 0.045, 10, "dark_metal")
    obj.add_wedge("nose_upper_armor_plate", 4.60, 3.05, 0.48, 0.86, 0.72, 0.86, 0.86, 1.06, "olive_panel")
    obj.add_box("left_door_armor_panel", (1.05, -1.09, 0.15), (1.45, 0.08, 0.70), "olive_panel")
    obj.add_box("right_door_armor_panel", (1.05, 1.09, 0.15), (1.45, 0.08, 0.70), "olive_panel")
    obj.add_elliptic_sections(
        "belly_mission_pack",
        [
            (2.15, 0.34, 0.16, -0.88),
            (1.10, 0.44, 0.18, -0.98),
            (-0.20, 0.36, 0.15, -0.88),
        ],
        14,
        "dark_metal",
    )
    obj.add_box("tail_antenna_spine", (-3.30, 0.0, 0.63), (1.10, 0.06, 0.18), "dark_metal")
    return obj


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    write_materials(MTL_PATH)
    model = build_model()
    model.write(OBJ_PATH)
    print(f"Wrote {OBJ_PATH}")
    print(f"Wrote {MTL_PATH}")


if __name__ == "__main__":
    main()
