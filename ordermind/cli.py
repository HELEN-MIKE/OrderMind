"""OrderMind 命令行入口。

命令行入口主要服务三类场景：
1. 开发阶段快速验证解析和校验逻辑；
2. 客户现场批量审单；
3. 自动化测试或后续集成脚本。
"""

from __future__ import annotations

import argparse
from pathlib import Path

from ordermind.extractors.dispatcher import parse_order_file
from ordermind.reporting import build_result_payload, issues_to_csv, lines_to_csv, payload_to_json
from ordermind.rules import validate_order
from ordermind.templates import load_template


def main() -> int:
    """解析命令行参数，执行一次订单解析和校验。"""

    parser = argparse.ArgumentParser(description="OrderMind 订单智脑离线审单工具")
    parser.add_argument("file", help="待解析订单文件，支持 .txt/.csv/.tsv/.xlsx/.xlsm/.pdf/图片 OCR")
    parser.add_argument(
        "--template",
        default="templates/default_order_rules.json",
        help="规则模板 JSON 路径",
    )
    parser.add_argument("--out", default="", help="输出 JSON 报告路径")
    parser.add_argument("--lines-csv", default="", help="导出订单明细 CSV 路径")
    parser.add_argument("--issues-csv", default="", help="导出问题清单 CSV 路径")
    args = parser.parse_args()

    record = parse_order_file(args.file)
    template = load_template(args.template)
    report = validate_order(record, template)
    payload = build_result_payload(record, report)
    output = payload_to_json(payload)

    if args.out:
        Path(args.out).write_text(output, encoding="utf-8")
    else:
        print(output)
    if args.lines_csv:
        Path(args.lines_csv).write_text(lines_to_csv(record), encoding="utf-8-sig")
    if args.issues_csv:
        Path(args.issues_csv).write_text(issues_to_csv(report), encoding="utf-8-sig")
    return 1 if report.errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
