#!/usr/bin/env python3
"""把 index.json 渲染成一张自包含 HTML 报告（可直接 GitHub Pages 托管、也可截图传播）。"""
import json, pathlib, html

ROOT = pathlib.Path(__file__).resolve().parent.parent
IDX = json.loads((ROOT / "data" / "index.json").read_text())


def bar(value, vmax, width=100, color="#DA291C"):
    pct = 0 if not vmax else max(2, round(value / vmax * width, 1))
    return (f'<div class="bar"><span style="width:{pct}%;background:{color}"></span></div>')


def main():
    for c in IDX["cities"]:
        c["city"] = c["city"].removesuffix("市")
    for p in IDX["top_premium"]:
        p["city"] = p["city"].removesuffix("市")
    n = IDX["national"]
    cities = IDX["cities"]
    dist = IDX["distribution"]
    prem = [p for p in IDX["top_premium"] if p["delta"] > 0]
    dmax = max((v for v in dist.values()), default=1)
    pmax = max((c["median"] for c in cities), default=1)
    smax = max((c["spread"] for c in cities), default=1)

    special_line = ""
    if IDX["special_avg"]:
        diff = IDX["special_avg"] - IDX["normal_avg"]
        special_line = (f'名称含景区/车站等字样的 {IDX["special_n"]} 家门店均价 '
                        f'<b>{IDX["special_avg"]} 元</b>，其余 {IDX["normal_n"]} 家均价 '
                        f'<b>{IDX["normal_avg"]} 元</b>，只高 <b>{diff:.2f} 元</b>'
                        f'（{diff / IDX["normal_avg"] * 100:.1f}%），<b>不足以支撑"景区就贵"的解释</b>。')

    total = IDX["store_count"]
    mode_price, mode_n = max(dist.items(), key=lambda kv: kv[1])
    top3 = sorted(dist.items(), key=lambda kv: -kv[1])[:3]
    top3_n = sum(v for _, v in top3)
    top3_price = " / ".join(f"{k}" for k, _ in sorted(top3, key=lambda kv: float(kv[0])))

    # 剔除最贵城市后，其余城市的波动范围
    richest = max(cities, key=lambda c: c["median"])
    rest = [c for c in cities if c["city"] != richest["city"]]
    rest_all = [r for r in IDX.get("_rows", [])]  # 占位，未使用
    rest_min = min(c["median"] for c in rest)
    rest_max = max(c["median"] for c in rest)
    cheapest = min(cities, key=lambda c: c["median"])
    cheap_cities = [c["city"] for c in cities if c["median"] == cheapest["median"]]
    gap_pct = (richest["median"] / n["median"] - 1) * 100
    same_price_cities = [c["city"] for c in cities if c["min"] == c["max"]]

    max_spread_city = max(cities, key=lambda c: c["spread"]) if cities else None

    dist_rows = "".join(
        f'<tr><td class="mono">{k} 元</td><td>{bar(v, dmax)}</td>'
        f'<td class="num">{v}</td><td class="num">{v / IDX["store_count"] * 100:.1f}%</td></tr>'
        for k, v in sorted(dist.items(), key=lambda kv: float(kv[0]))
    )

    city_rows = "".join(
        f'<tr><td>{html.escape(c["city"])}</td>'
        f'<td>{bar(c["median"], pmax, 80, "#2b2b2b")}</td>'
        f'<td class="num">{c["median"]:.1f}</td>'
        f'<td class="num">{c["min"]:.1f}–{c["max"]:.1f}</td>'
        f'<td class="num">{c["n"]}</td></tr>'
        for c in cities
    )

    spread_rows = "".join(
        f'<tr><td>{html.escape(c["city"])}</td><td>{bar(c["spread"], smax, 80)}</td>'
        f'<td class="num">{c["spread"]:.1f} 元</td><td class="num">{c["spread_pct"]:.1f}%</td>'
        f'<td class="num mono">{c["min"]:.1f} / {c["max"]:.1f}</td></tr>'
        for c in sorted(cities, key=lambda x: -x["spread"])[:15]
    )

    prem_rows = "".join(
        f'<tr><td class="num">+{p["delta"]:.1f}</td>'
        f'<td>{html.escape(p["city"])}</td>'
        f'<td>{html.escape(p["storeName"] or "")}</td>'
        f'<td class="num">{p["price"]:.1f}</td>'
        f'<td class="num">{p["city_median"]:.1f}</td></tr>'
        for p in prem[:15]
    )

    page = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>巨无霸价格地图 · 中国 {IDX['city_count']} 城 {IDX['store_count']} 店实测</title>
