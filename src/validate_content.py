#!/usr/bin/env python3
"""校验八卦食帖、局部供应变体及其 MCP 快照覆盖声明。"""
import collections
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

EXPECTED_VARIANTS = {
    "qian": {
        "main": "芝士安格斯厚牛堡",
        "companions": ["薯条", "可乐"],
        "fallback": {"main": "巨无霸", "companions": ["薯条", "可乐"]},
    },
    "kan": {
        "main": "培根安格斯厚牛堡",
        "companions": ["麦辣鸡翅", "可乐"],
        "fallback": {"main": "双层吉士汉堡", "companions": ["麦辣鸡翅", "可乐"]},
    },
}
VARIANT_NOTE = "部分门店供应，缺货时按下方食帖替换。"


def _item_counts(menus):
    presence = {slot: collections.defaultdict(set) for slot in ("morning", "main")}
    valid = {slot: set() for slot in presence}
    if not isinstance(menus, dict):
        return presence, valid
    for city, record in menus.items():
        if not isinstance(record, dict) or not isinstance(record.get("slots"), dict):
            continue
        for slot in presence:
            items = record["slots"].get(slot)
            if not isinstance(items, list) or not items:
                continue
            valid[slot].add(city)
            for item in items:
                if isinstance(item, dict) and isinstance(item.get("name"), str) and item["name"]:
                    presence[slot][item["name"]].add(city)
    return presence, valid


def _validate_meal(meal, label, slot, presence, valid, errors, *, partial_main=False):
    if not isinstance(meal, dict):
        errors.append(f"{label}: 食帖必须是对象")
        return
    required = {"main", "companions", "fallback"}
    if required - set(meal):
        errors.append(f"{label}: 缺字段 {sorted(required - set(meal))}")
        return

    if not isinstance(meal["main"], str) or not meal["main"].strip():
        errors.append(f"{label}: 主食名称无效")
    elif "当季" not in meal["main"]:
        matches = presence[slot].get(meal["main"], set())
        if partial_main:
            if not matches:
                errors.append(f"{label}: 主食「{meal['main']}」没有菜单快照样本")
        else:
            missing = valid[slot] - matches
            if missing:
                errors.append(f"{label}: 主食「{meal['main']}」在 {len(missing)} 家有效门店中缺失")

    if not isinstance(meal["companions"], list) or len(meal["companions"]) != 2:
        errors.append(f"{label}: 配餐必须恰好两项")
    else:
        for name in meal["companions"]:
            _validate_full_coverage(name, f"{label} 配餐", slot, presence, valid, errors)

    fallback = meal["fallback"]
    if not isinstance(fallback, dict) or {"main", "companions"} - set(fallback):
        errors.append(f"{label}: 替换食帖不完整")
        return
    _validate_full_coverage(fallback["main"], f"{label} 替换主食", slot, presence, valid, errors)
    if not isinstance(fallback["companions"], list) or len(fallback["companions"]) != 2:
        errors.append(f"{label}: 替换食帖配餐必须恰好两项")
    else:
        for name in fallback["companions"]:
            _validate_full_coverage(name, f"{label} 替换配餐", slot, presence, valid, errors)


def _validate_full_coverage(name, label, slot, presence, valid, errors):
    if not isinstance(name, str) or not name.strip():
        errors.append(f"{label}: 餐品名称无效")
        return
    if "当季" in name:
        return
    missing = valid[slot] - presence[slot].get(name, set())
    if missing:
        errors.append(f"{label}「{name}」在 {len(missing)} 家有效门店中缺失")


