from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from voxstudy.application.vault_index import build_vault_index, rank_related_notes


class VaultIndexTests(unittest.TestCase):
    def test_index_reads_metadata_and_skips_obsidian_internal_directories(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            vault = Path(temporary)
            note = vault / "Historia" / "Republica.md"
            note.parent.mkdir()
            note.write_text(
                "---\n"
                'title: "República romana"\n'
                "aliases:\n  - Roma republicana\n"
                "tags: [historia, política]\n"
                'summary: "Instituciones políticas de Roma."\n'
                "type: concepto\n"
                "---\n"
                "# República romana\n\nEl senado y los magistrados organizaban el gobierno.",
                encoding="utf-8",
            )
            for directory in (".obsidian", ".trash", ".git"):
                internal = vault / directory
                internal.mkdir()
                (internal / "ignored.md").write_text("secreto", encoding="utf-8")

            notes = build_vault_index(vault)

        self.assertEqual(len(notes), 1)
        self.assertEqual(notes[0].path, "Historia/Republica.md")
        self.assertEqual(notes[0].title, "República romana")
        self.assertEqual(notes[0].aliases, ("Roma republicana",))
        self.assertEqual(notes[0].tags, ("historia", "política"))
        self.assertEqual(notes[0].summary, "Instituciones políticas de Roma.")
        self.assertIn("senado", dict(notes[0].search_terms))

    def test_ranker_favors_relevant_title_and_honors_exclusions_and_limit(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            vault = Path(temporary)
            (vault / "a.md").write_text(
                "---\ntitle: República romana\naliases: [Roma antigua]\n---\n"
                "El senado y los magistrados organizaban el gobierno.",
                encoding="utf-8",
            )
            (vault / "b.md").write_text(
                "---\ntitle: Pintura renacentista\n---\n"
                "Técnicas de perspectiva y pigmentos.",
                encoding="utf-8",
            )
            notes = build_vault_index(vault)

        ranked = rank_related_notes("república romana y senado", notes, limit=1)
        self.assertEqual(len(ranked), 1)
        self.assertEqual(ranked[0].note.title, "República romana")
        self.assertIn("republica", ranked[0].matched_terms)

        excluded = rank_related_notes(
            "república romana y senado",
            notes,
            exclude_paths={ranked[0].note.path},
        )
        self.assertEqual(excluded, [])


if __name__ == "__main__":
    unittest.main()
