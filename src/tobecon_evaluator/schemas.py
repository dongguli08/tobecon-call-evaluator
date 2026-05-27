from __future__ import annotations

from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class TranscriptSegment:
    start: float
    end: float
    text: str
    speaker: str | None = None


@dataclass(slots=True)
class Transcript:
    call_id: str
    source_path: str
    language: str | None
    duration_seconds: float
    text: str
    segments: list[TranscriptSegment] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        return payload


@dataclass(slots=True)
class ScoreItem:
    dimension: str
    score: int
    rationale: str
    evidence: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ImprovementItem:
    start_time: float
    end_time: float
    quote: str
    issue: str
    recommendation: str


@dataclass(slots=True)
class CallAnalysis:
    call_id: str
    source_path: str
    duration_seconds: float
    language: str | None
    summary: list[str]
    scores: list[ScoreItem]
    improvements: list[ImprovementItem]
    manager_action_items: list[str]
    cost: dict[str, float]
    notes: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class AnalysisArtifact:
    transcript: Transcript
    analysis: CallAnalysis


def safe_call_id(path: Path) -> str:
    return path.stem.replace(" ", "_")

