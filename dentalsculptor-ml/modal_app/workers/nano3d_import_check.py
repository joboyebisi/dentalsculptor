"""
Verify Nano3D CPU worker imports at Modal image build time.

Run locally after changing cpu_image deps:
  python -m modal_app.workers.nano3d_import_check
"""

from __future__ import annotations


def verify_nano3d_cpu_imports() -> dict[str, str]:
    import numpy  # noqa: F401
    import scipy  # noqa: F401
    import trimesh  # noqa: F401
    from PIL import Image  # noqa: F401

    import io

    mesh = trimesh.creation.icosphere(subdivisions=1)
    mesh.fix_normals()
    buf = io.BytesIO()
    mesh.export(buf, file_type="glb")

    return {
        "numpy": numpy.__version__,
        "scipy": scipy.__version__,
        "trimesh": trimesh.__version__,
        "glbExportBytes": str(len(buf.getvalue())),
    }


if __name__ == "__main__":
    print(verify_nano3d_cpu_imports())
