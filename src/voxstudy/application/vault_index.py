"""Read-only index of Markdown notes in an Obsidian vault."""

from __future__ import annotations

import os
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass
from math import log
from pathlib import Path
from typing import Any

import yaml


_IGNORED_DIRECTORIES = {".obsidian", ".trash", ".git"}
_FRONTMATTER = re.compile(r"\A---\s*\n(.*?)\n---\s*(?:\n|\Z)", re.DOTALL)
_HEADING = re.compile(r"(?m)^#{1,6}\s+(.+?)\s*#*\s*$")
_TOKEN = re.compile(r"[\w-]+", re.UNICODE)
_FENCED_BLOCK = re.compile(r"```.*?```|~~~.*?~~~", re.DOTALL)
_STOPWORDS = frozenset(
    "a al algo algunas algunos ante asi aun bajo cada casi como con contra cual "
    "cuando de del desde donde durante e el ella ellas ellos en entre era es esa "
    "esas ese eso esos esta estaba estaban estas este esto estos fue fueron ha "
    "habia han hasta hay la las le les lo los mas me mi mientras muy nada ni no "
    "nos o otra otras otro otros para pero poco por porque que quien se sea sin "
    "sobre son su sus tambien te tiene tienen todo todos tras tu un una unas uno "
    "unos y ya the and for from with this that are was were have has into their "
    "you your not but can will its".split()
)


@dataclass(frozen=True)
class IndexedVaultNote:
    """Small, model-friendly summary of one Markdown note."""

    path: str
    title: str
    aliases: tuple[str, ...]
    tags: tuple[str, ...]
    summary: str
    headings: tuple[str, ...]
    search_terms: tuple[tuple[str, int], ...]
    note_type: str = ""


@dataclass(frozen=True)
class RelatedVaultNote:
    """A vault note ranked as a possible connection to a transcript."""

    note: IndexedVaultNote
    score: float
    matched_terms: tuple[str, ...]


def build_vault_index(vault: Path) -> list[IndexedVaultNote]:
    """Index Markdown note metadata without modifying the vault.

    Paths are stored relative to the vault so future link selection can be
    validated before VoxStudy writes a wikilink.
    """
    root = vault.expanduser().resolve()
    if not root.is_dir():
        raise NotADirectoryError(f"No existe la bóveda: {root}")

    indexed: list[IndexedVaultNote] = []
    for directory, child_directories, filenames in os.walk(root, followlinks=False):
        child_directories[:] = sorted(
            name for name in child_directories if name not in _IGNORED_DIRECTORIES
        )
        for filename in sorted(filenames):
            if Path(filename).suffix.lower() != ".md":
                continue
            path = Path(directory, filename)
            if path.is_symlink():
                continue
            try:
                resolved = path.resolve(strict=True)
                relative = resolved.relative_to(root).as_posix()
                text = resolved.read_text(encoding="utf-8")
            except (OSError, UnicodeError, ValueError):
                continue
            indexed.append(_index_note(relative, path.stem, text))

    indexed.sort(key=lambda note: (note.title.casefold(), note.path.casefold()))
    return indexed


