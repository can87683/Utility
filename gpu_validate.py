#!/usr/bin/env python3
# gpu_validation.py

import subprocess
import platform
import time
import sys


# --- Helper Functions ---
def run_command(command, success_msg, error_msg, capture_output=True, text=True):
    """Helper to run commands and handle success/error messages"""
    try:
        result = subprocess.run(command, capture_output=capture_output, text=text)
        if result.returncode == 0:
            print(success_msg)
            return result.stdout
        else:
            print(f"❌ {error_msg}")
            return None
    except Exception as e:
        print(f"❌ Error running {command[0]}: {e}")
        return None


def check_cuda():
    """Check for CUDA and related tools"""
    print("🧩 Checking CUDA installation...")

    # Check nvidia-smi
    nvidia_smi = run_command(
        ["nvidia-smi"],
        success_msg="✅ NVIDIA-SMI detected",
        error_msg="nvidia-smi not found"
    )
    if nvidia_smi:
        print(nvidia_smi.split("\n")[0])  # Print first line of output

    # Check nvcc
    nvcc_version = run_command(
        ["nvcc", "--version"],
        success_msg="✅ CUDA toolkit (nvcc) detected",
        error_msg="nvcc not installed (CUDA toolkit missing)"
    )
    if nvcc_version:
        line = next((l for l in nvcc_version.split("\n") if "release" in l), None)
        if line:
            print("✅ " + line)


def check_pytorch():
    """Check for PyTorch GPU support"""
    print("🔥 Checking PyTorch...")

    try:
        import torch
        print(f"PyTorch version: {torch.__version__}")

        if torch.cuda.is_available():
            print(f"✅ CUDA available: {torch.version.cuda}")
            print(f"🖥️ GPU: {torch.cuda.get_device_name(0)}")
            print(f"🧮 GPU Count: {torch.cuda.device_count()}")

            # Benchmark matmul
            start = time.time()
            x = torch.rand((4096, 4096), device='cuda')
            y = torch.mm(x, x)
            torch.cuda.synchronize()
            print(f"⚡ Matmul 4096x4096: {time.time() - start:.3f}s")
        else:
            print("❌ PyTorch GPU unavailable (CPU fallback)")

    except ImportError:
        print("❌ PyTorch not installed")


def check_tensorflow():
    """Check for TensorFlow GPU support"""
    print("🧠 Checking TensorFlow...")

    try:
        import tensorflow as tf
        print(f"TensorFlow version: {tf.__version__}")

        gpus = tf.config.list_physical_devices("GPU")
        if gpus:
            print(f"✅ GPU detected: {len(gpus)} device(s)")
            for gpu in gpus:
                print(f"   - {gpu.name}")

            # Benchmark matmul
            start = time.time()
            a = tf.random.normal([4096, 4096])
            b = tf.matmul(a, a)
            _ = b.numpy()
            print(f"⚡ Matmul 4096x4096: {time.time() - start:.3f}s")
        else:
            print("❌ TensorFlow GPU unavailable")

    except ImportError:
        print("❌ TensorFlow not installed")


def check_opencl():
    """Check for OpenCL support (optional)"""
    print("💡 Checking OpenCL (optional fallback)...")
    try:
        import pyopencl as cl
        plats = cl.get_platforms()
        print(f"✅ {len(plats)} OpenCL platform(s):")
        for p in plats:
            print(f"   - {p.name} ({p.vendor})")
    except ImportError:
        print("⚠️ pyopencl not installed (optional)")
    except Exception as e:
        print(f"❌ OpenCL error: {e}")


# --- Main Execution ---
def run_gpu_validation():
    print("=" * 60)
    print("🔍 GPU VALIDATION & BENCHMARK TOOL")
    print("=" * 60)
    print(f"OS: {platform.system()} {platform.release()} ({platform.platform()})")
    print(f"Python: {platform.python_version()}")
    print()

    # Run checks sequentially
    check_cuda()
    check_pytorch()
    check_tensorflow()
    check_opencl()

    print("=" * 60)
    print("🏁 GPU VALIDATION COMPLETE")
    print("=" * 60)
    print("If all ✅ checks passed, your system is GPU-ready 🚀")


# Run the validation process
if __name__ == "__main__":
    run_gpu_validation()
