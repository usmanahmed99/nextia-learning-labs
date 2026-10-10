"""Print the computer that a measurement ran on, for the top of every benchmark result.

    python -m scripts.machine

A latency or a throughput means little without the machine and the workload: write both
next to every number.
"""

import ctypes
import os
import platform
import subprocess
import sys


def _run(cmd: list[str]) -> str:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=10).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def cpu_and_memory() -> tuple[str, float | None]:
    system = platform.system()
    if system == "Darwin":
        cpu = _run(["sysctl", "-n", "machdep.cpu.brand_string"])
        mem = _run(["sysctl", "-n", "hw.memsize"])
        return cpu, int(mem) / 2**30 if mem else None
    if system == "Linux":
        cpu = ""
        try:
            for line in open("/proc/cpuinfo", encoding="utf-8"):
                if line.startswith("model name"):
                    cpu = line.split(":", 1)[1].strip()
                    break
            for line in open("/proc/meminfo", encoding="utf-8"):
                if line.startswith("MemTotal"):
                    return cpu, int(line.split()[1]) / 2**20
        except OSError:
            pass
        return cpu, None
    if system == "Windows":

        class Status(ctypes.Structure):
            _fields_ = [
                ("length", ctypes.c_ulong),
                ("load", ctypes.c_ulong),
                ("total", ctypes.c_ulonglong),
                ("avail", ctypes.c_ulonglong),
                ("pf_total", ctypes.c_ulonglong),
                ("pf_avail", ctypes.c_ulonglong),
                ("v_total", ctypes.c_ulonglong),
                ("v_avail", ctypes.c_ulonglong),
                ("ext", ctypes.c_ulonglong),
            ]

        s = Status()
        s.length = ctypes.sizeof(Status)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(s))
        return platform.processor(), s.total / 2**30
    return platform.processor(), None


def describe() -> dict:
    cpu, mem = cpu_and_memory()
    docker = _run(
        ["docker", "info", "--format", "{{.ServerVersion}} {{.NCPU}} {{.MemTotal}}"]
    ).split()
    load = os.getloadavg()[0] if hasattr(os, "getloadavg") else None
    return {
        "os": f"{platform.system()} {platform.release()} ({platform.machine()})",
        "cpu": cpu or "unknown",
        "cores": os.cpu_count(),
        "memory_gb": round(mem, 1) if mem else None,
        "python": platform.python_version(),
        "docker": (
            f"Engine {docker[0]}, {docker[1]} CPUs, {int(docker[2]) / 2**30:.1f} GB"
            if len(docker) == 3
            else "not running"
        ),
        "load_1min": round(load, 2) if load is not None else None,
    }


def main() -> int:
    d = describe()
    print(f"Computer: {d['cpu']}, {d['cores']} cores, {d['memory_gb']} GB memory; {d['os']}")
    print(f"Python {d['python']}; Docker: {d['docker']}")
    if d["load_1min"] is not None:
        print(
            f"Load average (1 minute): {d['load_1min']} (other programs that use the CPU make "
            "the numbers worse)"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
