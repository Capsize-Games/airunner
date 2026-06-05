/**
 * AI Runner – Electron main process.
 *
 * Spawns the Python backend as a child process, polls the /health endpoint
 * until it is ready, then loads the React frontend in a BrowserWindow.
 */

const { app, BrowserWindow, dialog } = require("electron");
const path = require("path");
const { spawn } = require("child_process");
const http = require("http");
const fs = require("fs");

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const BACKEND_HOST = "127.0.0.1";
const BACKEND_PORT = 8080;
const HEALTH_CHECK_INTERVAL_MS = 500;
const HEALTH_CHECK_TIMEOUT_MS = 120_000; // 2 minutes
const BACKEND_KILL_WAIT_MS = 5_000; // grace period before SIGKILL

// ---------------------------------------------------------------------------
// Resource path resolution
// ---------------------------------------------------------------------------

/**
 * Return the path to the resources directory.
 * In the packaged app this is process.resourcesPath.
 * In development this is <repo_root>/electron/resources/.
 */
function resourcesPath() {
  if (app.isPackaged) {
    return process.resourcesPath;
  }
  // Development: resources lives alongside the electron/ directory.
  return path.join(__dirname, "resources");
}

/**
 * Return the path to the embedded Python interpreter.
 */
function pythonInterpreterPath() {
  const base = resourcesPath();
  if (process.platform === "win32") {
    return path.join(base, "python", "python.exe");
  }
  return path.join(base, "python", "bin", "python3");
}

/**
 * Return the path to the airunner services package.
 * In the bundle it is installed into the embedded Python's site-packages.
 * We use PYTHONPATH to point to the installed package.
 */
function servicesPackagePath() {
  const base = resourcesPath();
  return path.join(base, "python", "lib");
}

// ---------------------------------------------------------------------------
// Backend process management
// ---------------------------------------------------------------------------

let backendProcess = null;

/**
 * Spawn the Python backend as a child process.
 *
 * On success the backend starts listening on BACKEND_HOST:BACKEND_PORT.
 * Returns the child process handle.
 */
function spawnBackend() {
  const pythonBin = pythonInterpreterPath();
  const resources = resourcesPath();

  // Verify the Python interpreter exists.
  if (!fs.existsSync(pythonBin)) {
    throw new Error(
      `Embedded Python not found at ${pythonBin}. ` +
        "Ensure the bundle was built correctly."
    );
  }

  const pythonArgs = [
    "-m",
    "airunner_services.bin.airunner_server",
    "--host",
    BACKEND_HOST,
    "--port",
    String(BACKEND_PORT),
  ];

  // Determine user data directory.
  const airunnerDataDir =
    process.env.AIRUNNER_DATA_DIR ||
    path.join(app.getPath("userData"), "data");

  const hfHome =
    process.env.HF_HOME ||
    path.join(app.getPath("userData"), "huggingface");

  const backendEnv = {
    ...process.env,
    PYTHONHOME: path.join(resources, "python"),
    PYTHONPATH: path.join(resources, "python"),
    AIRUNNER_DATA_DIR: airunnerDataDir,
    HF_HOME: hfHome,
    AIRUNNER_STATIC_DIR: path.join(resources, "web"),
    AIRUNNER_HEADLESS_SERVER_HOST: BACKEND_HOST,
    AIRUNNER_HEADLESS_SERVER_PORT: String(BACKEND_PORT),
    // Disable debug/dev features in the bundle.
    AIRUNNER_DEBUG: "0",
    AIRUNNER_API_ACCESS_LOG: "0",
  };

  console.log(
    `[main] Spawning backend: ${pythonBin} ${pythonArgs.join(" ")}`
  );
  console.log(`[main] AIRUNNER_DATA_DIR=${airunnerDataDir}`);
  console.log(`[main] HF_HOME=${hfHome}`);
  console.log(`[main] AIRUNNER_STATIC_DIR=${backendEnv.AIRUNNER_STATIC_DIR}`);

  const child = spawn(pythonBin, pythonArgs, {
    env: backendEnv,
    stdio: ["ignore", "pipe", "pipe"],
  });

  child.stdout.on("data", (data) => {
    console.log(`[backend:stdout] ${data.toString().trim()}`);
  });

  child.stderr.on("data", (data) => {
    console.error(`[backend:stderr] ${data.toString().trim()}`);
  });

  child.on("error", (err) => {
    console.error(`[main] Failed to spawn backend: ${err.message}`);
  });

  child.on("exit", (code, signal) => {
    const reason = signal
      ? `signal ${signal}`
      : `exit code ${code}`;
    console.log(`[main] Backend exited (${reason})`);
    backendProcess = null;
    handleBackendExit(code, signal);
  });

  return child;
}

/**
 * Handle unexpected backend exit.
 * Shows a dialog offering to restart or quit.
 */
