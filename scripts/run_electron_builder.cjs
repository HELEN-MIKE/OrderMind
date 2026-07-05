const { spawnSync } = require("child_process");
const path = require("path");

const builderCli = path.join(__dirname, "..", "node_modules", "electron-builder", "cli.js");
const args = process.argv.slice(2);

const env = {
  ...process.env,
  ELECTRON_MIRROR: process.env.ELECTRON_MIRROR || "https://npmmirror.com/mirrors/electron/",
};

const result = spawnSync(process.execPath, [builderCli, ...args], {
  env,
  stdio: "inherit",
  shell: false,
});

if (result.error) {
  console.error(result.error.message);
  process.exit(1);
}

process.exit(result.status ?? 1);
