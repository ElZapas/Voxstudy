from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from voxstudy.adapters.obsidian import save_study_guide
from voxstudy.models import AppConfig


class GuideSavingTests(unittest.TestCase):
    def test_saves_guide_and_only_links_existing_indexed_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            vault = Path(temporary)
            source_folder = vault / "Transcripciones"
            source_folder.mkdir()
            source = source_folder / "clase.md"
            source.write_text("# Clase\n\nTranscripción.", encoding="utf-8")
            related = vault / "Conceptos" / "Historia" / "Republica.md"
            related.parent.mkdir(parents=True)
            related.write_text("# República romana", encoding="utf-8")
            config = AppConfig(vault, Path("Transcripciones"), Path("Guías"))
            guide = {
                "title": "Guía de prueba",
                "summary": "Resumen breve.",
                "vault_relations": [
                    {"path": "Conceptos/Historia/Republica.md", "relation": "desarrolla", "explanation": "Conecta el tema."},
                    {"path": "../../outside.md", "relation": "falsa", "explanation": "No debe entrar."},
                ],
            }

            output = save_study_guide(
                config,
                source,
                guide,
                "deepseek-flash",
                {},
                related_note_candidates=[{
                    "path": "Conceptos/Historia/Republica.md",
                    "title": "República romana",
                }],
            )

            content = output.read_text(encoding="utf-8")
            self.assertTrue(output.is_relative_to(vault / "Guías"))
            self.assertIn("[[Conceptos/Historia/Republica|República romana]]", content)
            self.assertNotIn("outside.md", content)


if __name__ == "__main__":
    unittest.main()
