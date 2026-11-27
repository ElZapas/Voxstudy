"""Main VoxStudy terminal dashboard."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Static

from ...application.dashboard import DashboardData, load_dashboard_data


class DashboardScreen(Screen[None]):
    """Show setup/capture status and the latest Obsidian notes."""

    BINDINGS = [
        Binding("r", "refresh", "Actualizar", show=True),
        Binding("q", "quit", "Salir", show=True),
    ]

    CSS = """
    DashboardScreen {
        layout: vertical;
    }

    #dashboard-body {
        height: 1fr;
        padding: 1 2;
    }

    #status-row {
        height: auto;
        margin-bottom: 1;
    }

    .status-card {
        width: 1fr;
        height: auto;
        min-height: 5;
        padding: 1;
        margin-right: 1;
        border: round $accent;
    }

    #recent-title {
        height: 1;
        margin: 1 0;
        text-style: bold;
    }

    #recent-notes {
        height: 1fr;
    }

    #hint {
        height: auto;
        margin-top: 1;
        color: $text-muted;
    }
    """

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="dashboard-body"):
            with Horizontal(id="status-row"):
                yield Static(id="vault-status", classes="status-card")
                yield Static(id="capture-status", classes="status-card")
            yield Static("Notas recientes", id="recent-title")
            yield DataTable(id="recent-notes", zebra_stripes=True)
            yield Static("r: actualizar · q: salir", id="hint")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#recent-notes", DataTable)
        table.add_columns("Tipo", "Nota", "Modificada")
        self.refresh_data()

    def action_refresh(self) -> None:
        self.refresh_data()
        self.notify("Panel actualizado", timeout=2)

    def action_quit(self) -> None:
        self.app.exit()

    def refresh_data(self) -> None:
        data = load_dashboard_data()
        self._render_status(data)
        self._render_recent_notes(data)

    def _render_status(self, data: DashboardData) -> None:
        vault_widget = self.query_one("#vault-status", Static)
        if data.config is None:
            vault_widget.update(
                "[b]Bóveda[/b]\n"
                f"[yellow]{data.configuration_error or 'Sin configurar'}[/yellow]"
            )
        else:
            vault_widget.update(
                "[b]Bóveda[/b]\n"
                f"{data.config.vault}\n"
                f"Transcripciones: {data.config.transcript_folder}\n"
                f"Guías: {data.config.guide_folder}"
            )

        capture_widget = self.query_one("#capture-status", Static)
        if data.capture_error:
            capture_widget.update(f"[b]Captura[/b]\n[red]{data.capture_error}[/red]")
        elif data.capture is None or data.capture.session is None:
            capture_widget.update("[b]Captura[/b]\nSin sesión activa")
        else:
            session = data.capture.session
            if session.capture_finished:
                description = (
                    f"Transcripción en curso: {data.capture.completed_chunks}/"
                    f"{data.capture.total_chunks} bloques"
                )
            else:
                description = f"Capturando audio del sistema ({session.monitor})"
            capture_widget.update(
                f"[b]Captura[/b]\n{description}\nVideo: {session.title}"
            )

    def _render_recent_notes(self, data: DashboardData) -> None:
        table = self.query_one("#recent-notes", DataTable)
        table.clear(columns=False)
        if not data.recent_notes:
            table.add_row("—", "Todavía no hay notas de VoxStudy", "—")
            return
        for note in data.recent_notes:
            note_type = "Transcripción" if note.note_type == "transcription" else "Guía"
            table.add_row(
                note_type,
                note.title,
                note.modified_at.strftime("%Y-%m-%d %H:%M"),
                key=str(note.path),
            )
