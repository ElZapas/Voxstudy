"""Textual application shell; feature screens are added incrementally."""

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, Header, Static


class VoxStudyApp(App[None]):
    """Interactive terminal entry point for VoxStudy."""

    TITLE = "VoxStudy"
    CSS = """
    Screen {
        align: center middle;
    }

    #welcome {
        width: 70;
        height: auto;
        padding: 1 2;
        border: round $accent;
        text-align: center;
    }
    """
    BINDINGS = [Binding("q", "quit", "Salir", show=True)]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static(
            "[b]Bienvenido a VoxStudy[/b]\n\n"
            "La interfaz interactiva está conectada.\n"
            "En el siguiente paso añadiremos el panel principal.",
            id="welcome",
        )
        yield Footer()
