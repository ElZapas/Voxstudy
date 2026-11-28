"""Directory picker for the active Obsidian vault."""

from __future__ import annotations

from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, DirectoryTree, Footer, Input, Static

from ...config import VoxStudyError
from ...workflow import change_vault
from ..widgets.navbar import AppNavbar


class VaultPickerScreen(Screen[None]):
    """Browse for or enter the directory to use as the Obsidian vault."""

    BINDINGS = [Binding("escape", "cancel", "Cancelar", show=True)]

    CSS = """
    VaultPickerScreen { layout: vertical; }

    #vault-picker-body {
        height: 1fr;
        padding: 1 2;
    }

    #vault-picker-panel {
        height: 1fr;
        min-height: 8;
        padding: 1;
        border: heavy $muted;
        background: $surface;
    }

    #vault-picker-title {
        height: 1;
        color: $accent;
        text-style: bold;
    }

    #vault-picker-help, #vault-picker-status {
        height: auto;
        color: $muted;
        margin-bottom: 1;
    }

    #vault-path-row { height: 3; }
    #vault-path { width: 1fr; background: $panel; border: round $muted; }
    #browse-vault-path { width: 18; margin-left: 1; }

    #vault-tree {
        height: 1fr;
        margin-top: 1;
        border: heavy $muted;
        background: $background;
    }

    #vault-picker-buttons { height: 3; margin-top: 1; }
    #save-vault { margin-right: 1; }
    """

    def __init__(self, current_vault: Path | None = None) -> None:
        super().__init__()
        self.current_vault = current_vault or Path.home()

    def compose(self) -> ComposeResult:
        yield AppNavbar(active_page="settings")
        with Vertical(id="vault-picker-body"):
            with Vertical(id="vault-picker-panel"):
                yield Static("CARPETA DE LA BÓVEDA", id="vault-picker-title")
                yield Static(
                    "Selecciona una carpeta en el árbol o escribe una ruta. "
                    "La carpeta debe existir.",
                    id="vault-picker-help",
                )
                with Horizontal(id="vault-path-row"):
                    yield Input(str(self.current_vault), id="vault-path", placeholder="/ruta/a/tu/boveda")
                    yield Button("Explorar ruta", id="browse-vault-path")
                yield Static("", id="vault-picker-status")
                yield DirectoryTree(Path.home(), id="vault-tree")
                with Horizontal(id="vault-picker-buttons"):
                    yield Button("Usar esta carpeta", id="save-vault", variant="primary")
                    yield Button("Cancelar", id="cancel-vault")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#vault-tree", DirectoryTree).focus()

    def on_screen_resume(self) -> None:
        self.call_after_refresh(self._focus_tree)

    def _focus_tree(self) -> None:
        if self.is_mounted:
            self.query_one("#vault-tree", DirectoryTree).focus()

    def set_current_vault(self, path: Path) -> None:
        self.current_vault = path
        if self.is_mounted:
            self.query_one("#vault-path", Input).value = str(path)

    def on_directory_tree_directory_selected(self, event: DirectoryTree.DirectorySelected) -> None:
        self.query_one("#vault-path", Input).value = str(event.path)
        self.query_one("#vault-picker-status", Static).update(f"Carpeta seleccionada: {event.path}")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel-vault":
            await self.action_cancel()
        elif event.button.id == "browse-vault-path":
            self._browse_path()
        elif event.button.id == "save-vault":
            await self._save_vault()

    def _browse_path(self) -> None:
        raw_path = self.query_one("#vault-path", Input).value.strip()
        path = Path(raw_path).expanduser()
        if not path.is_dir():
            self.notify(f"No existe esa carpeta: {path}", severity="error", timeout=5)
            return
        tree = self.query_one("#vault-tree", DirectoryTree)
        tree.path = path.resolve()
        self.query_one("#vault-picker-status", Static).update(f"Explorando: {path.resolve()}")

    async def _save_vault(self) -> None:
        raw_path = self.query_one("#vault-path", Input).value.strip()
        if not raw_path:
            self.notify("Escribe o selecciona la carpeta de la bóveda.", severity="error", timeout=5)
            return
        try:
            config = change_vault(raw_path)
        except (VoxStudyError, OSError) as exc:
            self.notify(str(exc), severity="error", timeout=6)
            return
        await self.app.pop_screen()
        self.app.refresh_current_screen()
        self.app.notify(f"Bóveda seleccionada: {config.vault}", timeout=4)

    async def action_cancel(self) -> None:
        await self.app.pop_screen()
