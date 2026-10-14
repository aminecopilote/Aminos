import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class PackagingTests(unittest.TestCase):
    def test_every_subpackage_is_shipped(self):
        """A forgotten sub-package makes the installed app crash with ModuleNotFoundError (it happened with aminos.saas)."""
        cfg = tomllib.loads((ROOT / "pyproject.toml").read_text())["tool"]["setuptools"]
        found = cfg.get("packages", {})
        if isinstance(found, dict):  # packages.find with include patterns
            self.assertEqual(found["find"]["include"], ["aminos*"])
        else:
            for init in (ROOT / "aminos").rglob("__init__.py"):
                self.assertIn(".".join(init.relative_to(ROOT).parent.parts), found)


if __name__ == "__main__":
    unittest.main()