function handleBackendExit(code, signal) {
  // Ignore clean exits (SIGTERM from our shutdown).
  if (signal === "SIGTERM" || code === 0) {
    return;
  }

  const errorMessage = signal
    ? `The AI backend was killed by ${signal}.`
    : `The AI backend exited unexpectedly with code ${code}.`;

  dialog
    .showMessageBox({
      type: "error",
      title: "AI Runner – Backend Error",
      message: "The AI backend has stopped working.",
      detail: `${errorMessage}\n\nYou can restart the backend or quit the application.`,
      buttons: ["Restart Backend", "Quit"],
      defaultId: 0,
      cancelId: 1,
    })
    .then(({ response }) => {
      if (response === 0) {
        startBackendAndLoad();
      } else {
        app.quit();
      }
    })
    .catch(() => {
      app.quit();
    });
}

/**
 * Kill the backend process gracefully.
 */
async function killBackend() {
  if (!backendProcess) {
    return;
  }

  const child = backendProcess;
  backendProcess = null;

  return new Promise((resolve) => {
    // Try SIGTERM first.
    child.on("exit", () => resolve());

    const platform = process.platform;
    if (platform === "win32") {
      // On Windows, spawn taskkill for the process tree.
      const taskkill = spawn("taskkill", [
        "/PID",
        String(child.pid),
        "/T",
        "/F",
      ]);
      taskkill.on("exit", () => resolve());
      // Give up after the timeout.
      setTimeout(() => resolve(), BACKEND_KILL_WAIT_MS);
    } else {
      child.kill("SIGTERM");
      // Force kill after grace period.
      setTimeout(() => {
        try {
          child.kill("SIGKILL");
        } catch (_) {
          // Process may have already exited.
        }
        resolve();
      }, BACKEND_KILL_WAIT_MS);
    }
  });
}

// ---------------------------------------------------------------------------
// Health check polling
// ---------------------------------------------------------------------------

/**
 * Poll GET http://BACKEND_HOST:BACKEND_PORT/health until the backend responds
 * with HTTP 200, or until the timeout is reached.
 *
 * Returns true if the backend became healthy, false otherwise.
 */
function waitForBackendHealth() {
  return new Promise((resolve) => {
    const startTime = Date.now();

    function check() {
      const elapsed = Date.now() - startTime;
      if (elapsed >= HEALTH_CHECK_TIMEOUT_MS) {
        console.error("[main] Backend health check timed out");
        resolve(false);
        return;
      }

      const req = http.get(
        `http://${BACKEND_HOST}:${BACKEND_PORT}/health`,
        (res) => {
          if (res.statusCode === 200) {
            console.log("[main] Backend is healthy");
            resolve(true);
          } else {
            console.log(
              `[main] Backend returned status ${res.statusCode}, retrying...`
            );
            setTimeout(check, HEALTH_CHECK_INTERVAL_MS);
          }
          res.resume();
        }
      );

      req.on("error", () => {
        // Backend not ready yet; retry.
        setTimeout(check, HEALTH_CHECK_INTERVAL_MS);
      });

      req.setTimeout(2_000, () => {
        req.destroy();
        setTimeout(check, HEALTH_CHECK_INTERVAL_MS);
      });
    }

    check();
  });
}

// ---------------------------------------------------------------------------
// Window management
// ---------------------------------------------------------------------------

let mainWindow = null;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    minWidth: 900,
    minHeight: 600,
    title: "AI Runner",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
    show: false,
  });

  mainWindow.once("ready-to-show", () => {
    mainWindow.show();
  });

  mainWindow.on("closed", () => {
    mainWindow = null;
  });

  // Load the React frontend served by the Python backend.
  mainWindow.loadURL(`http://${BACKEND_HOST}:${BACKEND_PORT}`);
}

// ---------------------------------------------------------------------------
// Startup sequence
// ---------------------------------------------------------------------------

async function startBackendAndLoad() {
  try {
    backendProcess = spawnBackend();
  } catch (err) {
    dialog.showErrorBox(
      "AI Runner – Startup Error",
      `Failed to start the AI backend:\n\n${err.message}`
    );
    app.quit();
    return;
  }

  const healthy = await waitForBackendHealth();

  if (!healthy) {
    dialog.showErrorBox(
      "AI Runner – Startup Error",
      `The AI backend did not start within ${
        HEALTH_CHECK_TIMEOUT_MS / 1000
      } seconds.\n\n` +
        "Please check your system and try again. " +
        "Ensure you have an NVIDIA GPU with driver 525+ installed."
    );
    killBackend().then(() => app.quit());
    return;
  }

  createWindow();
}

// ---------------------------------------------------------------------------
// App lifecycle
// ---------------------------------------------------------------------------

app.whenReady().then(() => {
  startBackendAndLoad();

  app.on("activate", () => {
    // macOS: re-create window when dock icon is clicked and no windows open.
    if (mainWindow === null && backendProcess) {
      createWindow();
    }
  });
});

app.on("before-quit", async (event) => {
  event.preventDefault();
  await killBackend();
  app.exit(0);
});

app.on("window-all-closed", () => {
  // On macOS, keep the app running in the dock unless Cmd+Q is used.
  if (process.platform !== "darwin") {
    app.quit();
  }
});
