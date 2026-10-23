#!/usr/bin/env python3
"""按「早市 / 正餐」两个时段采集菜单快照，供签筒按时辰出签。只读调用。

麦当劳 MCP 的 query-meals 在不传 reservationDate 时返回**当前时段**可售菜单：
上午 10:30 前只有麦满分/炒双蛋堡/麦咖啡（早餐），午后才出现巨无霸等主食。
传 reservationDate（如 12:00）则返回该时段菜单，因此可以一次采到正餐单。
"""
import datetime, json, pathlib, sys, time
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from mcp_client import call, ROOT, CACHE
from mcp_client import extract_json

CITIES = [
    ("北京市", "王府井"), ("上海市", "南京东路"), ("广州市", "天河城"), ("深圳市", "华强北"),
    ("杭州市", "西湖"), ("成都市", "春熙路"), ("武汉市", "江汉路"), ("西安市", "钟楼"),
    ("南京市", "新街口"), ("重庆市", "解放碑"), ("拉萨市", "布达拉宫"),
]

KEEP = ["麦满分", "炒双蛋堡", "早安营养卷", "鸡肉汉堡", "巨无霸", "安格斯",
        "炸鸡", "蘸酱炸鸡", "小食甜品", "饮品", "麦咖啡"]
SKIP_WORD = ("套", "拼", "双人", "多人", "亲子", "随心", "周边", "玩具", "卡", "礼")

SLOTS = {"morning": "07:30", "main": "12:00"}


def txt(name):
    f = CACHE / f"raw_{name}.txt"
    return f.read_text() if f.exists() else ""


def fetch_menu(store_code, hhmm, day):
    args = {"storeCode": store_code, "orderType": 1, "beType": 1}
    if hhmm:
        args["reservationDate"] = f"{day} {hhmm}"
    call("query-meals", args)
    o = extract_json(txt("query-meals")) or {}
    d = o.get("data") or {}
    meals = d.get("meals") or {}
    if not meals:
        return []
    items = []
    for cat in d.get("categories") or []:
        cname = (cat.get("name") or "").replace("\n", "")
        if not any(k in cname for k in KEEP):
            continue
        for m in cat.get("meals") or []:
            info = meals.get(m.get("code")) or {}
            name = (info.get("name") or "").replace("\n", "")
            price = info.get("currentPrice")
            if not name or not price:
                continue
            if any(w in name for w in SKIP_WORD):
                continue
            items.append({"code": m.get("code"), "name": name,
                          "price": float(price), "cat": cname})
    seen, uniq = set(), []
    for it in items:
        k = (it["name"], it["price"])
        if k in seen:
            continue
        seen.add(k)
        uniq.append(it)
    return uniq


def main():
    day = (datetime.date.today() + datetime.timedelta(days=1)).isoformat()
    out = {}
    for city, kw in CITIES:
        try:
            call("query-nearby-stores", {"beType": 1, "searchType": 2, "city": city, "keyword": kw})
            o = extract_json(txt("query-nearby-stores")) or {}
            stores = [s for s in (o.get("data") or []) if s.get("storeCode")]
            if not stores:
                print(f"{city:8s} 无门店")
                continue
            s = stores[0]
            rec = {"city": city, "storeCode": s["storeCode"],
                   "storeName": s.get("storeName"), "slots": {}}
            for slot, hhmm in SLOTS.items():
                items = fetch_menu(s["storeCode"], hhmm, day)
                rec["slots"][slot] = items
                time.sleep(1.0)
            print(f"{city:8s} 早{len(rec['slots']['morning']):3d} 正{len(rec['slots']['main']):3d}  {s.get('storeName')}")
            out[city] = rec
        except Exception as e:
            print(f"{city:8s} 失败 {e}")
        time.sleep(1.0)
    p = ROOT / "data" / "menus.json"
    p.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(f"\n→ {p}  ({len(out)} 城, {p.stat().st_size/1024:.0f} KB)")


if __name__ == "__main__":
    main()
