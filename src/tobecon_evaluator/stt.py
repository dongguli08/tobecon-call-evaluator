from __future__ import annotations

from pathlib import Path
from typing import Protocol

from openai import OpenAI

from .config import DEFAULT_TRANSCRIPTION_MODEL
from .schemas import Transcript, TranscriptSegment, safe_call_id


class Transcriber(Protocol):
    def transcribe(self, audio_path: Path) -> Transcript: ...


class OpenAIWhisperTranscriber:
    def __init__(self, client: OpenAI | None = None, model: str = DEFAULT_TRANSCRIPTION_MODEL):
        self.client = client or OpenAI()
        self.model = model

    def transcribe(self, audio_path: Path) -> Transcript:
        with audio_path.open("rb") as audio_file:
            response = self.client.audio.transcriptions.create(
                model=self.model,
                file=audio_file,
                response_format="verbose_json",
            )

        segments: list[TranscriptSegment] = []
        for item in getattr(response, "segments", []) or []:
            segments.append(
                TranscriptSegment(
                    start=float(getattr(item, "start", 0.0)),
                    end=float(getattr(item, "end", 0.0)),
                    text=str(getattr(item, "text", "")).strip(),
                )
            )

        text = getattr(response, "text", "") or "\n".join(segment.text for segment in segments)
        language = getattr(response, "language", None)
        duration_seconds = segments[-1].end if segments else 0.0
        return Transcript(
            call_id=safe_call_id(audio_path),
            source_path=str(audio_path),
            language=language,
            duration_seconds=duration_seconds,
            text=text,
            segments=segments,
        )

