# ADR-0002 — plan-eng-review 결정 (AD-1 ~ AD-5)

- **Status**: Accepted
- **Date**: 2026-05-09
- **Decision driver**: 승인된 plan을 plan-eng-review 통과 후 lock-in. ADR-0001을 보강.

## Context

`/plan-eng-review` 실행 중 16개 발견 사항 중 5개 architecture 결정이 분기점. 각각 사용자 명시 선택으로 확정. 추가 4개는 best-practice 자동 반영.

## 결정 요약 (AD-1 ~ AD-5)

| ID | 결정 | 거부 옵션 | 이유 |
|---|---|---|---|
| AD-1 | MCP 자식 프로세스: bot startup에 1회 spawn 영구 보유 | per-request spawn (지연 0.5-2s), 자체 supervisor (복잡도) | claude-agent-sdk가 `mcp_servers` 옵션으로 자동 라이프사이클 관리. launchd KeepAlive로 crash 복구. |
| AD-2 | 동시성: `asyncio.Lock` 직렬화 + 워치리스트 점진 응답 (5종목씩) | 우선순위 top-N (기능 잘림), cron pre-fetch (TV 처리 부담 + 차트 자동 회전) | TV Desktop은 단일 차트만 동시 표시. mutex 외 옵션은 race condition. 점진 응답은 30종목 2분 응답을 사용자 친화적으로. |
| AD-3 | API 비용: 코드 cap (warn $5/200req, hard $10/500req per day) + Anthropic 콘솔 월 $30 cap (이중 방어) | 콘솔만, 코드만 | Pro/Max OAuth는 third-party 앱에서 명시 금지(Anthropic 공식 문서). API key + 보호 장치 필수. 코드 cap이 graceful, 콘솔 backstop. |
| AD-4 | 컨텍스트: SQLite `data/state.db` (chat_id → last_symbol/timeframe/session_id) | in-memory + TTL (재시작 손실), SDK session JSONL 단독 (long-term 누적) | 24/7 launchd 운영에서 재시작 시 "위클리도" 같은 후속 질의 깨지면 사용자 짜증. SQLite가 기본기. |
| AD-5 | Phase 6 (Push 보강): plan에서 제거, 1-2개월 운영 후 별도 spec | 유지 + isolation 예외 명시, 유지 + webhook fan-out | 가치 검증 미흡. ADR-0001 isolation 원칙 유지. 운영 데이터로 필요성 판단 후 재진입. |

## 자동 반영 (질문 없이 best practice)

| 항목 | 변경 | 이유 |
|---|---|---|
| SDK 교체 | `anthropic` → `claude-agent-sdk` | tool loop 자동, MCP stdio spawn 내장, session resume 지원. 우리 use case에 정확히 맞음. |
| Prompt caching | 정적 system prompt(analyze_prompt.md)에 cache_control 적용 | API 비용 90% 절감 가능 |
| ToS disclaimer | README에 "개인 자동화 용도, 상업적 사용 시 ToS 별도 검토" 명시 | public repo 클레임 리스크 완화 |
| 회귀 검증 | Verification 7번에 "Phase 5 후 Phase 2 회귀 확인" 추가 | 워치리스트 일괄이 단일 분석을 깨지 않는지 보장 |

## 거부된 발견들 (의도적 미반영)

