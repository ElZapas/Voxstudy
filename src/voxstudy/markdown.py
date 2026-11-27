"""Markdown rendering and filename helpers for Obsidian notes."""

from __future__ import annotations

import json
import re
import unicodedata
from datetime import datetime
from pathlib import Path

from .models import TranscriptSegment


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"[^a-z0-9]+", "-", ascii_text).strip("-") or "nota"


def timestamp(seconds: int) -> str:
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def render_transcript(title: str, monitor: str, started_at: str, segments: list[TranscriptSegment]) -> str:
    started = datetime.fromisoformat(started_at)
    body: list[str] = []
    for segment in segments:
        body.append(f"### [{timestamp(segment.start)}]\n")
        body.append(segment.text or "*(Sin voz detectada en este bloque.)*")
        body.append("")
    duration = timestamp(sum(segment.duration for segment in segments))
    return (
        "---\n"
        "type: transcription\n"
        f"title: {json.dumps(title, ensure_ascii=False)}\n"
        f"created: {started.astimezone().isoformat(timespec='minutes')}\n"
        f"audio_source: {json.dumps(monitor, ensure_ascii=False)}\n"
        "tags:\n"
        "  - transcripcion\n"
        "  - por-procesar\n"
        "---\n\n"
        f"# {title}\n\n"
        f"Duración aproximada: {duration}.\n\n"
        "## Transcripción\n\n"
        + "\n".join(body).rstrip()
        + "\n"
    )


def render_study_guide(guide: dict, source_note: Path, model: str, usage: dict) -> str:
    title = str(guide.get("title") or source_note.stem)
    source_link = f"[[{source_note.stem}]]"
    lines = [
        "---",
        "type: study-guide",
        f"title: {json.dumps(title, ensure_ascii=False)}",
        f"source: {json.dumps(source_link, ensure_ascii=False)}",
        f"model: {json.dumps(model)}",
        f"created: {datetime.now().astimezone().isoformat(timespec='minutes')}",
        f"input_tokens: {int(usage.get('prompt_tokens', 0) or 0)}",
        f"output_tokens: {int(usage.get('completion_tokens', 0) or 0)}",
        "tags:",
        "  - guia-estudio",
        "---",
        "",
        f"# {title}",
        "",
        f"> Fuente: {source_link}",
        "",
        "## Resumen",
        "",
        str(guide.get("summary", "")).strip(),
        "",
    ]
    objectives = _strings(guide.get("learning_objectives"))
    lines.extend(["## Objetivos de aprendizaje", ""])
    if objectives:
        lines.extend(f"- {item}" for item in objectives)
    else:
        lines.append("- *(Sin objetivos extraídos.)*")
    lines.append("")

    lines.extend(["## Esquema del contenido", ""])
    outline = guide.get("outline", [])
    if isinstance(outline, list) and outline:
        for item in outline:
            if not isinstance(item, dict):
                continue
            moment = str(item.get("timestamp", "")).strip()
            heading = str(item.get("heading", "Tema")).strip()
            summary = str(item.get("summary", "")).strip()
            when = f"[{moment}] " if moment else ""
            lines.append(f"- {when}**{heading}** — {summary}")
    else:
        lines.append("- *(Sin esquema extraído.)*")
    lines.append("")

    lines.extend(["## Términos clave", ""])
    terms = guide.get("key_terms", [])
    if isinstance(terms, list) and terms:
        for item in terms:
            if not isinstance(item, dict):
                continue
            name = str(item.get("term", "Término")).strip()
            definition = str(item.get("definition", "")).strip()
            importance = str(item.get("importance", "media")).strip()
            moment = str(item.get("timestamp", "")).strip()
            where = f" · [{moment}]" if moment else ""
            lines.append(f"- **{name}** ({importance}){where}: {definition}")
    else:
        lines.append("- *(No se extrajeron términos con suficiente sustento.)*")
    lines.append("")

    lines.extend(["## Ideas principales y relaciones", ""])
    ideas = guide.get("key_ideas", [])
    if isinstance(ideas, list) and ideas:
        for item in ideas:
            if not isinstance(item, dict):
                continue
            idea = str(item.get("idea", "Idea")).strip()
            explanation = str(item.get("explanation", "")).strip()
            refs = _strings(item.get("timestamps"))
            where = f" ({', '.join(f'[{ref}]' for ref in refs)})" if refs else ""
            lines.append(f"- **{idea}**{where}: {explanation}")
    else:
        lines.append("- *(Sin ideas adicionales extraídas.)*")
    lines.append("")

    lines.extend(["## Preguntas de práctica", ""])
    questions = guide.get("exam_questions", [])
    if isinstance(questions, list) and questions:
        for index, item in enumerate(questions, start=1):
            if not isinstance(item, dict):
                continue
            question = str(item.get("question", "")).strip()
            answer = str(item.get("answer", "")).strip()
            moment = str(item.get("timestamp", "")).strip()
            where = f" (fuente: [{moment}])" if moment else ""
            lines.extend([f"{index}. **{question}**{where}", f"   - Respuesta: {answer}"])
    else:
        lines.append("- *(Sin preguntas generadas.)*")
    lines.append("")

    lines.extend(["## Pasajes para revisar", ""])
    review = guide.get("review_notes", [])
    if isinstance(review, list) and review:
        for item in review:
            if not isinstance(item, dict):
                continue
            issue = str(item.get("issue", "")).strip()
            moment = str(item.get("timestamp", "")).strip()
            when = f"[{moment}] " if moment else ""
            lines.append(f"- {when}{issue}")
    else:
        lines.append("- *(No se señalaron pasajes dudosos.)*")
    lines.extend([
        "",
        "---",
        f"Tokens reportados por la API: {int(usage.get('total_tokens', 0) or 0)}.",
        "Revisa los términos propios y las respuestas comparándolos con la transcripción.",
        "",
    ])
    return "\n".join(lines)


def _strings(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item.strip() for item in value if isinstance(item, str) and item.strip()]
