"""Searchable library of VoxStudy notes."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Input, Static

from ...application.library import list_library_notes
from ...config import VoxStudyError
from ...models import VaultNote
from .study_guide import StudyGuideDetailScreen
from .transcript import TranscriptDetailScreen


class LibraryScreen(Screen[None]):
    """Show and filter all VoxStudy notes in the configured vault."""

    BINDINGS = [Binding("escape", "back", "Volver", show=True)]

    CSS = """
    LibraryScreen {
        layout: vertical;
    }

    #library-body {
        height: 1fr;
        padding: 1 2;
    }

    #library-title {
        height: 1;
        text-style: bold;
        margin-bottom: 1;
    }

    #note-search {
        margin-bottom: 1;
    }

    #library-notes {
        height: 1fr;
    }

    #library-hint {
        height: auto;
        margin-top: 1;
        color: $text-muted;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self._notes_by_path: dict[str, VaultNote] = {}

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="library-body"):
            yield Static("Biblioteca de VoxStudy", id="library-title")
            yield Input(placeholder="Buscar por título…", id="note-search")
            yield DataTable(id="library-notes", cursor_type="row", zebra_stripes=True)
            yield Static("↑/↓: seleccionar · Enter: ver nota · Esc: volver", id="library-hint")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#library-notes", DataTable)
        table.add_columns("Tipo", "Nota", "Modificada")
        self.refresh_notes()

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "note-search":
            self.refresh_notes(event.value)

    async def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        note = self._notes_by_path.get(event.row_key.value)
        if note is None:
            return
        screen_type = (
            TranscriptDetailScreen if note.note_type == "transcription"
            else StudyGuideDetailScreen
        )
        await self.app.push_screen(screen_type(note.path))

    async def action_back(self) -> None:
        await self.app.pop_screen()

    def refresh_notes(self, query: str = "") -> None:
        table = self.query_one("#library-notes", DataTable)
        table.clear(columns=False)
        self._notes_by_path.clear()
        try:
            notes = list_library_notes(query)
        except (VoxStudyError, OSError) as exc:
            self.notify(str(exc), severity="error", timeout=6)
            table.add_row("Error", "No se pudo cargar la biblioteca", "")
            return

        if not notes:
            empty_message = "No hay notas de VoxStudy" if not query.strip() else "Sin resultados"
            table.add_row("—", empty_message, "—")
            return
        for note in notes:
            self._notes_by_path[str(note.path)] = note
            note_type = "Transcripción" if note.note_type == "transcription" else "Guía"
            table.add_row(
                note_type,
                note.title,
                note.modified_at.strftime("%Y-%m-%d %H:%M"),
                key=str(note.path),
            )
