"""GPU/NPU detection — pick best model+quantization for the hardware.

Detection is best-effort: probes well-known commands (nvidia-smi,
rocm-smi) and Apple Silicon / Qualcomm NPU markers.  Output drives a
``HardwareProfile`` that the model selector consumes.
"""

from __future__ import annotations

import platform
import shutil
import subprocess
from dataclasses import dataclass, field
from enum import StrEnum


class Accelerator(StrEnum):
    NONE = "none"
    CPU_AVX2 = "cpu_avx2"
    CUDA = "cuda"
    ROCM = "rocm"
    MPS = "mps"  # Apple Silicon
    QNN = "qnn"  # Qualcomm Hexagon
    INTEL_NPU = "intel_npu"


@dataclass(frozen=True, slots=True)
class HardwareProfile:
    accelerator: Accelerator
    vram_gb: float = 0.0
    cpu_cores: int = 0
    arch: str = ""

    def quantization_for_size(self, model_params_b: float) -> str:
        """Pick the right ggml/gguf quantization for this hardware + model size."""
        if self.accelerator in (Accelerator.CUDA, Accelerator.ROCM):
            if self.vram_gb >= model_params_b * 0.6:
                return "q5_K_M"
            if self.vram_gb >= model_params_b * 0.4:
                return "q4_K_M"
            return "q3_K_M"
        if self.accelerator is Accelerator.MPS:
            return "q4_K_M"  # 4-bit is the sweet spot on Apple Silicon
        if self.accelerator in (Accelerator.QNN, Accelerator.INTEL_NPU):
            return "q4_0"
        # CPU paths
        if model_params_b > 7:
            return "q4_K_M"
        return "q5_K_M"


@dataclass
class HardwareDetector:
    runner: object | None = field(default=None)  # callable(list[str]) -> str | None

    def _run(self, cmd: list[str]) -> str:
        if callable(self.runner):
            out = self.runner(cmd)
            return str(out or "")
        if not shutil.which(cmd[0]):
            return ""
        try:
            r = subprocess.run(cmd, capture_output=True, timeout=2)
        except (OSError, subprocess.SubprocessError):
            return ""
        if r.returncode != 0:
            return ""
        return r.stdout.decode(errors="replace")

    def detect(self) -> HardwareProfile:
        arch = platform.machine().lower()
        cores = _cpu_count()

        # NVIDIA
        out = self._run(["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"])
        if out:
            try:
                mb = int(out.strip().splitlines()[0])
                return HardwareProfile(
                    accelerator=Accelerator.CUDA,
                    vram_gb=mb / 1024,
                    cpu_cores=cores,
                    arch=arch,
                )
            except (ValueError, IndexError):
                pass

        # AMD ROCm
        if shutil.which("rocm-smi"):
            return HardwareProfile(accelerator=Accelerator.ROCM, cpu_cores=cores, arch=arch)

        # Apple Silicon
        if platform.system() == "Darwin" and arch.startswith("arm"):
            return HardwareProfile(accelerator=Accelerator.MPS, cpu_cores=cores, arch=arch)

        return HardwareProfile(
            accelerator=Accelerator.CPU_AVX2 if cores >= 4 else Accelerator.NONE,
            cpu_cores=cores,
            arch=arch,
        )


def _cpu_count() -> int:
    try:
        import os

        return os.cpu_count() or 0
    except Exception:  # noqa: BLE001
        return 0


def pick_model(profile: HardwareProfile, candidates: list[tuple[str, float]]) -> str:
    """Given (model_name, params_in_billions) candidates, pick the largest that fits.

    On NVIDIA / ROCm, gates on VRAM at q4_K_M; elsewhere, falls back to the
    smallest candidate.
    """
    sorted_candidates = sorted(candidates, key=lambda c: c[1], reverse=True)
    if profile.accelerator in (Accelerator.CUDA, Accelerator.ROCM):
        for name, params in sorted_candidates:
            if profile.vram_gb >= params * 0.6:
                return name
    if profile.accelerator is Accelerator.MPS:
        for name, params in sorted_candidates:
            if params <= 13:
                return name
    return sorted_candidates[-1][0] if sorted_candidates else ""


__all__ = ["Accelerator", "HardwareDetector", "HardwareProfile", "pick_model"]
