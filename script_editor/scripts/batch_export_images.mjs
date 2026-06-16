import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { spawn } from "node:child_process";

const scriptPath = fileURLToPath(import.meta.url);
const projectDir = path.resolve(path.dirname(scriptPath), "..");
const port = Number(process.env.BOTC_BATCH_PORT || 1430);
const limit = Number(process.env.BOTC_BATCH_LIMIT || 0);
const filter = String(process.env.BOTC_BATCH_FILTER || "").trim();
const baseUrl = `http://127.0.0.1:${port}`;
const batchParams = new URLSearchParams({ batchExport: "1" });
if (Number.isFinite(limit) && limit > 0) {
  batchParams.set("batchLimit", String(Math.floor(limit)));
}
if (filter) {
  batchParams.set("batchFilter", filter);
}
const batchUrl = `${baseUrl}/?${batchParams}`;

let viteProcess = null;
let chromeProcess = null;
let chromeConnection = null;
let chromeUserDataDir = "";

async function main() {
  try {
    await ensureWebSocketAvailable();
    viteProcess = startViteServer();
    await waitForBatchServer();
    const page = await openBatchPage();
    await watchBatchStatus(page.sessionId);
  } catch (error) {
    console.error(error instanceof Error ? error.stack || error.message : error);
    process.exitCode = 1;
  } finally {
    chromeConnection?.close();
    await stopProcess(chromeProcess);
    await stopProcess(viteProcess);
    if (chromeUserDataDir) {
      await rm(chromeUserDataDir, {
        recursive: true,
        force: true,
        maxRetries: 8,
        retryDelay: 150,
      }).catch((error) => {
        console.warn(`Could not remove temporary Chrome profile: ${error.message}`);
      });
    }
  }
}

function startViteServer() {
  const viteBin = path.join(projectDir, "node_modules", ".bin", "vite");
  const processRef = spawn(viteBin, [
    "--host",
    "127.0.0.1",
    "--port",
    String(port),
    "--strictPort",
  ], {
    cwd: projectDir,
    stdio: ["ignore", "pipe", "pipe"],
  });

  processRef.stdout.on("data", (chunk) => {
    if (process.env.BOTC_BATCH_DEBUG) {
      process.stdout.write(chunk);
    }
  });
  processRef.stderr.on("data", (chunk) => {
    process.stderr.write(chunk);
  });
  return processRef;
}

async function waitForBatchServer() {
  const startedAt = Date.now();
  while (Date.now() - startedAt < 30000) {
    if (viteProcess?.exitCode !== null) {
      throw new Error(`Vite exited early with code ${viteProcess.exitCode}.`);
    }
    try {
      const manifestParams = new URLSearchParams();
      if (Number.isFinite(limit) && limit > 0) {
        manifestParams.set("limit", String(Math.floor(limit)));
      }
      if (filter) {
        manifestParams.set("filter", filter);
      }
      const manifestUrl = manifestParams.size
        ? `${baseUrl}/__batch_export_manifest?${manifestParams}`
        : `${baseUrl}/__batch_export_manifest`;
      const response = await fetch(manifestUrl);
      if (response.ok) {
        const manifest = await response.json();
        console.log(`Found ${manifest.total} JSON files under all_jsons.`);
        return;
      }
    } catch {
      // Server is still starting.
    }
    await sleep(250);
  }
  throw new Error("Timed out waiting for the batch export server.");
}

async function openBatchPage() {
  chromeUserDataDir = await mkdtemp(path.join(tmpdir(), "botc-batch-export-"));
  const chromePath = findChromePath();
  chromeProcess = spawn(chromePath, [
    "--headless=new",
    "--disable-gpu",
    "--hide-scrollbars",
    "--no-first-run",
    "--no-default-browser-check",
    `--user-data-dir=${chromeUserDataDir}`,
    "--remote-debugging-port=0",
    "about:blank",
  ], {
    stdio: ["ignore", "ignore", "pipe"],
  });

  const websocketUrl = await waitForDevtoolsUrl(chromeProcess);
  chromeConnection = new CdpConnection(websocketUrl);
  const { targetId } = await chromeConnection.send("Target.createTarget", { url: "about:blank" });
  const { sessionId } = await chromeConnection.send("Target.attachToTarget", {
    targetId,
    flatten: true,
  });
  await chromeConnection.send("Page.enable", {}, sessionId);
  await chromeConnection.send("Runtime.enable", {}, sessionId);
  await chromeConnection.send("Page.navigate", { url: batchUrl }, sessionId);
  console.log(`Opened ${batchUrl}`);
  return { sessionId };
}

