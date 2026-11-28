"""Markdown rendering and filename helpers for Obsidian notes."""

from __future__ import annotations

import html
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


def render_study_guide(
    guide: dict,
    source_note: Path,
    model: str,
    usage: dict,
    allowed_related_notes: dict[str, str] | None = None,
) -> str:
    title = _clean_text(guide.get("title") or source_note.stem)
    source_link = f"[[{source_note.stem}]]"
    summary_levels = guide.get("summary_levels")
    if not isinstance(summary_levels, dict):
        summary_levels = {}
    one_sentence = _clean_text(summary_levels.get("one_sentence")) or _clean_text(
        guide.get("summary")
    )
    paragraph = _clean_text(summary_levels.get("paragraph")) or _clean_text(
        guide.get("summary")
    )
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
        f"**En una frase:** {one_sentence}" if one_sentence else "",
        "",
        paragraph,
        "",
    ]
    by_topic = summary_levels.get("by_topic", [])
    if isinstance(by_topic, list) and by_topic:
        lines.extend(["### Síntesis por tema", ""])
        for item in by_topic:
            if isinstance(item, dict):
                topic = _clean_text(item.get("topic"))
                summary = _clean_text(item.get("summary"))
                if topic and summary:
                    lines.append(f"- **{topic}:** {summary}")
        lines.append("")

    guiding_questions = _strings(guide.get("guiding_questions"))
    if guiding_questions:
        lines.extend(["## Preguntas guía", "", *(f"- {item}" for item in guiding_questions), ""])

    objectives = _strings(guide.get("learning_objectives"))
    lines.extend(["## Objetivos de aprendizaje", ""])
    if objectives:
        lines.extend(f"- {item}" for item in objectives)
    else:
        lines.append("- *(Sin objetivos extraídos.)*")
    lines.append("")

    concept_map = _render_concept_map(guide.get("concept_map"))
    if concept_map:
        lines.extend(["## Mapa conceptual", "", *concept_map, ""])

    lines.extend(["## Desarrollo", ""])
    outline = guide.get("outline", [])
    if isinstance(outline, list) and outline:
        for item in outline:
            if not isinstance(item, dict):
                continue
            heading = _clean_text(item.get("heading")) or "Tema"
            summary = _clean_text(item.get("summary"))
            lines.extend([f"### {heading}", ""])
            if summary:
                lines.extend([summary, ""])
            for example in _strings(item.get("examples")):
                lines.extend(_callout("example", "Ejemplo de la fuente", example))
                lines.append("")
    else:
        lines.extend(["*(No se pudo organizar el contenido en temas.)*", ""])

    ideas = guide.get("key_ideas", [])
    lines.extend(["## Conectores de ideas", ""])
    rendered_ideas = False
    if isinstance(ideas, list):
        for item in ideas:
            if not isinstance(item, dict):
                continue
            idea = _clean_text(item.get("idea"))
            explanation = _clean_text(item.get("explanation"))
            if idea and explanation:
                lines.extend(_callout("important", idea, explanation))
                lines.append("")
                rendered_ideas = True
    if not rendered_ideas:
        lines.extend(["*(La fuente no presenta conexiones adicionales claras.)*", ""])

    lines.extend(["## Palabras clave", "", "| Término | Definición según la fuente | Importancia | Contraste |", "| --- | --- | --- | --- |"])
    terms = guide.get("key_terms", [])
    if isinstance(terms, list) and terms:
        for item in terms:
            if not isinstance(item, dict):
                continue
            name = _table_cell(item.get("term"))
            definition = _table_cell(item.get("definition"))
            importance = _table_cell(item.get("importance") or "media")
            contrast = _table_cell(item.get("contrast") or "—")
            if name:
                lines.append(f"| **{name}** | {definition or '—'} | {importance} | {contrast} |")
    else:
        lines.append("| — | No se extrajeron términos con suficiente sustento. | — | — |")
    lines.append("")

    vault_relations = _render_vault_relations(
        guide.get("vault_relations"), allowed_related_notes or {}
    )
    if vault_relations:
        lines.extend(["## Relaciones con la bóveda", "", *vault_relations, ""])

    confusions = guide.get("common_confusions", [])
    if isinstance(confusions, list) and confusions:
        lines.extend(["## Errores y confusiones frecuentes", ""])
        for item in confusions:
            if not isinstance(item, dict):
                continue
            confusion = _clean_text(item.get("confusion"))
            clarification = _clean_text(item.get("clarification"))
            if confusion and clarification:
                lines.extend([f"- **{confusion}:** {clarification}"])
        lines.append("")

    lines.extend(["## Autoevaluación", ""])
    questions = guide.get("exam_questions", [])
    if isinstance(questions, list) and questions:
        for item in questions:
            if not isinstance(item, dict):
                continue
            question = _clean_text(item.get("question"))
            answer = _clean_text(item.get("answer"))
            if question and answer:
                lines.extend(_callout("question", question, answer))
    else:
        lines.append("*(No se generaron preguntas de práctica.)*")
    lines.append("")

    flashcards = guide.get("flashcards", [])
    if isinstance(flashcards, list) and flashcards:
        lines.extend(["## Tarjetas", "", "#flashcards"])
        for item in flashcards:
            if not isinstance(item, dict):
                continue
            question = _clean_text(item.get("question"))
            answer = _clean_text(item.get("answer"))
            if question and answer:
                lines.append(f"{question} :: {answer}")
        lines.append("")

    lines.extend(["## Por verificar", ""])
    review = guide.get("review_notes", [])
    if isinstance(review, list) and review:
        for item in review:
            if not isinstance(item, dict):
                continue
            issue = _clean_text(item.get("issue"))
            if issue:
                lines.extend(_callout("warning", "Revisar transcripción", issue))
    else:
        lines.append("*(No se señalaron dudas importantes.)*")
    lines.extend([
        "",
        "---",
        f"Tokens reportados por la API: {int(usage.get('total_tokens', 0) or 0)}.",
        "Revisa los términos propios y las respuestas comparándolos con la transcripción.",
        "",
    ])
    return "\n".join(lines)


