/**
 * Target Extension for pi — provides tools for interacting with a target Raspberry Pi 5 via SSH/SCP.
 *
 * Auto-discovered from .pi/extensions/target/index.ts (no registration needed).
 */

import { Type } from "@mariozechner/pi-ai";
import { defineTool, type ExtensionAPI } from "@mariozechner/pi-coding-agent";

// ── Target Device State ─────────────────────────────────────────────────────

const targetState = {
	host: process.env.INVOKE_TARGET_HOST || "",
	user: process.env.INVOKE_TARGET_USER || "root",
	port: parseInt(process.env.INVOKE_TARGET_PORT || "22"),
	key: process.env.INVOKE_TARGET_KEY || "",
};

// ── Helpers ───────────────────────────────────────────────────────────────

async function sshExec(pi: ExtensionAPI, cmd: string, sudo = false): Promise<string> {
	if (!targetState.host) throw new Error("No target connected. Call target_connect first.");
	const ssh = [
		"-o", "ConnectTimeout=10",
		"-o", "StrictHostKeyChecking=no",
		"-o", "UserKnownHostsFile=/dev/null",
	];
	if (targetState.key) ssh.push("-i", targetState.key);
	ssh.push("-p", String(targetState.port), `${targetState.user}@${targetState.host}`);
	const full = sudo ? `sudo ${cmd}` : cmd;
	const r = await pi.exec("ssh", [...ssh, full], { timeout: 60_000 });
	if (r.code !== 0) {
		throw new Error(`SSH failed (exit ${r.code}): ${r.stderr || ""} ${r.stdout || ""}`);
	}
	return r.stdout + r.stderr;
}

// ── Extension Registration ─────────────────────────────────────────────────

