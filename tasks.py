import os
import re
import time
import shlex
from pathlib import Path
from invoke.tasks import task
from invoke.exceptions import Exit, UnexpectedExit

from yokto_core import (
    ROOT, IMAGE, CONTAINER_NAME, CONTAINER_USER, WORK_MOUNT, LEVELS, LOCK_FILE,
    _level, _validate, _kas_args,
    _read_lock, _write_lock, _clear_lock, _lock_alive,
    _filter_ssh_output, _ssh_opts,
)


def _ensure_image(ctx):
    try:
        ctx.run(f'docker image inspect {IMAGE}', hide=True)
    except UnexpectedExit:
        print(f"Image '{IMAGE}' not found. Running docker-init first...")
        docker_init(ctx)


def _container_running(ctx):
    r = ctx.run(f'docker ps -q --filter name={CONTAINER_NAME}', hide=True)
    return bool(r.stdout.strip())


def _ensure_container(ctx):
    if _container_running(ctx):
        return
    _ensure_image(ctx)
    # Remove any stopped container with same name
    ctx.run(f'docker rm -f {CONTAINER_NAME}', warn=True)
    ctx.run(
        f'docker run -d --name {CONTAINER_NAME} '
        f'-v "{ROOT}:{WORK_MOUNT}" '
        f'-v /etc/localtime:/etc/localtime:ro '
        f'--workdir {WORK_MOUNT} '
        f'{IMAGE} tail -f /dev/null',
        echo=True,
    )
    for _ in range(5):
        time.sleep(0.5)
        if _container_running(ctx):
            return
    raise Exit(f"Failed to start container {CONTAINER_NAME}")


def _run_in_container(ctx, cmd, user=CONTAINER_USER, **kwargs):
    _ensure_container(ctx)
    return ctx.run(
        f'docker exec -u {user} {CONTAINER_NAME} bash -lc {shlex.quote(cmd)}',
        **kwargs,
    )


def _lock_alive_ctx(ctx, lock):
    # First check if container is running
    r = ctx.run(f'docker ps -q --filter name={CONTAINER_NAME}', hide=True)
    if not r.stdout.strip():
        return False
    return _lock_alive(lambda c: ctx.run(c, hide=True).stdout, lock)


def _assert_no_running_build(ctx):
    lock = _read_lock()
    if _lock_alive_ctx(ctx, lock):
        raise Exit(
            f"{lock.get('type', 'Build').capitalize()} '{lock['level']}' is running. "
            "Only one operation at a time."
        )
    _clear_lock()


@task(help={"no-cache": "Do not use cache when building the image"})
def docker_init(ctx, no_cache=False):
    """Build the yokto Docker container."""
    uid = ctx.run("id -u", hide=True).stdout.strip()
    gid = ctx.run("id -g", hide=True).stdout.strip()
    flags = "--no-cache" if no_cache else ""
    ctx.run(
        f'docker build {flags} '
        f'-f {ROOT}/dockerfile '
        f'--build-arg USER_ID={uid} '
        f'--build-arg GROUP_ID={gid} '
        f'-t {IMAGE} {ROOT}',
        echo=True,
    )


@task(
    help={
        "base": "Minimal headless image (default)",
        "gui": "Wayland desktop + Weston",
        "chrome": "Wayland + Chromium",
        "games": "Wayland + games",
        "ai": "Wayland + AI tools (llama.cpp, whisper.cpp)",
        "update": "Force update of layer repos",
        "force": "Overwrite existing config files",
        "detach": "Run in background (for MCP)",
    }
)
def build_checkout(ctx, base=False, gui=False, chrome=False, games=False, ai=False, update=False, force=False, detach=False):
    """Fetch layers and write config (no build)."""
    _ensure_image(ctx)
    level = _validate(_level(base, gui, chrome, games, ai))
    _assert_no_running_build(ctx)

    if detach:
        _ensure_container(ctx)
        flags = ""
        if update:
            flags += " --update"
        if force:
            flags += " --force"
        cmd = (
            f'cd {WORK_MOUNT} && '
            f'nohup kas checkout{flags} {_kas_args(level)} > checkout-{level}.log 2>&1 & '
            f'echo $!'
        )
        r = ctx.run(
            f'docker exec -u {CONTAINER_USER} {CONTAINER_NAME} bash -lc {shlex.quote(cmd)}',
            hide=True,
        )
        pid = int(r.stdout.strip())
        _write_lock(level, pid, "checkout")
        print(f"Checkout '{level}' started (PID {pid}).")
    else:
        _ensure_container(ctx)
        flags = ""
        if update:
            flags += " --update"
        if force:
            flags += " --force"
        _write_lock(level, 0, "checkout")
        try:
            _run_in_container(
                ctx,
                f'cd {WORK_MOUNT} && kas checkout{flags} {_kas_args(level)}',
                echo=True,
            )
        finally:
            _clear_lock()


