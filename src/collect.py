#!/usr/bin/env python3
"""全国巨无霸价格采集器。只读调用，不产生任何订单/领券/抽奖行为。

每个城市用「城市名 + 地标关键词」定位门店，逐店查询到店自提菜单，
取巨无霸单品（非套餐）的 currentPrice。菜单为空的门店（快捷小站/景区小店）如实记为 null。
"""
import json, pathlib, sys, time, traceback
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from mcp_client import call, ROOT, CACHE
from mcp_client import extract_json
from mcp_client import bigmac_price

CITIES = [
    ("北京市", "王府井"), ("上海市", "南京东路"), ("广州市", "天河城"), ("深圳市", "华强北"),
    ("天津市", "滨江道"), ("重庆市", "解放碑"), ("成都市", "春熙路"), ("杭州市", "西湖"),
    ("南京市", "新街口"), ("武汉市", "江汉路"), ("西安市", "钟楼"), ("长沙市", "黄兴路"),
    ("郑州市", "二七广场"), ("济南市", "泉城路"), ("青岛市", "五四广场"), ("沈阳市", "中街"),
    ("大连市", "青泥洼桥"), ("哈尔滨市", "中央大街"), ("长春市", "重庆路"), ("石家庄市", "北国商城"),
    ("太原市", "柳巷"), ("合肥市", "淮河路"), ("南昌市", "八一广场"), ("福州市", "东街口"),
    ("厦门市", "中山路"), ("昆明市", "南屏街"), ("贵阳市", "喷水池"), ("南宁市", "朝阳广场"),
    ("兰州市", "张掖路"), ("西宁市", "西门口"), ("银川市", "新华街"), ("乌鲁木齐市", "大巴扎"),
    ("拉萨市", "布达拉宫"), ("海口市", "明珠广场"), ("呼和浩特市", "中山路"),
    ("苏州市", "观前街"), ("无锡市", "崇安寺"), ("宁波市", "天一广场"), ("温州市", "五马街"),
]
MAX_STORES = 5

OUT = ROOT / "data" / "latest.json"
OUT.parent.mkdir(parents=True, exist_ok=True)


def txt(name):
    f = CACHE / f"raw_{name}.txt"
    return f.read_text() if f.exists() else ""


def fetch_stores(city, kw):
    call("query-nearby-stores", {"beType": 1, "searchType": 2, "city": city, "keyword": kw})
    obj = extract_json(txt("query-nearby-stores")) or {}
    return [s for s in (obj.get("data") or []) if s.get("storeCode")]


def fetch_price(code):
    call("query-meals", {"storeCode": code, "orderType": 1, "beType": 1})
    obj = extract_json(txt("query-meals")) or {}
    meals = (obj.get("data") or {}).get("meals") or {}
    if not meals:
        return None, 0
    for h in bigmac_price(obj):
        if h["name"].strip() in ("巨无霸", "巨无霸汉堡"):
            return float(h["currentPrice"]), len(meals)
    return None, len(meals)


def main():
    result, done = [], set()
    if OUT.exists():
        try:
            result = json.loads(OUT.read_text())
            done = {r["city"] for r in result if r.get("stores")}
            print(f"断点续采：已有 {len(done)} 城")
        except Exception:
            result = []
    for city, kw in CITIES:
        if city in done:
            continue
        rec = {"city": city, "keyword": kw, "stores": []}
        try:
            ss = fetch_stores(city, kw)[:MAX_STORES]
            for s in ss:
                p, n = fetch_price(s["storeCode"])
                rec["stores"].append({
                    "storeCode": s["storeCode"], "storeName": s.get("storeName"),
                    "address": s.get("address"), "bigmac": p, "items": n,
                })
                time.sleep(1.0)
            ok = [x["bigmac"] for x in rec["stores"] if x["bigmac"]]
            print(f"{city:8s} {len(ss)}店 有效价{len(ok)} "
                  f"{'价格 ' + str(min(ok)) + '-' + str(max(ok)) if ok else '无数据'}")
        except Exception as e:
            rec["error"] = str(e)
            print(f"{city:8s} 失败 {e}")
            traceback.print_exc()
        result.append(rec)
            OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    valid = [r for r in result if any(s["bigmac"] for s in r.get("stores", []))]
    print(f"\n完成：{len(result)} 城，{len(valid)} 城有有效价格")


if __name__ == "__main__":
    main()
