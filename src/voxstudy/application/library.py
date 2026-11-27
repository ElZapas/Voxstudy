"""Queries and actions for navigating notes in the Obsidian vault."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from ..adapters.obsidian import list_vault_notes, open_note_in_obsidian
from ..config import VoxStudyError, load_config
from ..models import VaultNote


@dataclass(frozen=True)
class NoteDetail:
    note: VaultNote
    content: str


def list_library_notes(query: str = "") -> list[VaultNote]:
    """Return all VoxStudy notes, optionally filtered by title or filename."""
    config = load_config()
    notes = list_vault_notes(config, limit=None)
    normalized_query = query.strip().casefold()
    if not normalized_query:
        return notes
    return [
        note for note in notes
        if normalized_query in note.title.casefold()
        or normalized_query in note.path.name.casefold()
    ]


def load_note_detail(path_value: str | Path) -> NoteDetail:
    """Read a VoxStudy note after verifying it belongs to the configured vault."""
    config = load_config()
    path = Path(path_value).expanduser().resolve()
    try:
        path.relative_to(config.vault.resolve())
    except ValueError as exc:
        raise VoxStudyError("La nota debe estar dentro de la bóveda configurada.") from exc
    allowed_folders = (config.vault / config.transcript_folder, config.vault / config.guide_folder)
    if path.suffix.lower() != ".md" or not path.is_file() or not any(
        _is_relative_to(path, folder.resolve()) for folder in allowed_folders
    ):
        raise VoxStudyError("La selección no es una nota de VoxStudy en las carpetas configuradas.")

    content = path.read_text(encoding="utf-8")
    type_match = re.search(r"(?m)^type:\s*(transcription|study-guide)\s*$", content)
    if type_match is None:
        raise VoxStudyError("La nota seleccionada no contiene metadatos de VoxStudy.")
    title_match = re.search(r"(?m)^#\s+(.+?)\s*$", content)
    note = VaultNote(
        path=path,
        title=title_match.group(1) if title_match else path.stem,
        note_type=type_match.group(1),
        modified_at=datetime.fromtimestamp(path.stat().st_mtime).astimezone(),
    )
    return NoteDetail(note, content)


def open_library_note(path_value: str | Path) -> None:
    """Ask Obsidian to open a selected note."""
    config = load_config()
    path = Path(path_value).expanduser().resolve()
    # Validate that the selected file is one of VoxStudy's notes before launching the URI.
    load_note_detail(path)
    open_note_in_obsidian(config, path)


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True