@task(
    help={
        "base": "Minimal headless image (default)",
        "gui": "Wayland desktop + Weston",
        "chrome": "Wayland + Chromium",
        "games": "Wayland + games",
        "ai": "Wayland + AI tools (llama.cpp, whisper.cpp)",
        "log": "Save build output to a file (e.g. build-gui.log)",
        "detach": "Run in background (for MCP)",
    }
)
def build_start(ctx, base=False, gui=False, chrome=False, games=False, ai=False, log=None, detach=False):
    """Checkout layers and build the image."""
    _ensure_image(ctx)
    level = _validate(_level(base, gui, chrome, games, ai))
    _assert_no_running_build(ctx)

    if detach:
        _ensure_container(ctx)
        cmd = (
            f'cd {WORK_MOUNT} && '
            f'nohup kas build {_kas_args(level)} > build-{level}.log 2>&1 & '
            f'echo $!'
        )
        r = ctx.run(
            f'docker exec -u {CONTAINER_USER} {CONTAINER_NAME} bash -lc {shlex.quote(cmd)}',
            hide=True,
        )
        pid = int(r.stdout.strip())
        _write_lock(level, pid, "build")
        print(f"Build '{level}' started (PID {pid}).")
    elif log:
        _ensure_container(ctx)
        _write_lock(level, 0, "build")
        try:
            cmd = f'cd {WORK_MOUNT} && kas build {_kas_args(level)} > {log} 2>&1'
            ctx.run(
                f'docker exec -u {CONTAINER_USER} {CONTAINER_NAME} bash -lc {shlex.quote(cmd)}',
                echo=False,
                pty=False,
                warn=True,
            )
            print(f"\nBuild log saved to {log}")
        finally:
            _clear_lock()
    else:
        _ensure_container(ctx)
        _write_lock(level, 0, "build")
        try:
            _run_in_container(
                ctx,
                f'cd {WORK_MOUNT} && kas build {_kas_args(level)}',
                echo=True,
                pty=False,
            )
        finally:
            _clear_lock()


def _show_tail(ctx, log_name, lines=10):
    """Show last N lines of a log file from the shared volume."""
    log_path = ROOT / log_name
    if log_path.exists():
        ctx.run(f'tail -n {lines} "{log_path}"', echo=False)


def _show_head(ctx, log_name, lines=20):
    """Show first N lines of a log file from the shared volume."""
    log_path = ROOT / log_name
    if log_path.exists():
        ctx.run(f'head -n {lines} "{log_path}"', echo=False)


def _show_head_tail(ctx, log_name, head=10, tail=10):
    """Show first N and last N lines of a log file with ellipsis if file is large."""
    log_path = ROOT / log_name
    if not log_path.exists():
        return
    
    # Get total lines in file
    result = ctx.run(f'wc -l "{log_path}"', hide=True)
    total_lines = int(result.stdout.split()[0])
    
    if head > 0 and tail > 0:
        # Show both head and tail with separator if file is larger than head+tail
        if total_lines > (head + tail):
            ctx.run(f'head -n {head} "{log_path}"', echo=False)
            print("    ... (log output truncated) ...")
            ctx.run(f'tail -n {tail} "{log_path}"', echo=False)
        else:
            # File is small enough to show all
            ctx.run(f'cat "{log_path}"', echo=False)
    elif head > 0:
        ctx.run(f'head -n {head} "{log_path}"', echo=False)
    elif tail > 0:
        ctx.run(f'tail -n {tail} "{log_path}"', echo=False)