def _render_concept_map(value: object) -> list[str]:
    if not isinstance(value, dict):
        return []
    raw_nodes = value.get("nodes", [])
    raw_edges = value.get("edges", [])
    if not isinstance(raw_nodes, list) or not isinstance(raw_edges, list):
        return []

    nodes: dict[str, str] = {}
    for item in raw_nodes[:12]:
        if not isinstance(item, dict):
            continue
        identifier = str(item.get("id", ""))
        label = _clean_text(item.get("label"))
        if re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", identifier) and label:
            nodes[identifier] = _mermaid_text(label)

    edges: list[tuple[str, str, str, str]] = []
    for item in raw_edges:
        if not isinstance(item, dict):
            continue
        source = str(item.get("source", ""))
        target = str(item.get("target", ""))
        relation = _clean_text(item.get("relation"))
        explanation = _clean_text(item.get("explanation"))
        if source in nodes and target in nodes and source != target:
            edges.append((source, target, _mermaid_text(relation), explanation))
    if not nodes or not edges:
        return []

    lines = ["```mermaid", "flowchart TD"]
    lines.extend(f'    {identifier}["{label}"]' for identifier, label in nodes.items())
    lines.extend(
        f'    {source} -->|"{relation}"| {target}' if relation
        else f"    {source} --> {target}"
        for source, target, relation, _ in edges
    )
    lines.append("```")
    explanations = [
        f"- **{nodes[source]} — {relation} → {nodes[target]}:** {explanation}"
        for source, target, relation, explanation in edges
        if explanation
    ]
    if explanations:
        lines.extend(["", *explanations])
    return lines


def _render_vault_relations(value: object, allowed_notes: dict[str, str]) -> list[str]:
    if not isinstance(value, list):
        return []
    lines: list[str] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        raw_path = item.get("path")
        if not isinstance(raw_path, str) or raw_path not in allowed_notes:
            continue
        note_path = Path(raw_path)
        if note_path.is_absolute() or ".." in note_path.parts or note_path.suffix.lower() != ".md":
            continue
        if any(char in raw_path for char in "|[]#"):
            continue
        title = _clean_text(allowed_notes[raw_path])
        relation = _clean_text(item.get("relation"))
        explanation = _clean_text(item.get("explanation"))
        if not title or not explanation:
            continue
        target = note_path.with_suffix("").as_posix()
        link = f"[[{target}|{_wiki_alias(title)}]]"
        relation_text = f" — {relation}" if relation else ""
        lines.append(f"- {link}{relation_text}: {explanation}")
    return lines


def _callout(kind: str, title: str, body: str) -> list[str]:
    lines = [f"> [!{kind}]- {title}" if kind == "question" else f"> [!{kind}] {title}"]
    lines.extend(f"> {line}" if line else ">" for line in body.splitlines())
    return lines


def _clean_text(value: object) -> str:
    return re.sub(r"\s+", " ", value.strip()) if isinstance(value, str) else ""


def _table_cell(value: object) -> str:
    return _clean_text(value).replace("|", r"\|")


def _mermaid_text(value: str) -> str:
    escaped = html.escape(value.replace("`", "'"), quote=True)
    return escaped.replace("|", "&#124;")


def _wiki_alias(value: str) -> str:
    return value.replace("|", "&#124;").replace("[", "&#91;").replace("]", "&#93;")


def _strings(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item.strip() for item in value if isinstance(item, str) and item.strip()]
