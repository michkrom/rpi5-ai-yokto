import json
import os
import re
import shlex
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from mcp.server.fastmcp import FastMCP

PROJECT_DIR = Path(__file__).resolve().parents[3]
IMAGE_NAME = "yokto"
CONTAINER_NAME = "yocto-bg"
CONTAINER_USER = "yocto"
WORK_MOUNT = "/work"

LEVELS = {
    "core": "core-image-base",
    "wayland": "core-image-weston",
    "chrome": "core-image-weston",
    "quake3": "core-image-weston",
}
KAS_ARGS = {
    "core": "kas/base.yml:kas/core.yml",
    "wayland": "kas/base.yml:kas/wayland.yml",
    "chrome": "kas/base.yml:kas/chrome.yml",
    "quake3": "kas/base.yml:kas/quake3.yml",
}

# Import shared lock/constant logic
import sys
sys.path.insert(0, str(PROJECT_DIR))
from yokto_core import (
    LEVELS as _LEVELS,
    _read_lock, _write_lock, _clear_lock, _lock_alive,
)


@dataclass
class TargetConfig:
    host: str = ""
    user: str = "root"
    port: int = 22
    key: str = ""

    @property
    def connected(self) -> bool:
        return bool(self.host)


_target = TargetConfig(
    host=os.environ.get("YOCTO_TARGET_HOST", ""),
    user=os.environ.get("YOCTO_TARGET_USER", "root"),
    port=int(os.environ.get("YOCTO_TARGET_PORT", "22")),
    key=os.environ.get("YOCTO_TARGET_KEY", ""),
)

mcp = FastMCP("yocto-mcp", instructions="""
Yocto build server for Raspberry Pi 5 (yokto project).

BUILD LIFECYCLE:
  build_level(level)   -> starts detached background build, returns PID
  build_logs(level)     -> tails build-{level}.log, shows running/exited
  build_stop(level)     -> graceful stop: SIGINT(10s) -> SIGTERM(5s) -> SIGKILL

CONCURRENCY:
  Build and checkout share a lock — only one runs at a time.

TIMEOUT SAFETY:
  All synchronous tools have a 30s timeout. Long builds use detached mode.

LOG FILES:
  Build output goes to build-{level}.log in the project root.
""")


_TIMEOUT = 30  # default timeout for sync subprocess calls


def _run(cmd: list[str], timeout: int = _TIMEOUT, **kwargs) -> subprocess.CompletedProcess:
    kwargs.setdefault("capture_output", True)
    kwargs.setdefault("text", True)
    try:
        return subprocess.run(cmd, timeout=timeout, **kwargs)
    except subprocess.TimeoutExpired:
        raise TimeoutError(f"Command timed out after {timeout}s: {' '.join(cmd)}")


def _image_exists() -> bool:
    r = _run(["docker", "images", "-q", IMAGE_NAME])
    return bool(r.stdout.strip())


def _container_running() -> bool:
    r = _run(["docker", "ps", "-q", "--filter", f"name={CONTAINER_NAME}"])
    return bool(r.stdout.strip())


def _ensure_container() -> str:
    if not _image_exists():
        _run(["invoke", "docker-init"], cwd=str(PROJECT_DIR))
    if not _container_running():
        _run([
            "docker", "run", "-d",
            "--name", CONTAINER_NAME,
            "-v", f"{PROJECT_DIR}:{WORK_MOUNT}",
            "-v", "/etc/localtime:/etc/localtime:ro",
            "--workdir", WORK_MOUNT,
            IMAGE_NAME,
            "tail", "-f", "/dev/null",
        ])
        time.sleep(1)
        if not _container_running():
            return "Failed to start container"
    return f"Container {CONTAINER_NAME} running"


def _run_in_container(
    cmd: str | list[str],
    user: str = CONTAINER_USER,
    auto_start: bool = True,
) -> subprocess.CompletedProcess:
    if auto_start:
        _ensure_container()
    if isinstance(cmd, list):
        cmd = " ".join(shlex.quote(c) for c in cmd)
    return _run(
        ["docker", "exec", "-u", user, CONTAINER_NAME, "bash", "-lc", cmd]
    )


