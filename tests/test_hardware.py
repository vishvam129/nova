"""Tests for nova.hardware."""

from __future__ import annotations

from unittest.mock import patch

from nova.hardware import (
    Accelerator,
    HardwareDetector,
    HardwareProfile,
    pick_model,
)


def test_quantization_cuda_high_vram() -> None:
    p = HardwareProfile(accelerator=Accelerator.CUDA, vram_gb=24)
    assert p.quantization_for_size(13) == "q5_K_M"


def test_quantization_cuda_medium_vram() -> None:
    p = HardwareProfile(accelerator=Accelerator.CUDA, vram_gb=6)
    assert p.quantization_for_size(13) == "q4_K_M"


def test_quantization_cuda_low_vram() -> None:
    p = HardwareProfile(accelerator=Accelerator.CUDA, vram_gb=4)
    assert p.quantization_for_size(13) == "q3_K_M"


def test_quantization_mps() -> None:
    p = HardwareProfile(accelerator=Accelerator.MPS)
    assert p.quantization_for_size(7) == "q4_K_M"


def test_quantization_npu() -> None:
    p = HardwareProfile(accelerator=Accelerator.QNN)
    assert p.quantization_for_size(3) == "q4_0"


def test_quantization_cpu_large_model() -> None:
    p = HardwareProfile(accelerator=Accelerator.CPU_AVX2)
    assert p.quantization_for_size(13) == "q4_K_M"


def test_quantization_cpu_small_model() -> None:
    p = HardwareProfile(accelerator=Accelerator.CPU_AVX2)
    assert p.quantization_for_size(3) == "q5_K_M"


def test_detect_nvidia() -> None:
    def runner(cmd: list[str]) -> str:
        if cmd[0] == "nvidia-smi":
            return "24576\n"  # 24 GB
        return ""

    d = HardwareDetector(runner=runner)
    p = d.detect()
    assert p.accelerator is Accelerator.CUDA
    assert p.vram_gb == 24.0


def test_detect_no_gpu_falls_back_to_cpu() -> None:
    d = HardwareDetector(runner=lambda cmd: "")
    with (
        patch("nova.hardware.shutil.which", return_value=None),
        patch("nova.hardware.platform.system", return_value="Linux"),
    ):
        p = d.detect()
    assert p.accelerator in {Accelerator.CPU_AVX2, Accelerator.NONE}


def test_pick_model_cuda_picks_largest_fitting() -> None:
    p = HardwareProfile(accelerator=Accelerator.CUDA, vram_gb=20)
    name = pick_model(p, [("small", 7), ("medium", 13), ("large", 70)])
    # 70B needs ~42 GB; 13B needs ~7.8 GB → pick 13B
    assert name == "medium"


def test_pick_model_cpu_picks_smallest() -> None:
    p = HardwareProfile(accelerator=Accelerator.CPU_AVX2)
    name = pick_model(p, [("small", 3), ("medium", 13)])
    assert name == "small"


def test_pick_model_empty() -> None:
    p = HardwareProfile(accelerator=Accelerator.NONE)
    assert pick_model(p, []) == ""