def _latest_log():
    """Find the most recent build or checkout log file."""
    logs = sorted(ROOT.glob("build-*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
    logs += sorted(ROOT.glob("checkout-*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
    return sorted(logs, key=lambda p: p.stat().st_mtime, reverse=True)[0] if logs else None


@task(help={
    "lines": "Number of trailing log lines to show (deprecated, use --tail)",
    "head": "Number of leading log lines to show",
    "tail": "Number of trailing log lines to show (default: 20)",
    "headtail": "Show both head and tail lines (e.g. --headtail=10,10)"
})
def build_status(ctx, lines=0, head=0, tail=20, headtail=""):
    """Check if a detached build or checkout is running with output limiting."""
    # Handle deprecated "lines" parameter
    if lines > 0:
        tail = lines
    
    # Handle headtail parameter
    if headtail:
        try:
            h, t = map(int, headtail.split(','))
            head, tail = h, t
        except (ValueError, IndexError):
            print(f"Invalid headtail format. Use --headtail=head,tail (e.g. --headtail=10,10)")
            return
    
    lock = _read_lock()
    if not lock:
        print("No detached operation running.")
        # Show the most recent log instead
        log = _latest_log()
        if log:
            print(f"Showing last operation: {log.name}")
            if head > 0 or tail > 0:
                if head > 0 and tail > 0:
                    _show_head_tail(ctx, log.name, head, tail)
                elif head > 0:
                    _show_head(ctx, log.name, head)
                else:
                    _show_tail(ctx, log.name, tail)
            else:
                _show_tail(ctx, log.name, 20)  # default
        else:
            print("No build or checkout logs found.")
        return

    op_type = lock.get("type", "build")
    level = lock["level"]
    pid = lock.get("pid", 0)

    # Check if container is running first
    if not _container_running(ctx):
        print(f"Container not running (stale lock for {op_type} '{level}').")
        if head > 0 or tail > 0:
            if head > 0 and tail > 0:
                _show_head_tail(ctx, f"{op_type}-{level}.log", head, tail)
            elif head > 0:
                _show_head(ctx, f"{op_type}-{level}.log", head)
            else:
                _show_tail(ctx, f"{op_type}-{level}.log", tail)
        else:
            _show_tail(ctx, f"{op_type}-{level}.log", 20)  # default
        _clear_lock()
        print("Lock cleared.")
        return

    if _lock_alive_ctx(ctx, lock):
        print(f"{op_type.capitalize()} '{level}' is running (PID {pid}).")
        if head > 0 or tail > 0:
            if head > 0 and tail > 0:
                _show_head_tail(ctx, f"{op_type}-{level}.log", head, tail)
            elif head > 0:
                _show_head(ctx, f"{op_type}-{level}.log", head)
            else:
                _show_tail(ctx, f"{op_type}-{level}.log", tail)
        else:
            _show_tail(ctx, f"{op_type}-{level}.log", 20)  # default
    else:
        print(f"{op_type.capitalize()} '{level}' has finished.")
        if head > 0 or tail > 0:
            if head > 0 and tail > 0:
                _show_head_tail(ctx, f"{op_type}-{level}.log", head, tail)
            elif head > 0:
                _show_head(ctx, f"{op_type}-{level}.log", head)
            else:
                _show_tail(ctx, f"{op_type}-{level}.log", tail)
        else:
            _show_tail(ctx, f"{op_type}-{level}.log", 20)  # default
        _clear_lock()
        print("Lock cleared.")


@task(help={
    "lines": "Number of trailing log lines to show (deprecated, use --tail)",
    "head": "Number of leading log lines to show",
    "tail": "Number of trailing log lines to show (default: 20)",
    "headtail": "Show both head and tail lines (e.g. --headtail=10,10)"
})
def build_last(ctx, lines=0, head=0, tail=20, headtail=""):
    """Show the result of the most recent build or checkout operation with output limiting."""
    # Handle deprecated "lines" parameter
    if lines > 0:
        tail = lines
    
    # Handle headtail parameter
    if headtail:
        try:
            h, t = map(int, headtail.split(','))
            head, tail = h, t
        except (ValueError, IndexError):
            print(f"Invalid headtail format. Use --headtail=head,tail (e.g. --headtail=10,10)")
            return
    
    log = _latest_log()
    if not log:
        print("No build or checkout logs found.")
        return
    print(f"\n--- {log.name} ---")
    
    if head > 0 or tail > 0:
        if head > 0 and tail > 0:
            _show_head_tail(ctx, log.name, head, tail)
        elif head > 0:
            _show_head(ctx, log.name, head)
        else:
            _show_tail(ctx, log.name, tail)
    else:
        _show_tail(ctx, log.name, 20)  # default


@task(help={"force": "Use SIGKILL immediately", "lines": "Number of trailing log lines to show"})
def build_stop(ctx, force=False, lines=10):
    """Stop a detached build or checkout."""
    lock = _read_lock()
    if not lock:
        print("No detached operation running.")
        return

    op_type = lock.get("type", "build")
    level = lock["level"]
    pid = lock.get("pid", 0)

    if not _container_running(ctx):
        print(f"Container not running (stale lock for {op_type} '{level}'). Cleaning up.")
        _show_tail(ctx, f"{op_type}-{level}.log", lines)
        _clear_lock()
        return

    if not pid:
        print(f"No PID tracked for {op_type} '{level}'. Cleaning up lock.")
        _show_tail(ctx, f"{op_type}-{level}.log", lines)
        _clear_lock()
        return

    if force:
        ctx.run(
            f'docker exec -u root {CONTAINER_NAME} kill -9 {pid} 2>/dev/null || true',
            echo=True,
        )
        _clear_lock()
        print(f"{op_type.capitalize()} '{level}' killed.")
        _show_tail(ctx, f"{op_type}-{level}.log", lines)
        return

    print(f"Sending INT to {op_type} '{level}' (PID {pid})...")
    ctx.run(
        f'docker exec -u root {CONTAINER_NAME} kill -INT {pid} 2>/dev/null || true',
        echo=True,
    )

    for _ in range(10):
        time.sleep(1)
        r = ctx.run(
            f'docker exec {CONTAINER_NAME} bash -c '
            f'"st=$(ps -p {pid} -o state= 2>/dev/null); '
            f'test -n \\\"$st\\\" && test \\\"$st\\\" != Z && echo alive || echo dead"',
            hide=True,
            warn=True,
        )
        if "dead" in r.stdout:
            _clear_lock()
            print(f"{op_type.capitalize()} '{level}' stopped.")
            _show_tail(ctx, f"{op_type}-{level}.log", lines)
            return

    ctx.run(
        f'docker exec -u root {CONTAINER_NAME} kill -TERM {pid} 2>/dev/null || true',
        echo=True,
    )
    for _ in range(5):
        time.sleep(1)
        r = ctx.run(
            f'docker exec {CONTAINER_NAME} bash -c '
            f'"st=$(ps -p {pid} -o state= 2>/dev/null); '
            f'test -n \\\"$st\\\" && test \\\"$st\\\" != Z && echo alive || echo dead"',
            hide=True,
            warn=True,
        )
        if "dead" in r.stdout:
            _clear_lock()
            print(f"{op_type.capitalize()} '{level}' stopped.")
            _show_tail(ctx, f"{op_type}-{level}.log", lines)
            return

    ctx.run(
        f'docker exec -u root {CONTAINER_NAME} kill -9 {pid} 2>/dev/null || true',
        echo=True,
    )
    _clear_lock()
    print(f"{op_type.capitalize()} '{level}' killed.")
    _show_tail(ctx, f"{op_type}-{level}.log", lines)


@task(
    help={
        "base": "Minimal headless image (default)",
        "gui": "Wayland desktop + Weston",
        "chrome": "Wayland + Chromium",
        "games": "Wayland + games",
        "ai": "Wayland + AI tools (llama.cpp, whisper.cpp)",
        "command": "Command to run in the kas shell (if omitted, enters interactive shell)",
    }
)
def shell(ctx, base=False, gui=False, chrome=False, games=False, ai=False, command=""):
    """Open a shell with kas environment configured (sources checked out)."""
    _ensure_image(ctx)
    level = _validate(_level(base, gui, chrome, games, ai))
    if command:
        _run_in_container(
            ctx,
            f'cd {WORK_MOUNT} && kas shell {_kas_args(level)} -c {shlex.quote(command)}',
            echo=True,
            pty=False,
        )
    else:
        _ensure_container(ctx)
        ctx.run(
            f'docker exec -u {CONTAINER_USER} -it {CONTAINER_NAME} bash -c '
            f'"cd {WORK_MOUNT} && kas shell {_kas_args(level)}"',
            pty=False,
        )


@task(
    help={
        "base": "Minimal headless image (default)",
        "gui": "Wayland desktop + Weston",
        "chrome": "Wayland + Chromium",
        "games": "Wayland + games",
        "ai": "Wayland + AI tools (llama.cpp, whisper.cpp)",
        "command": "Command to run in the kas shell (if omitted, enters interactive shell)",
    }
)
def build_shell(ctx, base=False, gui=False, chrome=False, games=False, ai=False, command=""):
    """Enter kas shell with environment configured.
    
    Without --command: enters interactive shell.
    With --command: runs the command in kas environment.
    """
    _ensure_image(ctx)
    level = _validate(_level(base, gui, chrome, games, ai))
    if command:
        _run_in_container(
            ctx,
            f'cd {WORK_MOUNT} && kas shell {_kas_args(level)} -c {shlex.quote(command)}',
            echo=True,
            pty=False,
        )
    else:
        _ensure_container(ctx)
        ctx.run(
            f'docker exec -u {CONTAINER_USER} -it {CONTAINER_NAME} bash -c '
            f'"cd {WORK_MOUNT} && kas shell {_kas_args(level)}"',
            pty=False,
        )


@task
def container_shell(ctx):
    """Open a plain shell inside the running build container (no kas setup)."""
    _ensure_container(ctx)
    ctx.run(
        f'docker exec -u {CONTAINER_USER} -it {CONTAINER_NAME} bash',
        pty=False,
    )


@task
def container_status(ctx):
    """Check whether the build container is running / image exists."""
    try:
        ctx.run(f'docker image inspect {IMAGE}', hide=True)
        img = "exists"
    except UnexpectedExit:
        img = "NOT FOUND (run 'invoke docker-init' to build)"

    r = ctx.run(f'docker ps -q --filter name={CONTAINER_NAME}', hide=True)
    run = "running" if r.stdout.strip() else "stopped"
    print(f"Image '{IMAGE}': {img}")
    print(f"Container '{CONTAINER_NAME}': {run}")


@task
def container_start(ctx):
    """Start (or restart) the background build container."""
    # Check if image exists first
    try:
        ctx.run(f'docker image inspect {IMAGE}', hide=True)
    except UnexpectedExit:
        raise Exit(
            f"Image '{IMAGE}' not found. "
            f"Run 'invoke docker-init' first to build the image."
        )
    
    # If container is already running, nothing to do
    if _container_running(ctx):
        print(f"Container {CONTAINER_NAME} is already running")
        return
    
    # Remove any stopped container with same name
    ctx.run(f'docker rm -f {CONTAINER_NAME}', warn=True)
    
    ctx.run(
        f'docker run -d --name {CONTAINER_NAME} '
        f'-v "{ROOT}:{WORK_MOUNT}" '
        f'-v /etc/localtime:/etc/localtime:ro '
        f'--workdir {WORK_MOUNT} '
        f'{IMAGE} tail -f /dev/null',
        echo=True,
    )
    
    for _ in range(5):
        time.sleep(0.5)
        r = ctx.run(f'docker ps -q --filter name={CONTAINER_NAME}', hide=True)
        if r.stdout.strip():
            print(f"Container {CONTAINER_NAME} is running")
            return
    
    raise Exit(f"Failed to start container {CONTAINER_NAME}")


@task
def container_stop(ctx):
    """Stop and remove the background build container."""
    # Check if container exists first
    r = ctx.run(f'docker ps -a -q --filter name={CONTAINER_NAME}', hide=True)
    was_running = bool(r.stdout.strip())
    
    ctx.run(f'docker rm -f {CONTAINER_NAME}', warn=True, hide=True)
    
    if was_running:
        print(f"Container {CONTAINER_NAME} stopped and removed")
    else:
        print(f"Container {CONTAINER_NAME} was not running")


@task
def container_exec(ctx, command):
    """Run a command inside the build container (auto-starts if needed)."""
    _run_in_container(ctx, command, echo=True)


@task
def images(ctx):
    """List built .wic.bz2 images and .swu update files."""
    ctx.run(f"find {ROOT} -path '*/deploy/images/raspberrypi5/*.wic.bz2' -ls")
    ctx.run(f"find {ROOT} -name '*.swu' -ls")


def _clean_old_artifacts(images_dir):
    """Remove old artifacts, keeping one per image type (core/wayland/chrome/games)."""
    # Group images by their base name (core-image-*)
    image_groups = {}
    for wic in images_dir.glob("*.wic.bz2"):
        if wic.is_symlink():
            continue
        # Extract base name (e.g., "core-image-wayland" from "...-wayland-raspberrypi5...")
        name = wic.stem
        # Match pattern: core-image-{name}-raspberrypi5.rootfs
        if name.startswith("core-image-") and name.endswith(".rootfs"):
            base = name.replace(".rootfs", "")
        else:
            continue
        if base not in image_groups:
            image_groups[base] = []
        image_groups[base].append(wic)
    
    # For each image type, keep only the latest
    for base, files in image_groups.items():
        if len(files) <= 1:
            continue
        files_sorted = sorted(files)
        for old in files_sorted[:-1]:
            stem = old.stem.replace(".wic", "")
            print(f"  Pruning old artifacts: {stem}")
            for f in images_dir.glob(f"{stem}.*"):
                f.unlink()


def _find_wic(level):
    """Find the correct wic.bz2 image for a level."""
    images_dir = ROOT / "build" / "tmp" / "deploy" / "images" / "raspberrypi5"
    
    # Map levels to their image basenames (exact naming)
    level_to_basename = {
        "base": "image-base",
        "gui": "image-gui",
        "chrome": "image-chrome",
        "games": "image-games",
        "ai": "image-ai",
    }
    
    basename = level_to_basename.get(level, "core-image-weston")
    pattern = f"{basename}-raspberrypi5.rootfs.wic.bz2"
    target = images_dir / pattern
    
    if target.exists():
        return target
    
    # Check for symlinks pointing to the expected image
    matches = sorted(f for f in images_dir.glob(f"{basename}-raspberrypi5.rootfs.wic.bz2") if f.exists())
    if matches:
        return matches[-1]
    
    # NO fallback - require exact match to prevent flashing wrong image
    raise Exit(
        f"No .wic.bz2 found for level '{level}' (expected: {basename}). "
        f"Run 'invoke build-start --{level}' first."
    )


def _check_removable(device):
    """Check if device is a removable external drive."""
    devname = device.split("/")[-1]
    base_dev = re.sub(r'\d+$', '', devname)
    removable_path = f"/sys/block/{base_dev}/removable"
    if not os.path.exists(removable_path):
        raise Exit(f"Device {device} not found or is not a block device")
    with open(removable_path) as f:
        if f.read().strip() != "1":
            raise Exit(
                f"Device {device} is NOT removable. "
                "This looks like an internal drive. Refusing to flash. "
                "If you know what you're doing, use --force."
            )
    return True


@task(
    help={
        "device": "Target block device (e.g. /dev/sdb)",
        "base": "Minimal headless image (default)",
        "gui": "Wayland desktop + Weston",
        "chrome": "Wayland + Chromium",
        "games": "Wayland + games",
        "ai": "Wayland + AI tools (llama.cpp, whisper.cpp)",
        "force": "Skip removable drive check",
        "nobmap": "Skip bmap usage, use dd instead",
        "dd": "Use dd instead of bmaptool",
    }
)
def flash(ctx, device=None, base=False, gui=False, chrome=False, games=False, ai=False, force=False, nobmap=False, dd=False):
    """Flash the built image to an SD card. Runs on host for USB access."""
    level = _validate(_level(base, gui, chrome, games, ai))

    if not device or not device.startswith("/dev/"):
        raise Exit(f"Device must be an absolute path like /dev/sdX, got: {device}")

    if not force:
        _check_removable(device)

    dev = shlex.quote(device)
    images_dir = ROOT / "build" / "tmp" / "deploy" / "images" / "raspberrypi5"
    _clean_old_artifacts(images_dir)

    wic = _find_wic(level)
    wic_abs = wic.resolve()

    print(f"\n{'='*60}")
    print(f"  Flashing {wic.name}")
    print(f"  To: {device}")
    print(f"  Level: {level}")
    print(f"{'='*60}\n")

    if nobmap or dd:
        r = ctx.run(f'pkexec bash -c "bzcat {wic_abs} | dd of={dev} bs=4M conv=fsync status=progress"', warn=True)
    else:
        raw = str(wic_abs).replace(".wic.bz2", ".wic")
        bmap = str(wic_abs).replace(".wic.bz2", ".bmap")

        if not Path(bmap).exists() or Path(bmap).stat().st_mtime < Path(wic_abs).stat().st_mtime:
            print(f"\nGenerating bmap file...")
            r = ctx.run(f"bzcat {wic_abs} | dd conv=sparse bs=1M of={raw} && bmaptool create {raw} -o {bmap} && rm {raw}", warn=True)
        else:
            print(f"\nUsing existing bmap file...")
            r = None

        if r is None or r.ok:
            print(f"\nFlashing...")
            r = ctx.run(f"pkexec $(which bmaptool) copy {wic_abs} {dev}", warn=True)

            if r and r.exited != 0:
                print(f"\nbmaptool failed (exit {r.exited}), falling back to dd...")
                r = ctx.run(f'pkexec bash -c "bzcat {wic_abs} | dd of={dev} bs=4M conv=fsync status=progress"', warn=True)

    if r and r.exited != 0:
        print(f"\n{'!'*60}")
        print(f"  FLASH FAILED (exit code {r.exited})")
        print(f"{'!'*60}")
        if r.stdout:
            print(f"\nstdout:\n{r.stdout}")
        if r.stderr:
            print(f"\nstderr:\n{r.stderr}")
        raise Exit(f"Flashing failed with exit code {r.exited}")


@task(
    help={
        "layers": "Also remove kas-cloned layers (re-cloned on next build)",
        "sstate": "Also remove the sstate cache",
        "recipe": "Clean a specific recipe from the sstate cache (e.g. chromium-ozone-wayland)",
        "tmp_only": "Remove only build/tmp/ directory, keeping sstate-cache intact (for fresh builds without losing cache)",
        "all": "Remove everything: build output, layers, downloads/, sstate-cache/",
    }
)
def build_clean(ctx, layers=False, sstate=False, recipe="", tmp_only=False, all=False):
    """Remove build output. Without flags, preserves downloads/, sstate-cache/, and layers."""
    lock = _read_lock()
    if _lock_alive_ctx(ctx, lock):
        raise Exit(f"{lock.get('type', 'Build').capitalize()} '{lock['level']}' is running. Stop it first with 'invoke stop-build'.")
    _clear_lock()

    build_dir = ROOT / "build"
    
    if tmp_only:
        # Remove only build/tmp but keep sstate-cache
        if build_dir.exists():
            tmp_dir = build_dir / "tmp"
            if tmp_dir.exists():
                print(f"  Removing {tmp_dir}/ (preserving sstate-cache/)")
                ctx.run(f'rm -rf "{tmp_dir}"')
            cache_dir = build_dir / "cache"
            if cache_dir.exists():
                print(f"  Removing {cache_dir}/ (preserving sstate-cache/)")
                ctx.run(f'rm -rf "{cache_dir}"')
        return
    
    if build_dir.exists():
        if all:
            print(f"  Removing {build_dir}/ (full clean)")
            ctx.run(f'rm -rf "{build_dir}"')
        else:
            print(f"  Cleaning {build_dir}/ (preserves downloads/, sstate-cache/)")
            for item in build_dir.iterdir():
                if item.name not in ("downloads", "sstate-cache"):
                    ctx.run(f'rm -rf "{item}"')
    if layers or all:
        layers_dir = ROOT / "layers"
        if layers_dir.exists():
            for item in layers_dir.iterdir():
                if (item / ".git").exists():
                    print(f"  Removing {item}/ (kas-cloned)")
                    ctx.run(f'rm -rf "{item}"')
                else:
                    print(f"  Keeping {item}/ (custom, not kas-cloned)")
    if sstate or all:
        sstate_dir = build_dir / "sstate-cache"
        if sstate_dir.exists():
            print(f"  Removing {sstate_dir}/")
            ctx.run(f'rm -rf "{sstate_dir}"')
    if recipe:
        if not build_dir.exists():
            print(f"  Skipping recipe clean: build directory removed by --all")
        else:
            print(f"  Cleaning sstate for recipe: {recipe}")
            _ensure_image(ctx)
            _run_in_container(
                ctx,
                f'cd {WORK_MOUNT} && bitbake -c cleansstate {shlex.quote(recipe)}',
                echo=True,
            )




@task
def docker_purge(ctx):
    """Remove the yokto docker image and all related containers."""
    ctx.run(
        f'docker ps -a -q --filter ancestor={IMAGE} | xargs -r docker rm -f',
        warn=True,
        hide=True,
    )
    ctx.run(f'docker rmi -f {IMAGE}', warn=True)


@task(
    help={
        "base": "Minimal headless image (default)",
        "gui": "Wayland desktop + Weston",
        "chrome": "Wayland + Chromium",
        "games": "Wayland + games",
        "ai": "Wayland + AI tools (llama.cpp, whisper.cpp)",
        "detach": "Run in background",
    }
)
def swu_generate(ctx, base=False, gui=False, chrome=False, games=False, ai=False, detach=False):
    """Generate a .swu update file from a built image."""
    _ensure_image(ctx)
    level = _validate(_level(base, gui, chrome, games, ai))
    _assert_no_running_build(ctx)

    _ensure_container(ctx)
    
    # Map levels to image base names
    level_to_image = {
        "base": "image-base",
        "gui": "image-gui",
        "chrome": "image-chrome",
        "games": "image-games",
        "ai": "image-ai",
    }
    
    basename = level_to_image.get(level, "core-image")
    
    # Find the image for this specific level
    cmd = f'cd {WORK_MOUNT} && ls -t build/tmp/deploy/images/raspberrypi5/{basename}-*.wic.bz2 2>/dev/null | head -n 1'
    
    result = _run_in_container(ctx, cmd, hide=True)
    wic_path = result.stdout.strip()
    
    if not wic_path:
        raise Exit(f"No .wic.bz2 image found for level '{level}'. Run 'invoke build-start --{level}' first.")
    
    wic_file = Path(wic_path).name
    
    # Generate SWU
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    swu_name = f"yokto-{level}-{timestamp}.swu"
    
    print(f"Generating SWU from: {wic_file}")
    print(f"Output: {swu_name}")
    
    # SWU files are cpio archives - create using find | cpio
    gen_cmd = f'''
cd /work/build/tmp/deploy/images/raspberrypi5 &&
WIC_BZ2="{wic_file}" &&
bzcat "$WIC_BZ2" > image.wic &&
VERSION="{timestamp}" &&
HASH=$(sha256sum image.wic | cut -d' ' -f1) &&
cat > sw-description << EOF
SOFTWARE_VERSION = "$VERSION"
FILES_HASH = "$HASH"
ALLOW_DOWNGRADE = true
images: (
        {{
                filename = "image.wic"
                type = "raw"
                device = "/dev/mmcblk0"
        }}
)
EOF
# Create cpio archive (SWU format)
echo "image.wic sw-description" | cpio -o -H crc > "{swu_name}" &&
rm -f image.wic sw-description &&
cp "{swu_name}" /work/ &&
echo "SWU created: {swu_name}"
'''
    
    if detach:
        cmd_detached = (
            f'cd {WORK_MOUNT} && '
            f'nohup bash -lc {shlex.quote(gen_cmd)} > swu-generate-{level}.log 2>&1 & '
            f'echo $!'
        )
        r = ctx.run(
            f'docker exec -u {CONTAINER_USER} {CONTAINER_NAME} bash -lc {shlex.quote(cmd_detached)}',
            hide=True,
        )
        pid = int(r.stdout.strip())
        _write_lock(level, pid, "swu-generate")
        print(f"SWU generation '{level}' started (PID {pid}).")
    else:
        _write_lock(level, 0, "swu-generate")
        try:
            _run_in_container(ctx, gen_cmd, echo=True)
        finally:
            _clear_lock()


@task(
    help={
        "base": "Minimal headless image (default)",
        "gui": "Wayland desktop + Weston",
        "chrome": "Wayland + Chromium",
        "games": "Wayland + games",
        "ai": "Wayland + AI tools (llama.cpp, whisper.cpp)",
        "device": "Target block device (e.g. /dev/sdb)",
        "force": "Skip removable drive check",
    }
)
def swu_flash(ctx, base=False, gui=False, chrome=False, games=False, ai=False, device=None, force=False):
    """Flash a .swu update file to an SD card.
    
    Finds the most recent .swu file for the specified level and flashes it.
    """
    level = _validate(_level(base, gui, chrome, games, ai))
    
    # Map levels to image names for new SWU naming
    level_to_image = {
        "base": "image-base",
        "gui": "image-gui",
        "chrome": "image-chrome",
        "games": "image-games",
        "ai": "image-ai",
    }
    
    image_name = level_to_image.get(level, "image-gui")
    
    # First, look in deploy directory (new SWU naming)
    deploy_swu = ROOT / "build" / "tmp" / "deploy" / "images" / "raspberrypi5" / f"{image_name}.swu"
    if deploy_swu.exists():
        swu = deploy_swu
    else:
        # Fallback to old naming pattern
        swu_files = sorted(ROOT.glob(f"yokto-{level}-*.swu"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not swu_files:
            # Try any .swu file
            swu_files = sorted(ROOT.glob("*.swu"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not swu_files:
            raise Exit(f"No .swu file found for level '{level}'. Run 'invoke build-start --{level}' first.")
        swu = swu_files[0]
    
    if not device or not device.startswith("/dev/"):
        raise Exit(f"Device must be an absolute path like /dev/sdX, got: {device}")

    if not force:
        _check_removable(device)

    # Extract the wic image from the .swu file
    print(f"\nFlashing {swu.name} to {device}...")
    import tempfile
    import tarfile
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # .swu files are tar archives with sw-description and image files
        with tarfile.open(swu, 'r') as tar:
            # Find the .wic file
            members = [m for m in tar.getmembers() if m.name.endswith('.wic')]
            if not members:
                raise Exit("No .wic file found in .swu archive")
            
            wic_member = members[0]
            print(f"Found image: {wic_member.name}")
            tar.extract(wic_member, tmpdir)
            
            wic_path = Path(tmpdir) / wic_member.name
            
            print(f"\nFlashing to {device}...")
            r = ctx.run(f'pkexec bash -c "cat {wic_path} | dd of={device} bs=4M conv=fsync status=progress"', warn=True)
            
            if r and r.exited != 0:
                raise Exit(f"Flashing failed with exit code {r.exited}")
            
            print("Flash complete. Syncing...")
            ctx.run(f'pkexec sync', echo=True)
            print(f"Successfully flashed {swu.name} to {device}")


@task(
    help={
        "base": "Minimal headless image (default)",
        "gui": "Wayland desktop + Weston",
        "chrome": "Wayland + Chromium",
        "games": "Wayland + games",
        "ai": "Wayland + AI tools (llama.cpp, whisper.cpp)",
        "host": "Target device IP or hostname",
        "user": "SSH user (default: root)",
        "swu": "Explicit path to .swu file (overrides level-based search)",
    }
)
def swu_apply(ctx, base=False, gui=False, chrome=False, games=False, ai=False, host=None, user="root", swu=None):
    """Apply a .swu update to a running target device via SSH.
    
    Uses level flags to find the appropriate .swu file, or accepts explicit --swu path.
    Attempts /tmp first, falls back to /root if insufficient space.
    """
    level = _validate(_level(base, gui, chrome, games, ai))
    
    # Find the .swu file
    if swu:
        swu_path = Path(swu)
        if not swu_path.exists():
            raise Exit(f"SWU file not found: {swu}")
    else:
        # Map levels to image names for new SWU naming
        level_to_image = {
            "base": "image-base",
            "gui": "image-gui",
            "chrome": "image-chrome",
            "games": "image-games",
        "ai": "image-ai",
        }
        
        image_name = level_to_image.get(level, "image-gui")
        
        # First, look in deploy directory (new SWU naming)
        deploy_swu = ROOT / "build" / "tmp" / "deploy" / "images" / "raspberrypi5" / f"{image_name}.swu"
        if deploy_swu.exists():
            swu_path = deploy_swu
        else:
            # Fallback to old naming pattern in project root
            swu_files = sorted(ROOT.glob(f"yokto-{level}-*.swu"), key=lambda p: p.stat().st_mtime, reverse=True)
            if not swu_files:
                raise Exit(f"No .swu file found for level '{level}'. Run 'invoke build-start --{level}' first.")
            swu_path = swu_files[0]
    
    if not host:
        raise Exit(f"Host parameter is required. Usage: invoke swu-apply --{level} --host <target-ip>")
    
    print(f"Found SWU: {swu_path.name}")
    
    # Get SWU file size for info
    swu_size_mb = swu_path.stat().st_size / (1024 * 1024)
    print(f"SWU file size: {swu_size_mb:.1f} MB")
    
    # SSH options to suppress known hosts warning and post-quantum warnings
    ssh_opts = _ssh_opts()
    
    # Try /tmp first, then fall back to /root
    target_paths = ["/tmp", "/root"]
    target_path = None
    
    for tmp_path in target_paths:
        print(f"Trying to copy to {tmp_path} on target...")
        
        # Copy the SWU file to the target (capture output, filter, then display)
        scp_cmd = ["scp"] + ssh_opts + [str(swu_path), f"{user}@{host}:{tmp_path}/{swu_path.name}"]
        r = ctx.run(
            shlex.join(scp_cmd),
            echo=False, hide=False, warn=True, encoding="utf-8"
        )
        
        if r and r.exited == 0:
            # Filter and display output
            output = _filter_ssh_output(r.stdout + r.stderr)
            if output:
                print(output)
            
            # Verify file was copied correctly by checking size on target
            ssh_cmd = ["ssh"] + ssh_opts + ["-p", str(22), f"{user}@{host}",
             f"ls -la {tmp_path}/{swu_path.name} 2>/dev/null && wc -c < {tmp_path}/{swu_path.name}"]
            vr = ctx.run(
                shlex.join(ssh_cmd),
                hide=True, warn=True
            )
            vr.stdout = _filter_ssh_output(vr.stdout)
            vr.stderr = _filter_ssh_output(vr.stderr)
            if vr and vr.exited == 0 and vr.stdout.strip():
                try:
                    target_size = int(vr.stdout.strip().split('\n')[-1].strip())
                    if target_size == swu_path.stat().st_size:
                        target_path = tmp_path
                        print(f"Successfully copied to {tmp_path} ({swu_size_mb:.1f} MB)")
                        break
                    else:
                        print(f"Size mismatch on {tmp_path}: expected {swu_path.stat().st_size}, got {target_size}")
                except (ValueError, TypeError, IndexError):
                    print(f"File verification failed on {tmp_path}")
            else:
                print(f"File verification failed on {tmp_path}")
        else:
            # Filter and display error output
            err_output = _filter_ssh_output((r.stdout if r else "") + (r.stderr if r else ""))
            if err_output:
                print(err_output)
            print(f"Failed to copy to {tmp_path}, trying next location...")
    
    if not target_path:
        raise Exit(f"Failed to copy SWU file to target. Tried: {', '.join(target_paths)}")
    
    print(f"Applying update on target (using {target_path})...")
    
    # Apply the update directly with swupdate tool
    swupdate_cmd = ["ssh"] + ssh_opts + ["-p", str(22), f"{user}@{host}",
         f"/usr/bin/swupdate -i {target_path}/{swu_path.name}"]
    r = ctx.run(
        shlex.join(swupdate_cmd),
        echo=False, hide=False, warn=True, encoding="utf-8"
    )
    
    if r:
        output = _filter_ssh_output(r.stdout + r.stderr)
        if output:
            print(output)
    
    if r and r.exited == 0:
        print("Update applied successfully. Reboot the target to activate.")
    else:
        print(f"Update failed with exit code {r.exited if r else 'unknown'}")
        raise Exit("Failed to apply SWU update")
