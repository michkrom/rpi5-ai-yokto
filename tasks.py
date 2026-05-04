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
        "core": "Minimal headless image (default)",
        "wayland": "Wayland desktop + Weston",
        "weston": "Alias for --wayland",
        "chrome": "Wayland + Chromium",
        "quake3": "Wayland + Quake3e",
        "update": "Force update of layer repos",
        "force": "Overwrite existing config files",
        "detach": "Run in background (for MCP)",
    }
)
def build_checkout(ctx, core=False, wayland=False, weston=False, chrome=False, quake3=False, update=False, force=False, detach=False):
    """Fetch layers and write config (no build)."""
    _ensure_image(ctx)
    level = _validate(_level(core, wayland, weston, chrome, quake3))
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
        "core": "Minimal headless image (default)",
        "wayland": "Wayland desktop + Weston",
        "weston": "Alias for --wayland",
        "chrome": "Wayland + Chromium",
        "quake3": "Wayland + Quake3e",
        "log": "Save build output to a file (e.g. build-chrome.log)",
        "detach": "Run in background (for MCP)",
    }
)
def build_start(ctx, core=False, wayland=False, weston=False, chrome=False, quake3=False, log=None, detach=False):
    """Checkout layers and build the image."""
    _ensure_image(ctx)
    level = _validate(_level(core, wayland, weston, chrome, quake3))
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


def _latest_log():
    """Find the most recent build or checkout log file."""
    logs = sorted(ROOT.glob("build-*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
    logs += sorted(ROOT.glob("checkout-*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
    return sorted(logs, key=lambda p: p.stat().st_mtime, reverse=True)[0] if logs else None


@task(help={"lines": "Number of trailing log lines to show"})
def build_status(ctx, lines=10):
    """Check if a detached build or checkout is running."""
    lock = _read_lock()
    if not lock:
        print("No detached operation running.")
        return

    op_type = lock.get("type", "build")
    level = lock["level"]
    pid = lock.get("pid", 0)

    if _lock_alive_ctx(ctx, lock):
        print(f"{op_type.capitalize()} '{level}' is running (PID {pid}).")
        _show_tail(ctx, f"{op_type}-{level}.log", lines)
    else:
        print(f"{op_type.capitalize()} '{level}' has finished.")
        _show_tail(ctx, f"{op_type}-{level}.log", lines)


@task(help={"lines": "Number of trailing log lines to show"})
def build_last(ctx, lines=20):
    """Show the result of the most recent build or checkout operation."""
    log = _latest_log()
    if not log:
        print("No build or checkout logs found.")
        return
    print(f"\n--- {log.name} ---")
    ctx.run(f'tail -n {lines} "{log}"', echo=False)


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
        print("Container not running. Cleaning up stale lock.")
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
        "core": "Minimal headless image (default)",
        "wayland": "Wayland desktop + Weston",
        "weston": "Alias for --wayland",
        "chrome": "Wayland + Chromium",
        "quake3": "Wayland + Quake3e",
    }
)
def shell(ctx, core=False, wayland=False, weston=False, chrome=False, quake3=False, command=""):
    """Open a shell with kas environment configured (sources checked out)."""
    _ensure_image(ctx)
    level = _validate(_level(core, wayland, weston, chrome, quake3))
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
def docker_shell(ctx):
    """Open a plain docker shell (no kas setup)."""
    _ensure_container(ctx)
    ctx.run(
        f'docker exec -u {CONTAINER_USER} -it {CONTAINER_NAME} bash',
        pty=False,
    )


@task
def images(ctx):
    """List built .wic.bz2 images."""
    ctx.run(f"find {ROOT} -path '*/deploy/images/raspberrypi5/*.wic.bz2' -ls")


def _clean_old_artifacts(images_dir):
    """Remove all but the latest timestamped artifacts."""
    wics = sorted(f for f in images_dir.glob("*.wic.bz2") if not f.is_symlink())
    if len(wics) <= 1:
        return
    for old in wics[:-1]:
        stem = old.stem.replace(".wic", "")
        print(f"  Pruning old artifacts: {stem}")
        for f in images_dir.glob(f"{stem}.*"):
            f.unlink()


def _find_wic(level):
    """Find the correct wic.bz2 image for a level."""
    images_dir = ROOT / "build" / "tmp" / "deploy" / "images" / "raspberrypi5"
    if level == "core":
        basename = "core-image-base"
    else:
        basename = "core-image-weston"
    pattern = f"{basename}-raspberrypi5.rootfs.wic.bz2"
    target = images_dir / pattern
    if target.exists():
        return target
    matches = sorted(f for f in images_dir.glob(f"{basename}-raspberrypi5.rootfs.wic.bz2") if f.exists())
    if matches:
        return matches[-1]
    raise Exit(f"No .wic.bz2 found for level '{level}'. Run 'invoke build-start --{level}' first.")


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
        "core": "Minimal headless image (default)",
        "wayland": "Wayland desktop + Weston",
        "weston": "Alias for --wayland",
        "chrome": "Wayland + Chromium",
        "quake3": "Wayland + Quake3e",
        "force": "Skip removable drive check",
        "nobmap": "Skip bmap usage, use dd instead",
        "dd": "Use dd instead of bmaptool",
    }
)
def flash(ctx, device=None, core=False, wayland=False, weston=False, chrome=False, quake3=False, force=False, nobmap=False, dd=False):
    """Flash the built image to an SD card. Runs on host for USB access."""
    level = _validate(_level(core, wayland, weston, chrome, quake3))

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

        if not Path(bmap).exists():
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
        "all": "Remove everything: build output, layers, downloads/, sstate-cache/",
    }
)
def build_clean(ctx, layers=False, sstate=False, recipe="", all=False):
    """Remove build output. Without flags, preserves downloads/, sstate-cache/, and layers."""
    lock = _read_lock()
    if _lock_alive_ctx(ctx, lock):
        raise Exit(f"{lock.get('type', 'Build').capitalize()} '{lock['level']}' is running. Stop it first with 'invoke stop-build'.")
    _clear_lock()

    build_dir = ROOT / "build"
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


@task(
    help={
        "core": "Minimal headless image (default)",
        "wayland": "Wayland desktop + Weston",
        "weston": "Alias for --wayland",
        "chrome": "Wayland + Chromium",
        "quake3": "Wayland + Quake3e",
    }
)
def build_rebuild(ctx, core=False, wayland=False, weston=False, chrome=False, quake3=False):
    """Clean checkout layers + build output, then checkout and build."""
    level = _validate(_level(core, wayland, weston, chrome, quake3))
    print(f"\n{'='*60}\n  Clean rebuild: {level}\n{'='*60}")
    build_clean(ctx, layers=True)
    build_checkout(ctx, **{level: True})
    build_start(ctx, **{level: True})


@task
def docker_purge(ctx):
    """Remove the yokto docker image and all related containers."""
    ctx.run(
        f'docker ps -a -q --filter ancestor={IMAGE} | xargs -r docker rm -f',
        warn=True,
        hide=True,
    )
    ctx.run(f'docker rmi -f {IMAGE}', warn=True)