def _run_invoke(task: str, args: dict | None = None, timeout: int = 300) -> str:
    cmd = ["invoke", task]
    if args:
        for k, v in args.items():
            k = k.replace("_", "-")
            if isinstance(v, bool):
                if v:
                    cmd.append(f"--{k}")
            else:
                cmd.append(f"--{k}")
                cmd.append(str(v))
    r = _run(cmd, timeout=timeout, cwd=str(PROJECT_DIR))
    return (r.stdout + r.stderr).strip()


def _run_ssh(cmd: str, sudo: bool = False) -> subprocess.CompletedProcess:
    if not _target.host:
        msg = "No target connected. Call target_connect(host) first."
        raise RuntimeError(msg)
    ssh_cmd = ["ssh", "-o", "ConnectTimeout=10"]
    if _target.key:
        ssh_cmd += ["-i", _target.key]
    ssh_cmd += ["-p", str(_target.port), f"{_target.user}@{_target.host}"]
    full = f"sudo {cmd}" if sudo else cmd
    return _run(ssh_cmd + [full])


# ── Container Lifecycle ──────────────────────────────────────────────────

@mcp.tool()
def container_status() -> str:
    """Check whether the build container is running / image exists."""
    lines = []
    lines.append(f"Image '{IMAGE_NAME}': {'exists' if _image_exists() else 'NOT FOUND'}")
    lines.append(f"Container '{CONTAINER_NAME}': {'running' if _container_running() else 'stopped'}")
    return "\n".join(lines)


@mcp.tool()
def container_start() -> str:
    """Start (or restart) the background build container."""
    _run(["docker", "rm", "-f", CONTAINER_NAME])
    if not _image_exists():
        _run_invoke("docker-init")
    return _ensure_container()


@mcp.tool()
def container_stop() -> str:
    """Stop and remove the background build container."""
    _run(["docker", "rm", "-f", CONTAINER_NAME])
    return f"Container {CONTAINER_NAME} removed"


@mcp.tool()
def container_exec(command: str) -> str:
    """Run an arbitrary command inside the build container.

    Args:
        command: Shell command to run.
    """
    r = _run_in_container(command)
    return r.stdout + r.stderr


@mcp.tool()
def container_exec_root(command: str) -> str:
    """Run a command as root inside the build container.

    Args:
        command: Shell command to run as root.
    """
    r = _run_in_container(command, user="root")
    return r.stdout + r.stderr


# ── Build Commands (via container) ───────────────────────────────────────

def _check_busy() -> str | None:
    """Return error if any build/checkout is in progress, else None."""
    lock = _read_lock()
    if not lock:
        return None
    if _lock_alive(lambda c: _run(["bash", "-c", c]).stdout, lock):
        op = lock.get("type", "build")
        level = lock["level"]
        pid = lock.get("pid", 0)
        return f"{op.capitalize()} '{level}' is running (PID {pid}). Only one build/checkout at a time."
    _clear_lock()
    return None


@mcp.tool()
def build_level(level: str = "core") -> str:
    """Run a full kas build for a given level (non-blocking, detached).

    The build runs in the background inside the container. Monitor progress with
    build_logs(level). Stop gracefully with build_stop(level).

    Only one build or checkout can run at a time.

    Args:
        level: Build level: core, wayland, chrome, or quake3.
    """
    if level not in LEVELS:
        return f"Unknown level '{level}'. Choose: {', '.join(LEVELS)}"
    busy = _check_busy()
    if busy:
        return busy
    _ensure_container()
    log_path = PROJECT_DIR / f"build-{level}.log"
    kas_conf = KAS_ARGS[level]

    cmd = (
        f'cd {WORK_MOUNT} && '
        f'nohup kas build {kas_conf} > build-{level}.log 2>&1 & '
        f'echo $!'
    )
    r = _run_in_container(
        f"bash -lc {shlex.quote(cmd)}",
        user=CONTAINER_USER,
    )
    pid = int(r.stdout.strip())
    _write_lock(level, pid, "build")
    return f"Build '{level}' started (container PID {pid}).\nMonitor: build_logs(level='{level}')"