def rank_related_notes(
    transcript: str,
    notes: list[IndexedVaultNote],
    *,
    limit: int = 12,
    exclude_paths: set[str] | None = None,
) -> list[RelatedVaultNote]:
    """Rank candidate notes with local, field-weighted BM25 scoring."""
    if not notes or limit <= 0:
        return []

    query = Counter(_tokens(transcript))
    if not query:
        return []

    documents: list[dict[str, Counter[str]]] = []
    document_lengths: dict[str, list[int]] = {
        "title": [], "aliases": [], "tags": [], "headings": [], "summary": [], "body": []
    }
    document_terms: list[set[str]] = []
    for note in notes:
        fields = {
            "title": Counter(_tokens(note.title)),
            "aliases": Counter(_tokens(" ".join(note.aliases))),
            "tags": Counter(_tokens(" ".join(note.tags))),
            "headings": Counter(_tokens(" ".join(note.headings))),
            "summary": Counter(_tokens(note.summary)),
            "body": Counter(dict(note.search_terms)),
        }
        documents.append(fields)
        document_terms.append(set().union(*(set(value) for value in fields.values())))
        for name, counts in fields.items():
            document_lengths[name].append(sum(counts.values()))

    document_frequency = Counter(
        term for terms in document_terms for term in terms
    )
    count = len(notes)
    average_lengths = {
        name: sum(lengths) / count if count else 0.0
        for name, lengths in document_lengths.items()
    }
    field_weights = {
        "title": 5.0, "aliases": 5.0, "tags": 2.5,
        "headings": 2.0, "summary": 1.5, "body": 0.7,
    }
    excluded = exclude_paths or set()
    ranked: list[RelatedVaultNote] = []
    for note, fields in zip(notes, documents, strict=True):
        if note.path in excluded:
            continue
        score = 0.0
        matched: list[str] = []
        for term, query_count in query.items():
            df = document_frequency.get(term, 0)
            if not df:
                continue
            idf = log(1 + (count - df + 0.5) / (df + 0.5))
            query_weight = 1 + min(log(query_count), 1.5)
            term_score = 0.0
            for field_name, counts in fields.items():
                term_frequency = counts.get(term, 0)
                if not term_frequency:
                    continue
                length = sum(counts.values())
                average = average_lengths[field_name]
                length_ratio = length / average if average else 0.0
                normalized_tf = (term_frequency * 2.2) / (
                    term_frequency + 1.2 * (0.25 + 0.75 * length_ratio)
                )
                term_score += field_weights[field_name] * normalized_tf
            if term_score:
                matched.append(term)
                score += idf * query_weight * term_score
        if score > 0:
            ranked.append(RelatedVaultNote(note, score, tuple(sorted(matched))))

    ranked.sort(key=lambda item: (-item.score, item.note.title.casefold(), item.note.path))
    return ranked[:limit]


def _index_note(relative_path: str, filename_stem: str, text: str) -> IndexedVaultNote:
    match = _FRONTMATTER.match(text)
    metadata: dict[str, Any] = {}
    body = text
    if match:
        body = text[match.end():]
        try:
            parsed = yaml.safe_load(match.group(1))
        except yaml.YAMLError:
            parsed = None
        if isinstance(parsed, dict):
            metadata = parsed

    headings = tuple(_HEADING.findall(body))
    title = _as_text(metadata.get("title")) or (headings[0] if headings else filename_stem)
    aliases = _as_strings(metadata.get("aliases", metadata.get("alias")))
    tags = _as_strings(metadata.get("tags", metadata.get("tag")))
    summary = _as_text(metadata.get("summary", metadata.get("resumen")))
    if not summary:
        summary = _first_paragraph(body)

    note_type = _as_text(metadata.get("type", metadata.get("tipo")))
    searchable_body = _FENCED_BLOCK.sub(" ", body)[:100_000]
    return IndexedVaultNote(
        path=relative_path,
        title=title,
        aliases=aliases,
        tags=tags,
        summary=summary,
        headings=headings[:30],
        search_terms=tuple(sorted(Counter(_tokens(searchable_body)).items())),
        note_type=note_type,
    )


def _as_text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _as_strings(value: Any) -> tuple[str, ...]:
    if isinstance(value, str):
        values = [value]
    elif isinstance(value, list):
        values = value
    else:
        return ()

    return tuple(
        item.strip()
        for item in values
        if isinstance(item, str) and item.strip()
    )


def _first_paragraph(body: str) -> str:
    paragraph: list[str] = []
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped:
            if paragraph:
                break
            continue
        if stripped.startswith(("#", "```", ">", "- ", "* ", "+ ")):
            if paragraph:
                break
            continue
        paragraph.append(stripped)
    return " ".join(paragraph)[:500]


def _tokens(text: str) -> list[str]:
    normalized = unicodedata.normalize("NFKD", text.casefold())
    ascii_text = "".join(char for char in normalized if not unicodedata.combining(char))
    return [
        token for token in _TOKEN.findall(ascii_text)
        if len(token) > 2 and token not in _STOPWORDS
    ]
