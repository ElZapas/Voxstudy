"""Read and write VoxStudy notes inside the configured Obsidian vault."""

from __future__ import annotations

import re
import subprocess
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode

from ..config import VoxStudyError
from ..markdown import render_study_guide, render_transcript, slugify
from ..models import AppConfig, CaptureSession, VaultNote


def transcript_body(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"\A---\s*\n.*?\n---\s*\n", "", text, count=1, flags=re.DOTALL)
    text = re.sub(r"\A# .*?\n", "", text, count=1)
    text = re.sub(r"(?m)^## Transcripción\s*\n", "", text)
    if len(text.strip()) < 40:
        raise VoxStudyError("La nota no parece contener una transcripción suficiente para estudiar.")
    return text.strip()


def select_transcript(config: AppConfig, requested: str | None) -> Path:
    folder = config.vault / config.transcript_folder
    if requested:
        candidate = Path(requested).expanduser()
        if not candidate.is_absolute():
            direct = config.vault / candidate
            candidate = direct if direct.is_file() else folder / candidate
        candidate = candidate.resolve()
        try:
            candidate.relative_to(config.vault.resolve())
        except ValueError as exc:
            raise VoxStudyError("La transcripción debe estar dentro de la bóveda configurada.") from exc
        if candidate.suffix.lower() != ".md" or not candidate.is_file():
            raise VoxStudyError(f"No encuentro una nota Markdown de transcripción: {candidate}")
        return candidate

    candidates = [
        path for path in folder.glob("*.md")
        if re.search(r"(?m)^type:\s*transcription\s*$", path.read_text(encoding="utf-8", errors="replace"))
    ] if folder.is_dir() else []
    if not candidates:
        raise VoxStudyError(f"No hay transcripciones en {folder}")
    return max(candidates, key=lambda path: path.stat().st_mtime)


def list_vault_notes(config: AppConfig, limit: int | None = 5) -> list[VaultNote]:
    """List VoxStudy transcript and guide notes, newest first."""
    notes: list[VaultNote] = []
    for folder in (config.transcript_folder, config.guide_folder):
        directory = config.vault / folder
        if not directory.is_dir():
            continue
        for path in directory.glob("*.md"):
            try:
                preview = path.read_text(encoding="utf-8", errors="replace")[:4000]
                modified = datetime.fromtimestamp(path.stat().st_mtime).astimezone()
            except OSError:
                continue
            type_match = re.search(r"(?m)^type:\s*(transcription|study-guide)\s*$", preview)
            if type_match is None:
                continue
            title_match = re.search(r"(?m)^#\s+(.+?)\s*$", preview)
            notes.append(VaultNote(
                path=path,
                title=title_match.group(1) if title_match else path.stem,
                note_type=type_match.group(1),
                modified_at=modified,
            ))
    notes.sort(key=lambda note: note.modified_at, reverse=True)
    return notes if limit is None else notes[:max(0, limit)]


def open_note_in_obsidian(config: AppConfig, path: Path) -> None:
    """Open a note through Obsidian's URI handler."""
    resolved = path.expanduser().resolve()
    try:
        relative = resolved.relative_to(config.vault.resolve())
    except ValueError as exc:
        raise VoxStudyError("La nota debe estar dentro de la bóveda configurada.") from exc
    if not resolved.is_file() or resolved.suffix.lower() != ".md":
        raise VoxStudyError(f"No encuentro la nota Markdown: {resolved}")
    uri = "obsidian://open?" + urlencode({
        "vault": config.vault.name,
        "file": relative.as_posix(),
    })
    try:
        subprocess.Popen(
            ["xdg-open", uri],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except OSError as exc:
        raise VoxStudyError(f"No pude abrir Obsidian: {exc}") from exc


def _unique_path(folder: Path, filename: str) -> Path:
    candidate = folder / filename
    stem, suffix = candidate.stem, candidate.suffix
    number = 2
    while candidate.exists():
        candidate = folder / f"{stem}-{number}{suffix}"
        number += 1
    return candidate


def save_transcript(config: AppConfig, session: CaptureSession) -> Path:
    folder = config.vault / config.transcript_folder
    folder.mkdir(parents=True, exist_ok=True)
    started = datetime.fromisoformat(session.started_at)
    stamp = started.astimezone().strftime("%Y-%m-%d-%H%M")
    path = _unique_path(folder, f"{stamp}-{slugify(session.title)}.md")
    path.write_text(
        render_transcript(session.title, session.monitor, session.started_at, session.segments),
        encoding="utf-8",
    )
    return path


def save_study_guide(
    config: AppConfig,
    source_note: Path,
    guide: dict,
    model: str,
    usage: dict,
) -> Path:
    folder = config.vault / config.guide_folder
    folder.mkdir(parents=True, exist_ok=True)
    title = str(guide.get("title") or source_note.stem)
    filename = f"{source_note.stem}-guia-{slugify(title)}.md"
    path = _unique_path(folder, filename)
    path.write_text(render_study_guide(guide, source_note, model, usage), encoding="utf-8")
    return path