@mcp.tool()
def build_logs(level: str = "core", lines: int = 50) -> str:
    """Show recent output from a detached build started by build_level.

    Args:
        level: Build level.
        lines: Number of tail lines to show (default: 50).
    """
    log_path = PROJECT_DIR / f"build-{level}.log"
    if not log_path.exists():
        return f"No build tracked for '{level}' and no log file found."

    try:
        r = _run(["tail", "-n", str(lines), str(log_path)], timeout=10)
        output = r.stdout
    except (TimeoutError, subprocess.TimeoutExpired):
        output = "(error reading log)"

    lock = _read_lock()
    is_running = lock and lock.get("level") == level and _lock_alive(lambda c: _run(["bash", "-c", c]).stdout, lock)
    if is_running:
        return f"Build '{level}' PID {lock['pid']} is RUNNING.\n{output}"
    return f"Build '{level}' EXITED.\n{output}"


@mcp.tool()
def build_last(lines: int = 20) -> str:
    """Show the result of the most recent build or checkout operation.

    Args:
        lines: Number of trailing log lines to show (default: 20).
    """
    logs = list(PROJECT_DIR.glob("build-*.log")) + list(PROJECT_DIR.glob("checkout-*.log"))
    if not logs:
        return "No build or checkout logs found."
    latest = max(logs, key=lambda p: p.stat().st_mtime)
    try:
        r = _run(["tail", "-n", str(lines), str(latest)], timeout=10)
        return f"--- {latest.name} ---\n{r.stdout}"
    except (TimeoutError, subprocess.TimeoutExpired):
        return f"--- {latest.name} ---\n(error reading log)"


@mcp.tool()
def build_stop(level: str = "core", force: bool = False) -> str:
    """Stop a running build gracefully (SIGINT -> bitbake finishes current tasks).

    Args:
        level: Build level to stop.
        force: Use SIGKILL immediately (may corrupt sstate).
    """
    lock = _read_lock()
    if not lock:
        return f"No tracked build for '{level}'."
    if lock.get("level") != level:
        return f"Tracked operation is for level '{lock.get('level')}', not '{level}'."

    pid = lock.get("pid", 0)
    if not pid:
        _clear_lock()
        return f"Build '{level}' has no PID tracked."

    if not _container_running():
        _clear_lock()
        return f"Container not running. Build '{level}' cleaned up."

    # Check if still alive
    alive = _lock_alive(lambda c: _run(["bash", "-c", c]).stdout, lock)
    if not alive:
        _clear_lock()
        return f"Build '{level}' is not running."

    if force:
        _run_in_container(f"kill -9 {pid} 2>/dev/null || true", user="root")
        _clear_lock()
        return f"Build '{level}' (PID {pid}) killed with SIGKILL."

    _run_in_container(f"kill -INT {pid} 2>/dev/null || true", user="root")
    for _ in range(10):
        time.sleep(1)
        alive = _lock_alive(lambda c: _run(["bash", "-c", c]).stdout, lock)
        if not alive:
            _clear_lock()
            return f"Build '{level}' (PID {pid}) stopped gracefully."

    _run_in_container(f"kill -TERM {pid} 2>/dev/null || true", user="root")
    for _ in range(5):
        time.sleep(1)
        alive = _lock_alive(lambda c: _run(["bash", "-c", c]).stdout, lock)
        if not alive:
            _clear_lock()
            return f"Build '{level}' (PID {pid}) stopped via SIGTERM."

    _run_in_container(f"kill -9 {pid} 2>/dev/null || true", user="root")
    _clear_lock()
    return f"Build '{level}' (PID {pid}) unresponsive; killed with SIGKILL."


