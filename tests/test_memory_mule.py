from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


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

    def test_normalization_handles_react_router_circular_references(self) -> None:
        conversation = {
            "title": "Circular shared chat",
            "messages": [{"role": "user", "content": "Still readable."}],
        }
        payload = {"conversation": conversation}
        payload["cycle"] = payload

        normalized = memory_mule.normalize(payload, "https://chatgpt.com/share/example")

        self.assertIsNotNone(normalized)
        assert normalized is not None
        self.assertEqual(normalized["title"], "Circular shared chat")
        self.assertEqual(normalized["messages"][0]["content"], "Still readable.")

    def test_react_router_stream_recovers_a_shared_conversation(self) -> None:
        packed = [
            {"_1": 2},
            "loaderData",
            {"_3": 4},
            "conversation",
            {"_5": 6, "_7": 8, "_9": 10},
            "title",
            "Latest shared chat",
            "current_node",
            "assistant-node",
            "mapping",
            {"user-node": 11, "assistant-node": 12},
            {"parent": None, "message": 13},
            {"parent": "user-node", "message": 14},
            {"author": {"role": "user"}, "content": {"parts": ["Hello"]}},
            {"author": {"role": "assistant"}, "content": {"parts": ["Hi there"]}},
        ]
        frame = json.dumps(json.dumps(packed))
        source = (
            "<script>window.__reactRouterContext.streamController.enqueue("
            + frame
            + ");</script>"
        )

        normalized = next(
            result
            for payload in memory_mule.html_payloads(source)
            if (result := memory_mule.normalize(payload, "https://chatgpt.com/share/example"))
        )

        self.assertEqual(normalized["title"], "Latest shared chat")
        self.assertEqual(
            normalized["messages"],
            [
                {"role": "user", "content": "Hello", "index": 0},
                {"role": "assistant", "content": "Hi there", "index": 1},
            ],
        )

    def test_prepare_requires_browser_confirmation_without_writing_on_read_failure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            args = type(
                "Args",
                (),
                {
                    "repo": str(repo),
                    "url": "https://chatgpt.com/share/example",
                    "output": str(repo / "normalized.json"),
                    "input": None,
                },
            )()

            with patch.object(memory_mule, "read_chatgpt_share", side_effect=RuntimeError("unreadable page")):
                result = memory_mule.prepare(args)

            self.assertEqual(result["status"], "browser_fallback_required")
            self.assertTrue(result["browser_fallback"]["requires_confirmation"])
            self.assertFalse((repo / "docs").exists())
            self.assertFalse((repo / ".project-memory").exists())
            self.assertFalse((repo / "normalized.json").exists())

    def test_share_url_validation_accepts_pasted_public_share_link(self) -> None:
        result = memory_mule.validate_share_url(
            "Please import [https://chatgpt.com/share/abc-123](https://chatgpt.com/share/abc-123)."
        )

        self.assertEqual(result["status"], "valid_share_url")
        self.assertEqual(result["url"], "https://chatgpt.com/share/abc-123")

    def test_share_url_validation_rejects_private_session_link(self) -> None:
        result = memory_mule.validate_share_url("https://chatgpt.com/c/abc-123")

        self.assertEqual(result["status"], "invalid_share_url")
        self.assertEqual(result["reason"], "not_a_share_url")


if __name__ == "__main__":
    unittest.main()
