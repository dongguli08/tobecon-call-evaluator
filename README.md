# TOBECON 통화 평가기

한국어 CS 통화 MP3를 입력받아 전사, 분석, 리포트 생성을 순서대로 수행하는 과제용 프로젝트입니다.

## 목적

- 통화 1건씩 분석 가능한 구조를 만든다.
- STT 결과를 바탕으로 LLM이 직접 도구를 호출하며 평가하도록 한다.
- 통화별로 JSON과 Markdown 리포트를 함께 출력한다.
- 매니저가 바로 검토할 수 있는 수준의 요약, 평가, 개선 포인트, 액션 아이템을 남긴다.

## 동작 방식

1. **전사**
   - 입력 파일 형식: `mp3`, `wav`, `m4a`, `mp4`, `aac`, `flac`
   - 기본 STT: OpenAI Whisper(`whisper-1`)
2. **분석**
   - OpenAI `function calling`을 사용한다.
   - 모델이 상황에 따라 필요한 도구를 직접 선택한다.
3. **리포트 생성**
   - 통화별 JSON 파일 생성
   - 사람용 Markdown 파일 생성
   - 전체 인덱스 파일 생성

## 평가 항목

기본 평가 차원은 6개입니다.

- 친절도
- 문제 해결도
- 정책 준수
- 경청/공감
- 안내 명확성
- 클로징/후속 안내

필요하면 `src/tobecon_evaluator/config.py`에서 조정할 수 있습니다.

## 설치

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .
```

## 실행

### 1) 원본 오디오로 바로 실행

```bash
python -m tobecon_evaluator.cli \
  --input-dir ./data/raw \
  --output-dir ./out \
  --stt-provider openai-whisper
```

### 2) 전사 결과를 따로 넣고 실행

```bash
python -m tobecon_evaluator.cli \
  --transcript-dir ./data/transcripts \
  --output-dir ./out
```

## 출력 파일

통화 1건당:

- `out/<call_id>.json`
- `out/<call_id>.md`

전체 요약:

- `out/index.json`
- `out/index.md`

전사 파일을 직접 생성할 경우:

- `out/transcripts/<call_id>.json`

## 결과물 형식

### JSON

구조화된 제출용 데이터입니다. 주요 필드는 다음과 같습니다.

- `call_id`
- `source_path`
- `duration_seconds`
- `language`
- `summary`
- `scores`
- `improvements`
- `manager_action_items`
- `cost`
- `notes`

### Markdown

사람이 읽기 쉬운 보고서 형식입니다.

- 기본 정보
- 요약
- 평가 차원별 점수
- 개선이 필요한 구간
- 매니저용 액션 아이템
- 예상 API 비용
- 전사 샘플

## 비용 기준

- Whisper 전사: `whisper-1` 기준 **$0.006 / minute**
- GPT 분석: `gpt-5.4` 기준 **$2.50 / 1M input tokens**, **$15.00 / 1M output tokens**

위 값은 `src/tobecon_evaluator/pricing.py`와 `.env.example`에서 조정할 수 있습니다.

## 환경 변수 예시

`.env.example` 파일을 참고하세요.

- `OPENAI_API_KEY`
- `TOBECON_GPT_INPUT_COST_PER_1M`
- `TOBECON_GPT_OUTPUT_COST_PER_1M`
- `TOBECON_WHISPER_COST_PER_MINUTE`

## 참고

- 이 프로젝트는 “LLM이 직접 도구를 호출하며 판단한다”는 요구를 반영해, 분석 루프를 명시적으로 구성했습니다.
- 현재는 로컬 파일로 결과를 저장합니다.
- 필요하면 이후 Clova, ElevenLabs STT 어댑터를 추가할 수 있습니다.
