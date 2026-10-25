"""Run the real validator against isolated snapshots; never change the source data."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]

class ContentValidationTests(unittest.TestCase):
    def validate(self, menus, data=None):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for folder in ("src", "web", "data"):
                (root / folder).mkdir()
            shutil.copyfile(ROOT / "src/validate_content.py", root / "src/validate_content.py")
            if data is None:
                data = json.loads((ROOT / "web/gua-matrix.json").read_text(encoding="utf-8"))
            (root / "web/gua-matrix.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            (root / "data/menus.json").write_text(json.dumps(menus), encoding="utf-8")
            return subprocess.run([sys.executable, str(root / "src/validate_content.py")], capture_output=True, text=True)

    def test_current_snapshot_and_two_partial_variants_pass(self):
        menus = json.loads((ROOT / "data/menus.json").read_text(encoding="utf-8"))
        result = self.validate(menus)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("菜单变体 2 份 · 可出食帖 18 份", result.stdout)
        self.assertIn("校验通过", result.stdout)

    def test_empty_snapshot_fails(self):
        result = self.validate({})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("没有有效门店样本", result.stdout)

    def test_missing_breakfast_samples_fail(self):
        menus = json.loads((ROOT / "data/menus.json").read_text())
        for record in menus.values():
            record["slots"]["morning"] = []
        result = self.validate(menus)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("morning: 没有有效门店样本", result.stdout)

    def test_unknown_variant_main_fails(self):
        menus = json.loads((ROOT / "data/menus.json").read_text(encoding="utf-8"))
        data = json.loads((ROOT / "web/gua-matrix.json").read_text(encoding="utf-8"))
        qian = next(item for item in data["gua"] if item["id"] == "qian")
        qian["all_day"]["variants"][0]["main"] = "不存在的厚牛堡"
        result = self.validate(menus, data)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("没有菜单快照样本", result.stdout)

    def test_falsified_variant_coverage_fails(self):
        menus = json.loads((ROOT / "data/menus.json").read_text(encoding="utf-8"))
        data = json.loads((ROOT / "web/gua-matrix.json").read_text(encoding="utf-8"))
        qian = next(item for item in data["gua"] if item["id"] == "qian")
        qian["all_day"]["variants"][0]["sampleCoverage"]["matchingStores"] = 11
        result = self.validate(menus, data)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("matchingStores 与菜单快照不符（实际 10）", result.stdout)

    def test_partial_coverage_fallback_is_rejected(self):
        menus = json.loads((ROOT / "data/menus.json").read_text(encoding="utf-8"))
        data = json.loads((ROOT / "web/gua-matrix.json").read_text(encoding="utf-8"))
        qian = next(item for item in data["gua"] if item["id"] == "qian")
        variant = qian["all_day"]["variants"][0]
        variant["fallback"] = {"main": variant["main"], "companions": variant["companions"]}
        result = self.validate(menus, data)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("替换主食「芝士安格斯厚牛堡」在 1 家有效门店中缺失", result.stdout)

if __name__ == "__main__":
    unittest.main()
