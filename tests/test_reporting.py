from tobecon_evaluator.reporting import render_call_markdown
from tobecon_evaluator.schemas import (
    AnalysisArtifact,
    CallAnalysis,
    ImprovementItem,
    ScoreItem,
    Transcript,
    TranscriptSegment,
)


def test_render_call_markdown_contains_core_sections():
    transcript = Transcript(
        call_id="sample",
        source_path="/tmp/sample.mp3",
        language="ko",
        duration_seconds=42.0,
        text="안녕하세요",
        segments=[TranscriptSegment(start=0.0, end=2.0, text="안녕하세요")],
    )
    analysis = CallAnalysis(
        call_id="sample",
        source_path="/tmp/sample.mp3",
        duration_seconds=42.0,
        language="ko",
        summary=["요약1", "요약2", "요약3"],
        scores=[ScoreItem(dimension="친절도", score=4, rationale="친절했다", evidence=["안녕하세요"])],
        improvements=[
            ImprovementItem(
                start_time=0.0,
                end_time=2.0,
                quote="안녕하세요",
                issue="인사 외 추가 안내 부족",
                recommendation="다음 단계도 함께 안내한다",
            )
        ],
        manager_action_items=["코칭 필요"],
        cost={"stt_usd": 0.1, "llm_input_usd": 0.2, "llm_output_usd": 0.3, "total_usd": 0.6},
    )
    md = render_call_markdown(AnalysisArtifact(transcript=transcript, analysis=analysis))
    assert "# 통화 리포트 — sample" in md
    assert "## 평가 차원" in md
    assert "## 개선이 필요한 구간" in md
    assert "## 예상 API 비용" in md

