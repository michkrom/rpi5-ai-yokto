import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IMAGE = "yokto"
CONTAINER_NAME = "yocto-bg"
CONTAINER_USER = "yocto"
WORK_MOUNT = "/work"
LEVELS = ("core", "wayland", "chrome", "quake3")
LOCK_FILE = ROOT / ".build-lock"


def _level(core=False, wayland=False, weston=False, chrome=False, quake3=False):
    if quake3:
        return "quake3"
    if wayland or weston:
        return "wayland"
    if chrome:
        return "chrome"
    if core:
        return "core"
    return "core"


def _validate(level):
    if level not in LEVELS:
        raise ValueError(f"Unknown level '{level}'. Choose: {', '.join(LEVELS)}")
    return level


def _kas_args(level):
    return f'kas/base.yml:kas/{level}.yml'


# ── Lock file ─────────────────────────────────────────────────────────────

def _read_lock():
    """Read the lock file. Returns None if no lock or corrupt."""
    if not LOCK_FILE.exists():
        return None
    try:
        return json.loads(LOCK_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        LOCK_FILE.unlink(missing_ok=True)
        return None


def _write_lock(level, pid, op_type="build"):
    """Write the lock file."""
    LOCK_FILE.write_text(json.dumps({
        "level": level,
        "pid": pid,
        "type": op_type,
        "started": time.time(),
    }))


def _clear_lock():
    """Remove the lock file."""
    LOCK_FILE.unlink(missing_ok=True)


def _lock_alive(runner, lock):
    """Check if the locked process is still alive inside the container.

    runner: callable(cmd) -> stdout string.
    """
    if not lock:
        return False
    pid = lock.get("pid", 0)
    if not pid:
        return False  # No PID means non-detached or finished operation
    # Check if process exists AND is not a zombie (state Z)
    cmd = (
        f"docker exec {CONTAINER_NAME} bash -c "
        f"'st=$(ps -p {pid} -o state= 2>/dev/null); "
        f"test -n \"$st\" && test \"$st\" != Z && echo alive || echo dead'"
    )
    result = runner(cmd)
    return "alive" in result
