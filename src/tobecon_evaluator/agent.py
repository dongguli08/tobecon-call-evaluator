from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any
import json
import re

from openai import OpenAI

from .config import DEFAULT_ANALYSIS_MODEL, DEFAULT_EVALUATION_DIMENSIONS, SYSTEM_PROMPT
from .pricing import estimate_call_cost
from .schemas import (
    AnalysisArtifact,
    CallAnalysis,
    ImprovementItem,
    ScoreItem,
    Transcript,
)


def _segment_payload(transcript: Transcript, limit: int | None = None) -> list[dict[str, Any]]:
    segments = transcript.segments[:limit] if limit else transcript.segments
    return [
        {
            "index": idx,
            "start": segment.start,
            "end": segment.end,
            "text": segment.text,
            "speaker": segment.speaker,
        }
        for idx, segment in enumerate(segments)
    ]


class TranscriptToolbox:
    def __init__(self, transcript: Transcript):
        self.transcript = transcript

    def get_call_metadata(self, args: dict[str, Any]) -> dict[str, Any]:
        return {
            "call_id": self.transcript.call_id,
            "source_path": self.transcript.source_path,
            "duration_seconds": self.transcript.duration_seconds,
            "language": self.transcript.language,
            "segment_count": len(self.transcript.segments),
        }

    def list_segments(self, args: dict[str, Any]) -> dict[str, Any]:
        limit = int(args.get("limit", 20))
        return {"segments": _segment_payload(self.transcript, limit=limit)}

    def search_transcript(self, args: dict[str, Any]) -> dict[str, Any]:
        query = str(args.get("query", "")).strip().lower()
        limit = int(args.get("limit", 5))
        matches: list[dict[str, Any]] = []
        if not query:
            return {"matches": matches}
        for index, segment in enumerate(self.transcript.segments):
            haystack = segment.text.lower()
            if query in haystack:
                matches.append(
                    {
                        "index": index,
                        "start": segment.start,
                        "end": segment.end,
                        "text": segment.text,
                    }
                )
            if len(matches) >= limit:
                break
        return {"matches": matches}

    def get_segment_window(self, args: dict[str, Any]) -> dict[str, Any]:
        start = float(args.get("start", 0.0))
        end = float(args.get("end", start + 15.0))
        matches = [
            {
                "index": idx,
                "start": segment.start,
                "end": segment.end,
                "text": segment.text,
            }
            for idx, segment in enumerate(self.transcript.segments)
            if segment.end >= start and segment.start <= end
        ]
        return {"segments": matches}

    def estimate_cost(self, args: dict[str, Any]) -> dict[str, Any]:
        input_tokens = int(args.get("input_tokens", 0))
        output_tokens = int(args.get("output_tokens", 0))
        estimate = estimate_call_cost(
            duration_seconds=self.transcript.duration_seconds,
            llm_input_tokens=input_tokens,
            llm_output_tokens=output_tokens,
        )
        return estimate.to_dict()