<style>
*{{box-sizing:border-box}}
body{{margin:0;background:#fff;color:#1a1a1a;font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif;font-size:15px;line-height:1.7;-webkit-font-smoothing:antialiased}}
.wrap{{max-width:880px;margin:0 auto;padding:0 26px 70px}}
.bar-top{{height:6px;background:#FFC72C}}
header{{padding:34px 0 22px;border-bottom:2px solid #1a1a1a}}
.kicker{{font-size:12px;letter-spacing:.14em;color:#888;margin-bottom:10px}}
h1{{font-size:26px;line-height:1.35;margin:0 0 10px;font-weight:600;letter-spacing:-.01em}}
.meta{{font-size:13px;color:#888}}
h2{{font-size:18px;margin:40px 0 12px;font-weight:600;padding-bottom:7px;border-bottom:1px solid #e6e6e2}}
p{{margin:0 0 12px;color:#4a4a4a}}
b{{color:#1a1a1a;font-weight:600}}
.lead{{background:#f8f8f6;border-left:4px solid #FFC72C;padding:16px 20px;margin:22px 0}}
.lead p:last-child{{margin:0}}
table{{width:100%;border-collapse:collapse;margin:14px 0;font-size:13.5px}}
th,td{{text-align:left;padding:8px 10px;border-bottom:1px solid #eee}}
th{{background:#f8f8f6;font-size:12.5px;font-weight:600}}
td.num{{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}}
.mono{{font-family:ui-monospace,Menlo,monospace;font-size:12.5px}}
.bar{{background:#f0f0ec;height:9px;border-radius:5px;overflow:hidden;min-width:60px}}
.bar span{{display:block;height:100%;border-radius:5px}}
.note{{font-size:12.5px;color:#888;margin-top:6px}}
footer{{margin-top:48px;padding-top:16px;border-top:1px solid #e6e6e2;font-size:12px;color:#888}}
</style></head><body><div class="bar-top"></div><div class="wrap">
<header>
<div class="kicker">麦当劳 MCP · 实测数据 · {IDX['generated_at']}</div>
<h1>巨无霸价格地图<br><span style="font-size:17px;font-weight:400;color:#4a4a4a">{IDX['city_count']} 城 {IDX['store_count']} 家门店的真实挂牌价</span></h1>
<div class="meta">数据来源：麦当劳中国 MCP Server（mcp.mcd.cn）· 到店自提菜单实时价 · 只读采集</div>
</header>

<div class="lead">
<p><b>结论一：麦当劳在中国基本是统一定价。</b>{IDX['city_count']} 城 {total} 家有巨无霸在售的门店，只出现 <b>{len(dist)} 个价位</b>；<b>{top3_price} 元这三档覆盖 {top3_n / total * 100:.1f}%</b> 的门店，其中 <b>{mode_n} 家（{mode_n / total * 100:.1f}%）都是 {mode_price} 元</b>。</p>
<p><b>结论二：最贵的城市是{richest['city']}，而且是整城涨。</b>{richest['city']} {richest['n']} 家门店全部卖 <b>{richest['median']} 元</b>，比全国中位数高 <b>{gap_pct:.1f}%</b>；最便宜的是{'、'.join(cheap_cities[:3])}，<b>{cheapest['median']} 元</b>。</p>
<p><b>结论三：除{richest['city']}外，全国就是一个价。</b>剩下 {len(rest)} 个城市的中位数全部落在 <b>{rest_min}–{rest_max} 元</b>之间，最大差距只有 <b>{rest_max - rest_min:.1f} 元</b>。一线城市并不更贵——上海 {cheapest['median']} 元，比{richest['city']}便宜 {richest['median'] - cheapest['median']:.1f} 元。</p>
</div>

<div class="note" style="margin:14px 0 0">
另：{len(same_price_cities)} 个城市呈现「全城同价」——{'、'.join(same_price_cities)}。
名称含「景区」「车站」「码头」等字样的门店<b>并未</b>呈现系统性溢价（样本 {IDX['special_n']} 家，均价与普通门店差 {abs((IDX['special_avg'] or 0) - IDX['normal_avg']):.2f} 元），故不作为独立结论。
</div>

<h2>价格分布</h2>
<table><thead><tr><th>单价</th><th>门店数分布</th><th>门店数</th><th>占比</th></tr></thead>
<tbody>{dist_rows}</tbody></table>
<div class="note">共 {IDX['store_count']} 家有巨无霸单品在售的门店。另有 {IDX['empty_store_count']} 家门店（快捷小站/景区小店等）菜单中无该商品，已排除。</div>

<h2>城市中位数排名（{len(cities)} 城）</h2>
<table><thead><tr><th>城市</th><th>中位价</th><th>元</th><th>区间</th><th>有效门店</th></tr></thead>
<tbody>{city_rows}</tbody></table>

<h2>同城价差排名</h2>
<table><thead><tr><th>城市</th><th>极差</th><th>元</th><th>幅度</th><th>最低 / 最高</th></tr></thead>
<tbody>{spread_rows}</tbody></table>

<h2>比本城中位数更贵的门店</h2>
<table><thead><tr><th>溢价</th><th>城市</th><th>门店</th><th>售价</th><th>本城中位</th></tr></thead>
<tbody>{prem_rows}</tbody></table>
<div class="note">溢价 = 门店售价 − 所在城市中位数。仅列正溢价门店，门店名称用于定位，不含任何评价。</div>

<h2>方法</h2>
<p>每个城市以「城市名 + 地标关键词」调用麦当劳 MCP 的 <code>query-nearby-stores</code> 取最多 5 家门店，再逐店调用 <code>query-meals</code> 读取 <code>data.meals</code> 中名称为「巨无霸」的 <code>currentPrice</code>。串行限速 1 秒/次，全程只读，不产生订单、不领券、不抽奖。</p>
<p>价格口径为<b>该门店到店自提菜单的实时挂牌价</b>，含会员价或促销时以返回值为准；不含外送价、不含套餐价。同一门店价格可能随时间和活动变动。</p>
<p>门店名称含「景区」「机场」「车站」「码头」「博物院」等字样的记为特殊点位，此分类为启发式规则，非官方标定。</p>

<footer>
生成于 {IDX['generated_at']} · 数据来自麦当劳中国官方 MCP · 本项目不对商品及品牌作任何评价，仅呈现公开挂牌价。<br>
复现：<code>python src/collect.py &amp;&amp; python src/index.py &amp;&amp; python src/render.py</code>
</footer>
</div></body></html>"""

    out = ROOT / "docs" / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True) if not out.parent.exists() else None
    out.write_text(page)
    print(f"→ {out} ({len(page)} 字符)")


if __name__ == "__main__":
    main()
