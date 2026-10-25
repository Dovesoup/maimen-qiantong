#!/usr/bin/env python3
"""把 signs.json + menus.json 打包成网页用的 data.js（可离线、可直接 file:// 打开）。"""
import json, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
WEB = ROOT / "web"
signs = json.loads((WEB / "signs.json").read_text())
menus = json.loads((ROOT / "data" / "menus.json").read_text())


out = {}
for city, rec in menus.items():
    slots = {}
    for slot, items in (rec.get("slots") or {}).items():
        slots[slot] = [{"name": i["name"], "price": i["price"]} for i in items]
    if slots.get("main") or slots.get("morning"):
        out[city] = {"storeName": rec.get("storeName"), "slots": slots}

gen = json.loads((ROOT / "data" / "index.json").read_text()).get("generated_at", "") if (ROOT/"data"/"index.json").exists() else ""
js = (
    "window.META=" + json.dumps({"genAt": gen, "cities": len(out)}, ensure_ascii=False) + ";\n"
    "window.SIGNS=" + json.dumps({"main": signs["main"], "morning": signs["morning"]}, ensure_ascii=False, separators=(",", ":")) + ";\n"
    "window.MENUS=" + json.dumps(out, ensure_ascii=False, separators=(",", ":")) + ";\n"
)
p = WEB / "data.js"
p.write_text(js)
print(f"→ {p}  {len(js)/1024:.0f} KB  城数 {len(out)}  正签 {len(signs['main'])} 早签 {len(signs['morning'])}")

# 把数据内联进 index.html，保证单文件可离线、可直接预览，不依赖 data.js 的相对路径
page = WEB / "index.html"
if page.exists():
    html = page.read_text()
    import re
    inline = "<script>\n" + js + "</script>"
    if '<script src="data.js"></script>' in html:
        html = html.replace('<script src="data.js"></script>', inline)
    else:
        # 已经内联过：替换 window.META 起到 </script> 的数据块
        html = re.sub(r'<script>\nwindow\.META=.*?</script>', inline, html, count=1, flags=re.S)
    page.write_text(html)
    print(f"→ {page}  已内联数据 ({len(html)/1024:.0f} KB)")