class ToolUseAnalyzer:
    def __init__(self, client: OpenAI | None = None, model: str = DEFAULT_ANALYSIS_MODEL):
        self.client = client or OpenAI()
        self.model = model

    def analyze(self, transcript: Transcript) -> AnalysisArtifact:
        toolbox = TranscriptToolbox(transcript)
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_call_metadata",
                    "description": "통화 기본 메타데이터를 조회한다.",
                    "parameters": {"type": "object", "properties": {}},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "list_segments",
                    "description": "전사 구간 목록 일부를 반환한다.",
                    "parameters": {
                        "type": "object",
                        "properties": {"limit": {"type": "integer", "minimum": 1, "default": 20}},
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "search_transcript",
                    "description": "전사에서 특정 키워드를 검색한다.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string"},
                            "limit": {"type": "integer", "minimum": 1, "default": 5},
                        },
                        "required": ["query"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_segment_window",
                    "description": "특정 타임스탬프 주변의 구간을 조회한다.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "start": {"type": "number"},
                            "end": {"type": "number"},
                        },
                        "required": ["start", "end"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "estimate_cost",
                    "description": "통화 1건의 예상 API 비용을 계산한다.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "input_tokens": {"type": "integer", "minimum": 0},
                            "output_tokens": {"type": "integer", "minimum": 0},
                        },
                        "required": ["input_tokens", "output_tokens"],
                    },
                },
            },
        ]

        transcript_preview = "\n".join(
            f"[{segment.start:.1f}s-{segment.end:.1f}s] {segment.text}"
            for segment in transcript.segments[:30]
        )
        user_prompt = f"""\
다음 한국어 CS 통화 전사를 평가하라.

통화 ID: {transcript.call_id}
소스 파일: {transcript.source_path}
언어: {transcript.language or "unknown"}
길이(초): {transcript.duration_seconds:.1f}
평가 차원: {", ".join(DEFAULT_EVALUATION_DIMENSIONS)}

전사 미리보기:
{transcript_preview}

반드시 필요한 경우 도구를 호출해서 근거를 확인한 뒤 최종 JSON을 반환하라.
JSON 스키마:
{{
  "call_id": str,
  "source_path": str,
  "duration_seconds": number,
  "language": str|null,
  "summary": [str, str, str],
  "scores": [
    {{
      "dimension": str,
      "score": int,
      "rationale": str,
      "evidence": [str, ...]
    }}
  ],
  "improvements": [
    {{
      "start_time": number,
      "end_time": number,
      "quote": str,
      "issue": str,
      "recommendation": str
    }}
  ],
  "manager_action_items": [str, ...],
  "cost": {{
    "stt_usd": number,
    "llm_input_usd": number,
    "llm_output_usd": number,
    "total_usd": number
  }},
  "notes": str|null
}}

요구사항:
- summary는 3개 항목만 허용
- scores는 최소 5개 차원
- improvements는 실제 인용을 포함해야 함
- 각 score는 1~5 정수
"""

        messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

        while True:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=tools,
                tool_choice="auto",
                temperature=0.2,
            )
            choice = response.choices[0]
            message = choice.message

            if message.tool_calls:
                messages.append(
                    {
                        "role": "assistant",
                        "content": message.content,
                        "tool_calls": [tool_call.model_dump() for tool_call in message.tool_calls],
                    }
                )
                for tool_call in message.tool_calls:
                    tool_name = tool_call.function.name
                    raw_arguments = tool_call.function.arguments or "{}"
                    try:
                        arguments = json.loads(raw_arguments)
                    except json.JSONDecodeError:
                        arguments = {}
                    if not hasattr(toolbox, tool_name):
                        tool_result = {"error": f"unknown tool: {tool_name}"}
                    else:
                        tool_result = getattr(toolbox, tool_name)(arguments)
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": json.dumps(tool_result, ensure_ascii=False),
                        }
                    )
                continue

            content = (message.content or "").strip()
            payload = self._parse_json_response(content)
            analysis = self._build_analysis(transcript, payload, response.usage)
            return AnalysisArtifact(transcript=transcript, analysis=analysis)

    @staticmethod
    def _parse_json_response(content: str) -> dict[str, Any]:
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", content, re.DOTALL)
            if not match:
                raise ValueError(f"LLM did not return JSON: {content[:400]}")
            return json.loads(match.group(0))

    @staticmethod
    def _build_analysis(transcript: Transcript, payload: dict[str, Any], usage: Any) -> CallAnalysis:
        summary = [str(item) for item in payload.get("summary", [])][:3]
        scores = [
            ScoreItem(
                dimension=str(item.get("dimension", "")),
                score=int(item.get("score", 0)),
                rationale=str(item.get("rationale", "")),
                evidence=[str(x) for x in item.get("evidence", [])],
            )
            for item in payload.get("scores", [])
        ]
        improvements = [
            ImprovementItem(
                start_time=float(item.get("start_time", 0.0)),
                end_time=float(item.get("end_time", 0.0)),
                quote=str(item.get("quote", "")),
                issue=str(item.get("issue", "")),
                recommendation=str(item.get("recommendation", "")),
            )
            for item in payload.get("improvements", [])
        ]
        cost = payload.get("cost") or {}
        if not cost:
            input_tokens = int(getattr(usage, "prompt_tokens", 0) or 0)
            output_tokens = int(getattr(usage, "completion_tokens", 0) or 0)
            cost = estimate_call_cost(
                duration_seconds=transcript.duration_seconds,
                llm_input_tokens=input_tokens,
                llm_output_tokens=output_tokens,
            ).to_dict()
        return CallAnalysis(
            call_id=str(payload.get("call_id", transcript.call_id)),
            source_path=str(payload.get("source_path", transcript.source_path)),
            duration_seconds=float(payload.get("duration_seconds", transcript.duration_seconds)),
            language=payload.get("language", transcript.language),
            summary=summary,
            scores=scores,
            improvements=improvements,
            manager_action_items=[str(item) for item in payload.get("manager_action_items", [])],
            cost={str(k): float(v) for k, v in cost.items()},
            notes=payload.get("notes"),
        )

