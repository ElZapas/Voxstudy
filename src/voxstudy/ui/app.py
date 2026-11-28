"""Textual application shell and screen routing."""

from pathlib import Path

from textual.app import App

from ..config import DEFAULT_VAULT, VoxStudyError, load_config
from .screens.dashboard import DashboardScreen
from .screens.library import LibraryScreen
from .screens.vault_picker import VaultPickerScreen
from .theme import AETHER_THEME


class VoxStudyApp(App[None]):
    """Interactive terminal entry point for VoxStudy."""

    TITLE = "VoxStudy"
    AUTO_FOCUS = None
    SCREENS = {
        "dashboard": DashboardScreen,
        "library": LibraryScreen,
        "vault-picker": VaultPickerScreen,
    }

    CSS = """
    Screen {
        background: $background;
        color: $foreground;
    }

    Header, Footer {
        background: $panel;
        color: $foreground;
    }

    #app-navigation {
        height: 3;
        margin: 0 1;
        padding: 0 1;
        border: round $foreground-muted;
        background: $panel;
        align: left middle;
    }

    #brand-wave {
        width: 8;
        color: $secondary;
        text-style: bold;
        content-align: center middle;
    }

    #brand-name {
        width: 10;
        color: $accent;
        text-style: bold;
        content-align: left middle;
    }

    #app-navigation Button {
        width: auto;
        min-width: 1;
        height: 1;
        min-height: 1;
        padding: 0 1;
        border: none;
        background: $panel;
        color: $foreground;
    }

    #app-navigation Button:hover {
        background: $surface;
        color: $secondary;
    }

    #nav-home {
        width: 9;
        color: $accent;
        text-style: bold;
    }

    .nav-separator {
        width: 1;
        color: $muted;
        content-align: center middle;
    }

    #nav-library { width: 14; }
    #nav-refresh { width: 13; }
    #nav-quit { width: 8; }
    """

    async def on_mount(self) -> None:
        self.register_theme(AETHER_THEME)
        self.theme = AETHER_THEME.name
        await self.push_screen("dashboard")

    def get_theme_variable_defaults(self) -> dict[str, str]:
        return {"muted": "#67696f"}

    async def show_dashboard(self) -> None:
        while len(self.screen_stack) > 1 and not isinstance(self.screen, DashboardScreen):
            await self.pop_screen()
        if not isinstance(self.screen, DashboardScreen):
            await self.push_screen("dashboard")

    async def show_library(self) -> None:
        if isinstance(self.screen, LibraryScreen):
            return
        if any(isinstance(screen, LibraryScreen) for screen in self.screen_stack):
            while not isinstance(self.screen, LibraryScreen):
                await self.pop_screen()
            return
        await self.show_dashboard()
        await self.push_screen("library")

    async def show_vault_picker(self) -> None:
        try:
            current_vault = load_config().vault
        except VoxStudyError:
            current_vault = DEFAULT_VAULT if DEFAULT_VAULT.is_dir() else Path.home()
        picker = self.get_screen("vault-picker")
        assert isinstance(picker, VaultPickerScreen)
        picker.set_current_vault(current_vault)
        await self.push_screen("vault-picker")

    def refresh_current_screen(self) -> bool:
        refresh = getattr(self.screen, "refresh_view", None)
        if not callable(refresh):
            return False
        refresh()
        return True