export default function (pi: ExtensionAPI) {
	// ── Tools: Target Device (SSH) ───────────────────────────────────────────

	const targetConnect = defineTool({
		name: "target_connect",
		label: "Target Connect",
		description: "Connect to a target Raspberry Pi 5 via SSH.",
		parameters: Type.Object({
			host: Type.String({ description: "IP or hostname of the RPi5" }),
			user: Type.Optional(Type.String({ description: "SSH user", default: "root" })),
			port: Type.Optional(Type.Number({ description: "SSH port", default: 22 })),
			key: Type.Optional(Type.String({ description: "Path to SSH private key (optional)", default: "" })),
		}),
		async execute(_toolCallId, params, _signal, _onUpdate) {
			targetState.host = params.host;
			targetState.user = params.user ?? "root";
			targetState.port = params.port ?? 22;
			targetState.key = params.key ?? "";
			try {
				const r = await sshExec(pi, "echo OK");
				if (r.includes("OK")) {
					return {
						content: [{ type: "text", text: `Connected to ${targetState.user}@${targetState.host}:${targetState.port}` }],
						details: { connected: true },
					};
				}
			} catch (e) {
				targetState.host = "";
				return {
					content: [{ type: "text", text: `Connection failed: ${e instanceof Error ? e.message : String(e)}` }],
					details: { connected: false },
				};
			}
			targetState.host = "";
			return { content: [{ type: "text", text: "Connection failed." }], details: { connected: false } };
		},
	});

	const targetDisconnect = defineTool({
		name: "target_disconnect",
		label: "Target Disconnect",
		description: "Disconnect from the current target device.",
		parameters: Type.Object({}),
		async execute(_toolCallId, _params, _signal, _onUpdate) {
			targetState.host = "";
			targetState.user = "root";
			targetState.port = 22;
			targetState.key = "";
			return { content: [{ type: "text", text: "Disconnected." }], details: {} };
		},
	});

	const targetStatus = defineTool({
		name: "target_status",
		label: "Target Status",
		description: "Show current target connection status.",
		parameters: Type.Object({}),
		async execute(_toolCallId, _params, _signal, _onUpdate) {
			if (!targetState.host) {
				return {
					content: [{ type: "text", text: "Not connected. Use target_connect to connect." }],
					details: { connected: false },
				};
			}
			return {
				content: [{ type: "text", text: `Connected to ${targetState.user}@${targetState.host}:${targetState.port}` }],
				details: { connected: true },
			};
		},
	});

	const targetExec = defineTool({
		name: "target_exec",
		label: "Target Exec",
		description: "Run a command on the target via SSH. Note: This tool expects shell command syntax, not Python data structures. For complex commands with special characters, consider creating a script file locally and using target_copy followed by target_exec to run it.",
		parameters: Type.Object({ command: Type.String({ description: "Command to execute (must be valid shell syntax)" }) }),
		async execute(_toolCallId, params, _signal, _onUpdate) {
			try {
				const r = await sshExec(pi, params.command);
				return { content: [{ type: "text", text: r }], details: { exit: 0 } };
			} catch (e) {
				return {
					content: [{ type: "text", text: `Error: ${e instanceof Error ? e.message : String(e)}` }],
					details: { exit: 1 },
				};
			}
		},
	});

	const targetExecFile = defineTool({
		name: "target_exec_file",
		label: "Target Exec File",
		description: "Execute a local script file on the target device. The file is copied to the target and executed.",
		parameters: Type.Object({
			localPath: Type.String({ description: "Local path to the script file to execute" }),
			remotePath: Type.Optional(Type.String({ description: "Remote path where to copy the script (default: /tmp/script_$(date +%s).sh)", default: "" })),
			args: Type.Optional(Type.String({ description: "Arguments to pass to the script", default: "" })),
		}),
		async execute(_toolCallId, params, _signal, _onUpdate) {
			if (!targetState.host) {
				return {
					content: [{ type: "text", text: "No target connected. Call target_connect first." }],
					details: { error: "not_connected" },
				};
			}
			
			try {
				// Determine remote path
				const remotePath = params.remotePath || `/tmp/script_$(date +%s).sh`;
				
				// Copy the file to the target
				const keyArg = targetState.key ? ["-i", targetState.key] : [];
				const copyResult = await pi.exec("scp", [
					"-o", "StrictHostKeyChecking=no",
					"-o", "UserKnownHostsFile=/dev/null",
					"-P", String(targetState.port), ...keyArg,
					params.localPath, `${targetState.user}@${targetState.host}:${remotePath}`,
				], { timeout: 120_000 });
				
				if (copyResult.code !== 0) {
					return {
						content: [{ type: "text", text: `Failed to copy file: ${copyResult.stderr || copyResult.stdout}` }],
						details: { exit: copyResult.code },
					};
				}
				
				// Make the script executable and execute it
				const chmodCmd = `chmod +x ${remotePath}`;
				const chmodResult = await sshExec(pi, chmodCmd);
				
				const execCmd = `${remotePath} ${params.args || ""}`.trim();
				const execResult = await sshExec(pi, execCmd);
				
				// Optionally clean up the script
				// const cleanupCmd = `rm ${remotePath}`;
				// await sshExec(pi, cleanupCmd);
				
				return {
					content: [{ type: "text", text: `Script executed successfully:
${execResult}` }],
					details: { exit: 0 },
				};
			} catch (e) {
				return {
					content: [{ type: "text", text: `Error executing script: ${e instanceof Error ? e.message : String(e)}` }],
					details: { exit: 1 },
				};
			}
		},
	});

	const targetRunAsRoot = defineTool({
		name: "target_run_as_root",
		label: "Target Run As Root",
		description: "Run a command as root on the target Raspberry Pi via SSH.",
		parameters: Type.Object({ command: Type.String({ description: "Command to execute as root" }) }),
		async execute(_toolCallId, params, _signal, _onUpdate) {
			try {
				const r = await sshExec(pi, params.command, true);
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
		name: "target_copy",
		label: "Target Copy",
		description: "Copy a local file/directory to the target via SCP.",
		parameters: Type.Object({
			source: Type.String({ description: "Local path" }),
			dest: Type.String({ description: "Destination path on target" }),
		}),
		async execute(_toolCallId, params, _signal, _onUpdate) {
			if (!targetState.host) {
				return {
					content: [{ type: "text", text: "No target connected. Call target_connect first." }],
					details: { error: "not_connected" },
				};
			}
			const keyArg = targetState.key ? ["-i", targetState.key] : [];
			try {
				const r = await pi.exec("scp", [
					"-o", "StrictHostKeyChecking=no",
					"-o", "UserKnownHostsFile=/dev/null",
					"-P", String(targetState.port), ...keyArg, "-r",
					params.source, `${targetState.user}@${targetState.host}:${params.dest}`,
				], { timeout: 120_000 });
				return {
					content: [{ type: "text", text: `Copied ${params.source} -> ${targetState.host}:${params.dest}` }],
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

	pi.registerTool(targetConnect);
	pi.registerTool(targetDisconnect);
	pi.registerTool(targetStatus);
	pi.registerTool(targetExec);
	pi.registerTool(targetRunAsRoot);
	pi.registerTool(targetCopy);
	pi.registerTool(targetExecFile);

	pi.on("session_start", async (_event, ctx) => {
		ctx.ui.notify("Target tools loaded", "info");
	});
}