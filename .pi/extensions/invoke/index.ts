/**
 * Invoke Extension for pi — provides tools that wrap invoke tasks for Yocto builds.
 *
 * Auto-discovered from .pi/extensions/invoke/index.ts (no registration needed).
 * Tool names match invoke task names with `invoke_` prefix.
 */

import { Type } from "@mariozechner/pi-ai";
import { defineTool, type ExtensionAPI } from "@mariozechner/pi-coding-agent";

const LEVELS = ["base", "gui", "games", "chrome", "ai"] as const;

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
		host: process.env.INVOKE_TARGET_HOST || "",
		user: process.env.INVOKE_TARGET_USER || "root",
		port: parseInt(process.env.INVOKE_TARGET_PORT || "22"),
		key: process.env.INVOKE_TARGET_KEY || "",
	};

	async function sshExec(cmd: string, sudo = false): Promise<string> {
		if (!_target.host) throw new Error("No target connected. Call invoke_target_connect first.");
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

	// ── Tools: Container Management ───────────────────────────────────────

	const dockerInit = defineTool({
		name: "invoke_docker_init",
		label: "Docker Init",
		description: "Build the yokto Docker container.",
		parameters: Type.Object({
			noCache: Type.Boolean({ description: "Do not use cache when building the image", default: false }),
		}),
		async execute(_toolCallId, params, _signal, _onUpdate) {
			const args = params.noCache ? ["--no-cache"] : [];
			const r = await runInvokeShortCtx("docker-init", args);
			return { content: [{ type: "text", text: r.text }], details: { exit: r.success ? 0 : 1 } };
		},
	});

	const containerStatus = defineTool({
		name: "invoke_container_status",
		label: "Container Status",
		description: "Check whether the yokto Docker image exists and the build container is running.",
		parameters: Type.Object({}),
		async execute(_toolCallId, _params, _signal, _onUpdate) {
			const r = await runInvokeShortCtx("container-status", []);
			return { content: [{ type: "text", text: r.text }], details: { exit: r.success ? 0 : 1 } };
		},
	});

	const containerStart = defineTool({
		name: "invoke_container_start",
		label: "Container Start",
		description: "Start (or restart) the background yokto build container. Needed before builds.",
		parameters: Type.Object({}),
		async execute(_toolCallId, _params, _signal, _onUpdate) {
			const r = await runInvokeShortCtx("container-start", []);
			return { content: [{ type: "text", text: r.text }], details: { exit: r.success ? 0 : 1 } };
		},
	});

	const containerStop = defineTool({
		name: "invoke_container_stop",
		label: "Container Stop",
		description: "Stop and remove the background yokto build container.",
		parameters: Type.Object({}),
		async execute(_toolCallId, _params, _signal, _onUpdate) {
			const r = await runInvokeShortCtx("container-stop", []);
			return { content: [{ type: "text", text: r.text }], details: { exit: r.success ? 0 : 1 } };
		},
	});

	const containerShell = defineTool({
		name: "invoke_container_shell",
		label: "Container Shell",
		description: "Open a plain shell inside the running build container (no kas setup).",
		parameters: Type.Object({}),
		async execute(_toolCallId, _params, _signal, _onUpdate) {
			const r = await runInvokeShortCtx("container-shell", []);
			return { content: [{ type: "text", text: r.text }], details: { exit: r.success ? 0 : 1 } };
		},
	});

	const containerExec = defineTool({
		name: "invoke_container_exec",
		label: "Container Exec",
		description: "Run a command inside the yokto build container. Auto-starts container if needed.",
		parameters: Type.Object({
			command: Type.String({ description: "Shell command to run inside the container" }),
		}),
		async execute(_toolCallId, params, _signal, _onUpdate) {
			const r = await runInvokeShortCtx("container-exec", [params.command]);
			return { content: [{ type: "text", text: r.text }], details: { exit: r.success ? 0 : 1 } };
		},
	});

	const dockerPurge = defineTool({
		name: "invoke_docker_purge",
		label: "Docker Purge",
		description: "Remove the yokto docker image and all related containers.",
		parameters: Type.Object({}),
		async execute(_toolCallId, _params, _signal, _onUpdate) {
			const r = await runInvokeShortCtx("docker-purge", []);
			return { content: [{ type: "text", text: r.text }], details: { exit: r.success ? 0 : 1 } };
		},
	});

	// ── Tools: Build ─────────────────────────────────────────────────────────

	const buildCheckout = defineTool({
		name: "invoke_build_checkout",
		label: "Build Checkout",
		description: "Fetch layers and write config (no build). Runs in background via --detach.",
		parameters: Type.Object({
			level: Type.String({ description: "Build level: base, wayland, games, chrome, ai", default: "base" }),
			update: Type.Boolean({ description: "Force update of layer repos", default: false }),
			force: Type.Boolean({ description: "Overwrite existing config files", default: false }),
			detach: Type.Boolean({ description: "Run in background (for MCP)", default: false }),
		}),
		async execute(_toolCallId, params, _signal, _onUpdate) {
			const level = params.level ?? "base";
			if (!LEVELS.includes(level as (typeof LEVELS)[number])) {
				return {
					content: [{ type: "text", text: `Unknown level '${level}'. Choose: ${LEVELS.join(", ")}` }],
					details: { error: "unknown_level" },
				};
			}
			const args = [`--${level}`];
			if (params.update) args.push("--update");
			if (params.force) args.push("--force");
			if (params.detach) args.push("--detach");
			const r = await runInvokeCtx("build-checkout", args, 300_000);
			return { content: [{ type: "text", text: r.text }], details: { exit: r.success ? 0 : 1 } };
		},
	});

	const buildStart = defineTool({
		name: "invoke_build_start",
		label: "Build Start",
		description: "Checkout layers and build the image. Monitor with invoke_build_status. Stop with invoke_build_stop.",
		promptSnippet: "invoke_build_start(level) — start a detached Yocto build for base/wayland/games/chrome/ai",
		promptGuidelines: [
			"Use invoke_build_start when the user asks to build a Yocto image or compile the project.",
			"Use invoke_build_start when the user wants to build for a specific level (base, wayland, games, chrome, ai).",
			"After calling invoke_build_start, monitor progress with invoke_build_status or invoke_build_last.",
			"Only one build or checkout can run at a time; invoke_build_start will fail if another is running.",
		],
		parameters: Type.Object({
			level: Type.String({ description: "Build level: base, wayland, games, chrome, or ai", default: "base" }),
			detach: Type.Boolean({ description: "Run in background (for MCP)", default: true }),
		}),
		async execute(_toolCallId, params, _signal, _onUpdate) {
			const level = params.level ?? "base";
			if (!LEVELS.includes(level as (typeof LEVELS)[number])) {
				return {
					content: [{ type: "text", text: `Unknown level '${level}'. Choose: ${LEVELS.join(", ")}` }],
					details: { error: "unknown_level" },
				};
			}
			const args = [`--${level}`];
			if (params.detach) args.push("--detach");
			const r = await runInvokeCtx("build-start", args, 300_000);
			return { content: [{ type: "text", text: r.text }], details: { exit: r.success ? 0 : 1 } };
		},
	});

	const buildStop = defineTool({
		name: "invoke_build_stop",
		label: "Build Stop",
		description: "Stop a running detached build or checkout gracefully.",
		parameters: Type.Object({
			force: Type.Boolean({ description: "Use SIGKILL immediately", default: false }),
		}),
		async execute(_toolCallId, params, _signal, _onUpdate) {
			const args: string[] = [];
			if (params.force) args.push("--force");
			const r = await runInvokeShortCtx("build-stop", args);
			return { content: [{ type: "text", text: r.text }], details: { exit: r.success ? 0 : 1 } };
		},
	});

	const buildStatus = defineTool({
		name: "invoke_build_status",
		label: "Build Status",
		description: "Check if a detached build or checkout is running.",
		parameters: Type.Object({
			lines: Type.Number({ description: "Number of trailing log lines to show", default: 10 }),
		}),
		async execute(_toolCallId, params, _signal, _onUpdate) {
			const r = await runInvokeShortCtx("build-status", [`--lines=${params.lines}`]);
			return { content: [{ type: "text", text: r.text }], details: { exit: r.success ? 0 : 1 } };
		},
	});

	const buildLast = defineTool({
		name: "invoke_build_last",
		label: "Build Last",
		description: "Show the result of the most recent build or checkout operation.",
		parameters: Type.Object({
			lines: Type.Number({ description: "Number of trailing log lines", default: 20 }),
		}),
		async execute(_toolCallId, params, _signal, _onUpdate) {
			const r = await runInvokeShortCtx("build-last", [`--lines=${params.lines}`]);
			return { content: [{ type: "text", text: r.text }], details: { exit: r.success ? 0 : 1 } };
		},
	});

	const shell = defineTool({
		name: "invoke_shell",
		label: "Shell",
		description: "Open a shell with kas environment configured (sources checked out).",
		parameters: Type.Object({
			level: Type.String({ description: "Build level for env setup", default: "base" }),
			command: Type.String({ description: "Optional command to run (if blank, opens interactive shell)", default: "" }),
		}),
		async execute(_toolCallId, params, _signal, _onUpdate) {
			const level = params.level ?? "base";
			if (!LEVELS.includes(level as (typeof LEVELS)[number])) {
				return {
					content: [{ type: "text", text: `Unknown level '${level}'. Choose: ${LEVELS.join(", ")}` }],
					details: { error: "unknown_level" },
				};
			}
			const args = [`--${level}`];
			if (params.command) args.push(`--command=${params.command}`);
			const r = await runInvokeCtx("shell", args, 300_000);
			return { content: [{ type: "text", text: r.text }], details: { exit: r.success ? 0 : 1 } };
		},
	});

	const buildShell = defineTool({
		name: "invoke_build_shell",
		label: "Build Shell",
		description: "Enter kas shell with environment configured. Without --command: enters interactive shell. With --command: runs the command in kas environment.",
		parameters: Type.Object({
			level: Type.String({ description: "Build level for env setup", default: "base" }),
			command: Type.String({ description: "Command to run (if omitted, enters interactive shell)", default: "" }),
		}),
		async execute(_toolCallId, params, _signal, _onUpdate) {
			const level = params.level ?? "base";
			if (!LEVELS.includes(level as (typeof LEVELS)[number])) {
				return {
					content: [{ type: "text", text: `Unknown level '${level}'. Choose: ${LEVELS.join(", ")}` }],
					details: { error: "unknown_level" },
				};
			}
			const args = [`--${level}`];
			if (params.command) args.push(`--command=${params.command}`);
			const r = await runInvokeCtx("build-shell", args, 300_000);
			return { content: [{ type: "text", text: r.text }], details: { exit: r.success ? 0 : 1 } };
		},
	});

	const buildClean = defineTool({
		name: "invoke_build_clean",
		label: "Build Clean",
		description: "Remove build output. Preserves downloads/ and sstate/ by default.",
		parameters: Type.Object({
			layers: Type.Boolean({ description: "Also remove kas-cloned layers", default: false }),
			sstate: Type.Boolean({ description: "Also remove sstate cache", default: false }),
			recipe: Type.String({ description: "Clean a specific recipe from sstate", default: "" }),
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
		name: "invoke_build_rebuild",
		label: "Build Rebuild",
		description: "Clean checkout layers + build output, then checkout and build from scratch.",
		parameters: Type.Object({
			level: Type.String({ description: "Build level", default: "base" }),
		}),
		async execute(_toolCallId, params, _signal, _onUpdate) {
			const level = params.level ?? "base";
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

	const images = defineTool({
		name: "invoke_images",
		label: "Images",
		description: "List built .wic.bz2 image files.",
		parameters: Type.Object({}),
		async execute(_toolCallId, _params, _signal, _onUpdate) {
			const r = await runInvokeShortCtx("images", []);
			return { content: [{ type: "text", text: r.text }], details: { exit: r.success ? 0 : 1 } };
		},
	});

	const flash = defineTool({
		name: "invoke_flash",
		label: "Flash",
		description: "Flash a built .wic.bz2 image to an SD card.",
		parameters: Type.Object({
			device: Type.String({ description: "Block device path (e.g. /dev/sdb)" }),
			level: Type.String({ description: "Build level whose image to flash", default: "base" }),
			force: Type.Boolean({ description: "Skip removable drive safety check", default: false }),
		}),
		async execute(_toolCallId, params, _signal, _onUpdate) {
			const level = params.level ?? "base";
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
		name: "invoke_target_connect",
		label: "Target Connect",
		description: "Connect to a target Raspberry Pi 5 via SSH.",
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
		name: "invoke_target_disconnect",
		label: "Target Disconnect",
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
		name: "invoke_target_status",
		label: "Target Status",
		description: "Show current target connection status.",
		parameters: Type.Object({}),
		async execute(_toolCallId, _params, _signal, _onUpdate) {
			if (!_target.host) {
				return {
					content: [{ type: "text", text: "Not connected. Use invoke_target_connect to connect." }],
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
		name: "invoke_target_exec",
		label: "Target Exec",
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

	const targetRunAsRoot = defineTool({
		name: "invoke_target_run_as_root",
		label: "Target Run As Root",
		description: "Run a command as root on the target Raspberry Pi via SSH.",
		parameters: Type.Object({ command: Type.String({ description: "Command to execute as root" }) }),
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
		name: "invoke_target_copy",
		label: "Target Copy",
		description: "Copy a local file/directory to the target via SCP.",
		parameters: Type.Object({
			source: Type.String({ description: "Local path" }),
			dest: Type.String({ description: "Destination path on target" }),
		}),
		async execute(_toolCallId, params, _signal, _onUpdate) {
			if (!_target.host) {
				return {
					content: [{ type: "text", text: "No target connected. Call invoke_target_connect first." }],
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

	// ── Register All Tools ──────────────────────────────────────────────────

	// Container
	pi.registerTool(dockerInit);
	pi.registerTool(containerStatus);
	pi.registerTool(containerStart);
	pi.registerTool(containerStop);
	pi.registerTool(containerShell);
	pi.registerTool(containerExec);
	pi.registerTool(dockerPurge);

	// Build
	pi.registerTool(buildCheckout);
	pi.registerTool(buildStart);
	pi.registerTool(buildStop);
	pi.registerTool(buildStatus);
	pi.registerTool(buildLast);
	pi.registerTool(shell);
	pi.registerTool(buildShell);
	pi.registerTool(buildClean);
	pi.registerTool(buildRebuild);
	pi.registerTool(images);
	pi.registerTool(flash);

	// Target
	pi.registerTool(targetConnect);
	pi.registerTool(targetDisconnect);
	pi.registerTool(targetStatus);
	pi.registerTool(targetExec);
	pi.registerTool(targetRunAsRoot);
	pi.registerTool(targetCopy);

	pi.on("session_start", async (_event, ctx) => {
		ctx.ui.notify("Invoke tools loaded", "info");
	});
}
