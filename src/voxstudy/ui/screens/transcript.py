"""Detail view for a transcription note."""

from __future__ import annotations

from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Footer, Header, Markdown, Static

from ...application.library import load_note_detail, open_library_note
from ...config import VoxStudyError


class NoteDetailScreen(Screen[None]):
    """Shared note preview and Obsidian opening action."""

    BINDINGS = [
        Binding("o", "open_in_obsidian", "Abrir en Obsidian", show=True),
        Binding("escape", "back", "Volver", show=True),
    ]
    NOTE_KIND = "Nota"

    CSS = """
    NoteDetailScreen {
        layout: vertical;
    }

    #detail-body {
        height: 1fr;
        padding: 1 2;
    }

    #detail-title {
        height: auto;
        text-style: bold;
    }

    #detail-meta {
        height: auto;
        color: $text-muted;
        margin-bottom: 1;
    }

    #note-scroll {
        height: 1fr;
        border: round $accent;
        padding: 1;
    }
    """

    def __init__(self, note_path: str | Path) -> None:
        super().__init__()
        self.note_path = Path(note_path)

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="detail-body"):
            yield Static(self.NOTE_KIND, id="detail-title")
            yield Static(id="detail-meta")
            with VerticalScroll(id="note-scroll"):
                yield Markdown(id="note-content")
        yield Footer()

    async def on_mount(self) -> None:
        try:
            detail = load_note_detail(self.note_path)
        except (VoxStudyError, OSError) as exc:
            self.notify(str(exc), severity="error", timeout=6)
            await self.app.pop_screen()
            return
        self.query_one("#detail-title", Static).update(detail.note.title)
        self.query_one("#detail-meta", Static).update(
            f"{self.NOTE_KIND} · Modificada {detail.note.modified_at:%Y-%m-%d %H:%M} · {detail.note.path}"
        )
        self.query_one("#note-content", Markdown).update(detail.content)

    def action_open_in_obsidian(self) -> None:
        try:
            open_library_note(self.note_path)
        except (VoxStudyError, OSError) as exc:
            self.notify(str(exc), severity="error", timeout=6)
            return
        self.notify("Abriendo nota en Obsidian…", timeout=3)

    async def action_back(self) -> None:
        await self.app.pop_screen()


class TranscriptDetailScreen(NoteDetailScreen):
    NOTE_KIND = "Transcripción"
