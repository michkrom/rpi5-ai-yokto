/**
 * Yocto Extension for pi — delegates all build/container commands to invoke.
 *
 * Auto-discovered from .pi/extensions/yocto/index.ts (no registration needed).
 */

import { Type } from "@mariozechner/pi-ai";
import { defineTool, type ExtensionAPI } from "@mariozechner/pi-coding-agent";

const LEVELS = ["core", "wayland", "chrome", "quake3"] as const;

// ── Helpers ──────────────────────────────────────────────────────────────

async function runInvoke(
	pi: ExtensionAPI,
	task: string,
	args: string[] = [],
	timeoutMs: number = 300_000,
) {
	const r = await pi.exec("invoke", [task, ...args], { timeout: timeoutMs });
	const code = typeof r.code === "number" ? r.code : NaN;
	if (code !== 0) {
		return {
			success: false,
			text: `invoke ${task} ${args.join(" ")} failed (exit ${code}):\nstderr: ${r.stderr}\nstdout: ${r.stdout}`,
		};
	}
	return { success: true, text: r.stdout + r.stderr };
}

async function runInvokeShort(pi: ExtensionAPI, task: string, args: string[] = []) {
	return runInvoke(pi, task, args, 30_000);
}

// ── Extension Registration ───────────────────────────────────────────────

