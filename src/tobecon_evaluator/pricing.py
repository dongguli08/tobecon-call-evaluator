from __future__ import annotations

from dataclasses import dataclass
import os

WHISPER_COST_PER_MINUTE = float(os.getenv("TOBECON_WHISPER_COST_PER_MINUTE", "0.006"))
GPT_INPUT_COST_PER_1M = float(os.getenv("TOBECON_GPT_INPUT_COST_PER_1M", "2.50"))
GPT_OUTPUT_COST_PER_1M = float(os.getenv("TOBECON_GPT_OUTPUT_COST_PER_1M", "15.00"))


@dataclass(slots=True)
class CostEstimate:
    stt_usd: float
    llm_input_usd: float
    llm_output_usd: float

    @property
    def total_usd(self) -> float:
        return round(self.stt_usd + self.llm_input_usd + self.llm_output_usd, 6)

    def to_dict(self) -> dict[str, float]:
        return {
            "stt_usd": round(self.stt_usd, 6),
            "llm_input_usd": round(self.llm_input_usd, 6),
            "llm_output_usd": round(self.llm_output_usd, 6),
            "total_usd": self.total_usd,
        }


def estimate_call_cost(
    *,
    duration_seconds: float,
    llm_input_tokens: int,
    llm_output_tokens: int,
) -> CostEstimate:
    minutes = max(duration_seconds, 0.0) / 60.0
    stt = minutes * WHISPER_COST_PER_MINUTE
    llm_input = (llm_input_tokens / 1_000_000) * GPT_INPUT_COST_PER_1M
    llm_output = (llm_output_tokens / 1_000_000) * GPT_OUTPUT_COST_PER_1M
    return CostEstimate(stt_usd=stt, llm_input_usd=llm_input, llm_output_usd=llm_output)

