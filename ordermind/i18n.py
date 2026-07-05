"""中英文界面文案资源。

桌面应用最终会有前端壳，但语言资源应尽量保持独立。
第一版本地 Web UI 使用这个模块；后续 Tauri/Electron 版本也可以把这里的
key 迁移成前端 JSON，而业务层的错误 code 保持稳定不变。
"""

from __future__ import annotations

SUPPORTED_LANGUAGES = ("zh", "en")
DEFAULT_LANGUAGE = "zh"

TRANSLATIONS: dict[str, dict[str, str]] = {
    "zh": {
        "app_title": "OrderMind 订单智脑",
        "workspace_title": "离线智能审单工作台",
        "privacy_badge": "本机处理 · 不上传云端",
        "login_title": "登录 OrderMind",
        "username": "账号",
        "password": "密码",
        "old_password": "原密码",
        "new_password": "新密码",
        "login": "登录",
        "logout": "退出登录",
        "change_password_title": "首次登录需要修改密码",
        "change_password_hint": "为了避免长期使用默认密码，请先设置你的新密码。新密码至少 8 位，并包含字母和数字。",
        "change_password": "修改密码",
        "demo_account_hint": "演示账号：admin / Admin123456，首次登录后必须修改密码。",
        "login_failed": "账号或密码错误。",
        "password_changed": "密码已修改，请使用新密码登录。",
        "order_file": "订单文件",
        "rule_template": "校验模板",
        "start_review": "开始审单",
        "sample_orders": "脱敏示例订单",
        "sample_orders_hint": "不用准备客户文件，点击任一示例即可体验解析、校验和报告导出。",
        "first_time_guide": "首次使用指引",
        "guide_step_1_title": "第 1 步：选择订单文件",
        "guide_step_1_body": "点击“订单文件”，选择客户发来的 TXT、CSV、XLSX、PDF 或图片订单。扫描件和图片需要本机配置 OCR 命令。",
        "guide_step_2_title": "第 2 步：选择校验模板",
        "guide_step_2_body": "选择适合当前客户或产品线的规则模板。模板决定货号格式、必填项、金额尾差和小数位数。",
        "guide_step_3_title": "第 3 步：点击开始审单",
        "guide_step_3_body": "点击按钮后，OrderMind 会提取明细行并自动校验数量、金额、格式和必填项。",
        "guide_step_4_title": "第 4 步：查看结果并确认",
        "guide_step_4_body": "先看错误和警告，再核对订单明细。低置信度或复杂格式结果需要人工确认。",
        "current_version": "当前版本",
        "supported_formats": "支持 TXT / CSV / XLSX / PDF / 图片 OCR",
        "validation_scope": "校验范围",
        "validation_scope_value": "数量、金额、格式、必填项",
        "roadmap": "后续路线",
        "roadmap_value": "DOCX / 表格恢复 / 本地 AI",
        "result_title": "审单结果",
        "upload_again": "重新上传",
        "export_report": "导出报告",
        "export_excel": "导出 Excel",
        "report_title": "OrderMind 审单报告",
        "line_count": "明细行",
        "errors": "错误",
        "warnings": "警告",
        "order_lines": "订单明细",
        "issues": "校验问题",
        "structured_json": "结构化 JSON",
        "item_no": "货号",
        "product_name": "品名",
        "quantity": "数量",
        "unit_price": "单价",
        "subtotal": "小计",
        "material": "材质",
        "severity": "级别",
        "location": "位置",
        "issue": "问题",
        "no_issues": "未发现错误或警告。",
        "choose_file_error": "请先选择订单文件。",
        "switch_language": "English",
        "switch_language_code": "en",
    },
    "en": {
        "app_title": "OrderMind",
        "workspace_title": "Offline Order Review Workspace",
        "privacy_badge": "Processed locally · No cloud upload",
        "login_title": "Sign in to OrderMind",
        "username": "Username",
        "password": "Password",
        "old_password": "Current Password",
        "new_password": "New Password",
        "login": "Sign In",
        "logout": "Sign Out",
        "change_password_title": "Password Change Required",
        "change_password_hint": "To avoid long-term use of the default password, set a new password first. It must be at least 8 characters and include letters and numbers.",
        "change_password": "Change Password",
        "demo_account_hint": "Demo account: admin / Admin123456. The password must be changed after the first sign-in.",
        "login_failed": "Invalid username or password.",
        "password_changed": "Password changed. Please sign in with the new password.",
        "order_file": "Order File",
        "rule_template": "Rule Template",
        "start_review": "Review Order",
        "sample_orders": "Sanitized Sample Orders",
        "sample_orders_hint": "Try parsing, validation, and report export without preparing a customer file.",
        "first_time_guide": "First-Time Guide",
        "guide_step_1_title": "Step 1: Choose an order file",
        "guide_step_1_body": "Click Order File and choose a customer TXT, CSV, XLSX, PDF, or image order. Scanned files and images require a local OCR command.",
        "guide_step_2_title": "Step 2: Choose a rule template",
        "guide_step_2_body": "Select the template for the current customer or product line. Templates control item number format, required fields, amount tolerance, and decimal places.",
        "guide_step_3_title": "Step 3: Click Review Order",
        "guide_step_3_body": "OrderMind extracts order lines and checks quantity, amount, format, and required fields.",
        "guide_step_4_title": "Step 4: Review and confirm results",
        "guide_step_4_body": "Start with errors and warnings, then verify the extracted order lines. Low-confidence or complex-layout results still require human confirmation.",
        "current_version": "Current Version",
        "supported_formats": "TXT / CSV / XLSX / PDF / image OCR supported",
        "validation_scope": "Validation Scope",
        "validation_scope_value": "Quantity, amount, format, required fields",
        "roadmap": "Roadmap",
        "roadmap_value": "DOCX / table recovery / local AI",
        "result_title": "Review Result",
        "upload_again": "Upload Again",
        "export_report": "Export Report",
        "export_excel": "Export Excel",
        "report_title": "OrderMind Review Report",
        "line_count": "Lines",
        "errors": "Errors",
        "warnings": "Warnings",
        "order_lines": "Order Lines",
        "issues": "Validation Issues",
        "structured_json": "Structured JSON",
        "item_no": "Item No.",
        "product_name": "Product Name",
        "quantity": "Quantity",
        "unit_price": "Unit Price",
        "subtotal": "Subtotal",
        "material": "Material",
        "severity": "Severity",
        "location": "Location",
        "issue": "Issue",
        "no_issues": "No errors or warnings found.",
        "choose_file_error": "Please choose an order file first.",
        "switch_language": "中文",
        "switch_language_code": "zh",
    },
}


def normalize_language(lang: str | None) -> str:
    """把外部传入的语言参数归一到支持范围。

    UI URL 里可能传入 `zh-CN`、`en-US` 或空值。第一版只区分中文和英文，
    因此只取前两位，并在不支持时回退到中文。
    """

    if not lang:
        return DEFAULT_LANGUAGE
    short = lang.lower().split("-", 1)[0]
    return short if short in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE


def t(lang: str | None, key: str) -> str:
    """按语言和 key 读取文案；缺失时回退到中文，再回退到 key 本身。"""

    normalized = normalize_language(lang)
    return TRANSLATIONS.get(normalized, {}).get(
        key,
        TRANSLATIONS[DEFAULT_LANGUAGE].get(key, key),
    )
