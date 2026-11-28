"""Application workflows coordinating adapters and Obsidian output."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Callable

from .adapters.audio_capture import start_capture, split_audio, stop_capture
from .adapters.deepseek import DEFAULT_MODEL, request_guide
from .adapters.obsidian import save_study_guide, save_transcript, select_transcript, transcript_body
from .adapters.voxtype import require_local_whisper, transcribe_chunk
from .config import (
    RECORDINGS_DIR,
    VoxStudyError,
    clear_session,
    change_vault_config,
    load_config,
    load_session,
    save_session,
    setup_config,
)
from .models import (
    AppConfig,
    CaptureSession,
    CaptureStatus,
    GuideResult,
    TranscriptSegment,
    TranscriptionResult,
    WorkflowProgress,
)

ProgressCallback = Callable[[WorkflowProgress], None]


def setup(vault: str, transcript_folder: str, guide_folder: str) -> AppConfig:
    """Persist configuration and return the effective paths."""
    return setup_config(vault, transcript_folder, guide_folder)


def change_vault(vault: str) -> AppConfig:
    """Switch the configured Obsidian vault without changing folder names."""
    return change_vault_config(vault)


def start(title: str) -> CaptureSession:
    """Start system-audio capture and return the active session."""
    load_config()
    require_local_whisper()
    if load_session() is not None:
        raise VoxStudyError("Hay una sesión pendiente. Ejecuta 'voxstudy stop' antes de iniciar otra.")
    session = start_capture(title)
    save_session(session)
    return session


def stop(on_progress: ProgressCallback | None = None) -> TranscriptionResult:
    """Stop capture, transcribe its chunks, and save the transcript note."""
    config = load_config()
    session = load_session()
    if session is None:
        raise VoxStudyError("No hay una sesión iniciada desde VoxStudy.")

    stop_capture(session)
    save_session(session)
    work_dir = RECORDINGS_DIR / f"chunks-{session.audio_path.stem}"
    work_dir.mkdir(parents=True, exist_ok=True)
    chunks = split_audio(session.audio_path, work_dir)
    completed = len(session.segments)
    if completed > len(chunks):
        session.segments = []
        completed = 0

    _report_progress(on_progress, WorkflowProgress(
        stage="transcription_started",
        current=completed,
        total=len(chunks),
        message="Audio capturado; comienza la transcripción local con Voxtype.",
    ))
    total_samples = max(0, (session.audio_path.stat().st_size - 44) // 2)
    total_seconds = round(total_samples / 16000)
    for index in range(completed, len(chunks)):
        text = transcribe_chunk(chunks[index])
        duration = min(30, max(0, total_seconds - index * 30))
        session.segments.append(TranscriptSegment(index * 30, duration, text))
        save_session(session)
        _report_progress(on_progress, WorkflowProgress(
            stage="transcription_progress",
            current=index + 1,
            total=len(chunks),
            message=f"Bloque {index + 1}/{len(chunks)} completado.",
        ))

    note_path = save_transcript(config, session)
    session.audio_path.unlink(missing_ok=True)
    session.log_path.unlink(missing_ok=True)
    shutil.rmtree(work_dir, ignore_errors=True)
    clear_session()
    return TranscriptionResult(
        note_path=note_path,
        completed_chunks=len(chunks),
        monitor=session.monitor,
    )


def status() -> CaptureStatus:
    """Return the active session and its chunk progress, if any."""
    session = load_session()
    if session is None:
        return CaptureStatus(session=None)
    if session.capture_finished:
        work_dir = RECORDINGS_DIR / f"chunks-{session.audio_path.stem}"
        total = len(list(work_dir.glob("chunk-*.wav")))
        return CaptureStatus(session, len(session.segments), total)
    return CaptureStatus(session)


def create_guide(
    requested_transcript: str | None,
    model: str = DEFAULT_MODEL,
    on_progress: ProgressCallback | None = None,
) -> GuideResult:
    """Generate a study guide and return its path and provider usage."""
    config = load_config()
    source_note = select_transcript(config, requested_transcript)
    transcript = transcript_body(source_note)
    _report_progress(on_progress, WorkflowProgress(
        stage="guide_generation_started",
        message=f"Enviando {len(transcript)} caracteres a {model}.",
    ))
    guide, usage = request_guide(transcript, model)
    output = save_study_guide(config, source_note, guide, model, usage)
    return GuideResult(
        note_path=output,
        model=model,
        usage=usage,
        transcript_characters=len(transcript),
    )


def _report_progress(callback: ProgressCallback | None, progress: WorkflowProgress) -> None:
    if callback is not None:
        callback(progress)