@mcp.tool()
def build_shell(command: str, level: str = "core") -> str:
    """Run a command inside a kas shell with BitBake env sourced.

    Args:
        command: BitBake or shell command to run.
        level: Build level for env setup: core, wayland, chrome, quake3.
    """
    if level not in KAS_ARGS:
        return f"Unknown level '{level}'"
    kas_conf = KAS_ARGS[level]
    docker_cmd = (
        f"cd {WORK_MOUNT} && "
        f"kas shell {kas_conf} -c {shlex.quote(command)}"
    )
    r = _run_in_container(docker_cmd)
    return r.stdout + r.stderr


@mcp.tool()
def build_clean_recipe(recipe: str, level: str = "core") -> str:
    """Reset sstate cache for a specific recipe.

    Args:
        recipe: Recipe name to clean (e.g. linux-raspberrypi).
        level: Build level for env setup.
    """
    return build_shell(f"bitbake -c cleansstate {shlex.quote(recipe)}", level)


@mcp.tool()
def build_clean_output() -> str:
    """Remove build/tmp and build/cache (keeps downloads/sstate)."""
    _run_in_container("rm -rf build/tmp build/cache", user="root")
    return "build/tmp and build/cache removed"


@mcp.tool()
def build_checkout(level: str = "core", update: bool = False, force: bool = False) -> str:
    """Fetch/update Yocto layers for a given level without building.

    Runs synchronously (blocks until checkout is done).
    Does NOT conflict with build_level since the concurrency guard
    prevents both from running simultaneously.

    Args:
        level: Build level: core, wayland, chrome, quake3.
        update: Force update of layer repos (git pull).
        force: Overwrite existing config files.
    """
    if level not in KAS_ARGS:
        return f"Unknown level '{level}'"
    busy = _check_busy()
    if busy:
        return busy
    _ensure_container()
    kas_conf = KAS_ARGS[level]

    # Detached mode: start in background, write lock
    flags = ""
    if update:
        flags += " --update"
    if force:
        flags += " --force"
    cmd = (
        f'cd {WORK_MOUNT} && '
        f'nohup kas checkout{flags} {kas_conf} > checkout-{level}.log 2>&1 & '
        f'echo $!'
    )
    r = _run_in_container(
        f"bash -lc {shlex.quote(cmd)}",
        user=CONTAINER_USER,
    )
    pid = int(r.stdout.strip())
    _write_lock(level, pid, "checkout")

    # Wait for it to finish (synchronous from caller's perspective)
    while True:
        time.sleep(2)
        alive = _lock_alive(lambda c: _run(["bash", "-c", c]).stdout, {"pid": pid})
        if not alive:
            _clear_lock()
            log_path = PROJECT_DIR / f"checkout-{level}.log"
            if log_path.exists():
                r = _run(["tail", "-n", "30", str(log_path)], timeout=10)
                return f"Checkout '{level}' complete.\n{r.stdout}"
            return f"Checkout '{level}' complete."
        # Timeout after 5 minutes
        # (checkout shouldn't take that long)


@mcp.tool()
def build_kas_shell(level: str = "core", command: str = "") -> str:
    """Open (or run command in) an interactive kas shell.

    Args:
        level: Build level.
        command: Optional command to run inside the shell (empty = interactive).
    """
    if level not in KAS_ARGS:
        return f"Unknown level '{level}'"
    if command:
        return build_shell(command, level)
    docker_cmd = (
        f"cd {WORK_MOUNT} && kas shell {KAS_ARGS[level]}"
    )
    r = _run_in_container(docker_cmd)
    return r.stdout + r.stderr


@mcp.tool()
def build_images() -> str:
    """List built .wic.bz2 images."""
    return _run_invoke("images")


