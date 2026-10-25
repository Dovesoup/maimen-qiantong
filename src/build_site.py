#!/usr/bin/env python3
"""把 gua-matrix.json 注入单文件页面，生成可直接部署的 web/index.html。"""
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
WEB = ROOT / "web"
template = (WEB / "index.template.html").read_text()
data = json.loads((WEB / "gua-matrix.json").read_text())

payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
if "</script" in payload.lower():
    raise SystemExit("数据中含 </script，拒绝生成")
if "/*__GUA_DATA__*/null" not in template:
    raise SystemExit("模板缺少数据占位符")

html = template.replace("/*__GUA_DATA__*/null", payload)
(WEB / "index.html").write_text(html)
print(f"→ {WEB/'index.html'}  {len(html)/1024:.1f} KB  数据已内联 · {len(data['gua'])} 卦")
