const { spawnSync } = require("child_process");

module.exports = async function signWindows(configuration) {
  const certificateFile = process.env.WINDOWS_CERTIFICATE_FILE;
  const certificatePassword = process.env.WINDOWS_CERTIFICATE_PASSWORD;
  const timestampServer = process.env.WINDOWS_TIMESTAMP_SERVER || "http://timestamp.digicert.com";

  if (!certificateFile || !certificatePassword) {
    console.warn("Skipping Windows signing: WINDOWS_CERTIFICATE_FILE or WINDOWS_CERTIFICATE_PASSWORD is not configured.");
    return;
  }

  const pathToSign = configuration.path || configuration.file;
  if (!pathToSign) {
    console.warn("Skipping Windows signing: electron-builder did not provide a file path.");
    return;
  }

  const result = spawnSync(
    "signtool",
    [
      "sign",
      "/f",
      certificateFile,
      "/p",
      certificatePassword,
      "/tr",
      timestampServer,
      "/td",
      "sha256",
      "/fd",
      "sha256",
      pathToSign,
    ],
    { stdio: "inherit", shell: false }
  );

  if (result.error) {
    throw result.error;
  }
  if (result.status !== 0) {
    throw new Error(`signtool failed with exit code ${result.status}`);
  }
};
