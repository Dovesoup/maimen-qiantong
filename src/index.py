#!/usr/bin/env python3
"""巨无霸价格指数计算：全国分布 / 城市排名 / 同城极差 / 点位溢价榜。"""
import json, pathlib, re, statistics as st
from collections import Counter

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "latest.json"

SPECIAL = re.compile(r"景区|机场|车站|码头|博物院|博物馆|乐园|车站|火车站|高铁|服务区|游乐|公园|古镇|塔|广场店")


def load():
    raw = json.loads(DATA.read_text())
    out = []
    for r in raw:
        for s in r.get("stores", []):
            if s.get("bigmac"):
                out.append({
                    "city": r["city"], "storeName": s["storeName"],
                    "address": s.get("address"), "price": s["bigmac"],
                    "items": s.get("items"), "special": bool(SPECIAL.search(s.get("storeName") or "")),
                })
    return raw, out


def build():
    raw, rows = load()
    by_city = {}
    for r in rows:
        by_city.setdefault(r["city"], []).append(r["price"])

    cities = []
    for c, ps in by_city.items():
        cities.append({
            "city": c, "n": len(ps), "min": min(ps), "max": max(ps),
            "median": round(st.median(ps), 1), "mean": round(st.mean(ps), 2),
            "spread": round(max(ps) - min(ps), 1),
            "spread_pct": round((max(ps) / min(ps) - 1) * 100, 1),
        })
    cities.sort(key=lambda x: (-x["median"], -x["spread"]))

    # 溢价门店：相对本城中位数
    prem = []
    for r in rows:
        med = round(st.median(by_city[r["city"]]), 1)
        prem.append({**r, "city_median": med, "delta": round(r["price"] - med, 1)})
    prem.sort(key=lambda x: (-x["delta"], x["city"]))

    allp = [r["price"] for r in rows]
    dist = Counter(allp)
    return {
        "generated_at": __import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M"),
        "city_count": len(by_city),
        "valid_city_count": len(cities),
        "store_count": len(rows),
        "empty_store_count": sum(1 for r in raw for s in r.get("stores", []) if not s.get("bigmac")),
        "national": {
            "min": min(allp), "max": max(allp),
            "median": round(st.median(allp), 1), "mean": round(st.mean(allp), 2),
            "spread": round(max(allp) - min(allp), 1),
            "spread_pct": round((max(allp) / min(allp) - 1) * 100, 1),
        },
        "distribution": {str(k): v for k, v in sorted(dist.items())},
        "cities": cities,
        "top_premium": prem[:12],
        "special_avg": round(st.mean([r["price"] for r in rows if r["special"]]), 2) if any(r["special"] for r in rows) else None,
        "normal_avg": round(st.mean([r["price"] for r in rows if not r["special"]]), 2),
        "special_n": sum(1 for r in rows if r["special"]),
        "normal_n": sum(1 for r in rows if not r["special"]),
    }


if __name__ == "__main__":
    idx = build()
    out = ROOT / "data" / "index.json"
    out.write_text(json.dumps(idx, ensure_ascii=False, indent=2))
    n = idx["national"]
    print(f"城市 {idx['city_count']} / 有效门店 {idx['store_count']} / 菜单为空 {idx['empty_store_count']}")
    print(f"全国：{n['min']}–{n['max']} 元，中位 {n['median']}，极差 {n['spread']} 元（{n['spread_pct']}%）")
    print(f"特殊点位均价 {idx['special_avg']}（n={idx['special_n']}） vs 普通门店 {idx['normal_avg']}（n={idx['normal_n']}）")
    print("\n价格分布:", idx["distribution"])
    print("\n同城极差 TOP5:")
    for c in sorted(idx["cities"], key=lambda x: -x["spread"])[:5]:
        print(f"  {c['city']:8s} {c['min']}–{c['max']} 差{c['spread']}元({c['spread_pct']}%) n={c['n']}")
    print("\n溢价门店 TOP8:")
    for p in idx["top_premium"][:8]:
        if p["delta"] > 0:
            print(f"  +{p['delta']:>4} 元  {p['city']:8s} {p['storeName']}")
    print(f"\n→ {out}")
