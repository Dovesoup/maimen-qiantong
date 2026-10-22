#!/usr/bin/env python3
"""麦当劳 MCP 探测脚本 —— 只读调用，不下单、不领券、不抽奖。"""
import json, sys, urllib.request, pathlib

import os

ROOT = pathlib.Path(__file__).resolve().parent.parent
CACHE = ROOT / "data" / "cache"
TOKEN = os.environ.get("MCD_MCP_TOKEN", "").strip()
URL = "https://mcp.mcd.cn"

if not TOKEN:
    raise SystemExit(
        "缺少 MCD_MCP_TOKEN。\n"
        "1) 到 https://open.mcd.cn 手机号登录 → 控制台 → 激活，复制 Token\n"
        "2) export MCD_MCP_TOKEN=你的token"
    )


def _ensure_cache():
    CACHE.mkdir(parents=True, exist_ok=True)


def call(name, args, timeout=45):
    _ensure_cache()
    body = json.dumps({
        "jsonrpc": "2.0", "id": 1, "method": "tools/call",
        "params": {"name": name, "arguments": args},
    }).encode()
    req = urllib.request.Request(URL, data=body, method="POST", headers={
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    })
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read().decode("utf-8", "replace")
    if raw.startswith("event:") or raw.startswith("data:"):
        for line in raw.splitlines():
            if line.startswith("data:"):
                raw = line[5:].strip()
                break
    d = json.loads(raw)
    if "error" in d:
        return {"_error": d["error"]}
    res = d.get("result", {})
    content = res.get("content") or []
    txt = "\n".join(c.get("text", "") for c in content if c.get("type") == "text")
    try:
        return json.loads(txt)
    except Exception:
        (CACHE / f"raw_{name}.txt").write_text(txt)
        return {"_raw": txt[:4000], "_full_len": len(txt), "_isError": res.get("isError"),
                "_note": f"非 JSON，完整文本已存 .secrets/raw_{name}.txt"}


def brief(obj, depth=0, maxitems=3):
    """压缩打印，避免一次吐几万字符。"""
    pad = "  " * depth
    if isinstance(obj, dict):
        for k, v in list(obj.items())[:28]:
            if isinstance(v, (dict, list)):
                print(f"{pad}{k}:")
                brief(v, depth + 1, maxitems)
            else:
                s = str(v)
                print(f"{pad}{k}: {s[:120]}")
    elif isinstance(obj, list):
        print(f"{pad}[{len(obj)} items]")
        for it in obj[:maxitems]:
            brief(it, depth + 1, maxitems)
            print(f"{pad}---")


if __name__ == "__main__":
    name = sys.argv[1]
    args = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
    out = call(name, args)
    pathlib.Path(CACHE / f"resp_{name}.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2))
    print(f"### {name} {args}")
    brief(out, maxitems=int(sys.argv[3]) if len(sys.argv) > 3 else 3)
