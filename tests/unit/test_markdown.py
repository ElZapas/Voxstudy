from __future__ import annotations

import unittest
from pathlib import Path

from voxstudy.markdown import render_study_guide


class StudyGuideMarkdownTests(unittest.TestCase):
    def test_renders_study_sections_visual_map_and_only_allowed_links(self) -> None:
        guide = {
            "title": "República romana",
            "summary": "La clase explica sus instituciones.",
            "summary_levels": {
                "one_sentence": "Roma organizó un gobierno republicano.",
                "paragraph": "La clase describe instituciones y responsabilidades.",
                "by_topic": [{"topic": "Senado", "summary": "Aconsejaba a los magistrados."}],
            },
            "learning_objectives": ["Explicar la función del Senado."],
            "guiding_questions": ["¿Qué función tenía el Senado?"],
            "outline": [{
                "heading": "Instituciones",
                "summary": "El gobierno distribuía responsabilidades.",
                "examples": ["El Senado aconsejaba a los magistrados."],
            }],
            "key_terms": [{
                "term": "Senado", "definition": "Consejo político", "importance": "alta",
                "contrast": "Se diferencia de los magistrados.",
            }],
            "key_ideas": [{"idea": "Distribución de funciones", "explanation": "El Senado aconseja y los magistrados ejecutan."}],
            "concept_map": {
                "nodes": [{"id": "A", "label": "Senado"}, {"id": "B", "label": "Magistrados"}],
                "edges": [{"source": "A", "target": "B", "relation": "aconseja", "explanation": "La clase explica esta relación."}],
            },
            "vault_relations": [
                {"path": "Historia/Republica.md", "title": "título inventado", "relation": "desarrolla", "explanation": "Amplía el contexto."},
                {"path": "Fuera/NoExiste.md", "title": "Ajena", "relation": "relaciona", "explanation": "No debe enlazarse."},
            ],
            "common_confusions": [{"confusion": "Senado y magistrados", "clarification": "Tenían funciones distintas."}],
            "exam_questions": [{"question": "¿Qué hacía el Senado?", "answer": "Aconsejaba a los magistrados."}],
            "flashcards": [{"question": "Función del Senado", "answer": "Aconsejar a los magistrados."}],
            "review_notes": [{"issue": "No se entiende el nombre de una institución."}],
        }

        markdown = render_study_guide(
            guide,
            Path("transcripciones/clase.md"),
            "deepseek-flash",
            {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
            {"Historia/Republica.md": "República romana"},
        )

        self.assertIn("## Preguntas guía", markdown)
        self.assertIn("## Mapa conceptual", markdown)
        self.assertIn("flowchart TD", markdown)
        self.assertIn("## Desarrollo", markdown)
        self.assertIn("## Palabras clave", markdown)
        self.assertIn("## Autoevaluación", markdown)
        self.assertIn("#flashcards", markdown)
        self.assertIn("[[Historia/Republica|República romana]]", markdown)
        self.assertNotIn("título inventado", markdown)
        self.assertNotIn("Fuera/NoExiste", markdown)
        self.assertNotIn("00:00:", markdown)

    def test_drops_invalid_mermaid_edges(self) -> None:
        markdown = render_study_guide(
            {
                "title": "Prueba",
                "summary": "Resumen.",
                "concept_map": {
                    "nodes": [{"id": "A", "label": "A"}],
                    "edges": [{"source": "A", "target": "B", "relation": "causa"}],
                },
            },
            Path("source.md"),
            "model",
            {},
        )
        self.assertNotIn("```mermaid", markdown)


if __name__ == "__main__":
    unittest.main()
