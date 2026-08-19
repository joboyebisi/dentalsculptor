"""
TRELLIS.2 CUDA image for Modal GPU generation.

Adapted from https://github.com/dnouri/TRELLIS.2/tree/modal-integration
Build time: ~20–40 min on first deploy (CUDA extensions compile on GPU builder).
"""

from __future__ import annotations

import modal

from modal_app.trellis_config import (
    GPU_TYPE,
    HF_CACHE_PATH,
    HF_HUB_OFFLINE,
    MODEL_NAME,
    TRELLIS2_PATH,
    TRELLIS_COMMIT,
    modal_runtime_env,
)

PINNED_COMMITS = {
    "nvdiffrast": "253ac4fcea7de5f396371124af597e6cc957bfae",
    "nvdiffrec": "b296927cc7fd01c2ac1087c8065c4d7248f72da4",
    "utils3d": "9a4eb15e4021b67b12c460c7057d642626897ec8",
    "cumesh": "d8d28794721a3f4984b1b12c24403f546f41d28c",
    "flex_gemm": "8b9afa2d56f667b709ccd761d0bd7aab48bdd7cf",
    "trellis2": TRELLIS_COMMIT,
}

BUILD_TMP = "/tmp"

hf_cache_volume = modal.Volume.from_name("trellis2-hf-cache", create_if_missing=True)
# Create before deploy: modal secret create huggingface HF_TOKEN=hf_xxxx
hf_secret = modal.Secret.from_name("huggingface")

SYSTEM_PACKAGES = [
    "git",
    "ninja-build",
    "cmake",
    "build-essential",
    "clang",
    "libgl1-mesa-glx",
    "libglib2.0-0",
    "libjpeg-dev",
    "libpng-dev",
    "libgomp1",
    "libopenexr-dev",
]

CORE_PYTHON_PACKAGES = [
    "pillow",
    "imageio",
    "imageio-ffmpeg",
    "tqdm",
    "easydict",
    "opencv-python-headless",
    "scipy",
    "ninja",
    "trimesh",
    "huggingface-hub",
    "boto3>=1.35.0",
    "safetensors",
    "fastapi[standard]>=0.115.0",
    "python-multipart",
]

# Installed after torch 2.6.0 to avoid pip pulling torch 2.13+ (build timeout).
TORCH_VISION_PACKAGES = [
    # TRELLIS commit expects DINOv3 layers at model.layer; transformers 5 moved
    # them to model.model.layer and breaks inference.
    "transformers==4.57.6",
    "timm",
    "kornia",
]

trellis_gpu_image = (
    modal.Image.from_registry(
        "nvidia/cuda:12.4.0-devel-ubuntu22.04",
        add_python="3.10",
    )
    .apt_install(*SYSTEM_PACKAGES)
    .pip_install(*CORE_PYTHON_PACKAGES)
    .run_commands(
        "pip install --default-timeout=600 torch==2.6.0 torchvision==0.21.0 --index-url https://download.pytorch.org/whl/cu124",
        "pip install wheel setuptools psutil packaging",
        f"pip install --default-timeout=600 {' '.join(TORCH_VISION_PACKAGES)}",
        "pip install flash-attn==2.7.3 --no-build-isolation",
        f"pip install git+https://github.com/EasternJournalist/utils3d.git@{PINNED_COMMITS['utils3d']}",
        f"git clone https://github.com/NVlabs/nvdiffrast.git {BUILD_TMP}/nvdiffrast && cd {BUILD_TMP}/nvdiffrast && git checkout {PINNED_COMMITS['nvdiffrast']}",
        f"pip install {BUILD_TMP}/nvdiffrast --no-build-isolation",
        f"git clone https://github.com/JeffreyXiang/nvdiffrec.git {BUILD_TMP}/nvdiffrec && cd {BUILD_TMP}/nvdiffrec && git checkout {PINNED_COMMITS['nvdiffrec']}",
        f"pip install {BUILD_TMP}/nvdiffrec --no-build-isolation",
        f"git clone --recursive https://github.com/JeffreyXiang/CuMesh.git {BUILD_TMP}/CuMesh && cd {BUILD_TMP}/CuMesh && git checkout {PINNED_COMMITS['cumesh']}",
        f"pip install {BUILD_TMP}/CuMesh --no-build-isolation",
        f"git clone --recursive https://github.com/JeffreyXiang/FlexGEMM.git {BUILD_TMP}/FlexGEMM && cd {BUILD_TMP}/FlexGEMM && git checkout {PINNED_COMMITS['flex_gemm']}",
        f"pip install {BUILD_TMP}/FlexGEMM --no-build-isolation",
        gpu="T4",
    )
    .run_commands(
        f"git clone --recursive https://github.com/microsoft/TRELLIS.2.git {TRELLIS2_PATH} && cd {TRELLIS2_PATH} && git checkout {PINNED_COMMITS['trellis2']}",
    )
    .run_commands(
        f"pip install {TRELLIS2_PATH}/o-voxel --no-build-isolation",
        gpu="T4",
    )
    .env(
        {
            "ATTN_BACKEND": "flash_attn",
            "PYTHONPATH": TRELLIS2_PATH,
            "HF_HOME": HF_CACHE_PATH,
            "PYTORCH_CUDA_ALLOC_CONF": "expandable_segments:True",
            "OPENCV_IO_ENABLE_OPENEXR": "1",
            "TORCH_CUDA_ARCH_LIST": "8.0;8.6;8.9;9.0",
            "HF_HUB_OFFLINE": "1" if HF_HUB_OFFLINE else "0",
            **modal_runtime_env(),
        }
    )
)