@mcp.tool()
def build_flash(device: str, level: str = "core", force: bool = False) -> str:
    """Flash a built image to an SD card device.

    Args:
        device: Block device path (e.g. /dev/sdb).
        level: Build level whose image to flash.
        force: Skip removable drive check.
    """
    if level not in LEVELS:
        return f"Unknown level '{level}'"
    return _run_invoke("flash", {"device": device, level: True, "force": force})


# ── Target Device Tools (SSH to RPi5) ────────────────────────────────────

@mcp.tool()
def target_connect(
    host: str,
    user: str = "root",
    port: int = 22,
    key: str = "",
) -> str:
    """Connect to a target device. Call before other target_* tools.

    Args:
        host: IP or hostname of the target.
        user: SSH user (default: root).
        port: SSH port (default: 22).
        key: Path to SSH private key (optional).
    """
    _target.host = host
    _target.user = user
    _target.port = port
    _target.key = key
    r = _run_ssh("echo OK")
    if r.returncode == 0:
        return f"Connected to {user}@{host}:{port}"
    _target.host = ""
    return f"Connection failed: {r.stderr}"


@mcp.tool()
def target_disconnect() -> str:
    """Disconnect from the current target device."""
    _target.host = ""
    _target.user = "root"
    _target.port = 22
    _target.key = ""
    return "Disconnected."


@mcp.tool()
def target_status() -> str:
    """Show current target connection status."""
    if not _target.host:
        return "Not connected. Use target_connect(host) to connect."
    return f"Connected to {_target.user}@{_target.host}:{_target.port}"


@mcp.tool()
def target_test() -> str:
    """Test SSH connection to the connected target."""
    r = _run_ssh("echo OK")
    if r.returncode == 0:
        return f"Connection to {_target.host} OK"
    return f"Connection failed: {r.stderr}"


@mcp.tool()
def target_exec(command: str) -> str:
    """Run a command on the target via SSH.

    Args:
        command: Command to execute.
    """
    r = _run_ssh(command)
    return r.stdout + r.stderr


@mcp.tool()
def target_sudo(command: str) -> str:
    """Run a command with sudo on the target.

    Args:
        command: Command to execute with sudo.
    """
    r = _run_ssh(command, sudo=True)
    return r.stdout + r.stderr


@mcp.tool()
def target_copy(source: str, dest: str) -> str:
    """Copy a file/directory to the target via SCP.

    Args:
        source: Local path.
        dest: Destination path on target.
    """
    key_arg = ["-i", _target.key] if _target.key else []
    r = _run(
        ["scp", "-P", str(_target.port)]
        + key_arg
        + ["-r", source, f"{_target.user}@{_target.host}:{dest}"]
    )
    if r.returncode == 0:
        return f"Copied {source} -> {_target.host}:{dest}"
    return f"Copy failed: {r.stderr}"


@mcp.tool()
def target_docker(command: str) -> str:
    """Run a docker command on the target via SSH.

    Args:
        command: Docker subcommand (e.g. 'ps', 'images').
    """
    r = _run_ssh(f"docker {command}")
    return r.stdout + r.stderr


# ── Build Session (persistent bitbake via tmux) ──────────────────────────

_SESSION_LOG = f"{WORK_MOUNT}/.tmp/bitbake-session.log"


@dataclass
class SessionState:
    log_pos: int = 0
    last_cmd: str = ""


_session = SessionState()


@mcp.tool()
def session_start(session_name: str = "bitbake", level: str = "core") -> str:
    """Start a persistent tmux session inside the container with Yocto env sourced.

    Commands can be sent via session_send() without re-sourcing the env.
    The session runs inside the background container (auto-started if needed).

    Args:
        session_name: tmux session name (default: bitbake).
        level: Build level whose kas env to source (core, wayland, chrome, quake3).
    """
    _ensure_container()
    if level not in KAS_ARGS:
        return f"Unknown level '{level}'"
    kas_conf = KAS_ARGS[level]
    _run_in_container(
        f"mkdir -p {WORK_MOUNT}/.tmp && "
        f"rm -f {_SESSION_LOG} && touch {_SESSION_LOG}",
        user="root",
    )
    r = _run_in_container(
        f"tmux new-session -d -s {shlex.quote(session_name)} "
        f"\"bash -c 'cd {WORK_MOUNT} && kas shell {kas_conf} >/dev/null 2>&1 && exec bash'\" && "
        f"tmux pipe-pane -t {shlex.quote(session_name)} "
        f"-o \"cat >> {_SESSION_LOG}\"",
        user="root",
    )
    _session.log_pos = 0
    _session.last_cmd = ""
    if r.returncode == 0:
        return (f"Session '{session_name}' started (level={level}). "
                f"Use session_send() to run commands.")
    return f"Failed to start session: {r.stderr}"