- **Anthropic SDK Protocol 격리 (issue #10)**: claude-agent-sdk의 `query` 함수를 monkeypatch로 fake. 별도 Protocol 격리는 over-engineering.
- **Symbol fuzzy 매칭 (issue #9)**: 정적 dict로 시작, 추후 LLM 위임 옵션은 사용 패턴 본 후 결정. MVP에서는 결정 보류.
- **CI/E2E 테스트 한계 (issue #13)**: TV Desktop 의존성으로 자동화 어려움. 단위 테스트는 `query` mock으로 가능. live 테스트는 manual 유지.

## 영향 범위 (Critical Files 수정)

- `pyproject.toml` ✅ — `anthropic>=0.40` → `claude-agent-sdk>=0.2.111`
- `src/tvc/claude_sdk/analyst.py` ✅ — SDK 시그니처 + lock + ConversationStore/UsageGuard 의존
- `src/tvc/storage.py` ✅ (신규) — SQLite ConversationStore + UsageGuard 시그니처
- `src/tvc/mcp_client/` ✅ — 제거 (SDK가 MCP 처리)
- `README.md` ✅ — disclaimer 추가
- `plans/2026-05-08-tradingview-companion-design.md` ✅ — Architecture Decisions 섹션 추가, Phase 6 strikethrough, Verification 보강

## Codex Outside Voice 결과 반영 (2026-05-09)

`/plan-eng-review`의 Outside Voice 단계로 Codex (gpt-5.5)에서 28개 추가 발견. 4개 cross-model tension은 사용자 결정으로 채택, 다수 minor는 자동 반영, 일부는 TODOS.md로 deferral.

### 채택 (사용자 결정)
| 항목 | 결정 |
|---|---|
| Phase 0b ↔ 0a 순서 | **뒤집기**. MCP feasibility (프라이빗 인디케이터 추출 가능성)이 GO/NO-GO 게이트. 통과 못 하면 plan 폐기. |
| Telegram bot 정체성 | **02와 같은 봇, token 공유** (single Telegram interface vision 진정 달성). AD-6 신설. |
| 워치리스트 LLM 호출 | **결정론적 추출 + 1회 요약**. 종목당 LLM 제거. AD-7 신설. 비용 90% 절감. |
| AD-1 health check | **추가**. wedged MCP 감지 + SDK 재초기화 (controlled respawn). silent fail 차단. |

### 자동 반영 (best practice)
- **AD-3 token 단위 카운트**: SDK tool loop는 user message 1건당 N model call → token 누적이 정확. KST midnight reset 명시.
- **AD-4 SDK resume 비활성**: stale chart context drag 위험. session_id는 logging만, 매 응답은 fresh. symbol/timeframe만 SQLite 저장하고 매번 chart_set_symbol로 재드라이브.
- **AD-8 audit-safety 게이트 신설**: 02와 동일 차단 리스트(`config/blocked_auditors.yaml`)를 03도 참조. 차단 종목 분석 응답에 ⚠️ prefix. 차단 리스트는 manual sync (TODO-3로 자동화 후순위).
- **`private_indicators.json` 위치 변경**: `src/resources/` → `config/`. 패키징/commit 사고 방지.
- **screenshot 임시 저장 + unlink**: `data/screenshots/` 영구 저장 X. trade-secret leakage 방지.
- **analyze_prompt.md advice-shaped wording 회피 보강**: "BUY 시그널이니 진입" 같은 표현 금지, 인디케이터 저자 정의로 framing.
- **bot timeout/cancellation 처리**: try/finally + asyncio.wait_for로 timeout boundary. python-telegram-bot 핸들러 cancellation OK.
- **Edge cases 추가**: CDP localhost 9222 보안, lid-close 현실성, push/pull 메시지 prefix 분리.

### Deferral (TODOS.md)
- TODO-1: Phase 6 push 보강 (AD-5 deferral)
- TODO-2: 워치리스트 cron pre-fetch
- TODO-3: audit-safety 자동 동기화
- TODO-4: 인디케이터 자동 discovery (manual whitelist의 근본 개선)
- TODO-5/6/7: out of scope (Pine 자동 작성, fuzzy LLM, multi-user)
- TODO-8/9/10: 운영 메모

### 의도적 거부

- **"워치리스트 명령 자체 제거" (Codex 가장 강한 안)**: 사용자가 워치리스트를 핵심 use case로 명시. 제거 X. 대신 deterministic + LLM 1회로 비용 문제 해결.
- **"02 → 03 통합 재구조 (1)"**: ADR-0001 유지 + AD-6 token 공유로 single interface 달성.
- **"prompt caching 제거"**: AD-3 정밀화 후 1주 운영 데이터로 ROI 실측 → TODO-10. 즉각 제거 X.

## 다음 단계

- Plan lock 완료
- Codex CLI가 HANDOFF.md 입력으로 Phase 0b 검증부터 (GO/NO-GO 게이트 통과 후만 Phase 1+ 진입)
- Code review 단계: Tier 3 의무 cross-model 2단 (`/review` + `/security-review` + `/codex:adversarial-review`)
