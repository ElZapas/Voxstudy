"""Default and per-user prompts used to generate study guides."""

from __future__ import annotations

from pathlib import Path

from .config import CONFIG_PATH, VoxStudyError


DEFAULT_GUIDE_SYSTEM_PROMPT = """Eres un asistente que convierte transcripciones en guías de estudio fieles a la fuente.
La transcripción puede contener errores de reconocimiento de voz: no conviertas una palabra dudosa en un hecho seguro. No añadas información externa ni inventes definiciones. Si algo no se entiende, indícalo en `review_notes` con su marca temporal.
Prioriza conceptos, términos y relaciones que podrían ser evaluados, pero preséntalos como temas importantes del contenido, nunca como predicciones seguras de un examen.
Conserva marcas de tiempo existentes en las referencias. Si no hay una marca para un dato, usa una cadena vacía.
Responde solo con un objeto JSON válido, usando exactamente esta estructura:
{
  "title": "título breve",
  "summary": "resumen de 2 a 4 frases",
  "learning_objectives": ["objetivo verificable"],
  "outline": [{"timestamp": "00:00:00", "heading": "tema", "summary": "qué explica la fuente"}],
  "key_terms": [{"term": "término", "definition": "definición según la fuente", "importance": "alta|media", "timestamp": "00:00:00"}],
  "key_ideas": [{"idea": "idea", "explanation": "explicación y relación con otras ideas", "timestamps": ["00:00:00"]}],
  "exam_questions": [{"question": "pregunta de práctica", "answer": "respuesta apoyada por la fuente", "timestamp": "00:00:00"}],
  "review_notes": [{"issue": "fragmento dudoso o insuficientemente explicado", "timestamp": "00:00:00"}]
}
Usa listas vacías cuando una sección no tenga elementos sustentados. Escribe en español."""

GUIDE_PROMPT_PATH = CONFIG_PATH.parent / "guide_prompt.md"


def load_guide_system_prompt() -> str:
    """Load the user's prompt, falling back to the built-in default."""
    try:
        prompt = GUIDE_PROMPT_PATH.read_text(encoding="utf-8")
    except FileNotFoundError:
        return DEFAULT_GUIDE_SYSTEM_PROMPT
    except OSError as exc:
        raise VoxStudyError(f"No pude leer el prompt personalizado: {exc}") from exc
    if not prompt.strip():
        raise VoxStudyError(
            f"El prompt personalizado está vacío: {GUIDE_PROMPT_PATH}. "
            "Restáuralo desde la pantalla de prompts."
        )
    return prompt.strip()


def save_guide_system_prompt(prompt: str) -> Path:
    """Save the user's prompt in the local VoxStudy configuration directory."""
    if not prompt.strip():
        raise VoxStudyError("El prompt no puede quedar vacío.")
    path = GUIDE_PROMPT_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    try:
        temporary.write_text(prompt.rstrip() + "\n", encoding="utf-8")
        temporary.replace(path)
    except OSError as exc:
        temporary.unlink(missing_ok=True)
        raise VoxStudyError(f"No pude guardar el prompt personalizado: {exc}") from exc
    return path


def reset_guide_system_prompt() -> None:
    """Remove the override so VoxStudy uses the built-in prompt again."""
    try:
        GUIDE_PROMPT_PATH.unlink(missing_ok=True)
    except OSError as exc:
        raise VoxStudyError(f"No pude restaurar el prompt predeterminado: {exc}") from exc
