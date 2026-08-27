"""Pinned Nano3D/TRELLIS v1 Modal image.

Nano3D is not compatible with the TRELLIS.2 generation environment. Keep this
image isolated and pin the upstream commit used by the application.
"""

from __future__ import annotations

import modal

NANO3D_COMMIT = "7d20eb6887cb73e3bb4ec349ee27e0b670004512"
NANO3D_PATH = "/opt/nano3d"
NANO3D_HF_CACHE = "/weights/nano3d-hf"
UTILS3D_COMMIT = "9a4eb15e4021b67b12c460c7057d642626897ec8"

nano3d_hf_volume = modal.Volume.from_name("nano3d-hf-cache-v1", create_if_missing=True)

nano3d_gpu_image = (
    modal.Image.from_registry(
        "nvidia/cuda:11.8.0-devel-ubuntu22.04",
        add_python="3.10",
    )
    .apt_install(
        "git", "ninja-build", "cmake", "build-essential", "clang", "libeigen3-dev",
        "libgl1", "libglib2.0-0", "libgomp1", "ffmpeg",
        # Headless bpy (Nano3D inference.model_utils imports Blender Python).
        "libsm6", "libice6", "libx11-6", "libxext6", "libxrender1", "libglu1-mesa",
    )
    .run_commands(
        "pip install --default-timeout=600 torch==2.4.0 torchvision==0.19.0 --index-url https://download.pytorch.org/whl/cu118",
        "pip install --default-timeout=600 xformers==0.0.27.post2 --index-url https://download.pytorch.org/whl/cu118",
        "pip install wheel setuptools packaging psutil ninja",
        "pip install bpy==4.0.0 --extra-index-url https://download.blender.org/pypi/",
        "pip install flash-attn==2.5.9.post1 --no-build-isolation",
    )
    .pip_install(
        "rembg", "numpy<2", "pillow", "tqdm", "open3d",
        "trimesh", "opencv-python-headless", "easydict",
        "onnxruntime", "transformers<5", "plyfile", "xatlas", "pyvista",
        "pymeshfix", "igraph", "accelerate", "sentencepiece",
        "spconv-cu118", "diffusers==0.34.0", "scipy>=1.11.0",
        "safetensors", "huggingface-hub>=0.34.0", "boto3>=1.35.0",
        "fastapi[standard]>=0.115.0", "python-multipart",
    )
    .run_commands(
        f"git clone https://github.com/JAMESYJL/Nano3D.git {NANO3D_PATH} && cd {NANO3D_PATH} && git checkout {NANO3D_COMMIT}",
        f"pip install {NANO3D_PATH}/extensions/vox2seq --no-build-isolation",
        f"pip install git+https://github.com/EasternJournalist/utils3d.git@{UTILS3D_COMMIT}",
        "git clone https://github.com/NVlabs/nvdiffrast.git /tmp/nvdiffrast && pip install /tmp/nvdiffrast --no-build-isolation",
        "git clone https://github.com/autonomousvision/mip-splatting.git /tmp/mip-splatting && pip install /tmp/mip-splatting/submodules/diff-gaussian-rasterization/ --no-build-isolation",
        "git clone --recurse-submodules https://github.com/JeffreyXiang/diffoctreerast.git /tmp/diffoctreerast && pip install /tmp/diffoctreerast --no-build-isolation",
        "pip install kaolin -f https://nvidia-kaolin.s3.us-east-2.amazonaws.com/torch-2.4.0_cu118.html",
        f"PYTHONPATH={NANO3D_PATH} python -c \"import diff_gaussian_rasterization; import types,sys; p=types.ModuleType('inference'); p.__path__=['{NANO3D_PATH}/inference']; p.__package__='inference'; sys.modules['inference']=p; import bpy; from inference.model_utils import load_sparse_structure_encoder, inject_methods; from trellis.pipelines import TrellisImageTo3DPipeline; print('nano3d trellis imports ok')\"",
        gpu="A100",
    )
    .env(
        {
            "PYTHONPATH": NANO3D_PATH,
            "HF_HOME": NANO3D_HF_CACHE,
            "ATTN_BACKEND": "xformers",
            "SPARSE_ATTN_BACKEND": "xformers",
            "SPCONV_ALGO": "native",
            "PYTORCH_CUDA_ALLOC_CONF": "expandable_segments:True",
            "TORCH_CUDA_ARCH_LIST": "8.0",
        }
    )
)
