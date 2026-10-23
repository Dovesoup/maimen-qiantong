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
