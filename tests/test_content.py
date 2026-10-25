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
    def validate(self, menus):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for folder in ("src", "web", "data"):
                (root / folder).mkdir()
            shutil.copyfile(ROOT / "src/validate_content.py", root / "src/validate_content.py")
            shutil.copyfile(ROOT / "web/gua-matrix.json", root / "web/gua-matrix.json")
            (root / "data/menus.json").write_text(json.dumps(menus), encoding="utf-8")
            return subprocess.run([sys.executable, str(root / "src/validate_content.py")], capture_output=True, text=True)

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

if __name__ == "__main__":
    unittest.main()
