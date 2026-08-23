#!/usr/bin/env python3
"""
Shared helpers for the ai-scripts bundle (ai-menu, llama-chat, langchain-chat).

Centralizes the small runtime helpers that used to be duplicated across the
scripts: locating model files and the llama.cpp binaries, RAM detection,
power-safe thread caps and companion-script lookup.

All path/binary lookups are flexible so the same code works when a script is
run from the repo/unpackaged (no sudo) or installed under /usr/bin in the
image. Env overrides always win.
"""

import ipaddress
import json
import os
import shutil
import socket
import subprocess
import time
import urllib.request
from pathlib import Path


def models_dir():
    """Pick a writable model store directory.

    Priority: AI_MODELS_DIR env override, then /usr/share/models (created
    1777 world-writable by the image's ai-scripts recipe so any user can add
    files), then a per-user XDG dir (for running unpackaged on a normal
    desktop where /usr is not writable). Always probes that the candidate is
    actually writable before returning it.
    """
    explicit = os.environ.get("AI_MODELS_DIR")
    if explicit:
        return Path(explicit)
    for cand in [Path("/usr/share/models"),
                 Path(os.environ.get("XDG_DATA_HOME",
                       str(Path.home() / ".local" / "share"))) / "models"]:
        try:
            cand.mkdir(parents=True, exist_ok=True)
            probe = cand / ".write-test"
            probe.write_text("")
            probe.unlink()
            return cand
        except OSError:
            continue
    return Path("/usr/share/models")  # unreachable; lets callers report


def binary(name, env_key=None):
    """Locate an executable by basename.

    Priority: explicit env override, then PATH, then a user's own llama.cpp
    build (~/llama.cpp/build/bin), then /usr/bin. Returns a str path or None.
    """
    if env_key:
        env = os.environ.get(env_key)
        if env:
            return env
    hit = shutil.which(name)
    if hit:
        return hit
    for base in (Path.home() / "llama.cpp" / "build" / "bin",
                 Path("/usr/bin")):
        cand = base / name
        if cand.is_file():
            return str(cand)
    return None


def companion_script(name, env_key=None):
    """Locate a companion CLI script shipped in the same ai-scripts bundle.

    Checks the directory next to this utils module first (covers the installed
    /usr/bin case and running straight from a repo files/ dir), then visible
    via env override. Returns a Path.
    """
    here = Path(__file__).resolve().parent
    cand = here / name
    if cand.is_file():
        return cand
    env = os.environ.get(env_key) if env_key else None
    return Path(env) if env else cand  # cand path lets callers report missing


def total_ram_gb():
    """Total RAM in GB, rounded to 0.1, from /proc/meminfo."""
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemTotal:"):
                return round(int(line.split()[1]) / 1024 / 1024, 1)
    except Exception:
        pass
    return 4.0


def ram_tier(ram_gb):
    """RAM tier used by the model catalogue ('4g' or '8g')."""
    return "8g" if ram_gb >= 6.0 else "4g"


def thread_cap():
    """Power-safe CPU thread count (brownout mitigation on Pi 5).

    Defaults to min(nproc-1, 3) but at least 2; AI_THREADS overrides.
    """
    try:
        n = int(os.environ.get("AI_THREADS", "0"))
        if n > 0:
            return n
        n = (os.cpu_count() or 4) - 1
    except Exception:
        n = 3
    return max(2, min(n, 3))


def local_ip():
    """Best-effort IPv4 address of the first non-loopback interface."""
    try:
        out = subprocess.run(["ip", "-4", "addr", "show"],
                             capture_output=True, text=True, timeout=3).stdout
        for line in out.splitlines():
            line = line.strip()
            if line.startswith("inet ") and "127." not in line:
                return line.split()[1].split("/")[0]
    except Exception:
        pass
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        if ip:
            return ip
    except Exception:
        pass
    return "unknown"


def server_reachable(host, port, timeout=1.5):
    """Return True if a server accepts a TCP connection on host:port."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def server_ready(host, port, model_loaded=None, timeout=1.5):
    """Probe an OpenAI-compatible llama-server and return (ok, model).

    Uses GET /health (202 = model still loading, 200 = ready) and reads
    /props to return the loaded model filename. Returns (False, None) if no
    HTTP answer, (False, model) if the server is up but the model differs
    (or still loading), or (True, model) when it is serving the requested
    model. Passing model_loaded allows a strict "is THIS model ready" check.
    """
    base = "http://%s:%d" % (host, port)
    try:
        with urllib.request.urlopen(base + "/health", timeout=timeout) as r:
            healthy = r.status == 200
        try:
            with urllib.request.urlopen(base + "/props", timeout=timeout) as r2:
                props = json.loads(r2.read().decode() or "{}")
                model = (props.get("total_slots") and props.get("model_path")
                         or props.get("default_generation_settings", {}).get("model")
                         or props.get("model") or "")
        except Exception:
            model = ""
    except Exception:
        return False, ""
    if model_loaded is None:
        return healthy, model
    if healthy and (not model_loaded or".gguf" not in model_loaded):
        return healthy, model or model_loaded
    wanted = Path(model_loaded).name if model_loaded else ""
    return (wanted in model), model  # healthy XOR wanted-match


def wait_server_ready(host, port, model_loaded, timeout=1.5, tries=60):
    """Poll until llama-server health returns 200 and reports the requested
    model (or gives up). Returns (ok, model). Mirrors the old TCP-poll loop
    but waits for an actual HTTP-ready state, closing the start race where the
    socket opens before the model is loaded."""
    for _ in range(tries):
        ok, model = server_ready(host, port, model_loaded=model_loaded,
                                 timeout=timeout)
        if ok:
            return True, model
        time.sleep(1)
    return False, ""
