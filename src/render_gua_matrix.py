#!/usr/bin/env python3
"""把 gua-matrix.json 渲染成一页可审阅的双餐段食帖对照表。只读 JSON，不改正式签筒。"""
from html import escape
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
WEB = ROOT / "web"
data = json.loads((WEB / "gua-matrix.json").read_text())
meta = data["meta"]


def meal(m, label):
    main = m["main"]
    conditional = "当季" in main
    companion = " + ".join(m["companions"])
    fb = m["fallback"]
    fb_line = " + ".join([fb["main"], *fb["companions"]])
    tag = '<span class="conditional">条件签</span>' if conditional else ""
    variants = []
    for variant in m.get("variants", []):
        coverage = variant["sampleCoverage"]
        variant_fallback = variant["fallback"]
        variant_fallback_line = " + ".join([variant_fallback["main"], *variant_fallback["companions"]])
        variants.append(f"""
      <div class="variant">
        <div class="variant-head">可选口味：{escape(variant['main'])}</div>
        <div class="companions">{escape(' + '.join(variant['companions']))}</div>
        <div class="coverage">菜单快照供应 {coverage['matchingStores']}/{coverage['sampleStores']} 家（{escape(coverage['snapshotDate'])}）</div>
        <div class="availability">{escape(variant['availabilityNote'])}</div>
        <div class="fallback"><span>缺货替换</span>{escape(variant_fallback_line)}</div>
      </div>""".strip())
    return f"""
      <div class="meal-head">
        <span class="meal-label">{escape(label)}</span>
        <span class="meal-note">{'有新品才成立' if conditional else '照单点'}</span>
      </div>
      <div class="dish">{escape(main)}{tag}</div>
      <div class="companions">{escape(companion)}</div>
      <div class="fallback"><span>若无此味</span>{escape(fb_line)}</div>
      {''.join(variants)}
    """.strip()


rows = []
for g in data["gua"]:
    rows.append(f"""
    <tr>
      <td class="gua-cell" data-label="卦象">
        <div class="gua-top"><span class="symbol">{escape(g['symbol'])}</span><span class="taste">口味 · {escape(g['taste'])}</span></div>
        <div class="gua-name">{escape(g['name'])}<span>{escape(g['image'])}</span></div>
        <p class="line">{escape(g['line'])}</p>
      </td>
      <td class="meal-cell breakfast" data-label="早签 · 早餐食帖">{meal(g['breakfast'], '早签')}</td>
      <td class="meal-cell allday" data-label="正餐签 · 午晚食帖">{meal(g['all_day'], '正餐签')}</td>
    </tr>""".strip())

