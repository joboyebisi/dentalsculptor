"""
TRELLIS.2 Modal image — E0 build spike.

Build order (see docs/MODAL_SETUP_GUIDE.md):
  1. CUDA 12.4 base + PyTorch 2.6
  2. Kaolin, flash-attn, o-voxel extensions
  3. Clone microsoft/TRELLIS.2 + apply Modal compatibility patches
  4. Pre-download weights into Volume trellis-weights-v1 on first deploy

GPU: A100-40GB (1024³) or H100-80GB (1536³ full quality)
Reference: https://github.com/dnouri/TRELLIS.2/tree/modal-integration
"""

import modal

# Spike — not wired to app.py until build is validated on Modal A100/H100.
trellis_image = (
    modal.Image.from_registry(
        "nvidia/cuda:12.4.1-cudnn-devel-ubuntu22.04",
        add_python="3.10",
    )
    .apt_install("git", "ffmpeg", "libgl1", "libglib2.0-0")
    .pip_install(
        "torch==2.6.0",
        "torchvision",
        "trimesh>=4.0.0",
        "rembg>=2.0.50",
        "pillow>=10.0.0",
        "boto3>=1.35.0",
        "fastapi[standard]>=0.115.0",
        index_url="https://download.pytorch.org/whl/cu124",
    )
    .run_commands(
        "pip install huggingface_hub",
        # Pre-download TRELLIS weights into the Modal volume (run once after deploy):
        # "huggingface-cli download microsoft/TRELLIS.2 --local-dir /weights/huggingface/TRELLIS.2",
    )
    .env(
        {
            "PYTORCH_CUDA_ALLOC_CONF": "expandable_segments:True",
            "OPENCV_IO_ENABLE_OPENEXR": "1",
            "HF_HOME": "/weights/huggingface",
        }
    )
)
