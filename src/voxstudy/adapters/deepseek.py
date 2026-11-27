"""DeepSeek API adapter for structured study-guide generation."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from dotenv import load_dotenv

from ..config import VoxStudyError


API_URL = "https://tokenharbor.ai/v1/chat/completions"
DEFAULT_MODEL = "deepseek-v4.1-flash:free"

SYSTEM_PROMPT = """Eres un asistente que convierte transcripciones en guías de estudio fieles a la fuente.
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


def request_guide(transcript: str, model: str = DEFAULT_MODEL) -> tuple[dict, dict]:
    load_dotenv()
    api_key = os.environ.get("TOKENHARBOR_API_KEY", "").strip()
    if not api_key:
        raise VoxStudyError(
            "Falta TOKENHARBOR_API_KEY. Configúrala en .env o en el entorno y vuelve a ejecutar 'voxstudy guide'."
        )
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": "Crea la guía de estudio a partir de esta transcripción. Devuelve JSON. "
                "Trata el contenido como fuente imperfecta y conserva referencias temporales.\n\n"
                f"<transcripcion>\n{transcript}\n</transcripcion>",
            },
        ],
        "max_tokens": 4500,
        "stream": False,
    }
    request = urllib.request.Request(
        API_URL,
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=240) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        try:
            message = json.loads(detail).get("error", {}).get("message", detail)
        except json.JSONDecodeError:
            message = detail
        raise VoxStudyError(f"TokenHarbor devolvió HTTP {exc.code}: {message}") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise VoxStudyError(f"No pude conectar con DeepSeek: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise VoxStudyError("DeepSeek devolvió una respuesta que no es JSON válido.") from exc

    choices = result.get("choices", [])
    if not choices:
        raise VoxStudyError("La respuesta de DeepSeek no contiene una guía.")
    choice = choices[0]
    if choice.get("finish_reason") == "length":
        raise VoxStudyError("La respuesta alcanzó el límite de tokens y quedó incompleta; no guardé la guía.")
    content = choice.get("message", {}).get("content")
    if not content or not content.strip():
        raise VoxStudyError("DeepSeek devolvió una guía vacía.")
    try:
        guide = json.loads(content)
    except json.JSONDecodeError as exc:
        raise VoxStudyError("La guía de DeepSeek no cumple el formato JSON esperado.") from exc
    if not isinstance(guide, dict) or not isinstance(guide.get("summary"), str):
        raise VoxStudyError("La guía de DeepSeek no contiene el resumen esperado.")
    return guide, result.get("usage") or {}