export default function (pi: ExtensionAPI) {
	const cwd = pi.cwd;

	// ── Helpers with captured pi ──────────────────────────────────────────

	async function runInvokeCtx(task: string, args: string[] = [], timeoutMs: number = 300_000) {
		return runInvoke(pi, task, args, timeoutMs);
	}

	async function runInvokeShortCtx(task: string, args: string[] = []) {
		return runInvoke(pi, task, args, 30_000);
	}

	// ── Target Device State ───────────────────────────────────────────────

	const _target = {
		host: process.env.YOCTO_TARGET_HOST || "",
		user: process.env.YOCTO_TARGET_USER || "root",
		port: parseInt(process.env.YOCTO_TARGET_PORT || "22"),
		key: process.env.YOCTO_TARGET_KEY || "",
	};

	async function sshExec(cmd: string, sudo = false): Promise<string> {
		if (!_target.host) throw new Error("No target connected. Call yocto_target_connect first.");
		const ssh = ["-o", "ConnectTimeout=10"];
		if (_target.key) ssh.push("-i", _target.key);
		ssh.push("-p", String(_target.port), `${_target.user}@${_target.host}`);
		const full = sudo ? `sudo ${cmd}` : cmd;
		const r = await pi.exec("ssh", [...ssh, full], { timeout: 60_000 });
		if (r.code !== 0) {
			throw new Error(`SSH failed (exit ${r.code}): ${r.stderr || ""} ${r.stdout || ""}`);
		}
		return r.stdout + r.stderr;
	}

	// ── Tools: Container ─────────────────────────────────────────────────────

	const containerStatus = defineTool({
		name: "yocto_container_status",
		label: "Yocto Container",
		description: "Check whether the yokto Docker image exists and the build container is running.",
		parameters: Type.Object({}),
		async execute(_toolCallId, _params, _signal, _onUpdate) {
			const r = await runInvokeShortCtx("container-status", []);
			return { content: [{ type: "text", text: r.text }], details: { exit: r.success ? 0 : 1 } };
		},
	});

	const containerStart = defineTool({
		name: "yocto_container_start",
		label: "Start Yocto Container",
		description: "Start (or restart) the background yokto build container. Needed before builds.",
		parameters: Type.Object({}),
		async execute(_toolCallId, _params, _signal, _onUpdate) {
			const r = await runInvokeShortCtx("container-start", []);
			return { content: [{ type: "text", text: r.text }], details: { exit: r.success ? 0 : 1 } };
		},
	});

	const containerStop = defineTool({
		name: "yocto_container_stop",
		label: "Stop Yocto Container",
		description: "Stop and remove the background yokto build container.",
		parameters: Type.Object({}),
		async execute(_toolCallId, _params, _signal, _onUpdate) {
			const r = await runInvokeShortCtx("container-stop", []);
			return { content: [{ type: "text", text: r.text }], details: { exit: r.success ? 0 : 1 } };
		},
	});

	const containerExec = defineTool({
		name: "yocto_container_exec",
		label: "Exec in Yocto Container",
		description: "Run an arbitrary command inside the yokto build container. Auto-starts container if needed.",
		parameters: Type.Object({
			command: Type.String({ description: "Shell command to run inside the container" }),
		}),
		async execute(_toolCallId, params, _signal, _onUpdate) {
			const containerCmd = `docker exec -u yokto yocto-bg bash -lc '${params.command.replace(/'/g, "'\\''")}'`;
			const r = await runInvokeShortCtx("bash", [`--command=${containerCmd}`]);
			return { content: [{ type: "text", text: r.text }], details: { exit: r.success ? 0 : 1 } };
		},
	});

	// ── Tools: Build ─────────────────────────────────────────────────────────

	const buildStart = defineTool({
		name: "yocto_build_start",
		label: "Build Yocto Image",
		description:
			"Start a detached kas build for a level. Monitor with yocto_build_logs. Stop with yocto_build_stop.",
		promptSnippet:
			"yocto_build_start(level) — start a detached Yocto build for core/wayland/chrome/quake3",
		promptGuidelines: [
			"Use yocto_build_start when the user asks to build a Yocto image or compile the project.",
			"Use yocto_build_start when the user wants to build for a specific level (core, wayland, chrome, quake3).",
			"After calling yocto_build_start, monitor progress with yocto_build_logs.",
			"Only one build or checkout can run at a time; yocto_build_start will fail if another is running.",
		],
		parameters: Type.Object({
			level: Type.String({ description: "Build level: core, wayland, chrome, or quake3" }),
		}),
		async execute(_toolCallId, params, _signal, _onUpdate) {
			const level = params.level ?? "core";
			if (!LEVELS.includes(level as (typeof LEVELS)[number])) {
				return {
					content: [{ type: "text", text: `Unknown level '${level}'. Choose: ${LEVELS.join(", ")}` }],
					details: { error: "unknown_level" },
				};
			}
			const r = await runInvokeCtx("build-start", [`--${level}`, "--detach"], 300_000);
			return { content: [{ type: "text", text: r.text }], details: { exit: r.success ? 0 : 1 } };
		},
	});

	const buildCheckout = defineTool({
		name: "yocto_build_checkout",
		label: "Checkout Yocto Layers",
		description: "Checkout Yocto layers for a level without building. Runs in background via --detach.",
		parameters: Type.Object({
			level: Type.String({ description: "Build level: core, wayland, chrome, or quake3", default: "core" }),
			update: Type.Boolean({ description: "Force git pull of layer repos", default: false }),
			force: Type.Boolean({ description: "Overwrite existing config files", default: false }),
		}),
		async execute(_toolCallId, params, _signal, _onUpdate) {
			const level = params.level ?? "core";
			if (!LEVELS.includes(level as (typeof LEVELS)[number])) {
				return {
					content: [{ type: "text", text: `Unknown level '${level}'. Choose: ${LEVELS.join(", ")}` }],
					details: { error: "unknown_level" },
				};
			}
			const args = [`--${level}`, "--detach"];
			if (params.update) args.push("--update");
			if (params.force) args.push("--force");
			const r = await runInvokeCtx("build-checkout", args, 300_000);
			return { content: [{ type: "text", text: r.text }], details: { exit: r.success ? 0 : 1 } };
		},
	});

	const buildStop = defineTool({
		name: "yocto_build_stop",
		label: "Stop Yocto Build",
		description: "Stop a running detached build or checkout gracefully (SIGINT → SIGTERM → SIGKILL).",
		parameters: Type.Object({
			force: Type.Boolean({ description: "Use SIGKILL immediately (may corrupt sstate)", default: false }),
		}),
		async execute(_toolCallId, params, _signal, _onUpdate) {
			const args: string[] = [];
			if (params.force) args.push("--force");
			const r = await runInvokeShortCtx("build-stop", args);
			return { content: [{ type: "text", text: r.text }], details: { exit: r.success ? 0 : 1 } };
		},
	});

	const buildStatus = defineTool({
		name: "yocto_build_status",
		label: "Yocto Build Status",
		description: "Check if a detached build or checkout is running and show recent log lines.",
		parameters: Type.Object({
			lines: Type.Number({ description: "Number of trailing log lines to show", default: 10 }),
		}),
		async execute(_toolCallId, params, _signal, _onUpdate) {
			const r = await runInvokeShortCtx("build-status", [`--lines=${params.lines}`]);
			return { content: [{ type: "text", text: r.text }], details: { exit: r.success ? 0 : 1 } };
		},
	});

	const buildLogs = defineTool({
		name: "yocto_build_logs",
		label: "Yocto Build Logs",
		description: "Show recent output from a specific level's build log.",
		parameters: Type.Object({
			level: Type.String({ description: "Build level: core, wayland, chrome, quake3", default: "core" }),
			lines: Type.Number({ description: "Number of tail lines", default: 50 }),
		}),
		async execute(_toolCallId, params, _signal, _onUpdate) {
			const level = params.level ?? "core";
			const logPath = `${cwd}/build-${level}.log`;
			const r = await runInvokeShortCtx("bash", [`--command=tail -n ${params.lines} "${logPath}"`]);
			if (!r.success) {
				return {
					content: [{ type: "text", text: `No build log found for '${level}'. Start a build first with yocto_build_start.` }],
					details: { error: "no_log" },
				};
			}
			let status = "EXITED";
			try {
				const lockCheck = await runInvokeShortCtx("bash", [`--command=cat .build-lock 2>/dev/null || echo "none"`]);
				const lock = JSON.parse(lockCheck.text || "{}") || {};
				if (lock.level === level && lock.pid) {
					const aliveCmd = `docker exec yocto-bg bash -c 'st=$(ps -p ${lock.pid} -o state= 2>/dev/null); test -n "$st" && test "$st" != Z && echo alive || echo dead'`;
					const alive = await runInvokeShortCtx("bash", [`--command=${aliveCmd}`]);
					if (alive.text?.includes("alive")) status = `RUNNING (PID ${lock.pid})`;
				}
			} catch {}
			return {
				content: [{ type: "text", text: `Build '${level}' ${status}.\n${r.text}` }],
				details: { exit: 0 },
			};
		},
	});

	const buildLast = defineTool({
		name: "yocto_build_last",
		label: "Last Build Log",
		description: "Show the result of the most recent build or checkout.",
		parameters: Type.Object({
			lines: Type.Number({ description: "Number of trailing log lines", default: 20 }),
		}),
		async execute(_toolCallId, params, _signal, _onUpdate) {
			const r = await runInvokeShortCtx("build-last", [`--lines=${params.lines}`]);
			return { content: [{ type: "text", text: r.text }], details: { exit: r.success ? 0 : 1 } };
		},
	});

	const buildShell = defineTool({
		name: "yocto_build_shell",
		label: "Yocto Shell",
		description: "Run a shell command inside a kas-configured environment (sources checked out).",
		parameters: Type.Object({
			command: Type.String({ description: "BitBake or shell command to run inside the kas env" }),
			level: Type.String({ description: "Build level for env setup", default: "core" }),
		}),
		async execute(_toolCallId, params, _signal, _onUpdate) {
			const level = params.level ?? "core";
			if (!LEVELS.includes(level as (typeof LEVELS)[number])) {
				return {
					content: [{ type: "text", text: `Unknown level '${level}'. Choose: ${LEVELS.join(", ")}` }],
					details: { error: "unknown_level" },
				};
			}
			const r = await runInvokeCtx("shell", [`--${level}`, `--command=${params.command}`], 300_000);
			return { content: [{ type: "text", text: r.text }], details: { exit: r.success ? 0 : 1 } };
		},
	});

	const buildClean = defineTool({
		name: "yocto_build_clean",
		label: "Clean Yocto Build",
		description: "Remove build output. Preserves downloads/ and sstate/ by default.",
		parameters: Type.Object({
			layers: Type.Boolean({ description: "Also remove kas-cloned layers", default: false }),
			sstate: Type.Boolean({ description: "Also remove sstate cache", default: false }),
			recipe: Type.String({ description: "Clean a specific recipe from sstate (e.g. chromium-ozone-wayland)", default: "" }),
			all: Type.Boolean({ description: "Remove everything", default: false }),
		}),
		async execute(_toolCallId, params, _signal, _onUpdate) {
			const args: string[] = [];
			if (params.layers) args.push("--layers");
			if (params.sstate) args.push("--sstate");
			if (params.all) args.push("--all");
			if (params.recipe) args.push(`--recipe=${params.recipe}`);
			const r = await runInvokeShortCtx("build-clean", args);
			return { content: [{ type: "text", text: r.text }], details: { exit: r.success ? 0 : 1 } };
		},
	});

	const buildRebuild = defineTool({
		name: "yocto_build_rebuild",
		label: "Rebuild Yocto",
		description: "Clean checkout layers + build output, then checkout and build from scratch.",
		parameters: Type.Object({
			level: Type.String({ description: "Build level", default: "core" }),
		}),
		async execute(_toolCallId, params, _signal, _onUpdate) {
			const level = params.level ?? "core";
			if (!LEVELS.includes(level as (typeof LEVELS)[number])) {
				return {
					content: [{ type: "text", text: `Unknown level '${level}'. Choose: ${LEVELS.join(", ")}` }],
					details: { error: "unknown_level" },
				};
			}
			const r = await runInvokeCtx("build-rebuild", [`--${level}`], 300_000);
			return { content: [{ type: "text", text: r.text }], details: { exit: r.success ? 0 : 1 } };
		},
	});

	const buildImages = defineTool({
		name: "yocto_build_images",
		label: "List Yocto Images",
		description: "List built .wic.bz2 image files in deploy/images.",
		parameters: Type.Object({}),
		async execute(_toolCallId, _params, _signal, _onUpdate) {
			const r = await runInvokeShortCtx("images", []);
			return { content: [{ type: "text", text: r.text }], details: { exit: r.success ? 0 : 1 } };
		},
	});

	const buildFlash = defineTool({
		name: "yocto_build_flash",
		label: "Flash Yocto Image",
		description: "Flash a built .wic.bz2 image to an SD card. May trigger pkexec GUI password prompt.",
		parameters: Type.Object({
			device: Type.String({ description: "Block device path (e.g. /dev/sdb)" }),
			level: Type.String({ description: "Build level whose image to flash", default: "core" }),
			force: Type.Boolean({ description: "Skip removable drive safety check", default: false }),
		}),
		async execute(_toolCallId, params, _signal, _onUpdate) {
			const level = params.level ?? "core";
			if (!LEVELS.includes(level as (typeof LEVELS)[number])) {
				return {
					content: [{ type: "text", text: `Unknown level '${level}'. Choose: ${LEVELS.join(", ")}` }],
					details: { error: "unknown_level" },
				};
			}
			const args = [`--device=${params.device}`, `--${level}`];
			if (params.force) args.push("--force");
			const r = await runInvokeCtx("flash", args, 300_000);
			return { content: [{ type: "text", text: r.text }], details: { exit: r.success ? 0 : 1 } };
		},
	});

	// ── Tools: Target Device (SSH) ───────────────────────────────────────────

	const targetConnect = defineTool({
		name: "yocto_target_connect",
		label: "Connect to RPi5",
		description: "Connect to a target Raspberry Pi 5 via SSH. Required before other target_* tools.",
		parameters: Type.Object({
			host: Type.String({ description: "IP or hostname of the RPi5" }),
			user: Type.String({ description: "SSH user", default: "root" }),
			port: Type.Number({ description: "SSH port", default: 22 }),
			key: Type.String({ description: "Path to SSH private key (optional)", default: "" }),
		}),
		async execute(_toolCallId, params, _signal, _onUpdate) {
			_target.host = params.host;
			_target.user = params.user;
			_target.port = params.port;
			_target.key = params.key;
			try {
				const r = await sshExec("echo OK");
				if (r.includes("OK")) {
					return {
						content: [{ type: "text", text: `Connected to ${_target.user}@${_target.host}:${_target.port}` }],
						details: { connected: true },
					};
				}
			} catch (e) {
				_target.host = "";
				return {
					content: [{ type: "text", text: `Connection failed: ${e instanceof Error ? e.message : String(e)}` }],
					details: { connected: false },
				};
			}
			_target.host = "";
			return { content: [{ type: "text", text: "Connection failed." }], details: { connected: false } };
		},
	});

	const targetDisconnect = defineTool({
		name: "yocto_target_disconnect",
		label: "Disconnect from RPi5",
		description: "Disconnect from the current target device.",
		parameters: Type.Object({}),
		async execute(_toolCallId, _params, _signal, _onUpdate) {
			_target.host = "";
			_target.user = "root";
			_target.port = 22;
			_target.key = "";
			return { content: [{ type: "text", text: "Disconnected." }], details: {} };
		},
	});

	const targetStatus = defineTool({
		name: "yocto_target_status",
		label: "Target Status",
		description: "Show current target connection status.",
		parameters: Type.Object({}),
		async execute(_toolCallId, _params, _signal, _onUpdate) {
			if (!_target.host) {
				return {
					content: [{ type: "text", text: "Not connected. Use yocto_target_connect to connect." }],
					details: { connected: false },
				};
			}
			return {
				content: [{ type: "text", text: `Connected to ${_target.user}@${_target.host}:${_target.port}` }],
				details: { connected: true },
			};
		},
	});

	const targetExec = defineTool({
		name: "yocto_target_exec",
		label: "Exec on RPi5",
		description: "Run a command on the target via SSH.",
		parameters: Type.Object({ command: Type.String({ description: "Command to execute" }) }),
		async execute(_toolCallId, params, _signal, _onUpdate) {
			try {
				const r = await sshExec(params.command);
				return { content: [{ type: "text", text: r }], details: { exit: 0 } };
			} catch (e) {
				return {
					content: [{ type: "text", text: `Error: ${e instanceof Error ? e.message : String(e)}` }],
					details: { exit: 1 },
				};
			}
		},
	});

	const targetSudo = defineTool({
		name: "yocto_target_sudo",
		label: "Sudo on RPi5",
		description: "Run a command with sudo on the target via SSH.",
		parameters: Type.Object({ command: Type.String({ description: "Command with sudo" }) }),
		async execute(_toolCallId, params, _signal, _onUpdate) {
			try {
				const r = await sshExec(params.command, true);
				return { content: [{ type: "text", text: r }], details: { exit: 0 } };
			} catch (e) {
				return {
					content: [{ type: "text", text: `Error: ${e instanceof Error ? e.message : String(e)}` }],
					details: { exit: 1 },
				};
			}
		},
	});

	const targetCopy = defineTool({
		name: "yocto_target_copy",
		label: "Copy to RPi5",
		description: "Copy a local file/directory to the target via SCP.",
		parameters: Type.Object({
			source: Type.String({ description: "Local path" }),
			dest: Type.String({ description: "Destination path on target" }),
		}),
		async execute(_toolCallId, params, _signal, _onUpdate) {
			if (!_target.host) {
				return {
					content: [{ type: "text", text: "No target connected. Call yocto_target_connect first." }],
					details: { error: "not_connected" },
				};
			}
			const keyArg = _target.key ? ["-i", _target.key] : [];
			try {
				const r = await pi.exec("scp", [
					"-P", String(_target.port), ...keyArg, "-r",
					params.source, `${_target.user}@${_target.host}:${params.dest}`,
				], { timeout: 120_000 });
				return {
					content: [{ type: "text", text: `Copied ${params.source} -> ${_target.host}:${params.dest}` }],
					details: { exit: r.code },
				};
			} catch (e) {
				return {
					content: [{ type: "text", text: `Copy failed: ${e instanceof Error ? e.message : String(e)}` }],
					details: { exit: 1 },
				};
			}
		},
	});

	const targetDocker = defineTool({
		name: "yocto_target_docker",
		label: "Docker on RPi5",
		description: "Run a docker command on the target via SSH.",
		parameters: Type.Object({ command: Type.String({ description: "Docker subcommand" }) }),
		async execute(_toolCallId, params, _signal, _onUpdate) {
			try {
				const r = await sshExec(`docker ${params.command}`);
				return { content: [{ type: "text", text: r }], details: { exit: 0 } };
			} catch (e) {
				return {
					content: [{ type: "text", text: `Error: ${e instanceof Error ? e.message : String(e)}` }],
					details: { exit: 1 },
				};
			}
		},
	});

	// ── Register All Tools ──────────────────────────────────────────────────

	pi.registerTool(containerStatus);
	pi.registerTool(containerStart);
	pi.registerTool(containerStop);
	pi.registerTool(containerExec);

	pi.registerTool(buildStart);
	pi.registerTool(buildCheckout);
	pi.registerTool(buildStop);
	pi.registerTool(buildStatus);
	pi.registerTool(buildLogs);
	pi.registerTool(buildLast);
	pi.registerTool(buildShell);
	pi.registerTool(buildClean);
	pi.registerTool(buildRebuild);
	pi.registerTool(buildImages);
	pi.registerTool(buildFlash);

	pi.registerTool(targetConnect);
	pi.registerTool(targetDisconnect);
	pi.registerTool(targetStatus);
	pi.registerTool(targetExec);
	pi.registerTool(targetSudo);
	pi.registerTool(targetCopy);
	pi.registerTool(targetDocker);

	pi.on("session_start", async (_event, ctx) => {
		ctx.ui.notify("Yocto tools loaded (via invoke)", "info");
	});
}