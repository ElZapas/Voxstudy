"""Detail view for a study guide note."""

from .transcript import NoteDetailScreen


class StudyGuideDetailScreen(NoteDetailScreen):
    NOTE_KIND = "Guía de estudio"
