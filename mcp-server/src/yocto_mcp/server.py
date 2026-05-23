"""Yocto MCP server — thin wrapper around invoke tasks (tasks.py).

All build, container, and image commands delegate to invoke so tasks.py
remains the single source of truth. Target-device commands (SSH/SCP) are
implemented natively because no invoke equivalents exist.
"""

import json
import os
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path

from mcp.server.fastmcp import FastMCP

PROJECT_DIR = Path(__file__).resolve().parents[3]
WORK_MOUNT = "/work"

# Import shared constants
import sys
sys.path.insert(0, str(PROJECT_DIR))
from yokto_core import (
    LEVELS,
    CONTAINER_NAME,
    CONTAINER_USER,
    _read_lock,
    _lock_alive,
)

mcp = FastMCP("yocto-mcp", instructions="""
Yocto build server for Raspberry Pi 5 (yokto project).

All build and container commands delegate to the project's invoke tasks
(tasks.py) so there is a single source of truth.

BUILD LIFECYCLE:
  build_start(level)    -> invoke build-start --<level> --detach
  build_logs(level)     -> tail build-{level}.log, shows running/exited
  build_stop()          -> invoke build-stop (reads lock file)

CONCURRENCY:
  Build and checkout share a lock managed by invoke — only one runs at a time.
""")

_TIMEOUT_DEFAULT = 30
_TIMEOUT_BUILD = 300


# ── Helpers ──────────────────────────────────────────────────────────────

def _run(cmd: list[str], timeout: int = _TIMEOUT_DEFAULT, **kwargs) -> subprocess.CompletedProcess:
    kwargs.setdefault("capture_output", True)
    kwargs.setdefault("text", True)
    try:
        return subprocess.run(cmd, timeout=timeout, **kwargs)
    except subprocess.TimeoutExpired:
        raise TimeoutError(f"Command timed out after {timeout}s: {' '.join(cmd)}")


def _run_invoke(task: str, timeout: int = _TIMEOUT_BUILD, **kwargs) -> str:
    """Run an invoke task, translating kwargs to CLI flags."""
    cmd = ["invoke", task]
    for k, v in kwargs.items():
        flag = k.replace("_", "-")
        if isinstance(v, bool):
            if v:
                cmd.append(f"--{flag}")
        elif v is not None and v != "":
            cmd.append(f"--{flag}")
            cmd.append(str(v))
    r = _run(cmd, timeout=timeout, cwd=str(PROJECT_DIR))
    out = r.stdout.strip()
    err = r.stderr.strip()
    if r.returncode != 0:
        return f"Error (exit {r.returncode}):\n{err}\n{out}"
    return out if out else err


def _image_exists() -> bool:
    r = _run(["docker", "images", "-q", "yokto"], timeout=10)
    return bool(r.stdout.strip())


def _container_running() -> bool:
    r = _run(["docker", "ps", "-q", "--filter", f"name={CONTAINER_NAME}"], timeout=10)
    return bool(r.stdout.strip())


def _run_in_container(cmd: str | list[str], user: str = CONTAINER_USER) -> subprocess.CompletedProcess:
    if isinstance(cmd, list):
        cmd = " ".join(shlex.quote(c) for c in cmd)
    return _run(
        ["docker", "exec", "-u", user, CONTAINER_NAME, "bash", "-lc", cmd],
        timeout=_TIMEOUT_BUILD,
    )


# ── Container Lifecycle ────────────────────────────────────────────────

@mcp.tool()
def container_status() -> str:
    """Check whether the build container is running / image exists."""
    img = _image_exists()
    run = _container_running()
    lines = [
        f"Image 'yokto': {'exists' if img else 'NOT FOUND'}",
        f"Container '{CONTAINER_NAME}': {'running' if run else 'stopped'}",
    ]
    return "\n".join(lines)


@mcp.tool()
def container_start() -> str:
    """Start (or restart) the background build container."""
    if not _image_exists():
        _run_invoke("docker-init")
    _run(["docker", "rm", "-f", CONTAINER_NAME], timeout=10)
    _run([
        "docker", "run", "-d",
        "--name", CONTAINER_NAME,
        "-v", f"{PROJECT_DIR}:{WORK_MOUNT}",
        "-v", "/etc/localtime:/etc/localtime:ro",
        "--workdir", WORK_MOUNT,
        "yokto",
        "tail", "-f", "/dev/null",
    ], timeout=30)
    if _container_running():
        return f"Container {CONTAINER_NAME} is running"
    return "Failed to start container"


