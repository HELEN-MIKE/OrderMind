# 脱敏仿真订单样例

这些文件用于演示和验收 OrderMind 的解析、校验、HTML 报告和 Excel 报告导出流程。

所有公司名、联系人、地址、电话、订单号和业务主体都是虚构数据，不对应真实客户或供应商。样例只保留常见订单字段结构，例如付款方式、包装要求、交货期、货号、品名、数量、单价、小计、材质和单位。

## 文件说明

- `domestic_purchase_order_zh.txt`: 中文国内采购订单，金额和数量一致。
- `commercial_invoice_en.csv`: 英文商业发票样式订单，金额和数量一致。
- `proforma_invoice_en.tsv`: 英文形式发票样式订单，使用制表符分隔。
- `multi_currency_order.xlsx`: 多币种报价备注的 Excel 样式订单，核心审单金额按 USD 列校验。
- `text_pdf_order.pdf`: 可复制文本的 PDF 样式订单，用于验证文本型 PDF 导入。
- `review_findings_bad_amount_missing_material.txt`: 故意带问题样例，用于演示小计不一致、总金额不一致、品名/材质缺失、货号格式异常、单价小数位异常等审单发现。

## 重新生成 Excel 样例

```bash
python3 scripts/generate_customer_like_samples.py
```

## 快速验收

```bash
python3 -m unittest tests.test_customer_like_samples -v
python3 -m ordermind.cli samples/customer_like_orders/commercial_invoice_en.csv --template templates/default_order_rules.json
```
