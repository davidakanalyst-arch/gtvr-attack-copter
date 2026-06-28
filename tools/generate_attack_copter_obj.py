from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "source-model"
OBJ_PATH = OUT_DIR / "gtvr_attack_copter_shell.obj"
MTL_PATH = OUT_DIR / "gtvr_attack_copter_shell.mtl"


class ObjBuilder:
    def __init__(self) -> None:
        self.vertices: list[tuple[float, float, float]] = []
        self.faces: list[tuple[str, tuple[int, ...]]] = []

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
            self.faces.append((material, face))

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
            self.faces.append((material, face))

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
        import math

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
            self.faces.append((material, (base + i, base + j, base + segments + j, base + segments + i)))
        self.faces.append((material, tuple(base + i for i in range(segments - 1, -1, -1))))
        self.faces.append((material, tuple(base + segments + i for i in range(segments))))

    def write(self, obj_path: Path) -> None:
        lines = [
            "# GTVR Attack Copter low-poly exterior shell concept",
            "mtllib gtvr_attack_copter_shell.mtl",
        ]
        for vertex in self.vertices:
            lines.append(f"v {vertex[0]:.4f} {vertex[1]:.4f} {vertex[2]:.4f}")
        current_material = None
        for material, face in self.faces:
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

    # Length and height are intentionally EC135-class so this can become a visual shell.
    obj.add_wedge("faceted_nose", 5.3, 3.0, 0.45, 1.05, -0.75, -0.95, 0.85, 1.35, "matte_graphite")
    obj.add_wedge("glass_cockpit", 4.45, 2.35, 0.62, 1.02, 0.18, 0.38, 1.55, 1.75, "canopy_glass")
    obj.add_box("center_fuselage", (0.5, 0.0, 0.05), (5.2, 2.05, 2.05), "matte_graphite")
    obj.add_wedge("tail_boom", -1.8, -5.9, 0.65, 0.25, -0.20, 0.05, 0.65, 0.42, "matte_graphite")
    obj.add_box("engine_doghouse", (0.9, 0.0, 1.35), (3.0, 1.55, 0.70), "olive_panel")
    obj.add_box("left_intake_guard", (1.15, -0.98, 1.42), (1.35, 0.18, 0.42), "dark_metal")
    obj.add_box("right_intake_guard", (1.15, 0.98, 1.42), (1.35, 0.18, 0.42), "dark_metal")
    obj.add_box("left_exhaust_cover", (-0.55, -1.12, 1.08), (1.25, 0.22, 0.32), "dark_metal")
    obj.add_box("right_exhaust_cover", (-0.55, 1.12, 1.08), (1.25, 0.22, 0.32), "dark_metal")

    obj.add_box("left_stub_wing", (0.45, -1.68, -0.08), (1.75, 1.45, 0.18), "olive_panel")
    obj.add_box("right_stub_wing", (0.45, 1.68, -0.08), (1.75, 1.45, 0.18), "olive_panel")
    obj.add_cylinder("left_rocket_pod", (0.45, -2.32, -0.28), 0.22, 1.25, "x", 16, "dark_metal")
    obj.add_cylinder("right_rocket_pod", (0.45, 2.32, -0.28), 0.22, 1.25, "x", 16, "dark_metal")
    obj.add_cylinder("chin_sensor", (3.9, 0.0, -0.98), 0.34, 0.42, "z", 18, "dark_metal")

    obj.add_box("left_skid", (0.5, -1.15, -1.45), (5.2, 0.08, 0.08), "dark_metal")
    obj.add_box("right_skid", (0.5, 1.15, -1.45), (5.2, 0.08, 0.08), "dark_metal")
    obj.add_box("front_left_skid_strut", (2.3, -1.02, -1.05), (0.08, 0.08, 0.82), "dark_metal")
    obj.add_box("rear_left_skid_strut", (-1.4, -1.02, -1.05), (0.08, 0.08, 0.82), "dark_metal")
    obj.add_box("front_right_skid_strut", (2.3, 1.02, -1.05), (0.08, 0.08, 0.82), "dark_metal")
    obj.add_box("rear_right_skid_strut", (-1.4, 1.02, -1.05), (0.08, 0.08, 0.82), "dark_metal")

    obj.add_box("rotor_mast_placeholder", (0.2, 0.0, 2.05), (0.22, 0.22, 0.85), "dark_metal")
    obj.add_box("main_rotor_disc_reference", (0.2, 0.0, 2.55), (9.8, 0.08, 0.04), "dark_metal")
    obj.add_box("main_rotor_cross_reference", (0.2, 0.0, 2.55), (0.08, 9.8, 0.04), "dark_metal")
    obj.add_box("tail_fin", (-5.55, 0.0, 0.68), (0.22, 0.12, 1.35), "matte_graphite")
    obj.add_box("tail_rotor_reference", (-5.9, 0.0, 0.58), (0.06, 1.65, 0.06), "dark_metal")
    obj.add_box("tail_rotor_cross_reference", (-5.9, 0.0, 0.58), (0.06, 0.06, 1.65), "dark_metal")

    obj.add_box("left_flare_box", (-1.6, -1.05, 0.22), (0.48, 0.12, 0.32), "warning_red")
    obj.add_box("right_flare_box", (-1.6, 1.05, 0.22), (0.48, 0.12, 0.32), "warning_red")
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