@mcp.tool()
def container_stop() -> str:
    """Stop and remove the background build container."""
    _run(["docker", "rm", "-f", CONTAINER_NAME], timeout=10)
    return f"Container {CONTAINER_NAME} removed"


@mcp.tool()
def container_exec(command: str, user: str = CONTAINER_USER) -> str:
    """Run a command inside the build container (auto-starts container if needed)."""
    if not _container_running():
        if not _image_exists():
            _run_invoke("docker-init")
        _run([
            "docker", "run", "-d",
            "--name", CONTAINER_NAME,
            "-v", f"{PROJECT_DIR}:{WORK_MOUNT}",
            "-v", "/etc/localtime:/etc/localtime:ro",
            "--workdir", WORK_MOUNT,
            "yokto",
            "tail", "-f", "/dev/null",
        ], timeout=30)
    r = _run_in_container(command, user=user)
    return r.stdout.strip() + r.stderr.strip()


@mcp.tool()
def docker_init(no_cache: bool = False) -> str:
    """Build the yokto Docker image."""
    return _run_invoke("docker-init", no_cache=no_cache)


@mcp.tool()
def docker_purge() -> str:
    """Remove the yokto docker image and all related containers."""
    return _run_invoke("docker-purge")


# ── Build Commands (delegate to invoke) ─────────────────────────────────

@mcp.tool()
def build_start(level: str = "base", detach: bool = True, log: str = "") -> str:
    """Run a full kas build for a given level.

    By default runs detached so the tool returns immediately. Monitor with
    build_logs(level).

    Args:
        level: Build level: base, wayland, games, or chrome.
        detach: Run in background (recommended for agents).
        log: Optional log file path (only used when detach=False).
    """
    if level not in LEVELS:
        return f"Unknown level '{level}'. Choose: {', '.join(LEVELS)}"
    kwargs = {level: True}
    if detach:
        kwargs["detach"] = True
    elif log:
        kwargs["log"] = log
    return _run_invoke("build-start", **kwargs)


@mcp.tool()
def build_checkout(level: str = "base", update: bool = False, force: bool = False, detach: bool = True) -> str:
    """Fetch/update Yocto layers for a given level without building.

    Args:
        level: Build level: base, wayland, games, or chrome.
        update: Force update of layer repos (git pull).
        force: Overwrite existing config files.
        detach: Run checkout in background.
    """
    if level not in LEVELS:
        return f"Unknown level '{level}'. Choose: {', '.join(LEVELS)}"
    kwargs = {level: True, "update": update, "force": force}
    if detach:
        kwargs["detach"] = True
    return _run_invoke("build-checkout", **kwargs)


@mcp.tool()
def build_stop(force: bool = False) -> str:
    """Stop a running build or checkout gracefully.

    Args:
        force: Use SIGKILL immediately (may corrupt sstate).
    """
    return _run_invoke("build-stop", force=force)


@mcp.tool()
def build_status(lines: int = 10) -> str:
    """Check if a detached build or checkout is running.

    Args:
        lines: Number of trailing log lines to show.
    """
    return _run_invoke("build-status", lines=lines)


@mcp.tool()
def build_last(lines: int = 20) -> str:
    """Show the result of the most recent build or checkout operation.

    Args:
        lines: Number of trailing log lines.
    """
    return _run_invoke("build-last", lines=lines)


@mcp.tool()
def build_logs(level: str = "base", lines: int = 50) -> str:
    """Show recent output from a build log.

    Args:
        level: Build level: base, wayland, games, or chrome.
        lines: Number of tail lines to show.
    """
    log_path = PROJECT_DIR / f"build-{level}.log"
    if not log_path.exists():
        return f"No log file found for '{level}'."
    try:
        r = _run(["tail", "-n", str(lines), str(log_path)], timeout=10)
        output = r.stdout.strip()
    except (TimeoutError, subprocess.TimeoutExpired):
        output = "(error reading log)"

    lock = _read_lock()
    if lock and lock.get("level") == level:
        alive = _lock_alive(lambda c: _run(["bash", "-c", c]).stdout, lock)
        status = f"RUNNING (PID {lock.get('pid', '?')})" if alive else "EXITED"
    else:
        status = "EXITED"
    return f"Build '{level}' {status}.\n{output}"


