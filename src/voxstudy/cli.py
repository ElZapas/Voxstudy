"""Command-line entry point for VoxStudy."""

from __future__ import annotations

import argparse
import sys

from .adapters.deepseek import DEFAULT_MODEL
from .config import DEFAULT_GUIDE_FOLDER, DEFAULT_TRANSCRIPT_FOLDER, DEFAULT_VAULT, VoxStudyError
from .workflow import create_guide, setup, start, status, stop


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Transcribe system audio with Voxtype and create Obsidian notes.")
    commands = parser.add_subparsers(dest="command", required=True)

    setup_parser = commands.add_parser("setup", help="Configure the Obsidian vault.")
    setup_parser.add_argument("--vault", default=str(DEFAULT_VAULT), help="Path to the vault.")
    setup_parser.add_argument("--folder", default=DEFAULT_TRANSCRIPT_FOLDER, help="Transcript folder inside the vault.")
    setup_parser.add_argument("--guide-folder", default=DEFAULT_GUIDE_FOLDER, help="Study guide folder inside the vault.")

    start_parser = commands.add_parser("start", help="Start capturing system audio.")
    start_parser.add_argument("--title", default="Video sin título", help="Title for the Obsidian note.")
    commands.add_parser("stop", help="Stop capture, transcribe, and save a note.")
    commands.add_parser("status", help="Show capture or transcription status.")

    guide_parser = commands.add_parser("guide", help="Create a study guide with DeepSeek.")
    guide_parser.add_argument("transcript", nargs="?", help="Transcript note; defaults to the most recent one.")
    guide_parser.add_argument("--model", default=DEFAULT_MODEL, help=f"DeepSeek model (default: {DEFAULT_MODEL}).")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.command == "setup":
            setup(args.vault, args.folder, args.guide_folder)
        elif args.command == "start":
            start(args.title)
        elif args.command == "stop":
            stop()
        elif args.command == "status":
            status()
        elif args.command == "guide":
            create_guide(args.transcript, args.model)
        return 0
    except (VoxStudyError, OSError, KeyError, ValueError, IndexError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
