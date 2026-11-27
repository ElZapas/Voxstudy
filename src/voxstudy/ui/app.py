"""Textual application shell and screen routing."""

from textual.app import App
from textual.screen import Screen

from .screens.dashboard import DashboardScreen
from .screens.library import LibraryScreen


class VoxStudyApp(App[None]):
    """Interactive terminal entry point for VoxStudy."""

    TITLE = "VoxStudy"
    AUTO_FOCUS = None
    SCREENS = {"library": LibraryScreen}

    def get_default_screen(self) -> Screen:
        return DashboardScreen()
