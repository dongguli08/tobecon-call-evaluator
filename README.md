# TOBECON 통화 평가기

한국어 CS 통화 MP3를 입력받아 전사하고, LLM이 도구를 직접 호출하며 통화 품질을 분석한 뒤, JSON과 Markdown 리포트를 생성하는 과제용 프로젝트입니다.

## 1. 프로젝트 목적

이 프로젝트는 다음 요구사항을 만족하도록 설계했습니다.

- 한국어 CS 통화 5~10건을 입력으로 처리
- STT는 Whisper 계열로 처리
- Claude API 또는 OpenAI function calling / tool use 활용
- 단순 chained prompt가 아니라, **LLM이 직접 도구를 호출하는 구조** 구현
- 통화별로 다음 산출
  - 3줄 이내 요약
  - 5개 이상 평가 차원 점수
  - 개선이 필요한 구간(타임스탬프 + 인용)
  - 매니저용 액션 아이템
  - 예상 API 비용
- 결과물은 JSON과 사람이 읽는 리포트로 제공

---

## 2. 구현 범위

현재 저장소에는 다음이 구현되어 있습니다.

### 전사 계층
- 입력 형식: `mp3`, `wav`, `m4a`, `mp4`, `aac`, `flac`
- 기본 STT: OpenAI Whisper (`whisper-1`)

### 분석 계층
- OpenAI tool calling 기반 분석 에이전트
- 모델이 상황에 따라 필요한 도구를 직접 선택
- 도구 예시
  - 통화 메타데이터 조회
  - 전사 구간 검색
  - 특정 타임스탬프 주변 구간 조회
  - 비용 계산

### 리포트 계층
- 통화별 JSON 파일 생성
- 통화별 Markdown 파일 생성
- 전체 인덱스 파일 생성

---

## 3. 왜 이런 구조로 만들었는가

### 3.1 tool use를 분리한 이유
과제의 핵심은 “LLM이 직접 도구를 호출하며 판단하는가”입니다.  
그래서 전사 결과를 한 번에 프롬프트로 밀어 넣는 방식이 아니라, 메타데이터 확인 / 구간 검색 / 구간 조회 / 비용 계산을 도구로 분리했습니다.

### 3.2 평가 차원을 고정한 이유
점수 기준이 매번 흔들리면 결과가 일관되지 않습니다.  
그래서 기본 평가 차원을 6개로 고정했습니다.

- 친절도
- 문제 해결도
- 정책 준수
- 경청/공감
- 안내 명확성
- 클로징/후속 안내

이 구조는 실제 통화 평가 업무에서 바로 쓰기 쉬운 항목으로 구성했습니다.

### 3.3 Markdown과 JSON을 함께 만드는 이유
- **JSON**: 제출용 / 후처리용 / 자동화용
- **Markdown**: 사람이 읽는 검토용 / 설명용

즉, 매니저가 바로 볼 수 있으면서도, 나중에 데이터를 재가공하기 쉽게 만들었습니다.

### 3.4 비용 추정을 넣은 이유
과제 조건에 “통화 1건당 예상 API 비용 명시”가 포함되어 있어,  
전사 비용과 LLM 비용을 분리해서 계산하도록 넣었습니다.

---

## 4. 실행 방법

### 4.1 설치

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .
```

### 4.2 원본 오디오로 실행

```bash
python -m tobecon_evaluator.cli \
  --input-dir ./data/raw \
  --output-dir ./out \
  --stt-provider openai-whisper
```

### 4.3 전사 결과를 별도로 넣고 실행

```bash
python -m tobecon_evaluator.cli \
  --transcript-dir ./data/transcripts \
  --output-dir ./out
```

---

## 5. 출력 파일

통화 1건당 아래 파일이 생성됩니다.

- `out/<call_id>.json`
- `out/<call_id>.md`

전체 요약 파일:

- `out/index.json`
- `out/index.md`

전사 파일을 별도 생성한 경우:

- `out/transcripts/<call_id>.json`

---

## 6. 결과물 형식

### 6.1 JSON

주요 필드:

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

### 6.2 Markdown

사람이 읽기 쉽게 다음 순서로 정리됩니다.

- 기본 정보
- 요약
- 평가 차원별 점수
- 개선이 필요한 구간
- 매니저용 액션 아이템
- 예상 API 비용
- 전사 샘플

---

## 7. 비용 기준

- Whisper 전사: `whisper-1` 기준 **$0.006 / minute**
- GPT 분석: `gpt-5.4` 기준 **$2.50 / 1M input tokens**, **$15.00 / 1M output tokens**

이 값은 `src/tobecon_evaluator/pricing.py`와 `.env.example`에서 조정할 수 있습니다.

---

## 8. 환경 변수

`.env.example` 참고:

- `OPENAI_API_KEY`
- `TOBECON_GPT_INPUT_COST_PER_1M`
- `TOBECON_GPT_OUTPUT_COST_PER_1M`
- `TOBECON_WHISPER_COST_PER_MINUTE`

---

## 9. 검증 상태

- `pytest -q` 통과
- CLI 도움말 실행 확인
- 샘플 결과물 생성 확인

샘플 산출물은 데스크탑 경로에 별도로 만들어 두었습니다.

---

## 10. 남은 일

실제 제출 전에는 아래를 한 번 더 확인하면 좋습니다.

- 회사 제공 MP3 5~10건으로 실제 end-to-end 실행
- 결과 JSON/MD가 기대한 형식으로 생성되는지 확인
- 필요시 Clova / ElevenLabs STT 어댑터 추가

---

## 11. 참고

- 이 프로젝트는 “LLM이 직접 도구를 호출하며 판단한다”는 요구를 반영해 분석 루프를 명시적으로 구성했습니다.
- 현재는 로컬 파일로 결과를 저장합니다.
- 제출 직전에는 원격 `main` 브랜치 기준으로 최신 상태를 유지하는 것을 권장합니다.
