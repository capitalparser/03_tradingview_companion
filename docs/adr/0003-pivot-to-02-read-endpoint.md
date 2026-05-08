# ADR-0003 — Pivot: pull 데이터 source를 MCP에서 02 webhook payload로 전환

- **Status**: Accepted
- **Date**: 2026-05-09
- **Decision driver**: 사용자가 첨부한 webhook v6.1 명세 발견 → 우리가 MCP로 추출하려던 정보가 02_audit_safe_signals가 이미 받는 webhook payload에 더 풍부하게 존재함이 확인됨.

## Context

ADR-0001 ~ ADR-0002는 **차트 시각 출력(plot/label)을 tradingview-mcp로 추출** 하는 모델을 가정. 사용자가 첨부한 [Webhook v6.1 명세](../specs/webhook_v6_1.md)에서 결정적 사실 발견:

1. 사용자의 "프라이빗 시그널 인디케이터" = "자동매매용 통합시스템 지표 v3.2" (Whop 동기화). 단일 통합 시스템이고 출력은 37필드 JSON.
2. 02_audit_safe_signals가 **같은 인디케이터의 webhook payload를 이미 수신 중** (현재 v6.0 33필드 schema, v6.1의 atr_* 3필드만 누락).
3. 차트 plot/label은 lossy (인디케이터의 시각적 layer만), webhook은 lossless (score/conviction/daily_*/ai_summary 등 시각화엔 안 보이는 풍부한 의미 정보 포함).

## 핵심 결정

**Option B 채택**: 03의 pull 경로 핵심 데이터 source를 MCP 차트 추출 → **02 read endpoint** 로 전환.

### 새 architecture

```
TV Desktop alert 발화
  → webhook POST → Fly.io 02_audit_safe_signals
  → 02: dedup + audit-safe 필터 + 결정 로그 + raw payload 저장 (state.db: webhooks 테이블)
  → 02: Telegram push (기존 흐름)

03 pull 경로 (신규):
  사용자 Telegram: "삼성전자 봐줘"
  → 03 bot이 02의 GET /signals/KRX:005930?timeframe=240&secret=... 호출
  → 02가 가장 최근 webhook payload 반환 (37필드, audit_decision 포함)
  → 03 Claude가 webhook spec을 컨텍스트로 한국어 해석
  → Telegram 응답
```

MCP는 이제 **부수 기능**으로 격하: 차트 스크린샷 (`capture_screenshot`), 사용자 즉석 timeframe 변경 등.

## 거부된 옵션과 이유

