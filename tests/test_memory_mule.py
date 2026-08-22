from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
HELPER_PATH = REPOSITORY_ROOT / "chat2codex-memory-mule" / "scripts" / "memory_mule.py"
SPEC = importlib.util.spec_from_file_location("memory_mule", HELPER_PATH)
assert SPEC and SPEC.loader
memory_mule = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(memory_mule)


class MemoryMuleTests(unittest.TestCase):
    def test_skill_metadata_is_valid_and_minimal(self) -> None:
        skill = (REPOSITORY_ROOT / "chat2codex-memory-mule" / "SKILL.md").read_text(encoding="utf-8")
        self.assertTrue(skill.startswith("---\nname: chat2codex-memory-mule\ndescription:"))
        frontmatter = skill.split("---", 2)[1]
        keys = [line.split(":", 1)[0] for line in frontmatter.splitlines() if ":" in line]
        self.assertEqual(keys, ["name", "description"])

    def test_initialization_scans_existing_knowledge_and_preserves_it(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            (repo / "docs" / "adr").mkdir(parents=True)
            (repo / "README.md").write_text("# Example project\n", encoding="utf-8")
            (repo / "ROADMAP.md").write_text("# Roadmap\n", encoding="utf-8")
            (repo / "docs" / "adr" / "001-storage.md").write_text("# Storage decision\n", encoding="utf-8")

            result = memory_mule.initialize(repo, scan_sources=True)

            self.assertEqual(result["knowledge_scan"]["discovered"], 3)
            source_map_path = repo / "docs" / "project-memory" / "source-map.md"
            source_map = source_map_path.read_text(encoding="utf-8")
            self.assertIn("README.md", source_map)
            self.assertIn("ROADMAP.md", source_map)
            self.assertIn("docs/adr/001-storage.md", source_map)
            self.assertTrue((repo / "README.md").exists())
            self.assertIn(".project-memory/raw/", (repo / ".gitignore").read_text(encoding="utf-8"))

            curated = "- `README.md` — `canonical_source` for project definition."
            source_map_path.write_text(source_map.replace("_None recorded._", curated), encoding="utf-8")
            memory_mule.scan_knowledge(repo)
            self.assertIn(curated, source_map_path.read_text(encoding="utf-8"))

    def test_single_file_scan_classifies_without_moving_source(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            (repo / "notes").mkdir()
            note = repo / "notes" / "market-analysis.md"
            note.write_text("# Market analysis\n", encoding="utf-8")
            memory_mule.initialize(repo)

            result = memory_mule.scan_knowledge(repo, "notes/market-analysis.md")

            self.assertEqual(result["focus"]["suggested_category"], "Research & Analysis")
            self.assertTrue(note.exists())

    def test_normalization_and_hash_are_stable(self) -> None:
        payload = {
            "title": "Architecture discussion",
            "messages": [
                {"role": "user", "content": "Use repository-native Markdown."},
                {"role": "assistant", "content": "That preserves portability."},
            ],
        }
        url = "https://chatgpt.com/share/example"
        normalized = memory_mule.normalize(payload, url)
        self.assertIsNotNone(normalized)
        assert normalized is not None
        first = memory_mule.digest(normalized)
        second = memory_mule.digest(json.loads(json.dumps(normalized)))
        self.assertEqual(first, second)
        self.assertTrue(first.startswith("sha256:"))


if __name__ == "__main__":
    unittest.main()
