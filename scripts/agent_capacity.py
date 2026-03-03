import ctypes
import os
from typing import Dict


MB = 1024 * 1024


def _env_int(name: str, default: int) -> int:
    raw = str(os.getenv(name, "")).strip()
    if not raw:
        return int(default)
    try:
        return int(raw)
    except Exception:
        return int(default)


def _memory_windows_mb() -> tuple[int, int]:
    class MEMORYSTATUSEX(ctypes.Structure):
        _fields_ = [
            ("dwLength", ctypes.c_ulong),
            ("dwMemoryLoad", ctypes.c_ulong),
            ("ullTotalPhys", ctypes.c_ulonglong),
            ("ullAvailPhys", ctypes.c_ulonglong),
            ("ullTotalPageFile", ctypes.c_ulonglong),
            ("ullAvailPageFile", ctypes.c_ulonglong),
            ("ullTotalVirtual", ctypes.c_ulonglong),
            ("ullAvailVirtual", ctypes.c_ulonglong),
            ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
        ]

    stat = MEMORYSTATUSEX()
    stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):
        return 0, 0
    return int(stat.ullTotalPhys // MB), int(stat.ullAvailPhys // MB)


def _memory_linux_mb() -> tuple[int, int]:
    total_kb = 0
    avail_kb = 0
    try:
        with open("/proc/meminfo", "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("MemTotal:"):
                    total_kb = int(line.split()[1])
                elif line.startswith("MemAvailable:"):
                    avail_kb = int(line.split()[1])
    except Exception:
        return 0, 0
    if total_kb <= 0:
        return 0, 0
    return int(total_kb // 1024), int(avail_kb // 1024)


def detect_capacity() -> Dict[str, int]:
    logical_cpus = max(1, int(os.cpu_count() or 1))
    total_mb = 0
    free_mb = 0
    if os.name == "nt":
        total_mb, free_mb = _memory_windows_mb()
    elif os.path.exists("/proc/meminfo"):
        total_mb, free_mb = _memory_linux_mb()
    return {
        "logical_cpus": logical_cpus,
        "total_memory_mb": max(0, int(total_mb)),
        "free_memory_mb": max(0, int(free_mb)),
    }


def recommend_workers(task: str = "mixed") -> Dict[str, int]:
    cap = detect_capacity()
    cpu_limit = max(1, int(cap.get("logical_cpus", 1)))
    free_mb = max(0, int(cap.get("free_memory_mb", 0)))

    reserve_mb = max(0, _env_int("AUTO_AGENT_RESERVED_MB", 2048))
    hard_cap = max(1, _env_int("AUTO_AGENT_HARD_CAP", cpu_limit))

    per_worker_mb_map = {
        "io": 384,
        "mixed": 512,
        "cpu": 1024,
    }
    per_worker_mb = per_worker_mb_map.get(str(task or "mixed").strip().lower(), 512)
    per_worker_mb = max(128, _env_int("AUTO_AGENT_PER_WORKER_MB", per_worker_mb))

    if free_mb > reserve_mb:
        mem_limit = max(1, int((free_mb - reserve_mb) // per_worker_mb))
    else:
        mem_limit = 1

    auto_workers = max(1, min(cpu_limit, mem_limit, hard_cap))
    env_force = _env_int("AUTO_AGENT_MAX_WORKERS", 0)
    effective = auto_workers if env_force <= 0 else max(1, min(env_force, hard_cap))

    out = dict(cap)
    out.update(
        {
            "reserve_mb": reserve_mb,
            "per_worker_mb": per_worker_mb,
            "cpu_limit": cpu_limit,
            "mem_limit": mem_limit,
            "hard_cap": hard_cap,
            "auto_workers": auto_workers,
            "env_force_workers": max(0, env_force),
            "effective_workers": effective,
        }
    )
    return out