### Option A (현 plan 유지 — MCP만)
- MCP feasibility risk 그대로 (Codex outside voice가 가장 강조한 #1 risk)
- 차트 plot 추출은 lossy — score, conviction, ai_summary 등 못 받음
- TV Desktop 24/7 강제 → 운영 부담

### Option C (하이브리드 — MCP 주, webhook 보조)
- 두 경로 동시 유지로 복잡도 증가
- MCP risk 여전히 본질
- "데이터는 02에서, 시각화만 MCP에서"가 더 깔끔 — 그래서 Option B로

## 결과적 결정 변경 매트릭스

| ADR-0001/02 결정 | Option B 후 |
|---|---|
| AD-1 (MCP single-spawn) | 유효하지만 부수 기능 한정. Bot startup에 spawn하지 않고 "스크린샷 요청 시 lazy spawn"으로 격하 가능 |
| AD-2 (asyncio.Lock) | TV 단일 차트 의존 약화. lock은 MCP 호출에만 한정. webhook payload 조회는 무관 |
| AD-3 (cost cap) | 그대로 유효. LLM 호출에는 cap 동일 적용 |
| AD-4 (SQLite ConversationStore) | 그대로 유효 |
| AD-7 (워치리스트 deterministic) | 자연스럽게 더 강해짐 — webhook payload 자체가 deterministic |
| AD-8 (audit-safety) | 02가 이미 audit decision을 payload에 포함 → 03이 그대로 표시. **manual sync 부담 사라짐** |
| Phase 0b GO/NO-GO | "MCP 인디케이터 추출" → "02 endpoint health + sample query" 로 단순화 |

## 새 결정 (AD-9 ~ AD-11)

### AD-9. Pull 데이터 primary source = 02 read endpoint
- 03의 `Analyst.analyze_symbol`은 **02의 GET endpoint 호출이 1차**, MCP는 보조
- 응답은 항상 webhook payload (37필드) + audit_decision (CLEAN/SKIP/MANUAL_VERIFY) + 보조 메타
- 데이터 누락 시 (해당 종목 alert 미발화) graceful 응답: "최근 알림 없음 — 워치리스트 등록 확인"

### AD-10. Project isolation 갱신
- ADR-0001 분기 3 (isolation) **부분 완화**: 03 → 02 단방향 read-only HTTP 의존을 명시적으로 허용
- 02 → 03 의존은 여전히 금지 (양방향 의존 차단)
- 코드 import도 여전히 금지 (HTTP 인터페이스만)
- 02 다운 시 03 pull 경로만 다운, push 경로는 02 자체 기능이라 무관

### AD-11. 02 측 작업 (별도 spec 필요)
- v6.1 atr_* 3필드 schema 추가 (Pydantic 5분)
- `webhooks` 테이블 추가 (raw payload + received_at + audit_decision)
- TTL 30일 또는 무제한 (decision)
- `GET /signals/{ticker}?timeframe=...&secret=...` endpoint
- 같은 webhook_secret 재사용 가능 (기존 Auth 패턴 follow)
- decisions.jsonl 일부도 endpoint로 노출 검토 (필요 시)

## 영향 받는 파일

### 03 (생성/수정)
- `src/tvc/source/endpoint.py` (신규) — httpx 기반 02 client (timeout 5s, retry 1회)
- `src/tvc/claude_sdk/analyst.py` (수정) — primary source = EndpointClient, MCP는 옵션
- `src/tvc/storage.py` — 그대로 (변경 없음)
- `src/tvc/bot/handlers.py` — 자연어 → ticker → endpoint 호출
- `src/tvc/resources/analyze_prompt.md` — 37필드 의미 학습 (webhook spec 참조 명시)
- `pyproject.toml` — `httpx>=0.27` 추가 (Anthropic SDK 거치지 않는 직접 HTTP)
- `.env.example` — `AUDIT_SIGNALS_BASE_URL`, `AUDIT_SIGNALS_SECRET` 추가
- `docs/specs/webhook_v6_1.md` (신규) — 명세 사본

### 02 (별도 spec, 본 plan에선 contract만)
- `src/.../domain/webhook.py` — atr_* 3필드 추가
- `src/.../filters/dedup.py` 또는 `pipeline/handle_webhook.py` — webhooks 테이블 INSERT
- `src/.../server.py` — GET /signals 라우트
- migration script (state.db schema 추가)

## Verification

Phase 0b GO/NO-GO (재정의):
1. 02에 atr_* 3필드 + webhooks 테이블 + GET /signals 배포
2. 사용자가 alert 1개를 TV에서 발사 → 02가 수신 + state.db에 저장 확인
3. 03 (홈 머신)에서 `curl https://02.fly.dev/signals/KRX:005930?timeframe=240&secret=...` → 37필드 JSON 정상 수신
4. **3개 모두 통과 시 GO**, 하나라도 실패하면 02 디버그

## 거부된 minor 변경

- **02의 모든 알림 audit_decision 필드 추가**: 이미 decisions.jsonl에 있음. payload 자체에 포함 X (별도 endpoint로)
- **02가 03에 webhook 발사 (push)**: 양방향 의존이 됨, ADR-0001 위반. 03이 pull로만.
- **별도 service tier (예: Redis cache)**: 과한 인프라. SQLite + endpoint로 충분.

## 다음 단계

- 본 ADR + 변경된 plan을 commit + push
- 02 측 작업은 사용자가 02 cwd로 이동하여 별도 spec/plan 진행 권장 (project isolation)
- 03 측 코드 시그니처 조정 (EndpointClient 추가, MCP 격하)
- Phase 0b GO/NO-GO 게이트는 02 endpoint 배포 후 가능
