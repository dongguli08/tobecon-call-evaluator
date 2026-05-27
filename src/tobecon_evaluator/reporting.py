from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
from typing import Iterable

from .schemas import AnalysisArtifact, CallAnalysis


def render_call_markdown(artifact: AnalysisArtifact) -> str:
    analysis = artifact.analysis
    transcript = artifact.transcript

    lines: list[str] = []
    lines.append(f"# 통화 리포트 — {analysis.call_id}")
    lines.append("")
    lines.append(f"- source: `{analysis.source_path}`")
    lines.append(f"- duration: `{analysis.duration_seconds:.1f}s`")
    if analysis.language:
        lines.append(f"- language: `{analysis.language}`")
    lines.append("")

    lines.append("## 요약")
    for item in analysis.summary:
        lines.append(f"- {item}")
    lines.append("")

    lines.append("## 평가 차원")
    lines.append("| 차원 | 점수 | 근거 |")
    lines.append("| --- | --- | --- |")
    for score in analysis.scores:
        evidence = "<br>".join(score.evidence) if score.evidence else "-"
        lines.append(f"| {score.dimension} | {score.score} | {score.rationale}<br>{evidence} |")
    lines.append("")

    lines.append("## 개선이 필요한 구간")
    if analysis.improvements:
        for item in analysis.improvements:
            lines.append(
                f"- `{item.start_time:.1f}s`–`{item.end_time:.1f}s` / \"{item.quote}\"  \n"
                f"  - issue: {item.issue}  \n"
                f"  - recommendation: {item.recommendation}"
            )
    else:
        lines.append("- 없음")
    lines.append("")

    lines.append("## 매니저용 액션 아이템")
    for item in analysis.manager_action_items:
        lines.append(f"- {item}")
    lines.append("")

    lines.append("## 예상 API 비용")
    lines.append("| 항목 | USD |")
    lines.append("| --- | ---: |")
    for key, value in analysis.cost.items():
        lines.append(f"| {key} | {value:.6f} |")
    lines.append("")

    lines.append("## 원문 전사 샘플")
    for segment in transcript.segments[:8]:
        lines.append(f"- `{segment.start:.1f}s`–`{segment.end:.1f}s`: {segment.text}")
    lines.append("")
    return "\n".join(lines)


def render_index_markdown(artifacts: Iterable[AnalysisArtifact]) -> str:
    lines = ["# TOBECON Call Evaluator", ""]
    for artifact in artifacts:
        lines.append(f"## {artifact.analysis.call_id}")
        lines.append(f"- source: `{artifact.analysis.source_path}`")
        lines.append(f"- total cost: `${artifact.analysis.cost['total_usd']:.6f}`")
        lines.append(f"- summary: {artifact.analysis.summary[0] if artifact.analysis.summary else '-'}")
        lines.append("")
    return "\n".join(lines)


def write_outputs(output_dir: Path, artifacts: list[AnalysisArtifact]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    for artifact in artifacts:
        json_path = output_dir / f"{artifact.analysis.call_id}.json"
        md_path = output_dir / f"{artifact.analysis.call_id}.md"
        json_path.write_text(json.dumps(artifact.analysis.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        md_path.write_text(render_call_markdown(artifact), encoding="utf-8")

    (output_dir / "index.json").write_text(
        json.dumps([artifact.analysis.to_dict() for artifact in artifacts], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (output_dir / "index.md").write_text(render_index_markdown(artifacts), encoding="utf-8")