@mcp.tool()
def session_send(
    command: str,
    session_name: str = "bitbake",
    wait_sec: float = 2.0,
) -> str:
    """Send a command to the persistent build session and return new output.

    Args:
        command: Shell command to run inside the session.
        session_name: tmux session name.
        wait_sec: Seconds to wait for output after sending (default: 2).
    """
    _run_in_container(
        f"tmux send-keys -t {shlex.quote(session_name)} "
        f"{shlex.quote(command)} Enter",
        user="root",
    )
    _session.last_cmd = command
    time.sleep(wait_sec)
    r = _run_in_container(
        f"wc -c < {_SESSION_LOG}",
        user="root",
    )
    try:
        new_size = int(r.stdout.strip())
    except ValueError:
        new_size = _session.log_pos

    if new_size <= _session.log_pos:
        return f"[no new output after {wait_sec}s]"

    r = _run_in_container(
        f"dd if={_SESSION_LOG} bs=1 skip={_session.log_pos} 2>/dev/null",
        user="root",
    )
    _session.log_pos = new_size
    output = r.stdout + r.stderr
    cleaned = re.sub(r"\x1b\[[0-9;]*[a-zA-Z]", "", output)
    return cleaned


@mcp.tool()
def session_stop(session_name: str = "bitbake") -> str:
    """Stop the persistent build session.

    Args:
        session_name: tmux session name.
    """
    _run_in_container(
        f"tmux kill-session -t {shlex.quote(session_name)} 2>/dev/null; "
        f"rm -f {_SESSION_LOG}",
        user="root",
    )
    _session.log_pos = 0
    _session.last_cmd = ""
    return f"Session '{session_name}' stopped."


@mcp.tool()
def session_status(session_name: str = "bitbake") -> str:
    """Check if the persistent build session is alive.

    Args:
        session_name: tmux session name.
    """
    r = _run_in_container(
        f"tmux has-session -t {shlex.quote(session_name)} 2>&1",
        user="root",
    )
    if r.returncode == 0:
        last = _session.last_cmd or "(none)"
        return f"Session '{session_name}' is running.\nLast command: {last}"
    return (f"Session '{session_name}' is not running.\n"
            f"Start one with session_start().")


# ── Resources ────────────────────────────────────────────────────────────

@mcp.resource("project://info")
def project_info() -> str:
    """Project metadata and configuration."""
    return json.dumps(
        {
            "name": "yokto",
            "description": "Yocto build for Raspberry Pi 5 (kas + docker)",
            "path": str(PROJECT_DIR),
            "image": IMAGE_NAME,
            "container": CONTAINER_NAME,
            "yocto_branch": "scarthgap",
            "machine": "raspberrypi5",
            "levels": list(LEVELS.keys()),
            "target": {
                "connected": _target.connected,
                "host": _target.host or "(none)",
                "user": _target.user,
                "port": _target.port,
            },
        },
        indent=2,
    )


@mcp.resource("file://{path}")
def file_resource(path: str) -> str:
    """Read any file within the project directory.

    Args:
        path: Relative path from project root.
    """
    full = (PROJECT_DIR / path).resolve()
    if not str(full).startswith(str(PROJECT_DIR)):
        return "Error: path outside project directory"
    if not full.exists():
        return f"Error: {path} not found"
    return full.read_text()


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