async function watchBatchStatus(sessionId) {
  let lastLine = "";
  while (true) {
    await sleep(1000);
    const status = await readBatchStatus(sessionId);
    if (!status) {
      continue;
    }

    const line = status.current
      ? `${status.completed + status.failed}/${status.total} ${status.current}`
      : `${status.completed + status.failed}/${status.total}`;
    if (line !== lastLine) {
      console.log(line);
      lastLine = line;
    }

    if (status.done) {
      console.log(`Batch export finished: ${status.completed} succeeded, ${status.failed} failed.`);
      if (status.failed > 0) {
        console.log(JSON.stringify(status.failures.slice(-10), null, 2));
        process.exitCode = 1;
      }
      return;
    }
  }
}

async function readBatchStatus(sessionId) {
  const result = await chromeConnection.send("Runtime.evaluate", {
    expression: "window.__BOTC_BATCH_EXPORT_STATUS__ || null",
    returnByValue: true,
  }, sessionId);
  return result.result?.value ?? null;
}

function findChromePath() {
  const candidates = [
    process.env.CHROME_PATH,
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
  ].filter(Boolean);

  for (const candidate of candidates) {
    try {
      spawn(candidate, ["--version"], { stdio: "ignore" }).kill();
      return candidate;
    } catch {
      // Try the next browser.
    }
  }
  throw new Error("Could not find Chrome. Set CHROME_PATH to a Chromium-based browser executable.");
}

function waitForDevtoolsUrl(processRef) {
  return new Promise((resolve, reject) => {
    let stderr = "";
    const timeout = setTimeout(() => {
      reject(new Error("Timed out waiting for Chrome DevTools."));
    }, 15000);

    processRef.stderr.on("data", (chunk) => {
      stderr += chunk.toString();
      const match = stderr.match(/DevTools listening on (ws:\/\/[^\s]+)/u);
      if (match) {
        clearTimeout(timeout);
        resolve(match[1]);
      }
    });
    processRef.once("exit", (code) => {
      clearTimeout(timeout);
      reject(new Error(`Chrome exited early with code ${code}.`));
    });
  });
}

class CdpConnection {
  constructor(websocketUrl) {
    this.websocket = new WebSocket(websocketUrl);
    this.nextId = 1;
    this.pending = new Map();
    this.ready = new Promise((resolve, reject) => {
      this.websocket.addEventListener("open", resolve, { once: true });
      this.websocket.addEventListener("error", reject, { once: true });
    });
    this.websocket.addEventListener("message", (event) => this.handleMessage(event));
  }

  async send(method, params = {}, sessionId = undefined) {
    await this.ready;
    const id = this.nextId;
    this.nextId += 1;
    const message = { id, method, params };
    if (sessionId) {
      message.sessionId = sessionId;
    }

    return await new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject });
      this.websocket.send(JSON.stringify(message));
    });
  }

  handleMessage(event) {
    const message = JSON.parse(event.data.toString());
    if (!message.id || !this.pending.has(message.id)) {
      return;
    }
    const pending = this.pending.get(message.id);
    this.pending.delete(message.id);
    if (message.error) {
      pending.reject(new Error(message.error.message));
      return;
    }
    pending.resolve(message.result);
  }

  close() {
    this.websocket.close();
  }
}

async function ensureWebSocketAvailable() {
  if (typeof WebSocket === "undefined") {
    throw new Error("This script requires a Node.js runtime with global WebSocket support.");
  }
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function stopProcess(processRef) {
  if (!processRef || processRef.exitCode !== null) {
    return Promise.resolve();
  }

  return new Promise((resolve) => {
    const timeout = setTimeout(resolve, 2500);
    processRef.once("exit", () => {
      clearTimeout(timeout);
      resolve();
    });
    processRef.kill();
  });
}

await main();
