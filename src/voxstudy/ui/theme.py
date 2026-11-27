"""Color palette matching the current Aether/Omarchy theme."""

from textual.theme import Theme


AETHER_THEME = Theme(
    name="aether-uwu",
    primary="#5f79c9",
    secondary="#77c7df",
    accent="#5f79c9",
    foreground="#EFE4D1",
    background="#020418",
    surface="#1b1d2f",
    panel="#020312",
    success="#b5b272",
    warning="#dbdb7f",
    error="#ed3434",
    dark=True,
    variables={
        "muted": "#67696f",
        "input-selection-background": "#1b1d2f 80%",
        "block-cursor-text-style": "none",
    },
)
