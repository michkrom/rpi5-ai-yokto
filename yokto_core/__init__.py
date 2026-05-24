import json
import time
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IMAGE = "yokto"
CONTAINER_NAME = "yocto-bg"
CONTAINER_USER = "yocto"
WORK_MOUNT = "/work"
LEVELS = ("base", "wayland", "games", "chrome")
LOCK_FILE = ROOT / ".build-lock"


def _level(base=False, wayland=False, weston=False, chrome=False, games=False):
    """Return the level string based on which level is requested.
    
    One-of enumeration: base -> wayland -> games -> chrome
    """
    if chrome:
        return "chrome"
    if games:
        return "games"
    if wayland or weston:
        return "wayland"
    if base:
        return "base"
    return "base"


def _validate(level):
    if level not in LEVELS:
        raise ValueError(f"Unknown level '{level}'. Choose: {', '.join(LEVELS)}")
    return level


def _kas_args(level):
    """Return appropriate config chain for level.
    
    Chain: base -> wayland -> games -> chrome
    """
    if level == "base":
        return "kas/base.yml"
    elif level == "wayland":
        return "kas/base.yml:kas/wayland.yml"
    elif level == "games":
        return "kas/base.yml:kas/wayland.yml:kas/games.yml"
    else:  # chrome
        return "kas/base.yml:kas/wayland.yml:kas/games.yml:kas/chrome.yml"


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


# ── SSH/SCP output filtering ─────────────────────────────────────────────

_SSH_IGNORE_PATTERNS = re.compile(
    "|".join([
        r"Warning: Permanently added .* to the list of known hosts",
        r"\*\* WARNING: connection is not using a post-quantum key exchange algorithm",
        r"\*\* This session may be vulnerable to .+ attacks",
        r"\*\* The server may need to be upgraded",
        r"https?://openssh\.com/pq\.html",
    ]),
    re.IGNORECASE
)


def _filter_ssh_output(text: str) -> str:
    """Filter known hosts and post-quantum warnings from SSH output."""
    if not text:
        return text
    lines = text.split('\n')
    filtered = [line for line in lines if not _SSH_IGNORE_PATTERNS.search(line)]
    return '\n'.join(filtered).strip()


def _ssh_opts() -> list:
    """Return SSH options list to suppress known hosts and warnings."""
    return ["-o", "UserKnownHostsFile=/dev/null", "-o", "StrictHostKeyChecking=no", "-o", "LogLevel=ERROR"]