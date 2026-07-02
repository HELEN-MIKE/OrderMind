"""生成 OrderMind 第一版 XLSX 示例订单。

不依赖 openpyxl，直接写入最小可用的 XLSX ZIP 包，方便离线环境验证。
"""

from __future__ import annotations

import zipfile
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    output = root / "samples" / "sample_order.xlsx"
    output.parent.mkdir(parents=True, exist_ok=True)
    files = _xlsx_files()
    with zipfile.ZipFile(output, "w") as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    print(f"created {output}")


def _xlsx_files() -> dict[str, str]:
    """返回最小 XLSX 包所需文件。"""

    return {
        "[Content_Types].xml": """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
  <Override PartName="/xl/sharedStrings.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/>
</Types>
""",
        "_rels/.rels": """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>
""",
        "xl/workbook.xml": """<?xml version="1.0" encoding="UTF-8"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets><sheet name="订单" sheetId="1" r:id="rId1"/></sheets>
</workbook>
""",
        "xl/_rels/workbook.xml.rels": """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/sharedStrings" Target="sharedStrings.xml"/>
</Relationships>
""",
        "xl/sharedStrings.xml": """<?xml version="1.0" encoding="UTF-8"?>
<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" count="15" uniqueCount="15">
  <si><t>客户订单</t></si>
  <si><t>货号</t></si>
  <si><t>品名</t></si>
  <si><t>数量</t></si>
  <si><t>单价</t></si>
  <si><t>小计</t></si>
  <si><t>材质</t></si>
  <si><t>单位</t></si>
  <si><t>OM-2001</t></si>
  <si><t>玻璃杯</t></si>
  <si><t>高硼硅玻璃</t></si>
  <si><t>PCS</t></si>
  <si><t>OM-2002</t></si>
  <si><t>杯盖</t></si>
  <si><t>硅胶</t></si>
</sst>
""",
        "xl/worksheets/sheet1.xml": """<?xml version="1.0" encoding="UTF-8"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <sheetData>
    <row r="1"><c r="A1" t="s"><v>0</v></c></row>
    <row r="2">
      <c r="A2" t="s"><v>1</v></c><c r="B2" t="s"><v>2</v></c><c r="C2" t="s"><v>3</v></c>
      <c r="D2" t="s"><v>4</v></c><c r="E2" t="s"><v>5</v></c><c r="F2" t="s"><v>6</v></c><c r="G2" t="s"><v>7</v></c>
    </row>
    <row r="3">
      <c r="A3" t="s"><v>8</v></c><c r="B3" t="s"><v>9</v></c><c r="C3"><v>100</v></c>
      <c r="D3"><v>2.5</v></c><c r="E3"><v>250.00</v></c><c r="F3" t="s"><v>10</v></c><c r="G3" t="s"><v>11</v></c>
    </row>
    <row r="4">
      <c r="A4" t="s"><v>12</v></c><c r="B4" t="s"><v>13</v></c><c r="C4"><v>50</v></c>
      <c r="D4"><v>3</v></c><c r="E4"><v>150.00</v></c><c r="F4" t="s"><v>14</v></c><c r="G4" t="s"><v>11</v></c>
    </row>
    <row r="5"><c r="D5"><v>总金额</v></c><c r="E5"><v>400.00</v></c></row>
  </sheetData>
  <mergeCells count="1"><mergeCell ref="A1:G1"/></mergeCells>
</worksheet>
""",
    }


if __name__ == "__main__":
    main()
