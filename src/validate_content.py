#!/usr/bin/env python3
"""校验八卦食帖：数量、字段、食运、餐品名是否存在于 MCP 快照。"""
import collections
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
data = json.loads((ROOT / "web" / "gua-matrix.json").read_text())
menus = json.loads((ROOT / "data" / "menus.json").read_text())

needed = {"id", "symbol", "name", "image", "line", "fortune", "breakfast", "all_day"}
meals = {"main", "companions", "fallback"}
gua = data.get("gua", [])
errors = []

if len(gua) != 8:
    errors.append(f"卦象数量应为 8，实际 {len(gua)}")
if {g.get("fortune") for g in gua} - {"大吉", "中吉", "小吉", "平"}:
    errors.append("存在未知食运档位")

for g in gua:
    if needed - set(g):
        errors.append(f"{g.get('name', '?')}: 缺字段 {sorted(needed - set(g))}")
    for key in ("breakfast", "all_day"):
        m = g.get(key) or {}
        if meals - set(m):
            errors.append(f"{g.get('name', '?')}/{key}: 缺字段 {sorted(meals - set(m))}")
        if not isinstance(m.get("companions"), list) or len(m["companions"]) != 2:
            errors.append(f"{g.get('name', '?')}/{key}: 配餐必须恰好两项")
        fb = m.get("fallback") or {}
        if not fb.get("main") or not isinstance(fb.get("companions"), list):
            errors.append(f"{g.get('name', '?')}/{key}: 替换食帖不完整")

presence = {s: collections.defaultdict(set) for s in ("morning", "main")}
for city, rec in menus.items():
    for slot, items in rec.get("slots", {}).items():
        for item in items:
            presence[slot][item["name"]].add(city)
valid = {s: {c for c, r in menus.items() if r.get("slots", {}).get(s)} for s in presence}

for g in gua:
    for slot, key in (("morning", "breakfast"), ("main", "all_day")):
        meal = g[key]
        names = [meal["main"], *meal["companions"], meal["fallback"]["main"], *meal["fallback"]["companions"]]
        for name in names:
            if "当季" in name:
                continue
            missing = valid[slot] - presence[slot].get(name, set())
            if missing:
                errors.append(f"{g['name']}/{key}: 「{name}」在 {len(missing)} 家有效门店中缺失")

print(f"卦象 {len(gua)} 个 · 食帖 {len(gua) * 2} 份")
print(f"有效门店：早市 {len(valid['morning'])} 家，正餐 {len(valid['main'])} 家")
print("食运分布：" + " / ".join(f"{k} {v}" for k, v in collections.Counter(g["fortune"] for g in gua).items()))
if errors:
    print("\n校验失败：")
    for e in errors:
        print(" -", e)
    sys.exit(1)
print("校验通过：所有固定餐品与替换项均可在对应餐段的有效门店样本中找到。")
