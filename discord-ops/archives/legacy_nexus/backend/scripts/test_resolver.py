import sys
import unittest
from pathlib import Path

# Add repo root to path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(REPO_ROOT))

from backend.patcher.resolver import CircularDependencyError, MissingDependencyError, PatchResolver


class TestPatchResolver(unittest.TestCase):
    def test_simple_order(self):
        manifest = [{"id": "A", "enabled": True}, {"id": "B", "dependencies": ["A"], "enabled": True}]
        resolver = PatchResolver(manifest)
        sorted_patches = resolver.resolve()
        ids = [p["id"] for p in sorted_patches]
        self.assertEqual(ids, ["A", "B"])

    def test_cycle_detection(self):
        manifest = [{"id": "A", "dependencies": ["B"]}, {"id": "B", "dependencies": ["A"]}]
        resolver = PatchResolver(manifest)
        with self.assertRaises(CircularDependencyError):
            resolver.resolve()

    def test_missing_dep(self):
        manifest = [{"id": "A", "dependencies": ["MISSING"]}]
        resolver = PatchResolver(manifest)
        with self.assertRaises(MissingDependencyError):
            resolver.resolve()

    def test_auto_disable(self):
        manifest = [{"id": "A", "enabled": False}, {"id": "B", "dependencies": ["A"], "enabled": True}]
        resolver = PatchResolver(manifest)
        sorted_patches = resolver.resolve()
        final = resolver.validate_enabled_chain(sorted_patches)

        # B should be dropped because A is disabled
        self.assertEqual(len(final), 0)


if __name__ == "__main__":
    unittest.main()
