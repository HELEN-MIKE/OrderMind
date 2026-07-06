# OrderMind 发布、安装包与升级方案

## 1. 发布目标

从现在开始，OrderMind 每个对客户试用的版本都应产出可安装应用，而不只是源码或本地脚本。

每个客户试用版本必须包含：

- Mac 安装包。
- Windows 安装包。
- 版本号。
- 变更日志。
- 升级说明。
- 回滚说明。
- 发布前测试记录。

扫描件 PDF 和图片订单属于可选 OCR 能力：安装包不强制内置 OCR 引擎，客户电脑可安装 Tesseract，或通过 `ORDERMIND_OCR_COMMAND` 指向自定义 OCR 命令。

客户规则模板现在可在本地页面中查看、编辑并保存。内置模板随安装包分发，用户保存的模板写入桌面数据目录下的 `templates/`，升级应用时不应覆盖。

## 2. 版本号规则

使用语义化版本：

```text
主版本.次版本.修订版本
```

示例：

```text
0.1.0
0.2.0
1.0.0
```

文件位置：

```text
VERSION
CHANGELOG.md
release/update-manifest.example.json
```

发布前必须运行：

```bash
python3 scripts/generate_customer_like_samples.py
python3 scripts/release_check.py
```

## 3. 安装包要求

### Mac

正式发布建议产物：

```text
OrderMind_版本号_aarch64.dmg
OrderMind_版本号_x64.dmg
```

如果只服务 Apple Silicon Mac，可以先产出：

```text
OrderMind_版本号_aarch64.dmg
```

### Windows

正式发布建议产物：

```text
OrderMind_版本号_x64-setup.exe
```

也可以额外提供：

```text
OrderMind_版本号_x64.msi
```

## 4. 推荐技术路线

正式桌面应用建议使用：

```text
Tauri 2 + 前端 UI + 本地 OrderMind 核心服务
```

原因：

- 可生成 Mac 和 Windows 安装包。
- 支持应用内更新。
- 支持签名更新包。
- 应用体积相对 Electron 更小。

Tauri 官方更新插件要求更新包签名。正式发布时必须生成私钥/公钥，并把公钥配置进应用，把每个安装包的签名写入更新清单。

### 当前实现路线

当前仓库先采用 Electron 桌面壳包裹本地 Python Web 工作台：

- Electron 负责打开原生桌面窗口。
- Python 后端使用 PyInstaller 打成 sidecar 可执行文件。
- 桌面壳启动时自动选择本机端口，并通过 `/health` 等待后端就绪。
- 用户数据写入桌面应用数据目录，不写入源码仓库的 `data/users.json`。

选择 Electron 是为了先产出可双击运行和可安装的客户试用版；后续如果需要更小体积和更强签名更新能力，再迁移到 Tauri。

## 5. 升级机制

推荐升级流程：

```text
应用启动
  -> 检查当前版本
  -> 请求更新清单
  -> 如果有新版本，显示更新说明
  -> 用户确认
  -> 下载新安装包
  -> 校验签名
  -> 安装升级
  -> 重启应用
```

更新清单示例：

```text
release/update-manifest.example.json
```

正式环境需要把示例里的 `example.com`、签名和安装包文件名替换成真实发布地址。

## 6. 客户升级策略

### 试用阶段

建议使用“手动升级 + 应用内提醒”：

- 应用提示有新版本。
- 用户点击下载地址。
- 客户下载安装包覆盖安装。
- 本地数据保留。

这样实现简单，适合早期客户试用。

### 正式阶段

建议升级为“应用内自动更新”：

- 应用自动检查新版本。
- 下载签名安装包。
- 自动完成升级。
- 失败时保留旧版本。

## 7. 本地数据迁移

每个版本发布时必须说明是否涉及数据迁移。

第一版当前数据：

```text
data/users.json
templates/*.json
```

后续迁移到 SQLite 时必须提供迁移脚本：

