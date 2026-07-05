const { spawnSync } = require("child_process");

const args = process.argv.slice(2);

if (args.length === 0) {
  console.error("Usage: node scripts/run_python.cjs <script.py> [...args]");
  process.exit(2);
}

const candidates = [];
if (process.env.PYTHON) {
  candidates.push([process.env.PYTHON]);
}
if (process.platform === "win32") {
  candidates.push(["py", "-3"], ["python"], ["python3"]);
} else {
  candidates.push(["python3"], ["python"]);
}

for (const candidate of candidates) {
  const [command, ...prefixArgs] = candidate;
  const result = spawnSync(command, [...prefixArgs, ...args], {
    stdio: "inherit",
    shell: false,
  });

  if (result.error && result.error.code === "ENOENT") {
    continue;
  }
  if (result.error) {
    console.error(result.error.message);
    process.exit(1);
  }
  process.exit(result.status ?? 1);
}

console.error("No Python interpreter found. Set PYTHON or install Python 3.");
process.exit(127);
