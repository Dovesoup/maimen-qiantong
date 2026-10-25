#!/usr/bin/env python3
"""麦当劳 MCP 只读客户端及响应解析。"""
import json
import os
import pathlib
import sys
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
CACHE = ROOT / "data" / "cache"
URL = "https://mcp.mcd.cn"


class McpError(RuntimeError):
    """MCP 调用、协议或业务响应失败。"""


def extract_json(text):
    """从纯 JSON 或 MCP 的说明文字 + ``Original Response`` 中解析 JSON。"""
    if not isinstance(text, str):
        raise McpError("MCP text response was not text")

    # 说明文本可能含示例 JSON；有标记时只解析标记之后的真实响应。
    marker = "## Original Response"
    if marker in text:
        text = text.split(marker, 1)[1]

    decoder = json.JSONDecoder()
    for index, char in enumerate(text):
        if char not in "[{":
            continue
        try:
            value, _ = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue
        return value
    raise McpError("MCP response did not contain valid JSON")


def _error_message(payload):
    """识别明确的通用错误字段，不把普通业务 code 当作错误码。"""
    if not isinstance(payload, dict):
        return None
    if payload.get("success") is False:
        return "success=false"
    if payload.get("error") not in (None, "", False, {}, []):
        return "error field present"
    for key in ("errCode", "errcode", "errorCode", "error_code"):
        code = payload.get(key)
        if code not in (None, "", 0, "0", False):
            return f"{key}={code}"
    # Several APIs use generic code/message pairs for failures. Only treat
    # this as an error when no normal data payload is present.
    if "data" not in payload and "code" in payload and any(
            key in payload for key in ("message", "msg")):
        return "code/message response without data"
    return None


def _parse_response(body):
    try:
        response = json.loads(body)
    except (TypeError, json.JSONDecodeError) as exc:
        raise McpError("MCP returned invalid JSON-RPC response") from exc
    if not isinstance(response, dict):
        raise McpError("MCP returned an invalid JSON-RPC response")

    if response.get("error") is not None:
        error = response["error"]
        code = error.get("code") if isinstance(error, dict) else None
        suffix = f" (code {code})" if code is not None else ""
        raise McpError(f"MCP JSON-RPC error{suffix}")

    result = response.get("result")
    if not isinstance(result, dict):
        raise McpError("MCP response did not include a result")
    if result.get("isError") is True:
        raise McpError("MCP tool reported an error")

    structured = result.get("structuredContent")
    if isinstance(structured, (dict, list)):
        payload = structured
    else:
        blocks = result.get("content") or []
        text_blocks = [block.get("text", "") for block in blocks
                       if isinstance(block, dict) and block.get("type") == "text"]
        if not text_blocks:
            raise McpError("MCP response contained no structured content")
        payload = extract_json("\n".join(text_blocks))

    message = _error_message(payload)
    if message:
        raise McpError(f"MCP tool returned an application error ({message})")
    return payload


def bigmac_price(meal_obj):
    """从 query-meals 的 data.meals 里找巨无霸（单品，非套餐）。"""
    hits = []
    meals = (meal_obj.get("data") or {}).get("meals") or {}
    for code, meal in meals.items():
        if not isinstance(meal, dict):
            continue
        name = meal.get("name") or ""
        if "巨无霸" not in name:
            continue
        hits.append({
            "code": code,
            "name": name.replace("\n", " "),
            "currentPrice": meal.get("currentPrice"),
            "originalPrice": meal.get("originalPrice"),
            "discountType": meal.get("discountType"),
        })
    return hits


def call(name, args, timeout=45):
    """调用 MCP 工具并解析本次 HTTP 响应；不读取历史响应缓存。"""
    token = os.environ.get("MCD_MCP_TOKEN", "").strip()
    if not token:
        raise McpError(
            "缺少 MCD_MCP_TOKEN。请先在 https://open.mcd.cn 激活 MCP Token，"
            "再通过环境变量 MCD_MCP_TOKEN 提供。"
        )

    body = json.dumps({
        "jsonrpc": "2.0", "id": 1, "method": "tools/call",
        "params": {"name": name, "arguments": args},
    }).encode()
    req = urllib.request.Request(URL, data=body, method="POST", headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    })
    with urllib.request.urlopen(req, timeout=timeout) as response:
        raw = response.read().decode("utf-8", "replace")

    if raw.startswith(("event:", "data:")):
        data_lines = [line[5:].strip() for line in raw.splitlines()
                      if line.startswith("data:")]
        if not data_lines:
            raise McpError("MCP returned an empty event stream")
        raw = data_lines[-1]
    return _parse_response(raw)


def brief(obj, depth=0, maxitems=3):
    """压缩打印，避免一次吐几万字符。"""
    pad = "  " * depth
    if isinstance(obj, dict):
        for key, value in list(obj.items())[:28]:
            if isinstance(value, (dict, list)):
                print(f"{pad}{key}:")
                brief(value, depth + 1, maxitems)
            else:
                print(f"{pad}{key}: {str(value)[:120]}")
    elif isinstance(obj, list):
        print(f"{pad}[{len(obj)} items]")
        for item in obj[:maxitems]:
            brief(item, depth + 1, maxitems)
            print(f"{pad}---")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("用法：python src/mcp_client.py TOOL_NAME [JSON_ARGUMENTS] [MAX_ITEMS]")
    name = sys.argv[1]
    args = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
    out = call(name, args)
    CACHE.mkdir(parents=True, exist_ok=True)
    (CACHE / f"resp_{name}.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2))
    print(f"### {name} {args}")
    brief(out, maxitems=int(sys.argv[3]) if len(sys.argv) > 3 else 3)
