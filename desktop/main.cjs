const { app, BrowserWindow, Menu, dialog } = require("electron");
const { spawn } = require("child_process");
const fs = require("fs");
const http = require("http");
const net = require("net");
const path = require("path");

let mainWindow = null;
let backendProcess = null;

const DEFAULT_DEV_PORT = 8765;

async function createWindow() {
  const port = await findAvailablePort(DEFAULT_DEV_PORT);
  await startBackend(port);
  configureApplicationMenu();

  mainWindow = new BrowserWindow({
    width: 1200,
    height: 820,
    minWidth: 960,
    minHeight: 680,
    title: "OrderMind 订单智脑",
    icon: path.join(__dirname, "resources", "icon.png"),
    webPreferences: {
      preload: path.join(__dirname, "preload.cjs"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true
    }
  });

  await waitForBackend(port);
  await mainWindow.loadURL(`http://127.0.0.1:${port}/login`);

  mainWindow.on("closed", () => {
    mainWindow = null;
  });
}

function configureApplicationMenu() {
  const template = [
    {
      label: "OrderMind",
      submenu: [
        { role: "about", label: "关于 OrderMind" },
        { type: "separator" },
        { role: "quit", label: "退出 OrderMind" }
      ]
    },
    {
      label: "视图",
      submenu: [
        { role: "reload", label: "刷新" },
        { role: "forceReload", label: "强制刷新" },
        { type: "separator" },
        { role: "resetZoom", label: "实际大小" },
        { role: "zoomIn", label: "放大" },
        { role: "zoomOut", label: "缩小" },
        { type: "separator" },
        { role: "togglefullscreen", label: "切换全屏" }
      ]
    },
    {
      label: "窗口",
      submenu: [
        { role: "minimize", label: "最小化" },
        { role: "close", label: "关闭窗口" }
      ]
    }
  ];
  Menu.setApplicationMenu(Menu.buildFromTemplate(template));
}

async function startBackend(port) {
  const backend = resolveBackendExecutable();
  const dataDir = app.getPath("userData");
  fs.mkdirSync(dataDir, { recursive: true });

  backendProcess = spawn(backend.command, backend.args, {
    cwd: backend.cwd,
    env: {
      ...process.env,
      ORDERMIND_HOST: "127.0.0.1",
      ORDERMIND_PORT: String(port),
      ORDERMIND_DATA_DIR: path.join(dataDir, "data"),
      ORDERMIND_RESOURCE_DIR: backend.cwd
    },
    stdio: ["ignore", "pipe", "pipe"],
    windowsHide: true
  });

  backendProcess.stdout.on("data", (chunk) => {
    console.log(`[ordermind] ${chunk.toString().trim()}`);
  });
  backendProcess.stderr.on("data", (chunk) => {
    console.error(`[ordermind] ${chunk.toString().trim()}`);
  });
  backendProcess.on("exit", (code, signal) => {
    if (mainWindow) {
      dialog.showErrorBox(
        "OrderMind 后端已停止",
        `本地审单服务已退出。退出码：${code ?? "unknown"}，信号：${signal ?? "none"}`
      );
      mainWindow.close();
    }
  });
}

function resolveBackendExecutable() {
  if (!app.isPackaged) {
    return {
      command: process.env.PYTHON || "python3",
      args: ["run_app.py"],
      cwd: path.resolve(__dirname, "..")
    };
  }

  const binaryName = process.platform === "win32" ? "ordermind-backend.exe" : "ordermind-backend";
  const backendPath = path.join(process.resourcesPath, "desktop-sidecar", binaryName);
  return {
    command: backendPath,
    args: [],
    cwd: process.resourcesPath
  };
}

function findAvailablePort(startPort) {
  return new Promise((resolve, reject) => {
    const server = net.createServer();
    server.unref();
    server.on("error", (error) => {
      if (error.code === "EADDRINUSE") {
        resolve(findAvailablePort(startPort + 1));
      } else {
        reject(error);
      }
    });
    server.listen(startPort, "127.0.0.1", () => {
      const address = server.address();
      server.close(() => resolve(address.port));
    });
  });
}

async function waitForBackend(port) {
  const deadline = Date.now() + 15000;
  while (Date.now() < deadline) {
    if (await healthCheck(port)) {
      return;
    }
    await new Promise((resolve) => setTimeout(resolve, 250));
  }
  throw new Error(`OrderMind backend did not start on port ${port}`);
}

function healthCheck(port) {
  return new Promise((resolve) => {
    const request = http.get(
      {
        host: "127.0.0.1",
        port,
        path: "/health",
        timeout: 1000
      },
      (response) => {
        response.resume();
        resolve(response.statusCode === 200);
      }
    );
    request.on("error", () => resolve(false));
    request.on("timeout", () => {
      request.destroy();
      resolve(false);
    });
  });
}

function stopBackend() {
  if (backendProcess && !backendProcess.killed) {
    backendProcess.kill();
  }
  backendProcess = null;
}

app.whenReady().then(createWindow).catch((error) => {
  dialog.showErrorBox("OrderMind 启动失败", error.message);
  app.quit();
});

app.on("window-all-closed", () => {
  stopBackend();
  app.quit();
});

app.on("before-quit", stopBackend);
