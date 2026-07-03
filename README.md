# OrderMind 订单智脑

OrderMind 是一个本地优先的智能审单工具。第一版先实现离线解析 TXT/CSV/TSV/XLSX 订单、字段抽取、规则校验、中英文界面、账号密码登录、首次登录修改密码和首次使用操作指引。

## 当前第一版能力

- 支持 TXT、CSV、TSV、XLSX、XLSM 文件导入。
- 自动识别货号、品名、数量、单价、小计、材质、单位、总金额、付款方式、包装要求、交货期。
- 支持规则模板校验：必填项、货号格式、单位、单价小数位、单行金额、总金额、总数量。
- 提供中英文界面切换。
- 提供本地账号密码登录，默认账号为 `admin / Admin123456`，首次登录后必须修改密码。
- 提供首次使用指引，打开应用后按页面上的步骤完成上传和审单。
- 提供命令行入口，方便批量审单和开发验证。

## 运行本地 Web 应用

```bash
cd /Users/dlj/MyPython/OrderMind
python3 run_app.py
```

然后在浏览器打开：

```text
http://127.0.0.1:8765
```

首次登录：

```text
账号：admin
密码：Admin123456
```

登录后系统会要求修改密码。新密码至少 8 位，并包含字母和数字。

## 运行命令行审单

```bash
cd /Users/dlj/MyPython/OrderMind
python3 -m ordermind.cli samples/sample_order.txt --template templates/default_order_rules.json
python3 -m ordermind.cli samples/sample_order.xlsx --template templates/default_order_rules.json
```

如果订单存在错误，CLI 会返回非 0 退出码。这是为了支持后续批量审单和自动化质量门。

## 运行测试

```bash
cd /Users/dlj/MyPython/OrderMind
python3 -m unittest discover -s tests -v
python3 -m compileall ordermind run_app.py scripts
python3 scripts/release_check.py
```

## 构建桌面应用

当前桌面壳使用 Electron 包裹本地 Python 审单服务。应用启动后会自动选择本机端口、启动后端服务，并把用户数据保存到桌面应用数据目录中。

首次准备打包环境：

```bash
cd /Users/dlj/MyPython/OrderMind
npm install
python3 -m venv .venv-build
.venv-build/bin/python -m pip install pyinstaller==6.21.0
```

本机开发运行：

```bash
npm run desktop:dev
```

生成本机 Mac 测试安装包：

```bash
npm run desktop:dist:mac
```

当前默认生成 `.zip` 客户试用包。如果本机具备完整 DMG 构建环境，也可以运行：

```bash
npm run desktop:dist:mac:dmg
```

生成 Windows 安装包需要在 Windows 机器或 CI 环境执行：

```bash
npm run desktop:dist:win
```

安装包输出目录：

```text
release/installers/
```

## 项目结构

```text
ordermind/
  auth.py                 本地账号、密码哈希、首次改密
  i18n.py                 中英文界面文案
  models.py               订单、明细、证据、校验报告数据模型
  rules.py                规则模板和确定性校验引擎
  templates.py            JSON 规则模板读写
  reporting.py            JSON/CSV 输出
  webapp.py               本地 Web 界面
  extractors/
    dispatcher.py         文件格式分发
    text.py               TXT/CSV/TSV 解析
    xlsx.py               轻量 XLSX 解析
templates/
  default_order_rules.json
samples/
  sample_order.txt
  sample_order.xlsx
docs/
  requirements-and-roadmap.md
  collaboration.md
  desktop-app-plan.md
  release-and-upgrade.md
desktop/
  main.cjs                 Electron 桌面壳入口
  preload.cjs              桌面窗口预加载脚本
tests/
```

## 发布要求

每个发给客户试用的版本都必须有版本号、变更日志、Mac 安装包、Windows 安装包和升级说明。

当前 `0.1.0` 已建立发布元数据和升级清单模板。正式 `.dmg`、`.msi` 或 `.exe` 安装包将在桌面壳接入后生成。

发布与升级细则见：

[docs/release-and-upgrade.md](docs/release-and-upgrade.md)

## 重要边界

第一版是可运行 MVP，不是最终文档智能引擎。DOC、DOCX、PDF、扫描件 OCR、复杂合并单元格、跨页表格、本地大模型语义识别会在后续版本扩展。

当前 XLSX 解析器为了离线无依赖，直接读取 XLSX 内部 XML。生产版建议接入更成熟的解析引擎，并保留当前实现作为兜底。