```text
scripts/migrate_data.py
```

迁移原则：

- 不删除用户旧数据。
- 迁移前创建备份。
- 迁移失败时可回滚。
- CHANGELOG 记录迁移影响。

用户规则模板目录:

```text
ORDERMIND_DATA_DIR/templates/
```

发布验收时需要确认保存的用户模板可以在首页模板下拉框中选择，并且不会改写安装包内置 `templates/default_order_rules.json`。

## 8. 发布前门禁

每次打包前必须执行：

```bash
python3 -m unittest discover -s tests -v
python3 -m compileall ordermind run_app.py scripts
python3 scripts/release_check.py
python3 -m ordermind.cli samples/sample_order.txt --template templates/default_order_rules.json
python3 -m ordermind.cli samples/sample_order.xlsx --template templates/default_order_rules.json
npm install
python3 -m venv .venv-build
.venv-build/bin/python -m pip install pyinstaller==6.21.0
npm run desktop:dist:mac
```

全部通过后，才可以打包给客户试用。

当前 Mac 默认生成 `.zip` 客户试用包。`.dmg` 目标保留为独立命令：

```bash
npm run desktop:dist:mac:dmg
```

Windows 安装包需要在 Windows 构建环境中运行：

```bash
npm run desktop:dist:win
```

仓库已经提供 GitHub Actions workflow：

```text
.github/workflows/release-build.yml
```

它会在 `windows-latest` 上执行测试、发布元数据检查，并构建 Windows `.exe` / `.msi` 安装包；在 `macos-latest` 上构建 macOS `.zip`。如果没有本地 Windows 机器，先使用该 workflow 作为 Windows 安装包的第一道验证。

OCR 验收建议额外准备一张扫描件或图片订单，并确保本机存在:

```bash
tesseract
```

或设置:

```bash
ORDERMIND_OCR_COMMAND=/path/to/ocr-command
```

OCR 命令需要把识别文本写到标准输出，OrderMind 再按普通文本订单进行字段抽取和规则校验。

复杂表格恢复当前覆盖:

- Excel 合并标题行、备注行后的明细表识别。
- Excel 两行拆分表头，例如 `Item` + `No`、`Unit` + `Price`。
- OCR/PDF 文本中的多空格对齐表格。

仍需人工复核或后续增强:

- 跨页表格。
- 复杂嵌套表头。
- 图片中严重错列、漏列或识别错误的订单。

## 9. 当前状态

当前 `0.1.0` 版本已经建立发布元数据、升级规划和 Electron 桌面壳配置。

下一步应做：

- 在 macOS 上生成并验收 `.zip`，具备签名和 DMG 构建条件后再生成 `.dmg`。
- 在 Windows 或 CI 上生成并验收 `.exe` / `.msi`。
- 准备真实扫描件或图片订单样例，验证本机 OCR 命令的识别质量和多空格表格恢复效果。
- 规划代码签名、公证和自动更新。
- 后续评估是否迁移到 Tauri updater。
- 增加 GitHub Actions 或其他 CI，同时在 macOS 和 Windows 上构建安装包。

## 10. CI 构建建议

当前 CI 构建入口：

```text
workflow_dispatch -> 手动触发安装包构建
pull_request      -> 改动发布/桌面/测试相关文件时验证
v* tag            -> 版本标签触发安装包构建
```

构建环境：

```text
macos-latest   -> 生成 zip
windows-latest -> 生成 exe / msi
```

注意：

- Mac 安装包需要在 macOS 环境构建。
- Windows 安装包需要在 Windows 环境构建。
- 桌面打包脚本必须使用 `node scripts/run_python.cjs ...` 和 `node scripts/run_electron_builder.cjs ...`，避免依赖 `python3` 或行内环境变量写法导致 Windows 构建失败。
- 代码签名和公证会影响客户电脑能否顺利安装。
- 早期内测可以先不签名，但客户正式试用前应规划签名。
