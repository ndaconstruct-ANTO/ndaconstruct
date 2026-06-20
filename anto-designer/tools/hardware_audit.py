"""Audit matériel d'Anto Designer — À LANCER SUR VOTRE PROPRE ORDINATEUR.

Aucune dépendance : double-cliquez ou exécutez `python hardware_audit.py`.
Le script lit uniquement les caractéristiques de la machine et affiche un
rapport + un verdict indicatif. Il n'envoie rien sur Internet.
"""

from __future__ import annotations

import platform
import shutil
import subprocess
import sys


def _ram_gb() -> float:
    try:
        if platform.system() == "Windows":
            import ctypes

            class MS(ctypes.Structure):
                _fields_ = [("dwLength", ctypes.c_ulong),
                            ("dwMemoryLoad", ctypes.c_ulong),
                            ("ullTotalPhys", ctypes.c_ulonglong),
                            ("ullAvailPhys", ctypes.c_ulonglong),
                            ("ullTotalPageFile", ctypes.c_ulonglong),
                            ("ullAvailPageFile", ctypes.c_ulonglong),
                            ("ullTotalVirtual", ctypes.c_ulonglong),
                            ("ullAvailVirtual", ctypes.c_ulonglong),
                            ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
            ms = MS(); ms.dwLength = ctypes.sizeof(MS)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(ms))
            return round(ms.ullTotalPhys / 1024**3, 1)
        # Linux / macOS
        if hasattr(__import__("os"), "sysconf"):
            import os
            return round(os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")
                         / 1024**3, 1)
    except Exception:
        pass
    return 0.0


def _gpu() -> str:
    sysname = platform.system()
    try:
        if shutil.which("nvidia-smi"):
            out = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total",
                                  "--format=csv,noheader"],
                                 capture_output=True, text=True, timeout=8)
            if out.returncode == 0 and out.stdout.strip():
                return "NVIDIA: " + out.stdout.strip().replace("\n", " | ")
        if sysname == "Windows":
            out = subprocess.run(
                ["wmic", "path", "win32_VideoController", "get", "name"],
                capture_output=True, text=True, timeout=8)
            names = [l.strip() for l in out.stdout.splitlines() if l.strip()
                     and "Name" not in l]
            if names:
                return " | ".join(names)
    except Exception:
        pass
    return "GPU non détecté automatiquement"


def main() -> int:
    ram = _ram_gb()
    disk = shutil.disk_usage(".")
    gpu = _gpu()
    cpu = platform.processor() or "inconnu"
    try:
        import os
        cores = os.cpu_count() or 0
    except Exception:
        cores = 0

    print("=" * 60)
    print(" ANTO DESIGNER — Audit matériel (votre ordinateur)")
    print("=" * 60)
    print(f"OS            : {platform.system()} {platform.release()} ({platform.machine()})")
    print(f"Python        : {sys.version.split()[0]}")
    print(f"CPU           : {cpu}")
    print(f"Cœurs logiques: {cores}")
    print(f"RAM totale    : {ram} Go")
    print(f"Disque libre  : {round(disk.free / 1024**3, 1)} Go / {round(disk.total/1024**3,1)} Go")
    print(f"Carte graphique: {gpu}")
    print("-" * 60)

    # Verdict indicatif.
    layers_ok = ram >= 2 and disk.free / 1024**3 >= 2
    gpu_ai = "NVIDIA" in gpu
    print("VERDICT INDICATIF :")
    if layers_ok:
        print("  • Génération par CALQUES (cœur d'Anto Designer) : OUI, fluide.")
    else:
        print("  • Génération par calques : possible mais ressources limitées.")
    if gpu_ai:
        print("  • IA locale optionnelle (Stable Diffusion) : POSSIBLE (GPU NVIDIA).")
    else:
        print("  • IA locale optionnelle : limitée/lente sans GPU NVIDIA dédié.")
    print("=" * 60)
    print("Copiez ce rapport et envoyez-le pour un audit personnalisé.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
