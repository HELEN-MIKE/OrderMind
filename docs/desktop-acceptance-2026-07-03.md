# OrderMind 桌面壳验收记录 2026-07-03

## 1. 验收范围

本次验收覆盖 OrderMind `0.1.0` 桌面壳阶段的核心闭环：

- Electron 桌面壳启动本地 Python sidecar。
- 本地服务健康检查。
- 登录与首次登录改密。
- 中文/英文首页。
- TXT 与 XLSX 样例订单上传审单。
- 中文/英文审单结果页。
- 审单结果本地 HTML / Excel 报告导出。
- 桌面应用图标与基础菜单。
- Mac Apple Silicon 试用包生成。

## 2. 验收环境

- 验收时间：2026-07-03 22:58 CST。
- 项目路径：`/Users/dlj/MyPython/OrderMind`。
- 桌面壳健康检查：`http://127.0.0.1:8766/health` 返回 `{"status":"ok"}`。
- 隔离测试服务：`ORDERMIND_PORT=8890`，`ORDERMIND_DATA_DIR=/private/tmp/ordermind-walkthrough-20260703`。
- Mac 试用包：`release/installers/OrderMind_0.1.0_mac_arm64.zip`。
- Mac 应用目录：`release/installers/mac-arm64/OrderMind.app`。

## 3. 走查结果

| 验收项 | 结果 | 证据 |
| --- | --- | --- |
| 桌面壳启动 | 通过 | `/health` 返回 `{"status":"ok"}` |
| 中文登录页 | 通过 | 页面包含 `登录 OrderMind` |
| 英文登录页 | 通过 | 页面包含 `Sign in to OrderMind` |
| 首次登录改密 | 通过 | 临时账号进入改密页，改密后可用新密码登录 |
| 中文首页 | 通过 | 页面包含 `订单文件` 与 `开始审单` |
| 英文首页 | 通过 | 页面包含 `Order File` 与 `Review Order` |
| TXT 样例审单 | 通过 | 中文/英文结果页均返回 0 错误、0 警告 |
| XLSX 样例审单 | 通过 | 中文结果页返回 0 错误、0 警告 |
| 本地 HTML 报告导出 | 通过 | `/export-report` 返回 `sample_order-report.html` 附件 |
| 本地 Excel 报告导出 | 通过 | `/export-report` 返回 `sample_order-report.xlsx` 附件，包含 4 个工作表 |
| 桌面图标资源 | 通过 | `desktop/resources/icon.icns` 与 `desktop/resources/icon.ico` 已生成 |
| 桌面基础菜单 | 通过 | 已配置关于、退出、刷新、缩放、全屏、窗口关闭/最小化 |
| Mac zip 试用包 | 通过 | `npm run desktop:dist:mac` 已生成 zip 与 blockmap |

本轮临时页面证据保存在：

```text
/private/tmp/ordermind-walkthrough-20260703/
```

包含登录页、改密页、首页、结果页 HTML，以及中文登录页截图。

## 4. 发现并修复的问题

### 英文结果页空问题提示混用中文

现象：

- 英文结果页标题、表头和按钮已经是英文。
- 当审单没有错误或警告时，问题列表兜底文案仍显示 `未发现错误或警告。`。

根因：

- `render_result()` 中空问题列表文案被硬编码为中文，没有走 `ordermind/i18n.py`。

修复：

- 将空问题列表文案改为 `t(lang, "no_issues")`。
- 新增回归测试，覆盖中文和英文结果页的空问题提示。

### 新增本地 HTML / Excel 报告导出

结果页新增 `导出报告 / Export Report` 和 `导出 Excel / Export Excel` 按钮。当前第一版支持导出独立 HTML 文件和 Excel 2007+ `.xlsx` 文件，包含：

- 摘要指标。
- 订单明细。
- 校验问题。
- 结构化 JSON。

烟测结果：

```text
POST /export-report -> 200
Content-Disposition: attachment; filename="sample_order-report.html"

POST /export-report -> 200
Content-Disposition: attachment; filename="sample_order-report.xlsx"
Excel sheets: 摘要, 订单明细, 校验问题, 结构化JSON
```

### 新增桌面图标与基础菜单

新增标准库脚本 `scripts/generate_desktop_icons.py`，可复现生成：

- `desktop/resources/icon.icns`
- `desktop/resources/icon.ico`
- `desktop/resources/icon.png`

Electron 窗口新增基础菜单：

- 关于 OrderMind。
- 退出 OrderMind。
- 刷新、强制刷新。
- 实际大小、放大、缩小。
- 切换全屏。
- 最小化、关闭窗口。

涉及文件：

- `ordermind/webapp.py`
- `tests/test_i18n_webapp.py`

## 5. 当前限制

- 当前 Mac 默认产物是 `.zip` 试用包；`.dmg` 目标保留为独立命令，后续具备完整签名/公证/DMG 构建环境后再纳入正式门禁。
- Windows `.exe` / `.msi` 需要在 Windows 或 CI 构建环境中生成。
- 当前桌面壳复用本地 Web 工作台，后续需要继续增强原生桌面体验、PDF 报告、签名、公证和自动更新。

## 6. 后续建议

下一阶段建议按以下顺序继续：

1. 增加 PDF 报告导出。
2. 建 Windows 构建环境并产出 `.exe` / `.msi`。
3. 规划代码签名、公证和自动更新。
4. 增加客户真实订单样例验收。
5. 再统一提交并同步 GitHub/Gitee。
