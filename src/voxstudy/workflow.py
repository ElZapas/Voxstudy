"""Application workflows coordinating adapters and Obsidian output."""

from __future__ import annotations

import shutil
from pathlib import Path

from .adapters.audio_capture import start_capture, split_audio, stop_capture
from .adapters.deepseek import DEFAULT_MODEL, request_guide
from .adapters.obsidian import save_study_guide, save_transcript, select_transcript, transcript_body
from .adapters.voxtype import require_local_whisper, transcribe_chunk
from .config import (
    RECORDINGS_DIR,
    VoxStudyError,
    clear_session,
    load_config,
    load_session,
    save_session,
    setup_config,
)
from .models import CaptureSession, TranscriptSegment


def setup(vault: str, transcript_folder: str, guide_folder: str) -> None:
    config = setup_config(vault, transcript_folder, guide_folder)
    print("Configuración guardada.")
    print(f"Transcripciones: {config.vault / config.transcript_folder}")
    print(f"Guías de estudio: {config.vault / config.guide_folder}")


def start(title: str) -> None:
    load_config()
    require_local_whisper()
    if load_session() is not None:
        raise VoxStudyError("Hay una sesión pendiente. Ejecuta 'voxstudy stop' antes de iniciar otra.")
    session = start_capture(title)
    save_session(session)
    print(f"Capturando solo el audio del sistema: {session.monitor}")
    print(f"Video: {session.title}")
    print("Al terminar, ejecuta: voxstudy stop")


def stop() -> Path:
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

    print(f"Audio capturado. Transcribiendo {len(chunks)} bloques con Voxtype local…")
    total_samples = max(0, (session.audio_path.stat().st_size - 44) // 2)
    total_seconds = round(total_samples / 16000)
    for index in range(completed, len(chunks)):
        text = transcribe_chunk(chunks[index])
        duration = min(30, max(0, total_seconds - index * 30))
        session.segments.append(TranscriptSegment(index * 30, duration, text))
        save_session(session)
        print(f"Bloque {index + 1}/{len(chunks)} completado.")

    note_path = save_transcript(config, session)
    session.audio_path.unlink(missing_ok=True)
    session.log_path.unlink(missing_ok=True)
    shutil.rmtree(work_dir, ignore_errors=True)
    clear_session()
    print(f"Nota guardada en la bóveda:\n{note_path}")
    print("La captura excluyó el micrófono.")
    return note_path


def status() -> None:
    session = load_session()
    if session is None:
        print("No hay una sesión de VoxStudy activa.")
        return
    if session.capture_finished:
        work_dir = RECORDINGS_DIR / f"chunks-{session.audio_path.stem}"
        total = len(list(work_dir.glob("chunk-*.wav")))
        print(f"Captura detenida; transcripción en curso ({len(session.segments)}/{total} bloques).")
    else:
        print(f"Capturando audio del sistema: {session.monitor}")
    print(f"Video: {session.title}")
    print(f"Inició: {session.started_at}")


def create_guide(requested_transcript: str | None, model: str = DEFAULT_MODEL) -> Path:
    config = load_config()
    source_note = select_transcript(config, requested_transcript)
    transcript = transcript_body(source_note)
    print(f"Enviando {len(transcript)} caracteres a {model} para crear la guía…")
    guide, usage = request_guide(transcript, model)
    output = save_study_guide(config, source_note, guide, model, usage)
    print(f"Guía guardada en la bóveda:\n{output}")
    print(
        "Tokens según DeepSeek: "
        f"entrada {int(usage.get('prompt_tokens', 0) or 0)}, "
        f"salida {int(usage.get('completion_tokens', 0) or 0)}."
    )
    return output
