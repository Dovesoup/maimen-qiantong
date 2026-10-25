#!/usr/bin/env python3
"""按「早市 / 正餐」两个时段采集菜单快照，供签筒按时辰出签。只读调用。

麦当劳 MCP 的 query-meals 在不传 reservationDate 时返回**当前时段**可售菜单：
上午 10:30 前只有麦满分/炒双蛋堡/麦咖啡（早餐），午后才出现巨无霸等主食。
传 reservationDate（如 12:00）则返回该时段菜单，因此可以一次采到正餐单。
"""
import datetime, json, os, pathlib, sys, tempfile, time
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from mcp_client import call, McpError, ROOT

CITIES = [
    ("北京市", "王府井"), ("上海市", "南京东路"), ("广州市", "天河城"), ("深圳市", "华强北"),
    ("杭州市", "西湖"), ("成都市", "春熙路"), ("武汉市", "江汉路"), ("西安市", "钟楼"),
    ("南京市", "新街口"), ("重庆市", "解放碑"), ("拉萨市", "布达拉宫"),
]

KEEP = ["麦满分", "炒双蛋堡", "早安营养卷", "鸡肉汉堡", "巨无霸", "安格斯",
        "炸鸡", "蘸酱炸鸡", "小食甜品", "饮品", "麦咖啡"]
SKIP_WORD = ("套", "拼", "双人", "多人", "亲子", "随心", "周边", "玩具", "卡", "礼")

SLOTS = {"morning": "07:30", "main": "12:00"}


def _data(payload, tool):
    if not isinstance(payload, dict) or "data" not in payload:
        raise McpError(f"{tool} response is missing its data field")
    return payload["data"]


def _write_snapshot(path, snapshot):
    """Write the complete snapshot atomically so a failed run cannot truncate it."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(snapshot, stream, ensure_ascii=False, indent=1)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def _save_complete_snapshot(path, snapshot, failures, expected_cities):
    have_samples = {
        slot: any(rec.get("slots", {}).get(slot) for rec in snapshot.values())
        for slot in SLOTS
    }
    complete = (not failures and len(snapshot) == expected_cities
                and all(have_samples.values()))
    if complete:
        _write_snapshot(path, snapshot)
    return complete, have_samples


def fetch_menu(store_code, hhmm, day):
    args = {"storeCode": store_code, "orderType": 1, "beType": 1}
    if hhmm:
        args["reservationDate"] = f"{day} {hhmm}"
    o = call("query-meals", args)
    d = _data(o, "query-meals")
    if not isinstance(d, dict):
        raise McpError("query-meals response has an invalid data object")
    meals = d.get("meals") or {}
    categories = d.get("categories") or []
    if not isinstance(meals, dict) or not isinstance(categories, list):
        raise McpError("query-meals response has an invalid menu shape")
    if not meals:
        return []
    items = []
    for cat in categories:
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
    failures = []
    for city, kw in CITIES:
        try:
            o = call("query-nearby-stores", {"beType": 1, "searchType": 2, "city": city, "keyword": kw})
            store_data = _data(o, "query-nearby-stores")
            if not isinstance(store_data, list):
                raise McpError("query-nearby-stores response has an invalid store list")
            stores = [s for s in store_data if isinstance(s, dict) and s.get("storeCode")]
            if not stores:
                raise McpError("query-nearby-stores returned no usable stores")
            s = stores[0]
            rec = {"city": city, "storeCode": s["storeCode"],
                   "storeName": s.get("storeName"), "slots": {}}
            for slot, hhmm in SLOTS.items():
                items = fetch_menu(s["storeCode"], hhmm, day)
                rec["slots"][slot] = items
                time.sleep(1.0)
            print(f"{city:8s} 早{len(rec['slots']['morning']):3d} 正{len(rec['slots']['main']):3d}  {s.get('storeName')}")
            out[city] = rec
        except Exception as exc:
            failures.append(city)
            print(f"{city:8s} 失败 {type(exc).__name__}")
        time.sleep(1.0)
    p = ROOT / "data" / "menus.json"
    complete, have_samples = _save_complete_snapshot(p, out, failures, len(CITIES))
    if not complete:
        missing = len(CITIES) - len(out)
        print(f"\n采集未完成：失败 {len(failures)} 城，缺失 {missing} 城；"
              f"早市样本={'有' if have_samples['morning'] else '无'}，"
              f"正餐样本={'有' if have_samples['main'] else '无'}。")
        print("未替换已有菜单快照。")
        return 1

    print(f"\n→ {p}  ({len(out)} 城, {p.stat().st_size/1024:.0f} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