def validate_content(data, menus):
    errors = []
    if not isinstance(data, dict):
        return ["内容数据必须是对象"], {"morning": set(), "main": set()}, collections.Counter(), 0
    if not isinstance(menus, dict):
        menus = {}

    gua = data.get("gua", [])
    if not isinstance(gua, list) or len(gua) != 8:
        errors.append(f"卦象数量应为 8，实际 {len(gua) if isinstance(gua, list) else '无效'}")
        gua = gua if isinstance(gua, list) else []
    if "fortuneScale" in data:
        errors.append("已取消运势档位，fortuneScale 应删除")

    needed = {"id", "symbol", "name", "image", "line", "taste", "breakfast", "all_day"}
    presence, valid = _item_counts(menus)
    for slot in valid:
        if not valid[slot]:
            errors.append(f"{slot}: 没有有效门店样本，无法核对餐品")

    seen_ids = set()
    variant_count = 0
    tastes = collections.Counter()
    meta = data.get("meta") if isinstance(data.get("meta"), dict) else {}
    snapshot_date = meta.get("collectedOn")
    for gua_item in gua:
        if not isinstance(gua_item, dict):
            errors.append("卦象条目必须是对象")
            continue
        label = gua_item.get("name", "?")
        if needed - set(gua_item):
            errors.append(f"{label}: 缺字段 {sorted(needed - set(gua_item))}")
        if "fortune" in gua_item:
            errors.append(f"{label}: fortune 字段已取消，应改用 taste")
        if gua_item.get("id") in seen_ids:
            errors.append(f"{label}: id 重复")
        seen_ids.add(gua_item.get("id"))
        expected_taste = str(gua_item.get("image", "")).rsplit("·", 1)[-1].strip()
        if not isinstance(gua_item.get("taste"), str) or gua_item["taste"] != expected_taste:
            errors.append(f"{label}: taste 必须等于 image 中点号后的口味标签「{expected_taste}」")
        tastes[gua_item.get("taste", "未知")] += 1

        _validate_meal(gua_item.get("breakfast"), f"{label}/breakfast", "morning",
                       presence, valid, errors)
        _validate_meal(gua_item.get("all_day"), f"{label}/all_day", "main",
                       presence, valid, errors)

        variants = gua_item.get("all_day", {}).get("variants", []) \
            if isinstance(gua_item.get("all_day"), dict) else []
        expected = EXPECTED_VARIANTS.get(gua_item.get("id"))
        if expected is None:
            if variants:
                errors.append(f"{label}: 不支持为该卦添加正餐变体")
            continue
        if not isinstance(variants, list) or len(variants) != 1:
            errors.append(f"{label}: 必须恰有一个经过核验的正餐变体")
            continue
        variant_count += len(variants)
        variant = variants[0]
        if not isinstance(variant, dict):
            errors.append(f"{label}: 变体必须是对象")
            continue
        if any(variant.get(key) != value for key, value in expected.items()):
            errors.append(f"{label}: 变体食帖内容与已核验版本不一致")
        _validate_meal(variant, f"{label}/all_day/variant", "main",
                       presence, valid, errors, partial_main=True)
        if variant.get("availabilityNote") != VARIANT_NOTE:
            errors.append(f"{label}: 变体必须说明部分门店供应和缺货替换方式")

        coverage = variant.get("sampleCoverage")
        if not isinstance(coverage, dict):
            errors.append(f"{label}: 变体缺少 sampleCoverage")
            continue
        actual_matches = len(presence["main"].get(variant.get("main"), set()))
        if type(coverage.get("matchingStores")) is not int or coverage["matchingStores"] != actual_matches:
            errors.append(f"{label}: matchingStores 与菜单快照不符（实际 {actual_matches}）")
        if type(coverage.get("sampleStores")) is not int or coverage["sampleStores"] != len(valid["main"]):
            errors.append(f"{label}: sampleStores 与有效正餐样本数不符（实际 {len(valid['main'])}）")
        if coverage.get("snapshotDate") != snapshot_date:
            errors.append(f"{label}: snapshotDate 与菜单快照日期不符（实际 {snapshot_date}）")

    for required_id in EXPECTED_VARIANTS:
        if required_id not in seen_ids:
            errors.append(f"缺少要求的菜单变体卦象：{required_id}")

    return errors, valid, tastes, variant_count


def main():
    data = json.loads((ROOT / "web" / "gua-matrix.json").read_text(encoding="utf-8"))
    menus = json.loads((ROOT / "data" / "menus.json").read_text(encoding="utf-8"))
    errors, valid, tastes, variant_count = validate_content(data, menus)
    gua_count = len(data.get("gua", [])) if isinstance(data.get("gua"), list) else 0
    base_count = gua_count * 2
    print(f"卦象 {gua_count} 个 · 基础食帖 {base_count} 份 · 菜单变体 {variant_count} 份 · 可出食帖 {base_count + variant_count} 份")
    print(f"有效门店：早市 {len(valid['morning'])} 家，正餐 {len(valid['main'])} 家")
    print("口味标签：" + " / ".join(f"{name} {count}" for name, count in tastes.items()))
    if errors:
        print("\n校验失败：")
        for error in errors:
            print(" -", error)
        return 1
    print("校验通过：16 份基础食帖覆盖全部有效样本；2 个变体的部分供应率、配餐与替换食帖均与快照相符。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
