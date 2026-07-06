# OrderMind 签名、公证与自动更新

## 当前策略

OrderMind 已经具备正式发布所需的配置入口，但真实签名和公证必须等证书与密钥准备好后执行。

- macOS: 使用 Apple Developer ID Application 证书签名，并通过 Apple notarytool 公证。
- Windows: 使用代码签名证书和 `signtool` 签名，签名 hook 配置在 `build.win.signtoolOptions.sign`。
- 自动更新: Electron 安装包使用 `electron-updater` 的 generic provider；桌面菜单支持检查、下载、重启安装。应用内也提供更新清单检查页，早期客户试用阶段可先提示下载新安装包。

## 必要环境变量

macOS 公证:

```bash
APPLE_ID=developer@example.com
APPLE_APP_SPECIFIC_PASSWORD=xxxx-xxxx-xxxx-xxxx
APPLE_TEAM_ID=TEAMID1234
```

Windows 签名:

```bash
WINDOWS_CERTIFICATE_FILE=/secure/path/certificate.pfx
WINDOWS_CERTIFICATE_PASSWORD=secret
WINDOWS_TIMESTAMP_SERVER=http://timestamp.digicert.com
```

更新发布地址:

```bash
ORDERMIND_UPDATE_BASE_URL=https://example.com/ordermind/releases/0.1.0
ORDERMIND_UPDATE_MANIFEST_URL=https://example.com/ordermind/releases/update-manifest.json
```

## 本地检查

```bash
npm run release:check-signing
npm run release:manifest -- --base-url "$ORDERMIND_UPDATE_BASE_URL"
```

`release:check-signing` 不会打印任何密钥值。缺少证书时它会明确报告缺失项，避免把“未配置证书”误判成构建失败。

本地打包时，如果 `ORDERMIND_UPDATE_BASE_URL` 没有配置，构建启动器会使用示例地址保证试包流程不断。正式发布必须改成真实下载地址。

正式托管目录需要同时上传安装包、`latest*.yml`、`*.blockmap` 和 `update-manifest.generated.json`。前两类文件供 `electron-updater` 使用，最后一个文件供 OrderMind 页面里的更新清单使用。

## 打包命令

```bash
npm run desktop:dist:mac
npm run desktop:dist:win
```

如果证书环境没有配置，macOS 公证和 Windows 签名 hook 会跳过并输出提示。正式客户发布前必须补齐证书后重新打包。

## 应用内更新检查

本地 Web 工作台提供 `检查更新` 页面。它读取 `ORDERMIND_UPDATE_MANIFEST_URL` 指向的 JSON 清单，显示:

- 当前版本。
- 最新版本。
- 更新状态。
- 下载地址。
- 更新说明。

早期试用阶段建议先走“提示下载新安装包”的手动升级模式。等证书、公证、托管地址稳定后，再把 `ORDERMIND_UPDATE_BASE_URL` 指向正式托管目录，桌面菜单即可走安装包级下载和重启安装流程。