html = f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>麦门签 · 两套八卦 × 十八份食帖</title>
<style>
  :root{{--red:#da291c;--dark:#781f18;--yellow:#ffc72c;--cream:#f5f0e6;--paper:#fffdf8;--ink:#28231f;--muted:#776e64;--line:#ded5c7}}
  *{{box-sizing:border-box}} html{{scroll-behavior:smooth}}
  body{{margin:0;background:var(--cream);color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif}}
  .page{{max-width:1280px;margin:0 auto;padding:52px 32px 76px}}
  .kicker{{font-size:11px;font-weight:700;letter-spacing:.2em;color:var(--red)}}
  h1{{font-size:clamp(36px,5vw,64px);line-height:1.04;letter-spacing:-.055em;margin:14px 0 18px;font-weight:800}}
  h1 em{{font-style:normal;color:var(--red)}}
  .lead{{font-size:16px;line-height:1.85;color:var(--muted);max-width:720px;margin:0}}
  .stats{{display:flex;gap:28px;flex-wrap:wrap;margin:28px 0 0;padding:18px 0 0;border-top:1px solid var(--line)}}
  .stats div{{font-size:12px;color:var(--muted)}} .stats b{{display:block;font-size:24px;color:var(--ink);letter-spacing:-.03em;margin-bottom:2px}}
  .how{{display:grid;grid-template-columns:repeat(3,1fr);gap:1px;background:var(--line);border:1px solid var(--line);border-radius:12px;overflow:hidden;margin:32px 0 18px}}
  .how div{{background:var(--paper);padding:18px 20px;font-size:13px;line-height:1.65;color:var(--muted)}}
  .how b{{display:block;color:var(--ink);font-size:14px;margin-bottom:4px}}
  .how span{{display:inline-grid;place-items:center;width:22px;height:22px;border-radius:50%;background:var(--red);color:#fff;font-size:11px;margin-right:6px}}
  .table-wrap{{background:var(--paper);border:1px solid var(--line);border-radius:15px;overflow:hidden}}
  table{{width:100%;border-collapse:collapse;table-layout:fixed}}
  thead th{{background:var(--dark);color:#fff7e6;text-align:left;padding:15px 20px;font-size:12px;font-weight:650;letter-spacing:.03em}}
  thead th:first-child{{width:25%}} thead th:not(:first-child){{width:37.5%;border-left:1px solid rgba(255,255,255,.14)}}
  tbody tr{{border-top:1px solid var(--line)}} tbody tr:first-child{{border-top:0}}
  td{{vertical-align:top;padding:24px 20px}}
  .gua-cell{{background:#fbf7ef}} .meal-cell{{border-left:1px solid var(--line)}}
  .gua-top{{display:flex;justify-content:space-between;align-items:center;gap:8px}}
  .symbol{{font-family:"Songti SC",serif;font-size:42px;line-height:1;color:var(--red)}}
  .taste{{font-size:11px;font-weight:700;padding:5px 8px;border-radius:4px;white-space:nowrap;background:#f7e8ce;color:#7d4d0c;border:1px solid #e6c999}}
  .gua-name{{font-size:22px;font-weight:750;letter-spacing:-.02em;margin-top:9px}}
  .gua-name span{{font-size:12px;font-weight:500;color:var(--red);margin-left:7px;letter-spacing:0}}
  .line{{font-family:"Songti SC","STSong",serif;font-size:13px;color:var(--muted);margin:10px 0 0;line-height:1.65}}
  .meal-head{{display:flex;justify-content:space-between;align-items:center;margin-bottom:10px}}
  .meal-label{{font-size:11px;font-weight:750;letter-spacing:.1em;color:var(--red)}}
  .allday .meal-label{{color:var(--dark)}}
  .meal-note{{font-size:10px;color:#978d81}}
  .dish{{font-size:17px;line-height:1.45;font-weight:750;letter-spacing:-.02em}}
  .companions{{margin-top:6px;font-size:14px;color:var(--muted);line-height:1.55}}
  .conditional{{display:inline-block;vertical-align:2px;font-size:10px;font-weight:600;color:var(--dark);border:1px solid #d6b7a9;border-radius:3px;padding:2px 5px;margin-left:7px;white-space:nowrap}}
  .fallback{{margin-top:12px;padding-top:9px;border-top:1px dashed #ded5c7;font-size:11px;color:#8a7f72;line-height:1.55}}
  .fallback span{{display:inline-block;color:var(--red);margin-right:7px;font-weight:650}}
  .variant{{margin-top:14px;padding:12px;border:1px solid #ead8c9;border-radius:8px;background:#fffaf3}}
  .variant-head{{font-size:14px;font-weight:750;line-height:1.5}}
  .coverage,.availability{{margin-top:5px;font-size:10px;color:#8a7f72;line-height:1.6}}
  .availability{{color:var(--dark)}}
  .foot{{display:grid;grid-template-columns:1.3fr 1fr;gap:28px;margin-top:24px;font-size:12px;line-height:1.8;color:var(--muted)}}
  .foot strong{{display:block;color:var(--ink);font-size:13px;margin-bottom:5px}}
  .stamp{{border-left:3px solid var(--red);padding-left:14px}}
  .sig{{margin-top:30px;padding-top:16px;border-top:1px solid var(--line);display:flex;justify-content:space-between;gap:18px;font-size:11px;color:#928779}}
  @media(max-width:780px){{
    .page{{padding:34px 16px 52px}} .stats{{gap:20px}} .how{{grid-template-columns:1fr}}
    .table-wrap{{border:0;background:transparent;overflow:visible}}
    table,tbody,tr,td{{display:block;width:100%}} thead{{display:none}}
    tbody tr{{background:var(--paper);border:1px solid var(--line);border-radius:14px;overflow:hidden;margin-bottom:16px}}
    td{{padding:20px}} .gua-cell{{background:#fbf7ef}} .meal-cell{{border-left:0;border-top:1px solid var(--line)}}
    .meal-cell:before{{content:attr(data-label);display:block;font-size:10px;font-weight:700;letter-spacing:.08em;color:#928779;margin-bottom:9px}}
    .dish{{font-size:18px}} .foot{{grid-template-columns:1fr;gap:16px}} .sig{{display:block}}
  }}
  @media print{{body{{background:#fff}}.page{{max-width:none;padding:20px}}.table-wrap{{border-radius:0}}.how{{display:none}}}}
</style>
</head>
<body>
<main class="page">
  <div class="kicker">MAIMEN QIAN · GUA MENU MATRIX · {escape(meta['version'])}</div>
  <h1>八种食象，<br><em>两套吃法。</em></h1>
  <p class="lead">同一套八卦，只换餐段和食帖。先由用户选早餐或午晚，再摇出三根薯条对应的一个点餐结果。部分门店供应的口味变体会明确标注样本覆盖与缺货替换。</p>
  <div class="stats">
    <div><b>8</b>卦象</div><div><b>18</b>份可出食帖</div><div><b>2</b>个餐段入口</div><div><b>0</b>个价格</div>
  </div>

  <section class="how" aria-label="使用方式">
    <div><b><span>1</span>先选餐段</b>早餐或午晚正餐，只由用户自己判断。</div>
    <div><b><span>2</span>摇出一卦</b>三根薯条定阴阳，八种卦象，一个结果。</div>
    <div><b><span>3</span>照单点餐</b>缺货不重摇，只替换整份食帖一次。</div>
  </section>

  <div class="table-wrap">
    <table>
      <thead><tr><th>卦象 / 口味</th><th>早签 · 早餐食帖</th><th>正餐签 · 午晚食帖（含部分门店变体）</th></tr></thead>
      <tbody>{''.join(rows)}
      </tbody>
    </table>
  </div>

  <section class="foot">
    <div class="stamp"><strong>随机结果的边界</strong>食帖由随机结果给出，只用于点餐娱乐，不预测运势，也不代表菜品高低。口味标签只是食帖的描述。</div>
    <div><strong>数据来自哪里</strong>餐品名核对自麦当劳中国 MCP 菜单快照，采集于 {escape(meta['collectedOn'])}；覆盖 {meta['cityCount']} 城，早市 {meta['breakfastStoreCount']} 家有效、正餐 {meta['mainStoreCount']} 家有效。两款厚牛堡变体分别在 10/11、9/11 家正餐样本出现，其他固定餐品在所有对应有效样本中出现。样本不代表全国全时段供应。</div>
  </section>
  <div class="sig"><span>无城市 · 无价格 · 新品仅作条件食帖</span><span>完整食帖对照表 · 非麦当劳官方产品</span></div>
</main>
</body>
</html>
"""
out = WEB / "gua-matrix.html"
out.write_text(html)
print(f"→ {out}  {len(html)/1024:.1f} KB  {len(data['gua'])} 卦 · {len(data['gua']) * 2 + sum(len(g['all_day'].get('variants', [])) for g in data['gua'])} 份食帖")