@mcp.tool()
def build_shell(command: str, level: str = "base") -> str:
    """Run a command inside a kas shell with BitBake env sourced.

    Args:
        command: BitBake or shell command to run.
        level: Build level for env setup: base, wayland, games, or chrome.
    """
    if level not in LEVELS:
        return f"Unknown level '{level}'. Choose: {', '.join(LEVELS)}"
    return _run_invoke("shell", **{level: True, "command": command}, timeout=_TIMEOUT_BUILD)


@mcp.tool()
def build_clean(layers: bool = False, sstate: bool = False, recipe: str = "", all: bool = False) -> str:
    """Remove build output. Preserves downloads/ and sstate/ by default.

    Args:
        layers: Also remove kas-cloned layers.
        sstate: Also remove sstate cache.
        recipe: Clean a specific recipe from sstate (e.g. chromium-ozone-wayland).
        all: Remove everything.
    """
    kwargs = {"layers": layers, "sstate": sstate, "all": all}
    if recipe:
        kwargs["recipe"] = recipe
    return _run_invoke("build-clean", **kwargs)


@mcp.tool()
def build_rebuild(level: str = "base") -> str:
    """Clean checkout layers + build output, then checkout and build.

    Args:
        level: Build level: base, wayland, games, or chrome.
    """
    if level not in LEVELS:
        return f"Unknown level '{level}'. Choose: {', '.join(LEVELS)}"
    return _run_invoke("build-rebuild", **{level: True})


@mcp.tool()
def build_images() -> str:
    """List built .wic.bz2 images."""
    return _run_invoke("images")


@mcp.tool()
def build_flash(device: str, level: str = "base", force: bool = False) -> str:
    """Flash a built image to an SD card device.

    Runs on the host for USB access (may trigger pkexec GUI password prompt).

    Args:
        device: Block device path (e.g. /dev/sdb).
        level: Build level whose image to flash: base, wayland, games, or chrome.
        force: Skip removable drive check.
    """
    if level not in LEVELS:
        return f"Unknown level '{level}'. Choose: {', '.join(LEVELS)}"
    return _run_invoke("flash", **{level: True, "device": device, "force": force})


# ── Target Device Tools (SSH to RPi5) ──────────────────────────────────

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


def _run_ssh(cmd: str, sudo: bool = False) -> subprocess.CompletedProcess:
    if not _target.host:
        msg = "No target connected. Call target_connect(host) first."
        raise RuntimeError(msg)
    ssh_cmd = ["ssh", "-o", "ConnectTimeout=10", "-o", "StrictHostKeyChecking=no"]
    if _target.key:
        ssh_cmd += ["-i", _target.key]
    ssh_cmd += ["-p", str(_target.port), f"{_target.user}@{_target.host}"]
    full = f"sudo {cmd}" if sudo else cmd
    return _run(ssh_cmd + [full], timeout=_TIMEOUT_BUILD)


@mcp.tool()
def target_connect(host: str, user: str = "root", port: int = 22, key: str = "") -> str:
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
    try:
        r = _run_ssh("echo OK")
        if r.returncode == 0:
            return f"Connected to {user}@{host}:{port}"
    except Exception as e:
        _target.host = ""
        return f"Connection failed: {e}"
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
        ["scp", "-P", str(_target.port), "-o", "StrictHostKeyChecking=no"]
        + key_arg
        + ["-r", source, f"{_target.user}@{_target.host}:{dest}"],
        timeout=_TIMEOUT_BUILD,
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


# ── Resources ────────────────────────────────────────────────────────────

@mcp.resource("project://info")
def project_info() -> str:
    """Project metadata and configuration."""
    return json.dumps(
        {
            "name": "yokto",
            "description": "Yocto build for Raspberry Pi 5 (kas + docker)",
            "path": str(PROJECT_DIR),
            "image": "yokto",
            "container": CONTAINER_NAME,
            "yocto_branch": "scarthgap",
            "machine": "raspberrypi5",
            "levels": list(LEVELS),
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
