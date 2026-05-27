from __future__ import annotations

from pathlib import Path
import argparse
import json

from .agent import ToolUseAnalyzer
from .reporting import write_outputs
from .stt import OpenAIWhisperTranscriber
from .schemas import AnalysisArtifact, Transcript, TranscriptSegment


AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".mp4", ".aac", ".flac"}


def iter_audio_files(input_dir: Path) -> list[Path]:
    return sorted(path for path in input_dir.iterdir() if path.is_file() and path.suffix.lower() in AUDIO_EXTENSIONS)


def load_transcript_json(path: Path) -> Transcript:
    payload = json.loads(path.read_text(encoding="utf-8"))
    segments = [
        TranscriptSegment(
            start=float(item["start"]),
            end=float(item["end"]),
            text=item["text"],
            speaker=item.get("speaker"),
        )
        for item in payload.get("segments", [])
    ]
    return Transcript(
        call_id=payload["call_id"],
        source_path=payload["source_path"],
        language=payload.get("language"),
        duration_seconds=float(payload["duration_seconds"]),
        text=payload["text"],
        segments=segments,
    )


def save_transcript_json(output_dir: Path, transcript: Transcript) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / f"{transcript.call_id}.json").write_text(
        json.dumps(transcript.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def build_artifacts(
    *,
    input_dir: Path | None,
    transcript_dir: Path | None,
    output_dir: Path,
    stt_provider: str,
) -> list[AnalysisArtifact]:
    if stt_provider != "openai-whisper":
        raise ValueError(f"Unsupported STT provider: {stt_provider}")

    transcriber = OpenAIWhisperTranscriber()
    analyzer = ToolUseAnalyzer()
    artifacts: list[AnalysisArtifact] = []

    transcripts: list[Transcript] = []
    if transcript_dir is not None:
        for path in sorted(transcript_dir.glob("*.json")):
            transcripts.append(load_transcript_json(path))
    elif input_dir is not None:
        for audio_path in iter_audio_files(input_dir):
            transcript = transcriber.transcribe(audio_path)
            transcripts.append(transcript)
            save_transcript_json(output_dir / "transcripts", transcript)
    else:
        raise ValueError("Either --input-dir or --transcript-dir must be provided")

    for transcript in transcripts:
        artifact = analyzer.analyze(transcript)
        artifacts.append(artifact)

    return artifacts


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Korean CS call evaluator")
    parser.add_argument("--input-dir", type=Path, default=None, help="Directory containing audio files")
    parser.add_argument("--transcript-dir", type=Path, default=None, help="Directory containing pre-generated transcripts")
    parser.add_argument("--output-dir", type=Path, required=True, help="Where to write JSON/Markdown outputs")
    parser.add_argument("--stt-provider", default="openai-whisper", help="STT provider to use")
    args = parser.parse_args(argv)

    artifacts = build_artifacts(
        input_dir=args.input_dir,
        transcript_dir=args.transcript_dir,
        output_dir=args.output_dir,
        stt_provider=args.stt_provider,
    )
    write_outputs(args.output_dir, artifacts)
    print(f"wrote {len(artifacts)} call report(s) to {args.output_dir}")


if __name__ == "__main__":
    main()
