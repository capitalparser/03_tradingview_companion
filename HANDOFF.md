# HANDOFF.md — Codex 인수 가이드

본 프로젝트는 Tier 3 워크플로우에 따라 Claude(Opus)가 **스캐폴드/골격까지**만 작성하고, 실제 코드 구현·테스트·디버깅은 **Codex CLI**가 인수한다. 본 문서는 인수 시점의 모든 입력을 한 곳에 정리한다.

---

## 1. 프로젝트 한 줄 (Option B 후, ADR-0003)

홈 macOS에서 Telegram bot을 long-polling으로 운용하면서, 사용자 메시지를 받아 **02_audit_safe_signals의 read endpoint**(`GET /signals/{ticker}`)로 가장 최근 webhook payload(37필드 v6.1)를 조회하고, **claude-agent-sdk** 로 한국어 해석 응답을 생성한다. **MCP는 부수 기능**(스크린샷 등)으로 격하. 매수/매도 추천 X — 보조 애널리스트.

`02_audit_safe_signals`와 같은 Telegram bot token 공유(AD-6, single interface). 03 → 02 단방향 HTTP 의존 허용(AD-10). 코드/import 공유는 여전히 금지.

## 2. 입력 자료 (이 순서로 읽을 것)

1. **`CLAUDE.md`** — 프로젝트 시스템 컨텍스트.
2. **`CONTEXT.md`** — 도메인 사전.
3. **`docs/adr/0001-domain-and-architecture-seed.md`** — 5개 핵심 분기 (AD-10 update 포함).
4. **`docs/adr/0002-plan-eng-review-decisions.md`** — AD-1~8 (plan-eng-review).
5. **`docs/adr/0003-pivot-to-02-read-endpoint.md`** — Option B pivot, AD-9~11. **반드시 준수**.
6. **`docs/specs/webhook_v6_1.md`** — 37필드 v6.1 명세 사본 (analyze prompt 컨텍스트).
7. **`docs/specs/02_read_endpoint_contract.md`** — 02 측 신규 작업 명세 (별도 spec).
8. **`plans/2026-05-08-tradingview-companion-design.md`** — 전체 plan + AD-1~11.
9. **`README.md`** — 외부 시야 + ToS disclaimer.
10. **(zone 컨벤션)** `~/vault/01_Projects/CLAUDE.md` — Tier 3 의무 워크플로우, cross-model 리뷰 규칙.

## 3. 현재 스캐폴드 상태 (post-Option-B)

```
.
├── CLAUDE.md, CONTEXT.md, README.md, LICENSE
├── HANDOFF.md (본 파일)
├── TODOS.md
├── pyproject.toml (claude-agent-sdk + python-telegram-bot + httpx + aiosqlite)
├── .env.example, .gitignore
├── config/
│   ├── blocked_auditors.yaml          # 02 sync (AD-8 + AD-10 후 의미 약화)
│   ├── private_indicators.example.json
│   └── private_indicators.json (.gitignored — 사용자가 채움. Option B 후 사실상 unused)
├── docs/
│   ├── adr/
│   │   ├── 0001-domain-and-architecture-seed.md
│   │   ├── 0002-plan-eng-review-decisions.md   # AD-1 ~ AD-8
│   │   └── 0003-pivot-to-02-read-endpoint.md   # AD-9 ~ AD-11 (Option B)
│   └── specs/
│       ├── webhook_v6_1.md                  # 37필드 인디케이터 명세 (analyze prompt 컨텍스트)
│       └── 02_read_endpoint_contract.md     # 02 측 신규 작업 spec
├── plans/2026-05-08-tradingview-companion-design.md
├── src/tvc/
│   ├── __init__.py
│   ├── config.py                    # 완성 (audit_signals_base_url/secret 추가)
│   ├── storage.py                   # 시그니처 — SQLiteConversationStore, SQLiteUsageGuard
│   ├── source/                      # 신규 (Option B)
│   │   ├── __init__.py
│   │   └── endpoint.py              # 시그니처 — 02 read endpoint client (httpx)
│   ├── bot/
│   │   ├── auth.py                  # 시그니처
│   │   ├── handlers.py              # 시그니처
│   │   └── __main__.py              # 시그니처
│   ├── claude_sdk/
│   │   └── analyst.py               # 시그니처 — Endpoint 1차, MCP는 보조 메서드
│   └── resources/
│       ├── symbol_map.json          # 시드 (10종)
│       └── analyze_prompt.md        # 분석 출력 템플릿
├── tests/
│   ├── conftest.py                  # fake fixture 시그니처
│   └── unit/, integration/
└── deploy/launchd/com.tvcompanion.bot.plist.example
```

**Option B 후 위상 변화**:
- `src/tvc/mcp_client/` 이미 제거 (claude-agent-sdk 위임)
- `src/tvc/source/` 신규 — 1차 데이터 소스. Option B의 핵심.
- `private_indicators.json` 의미 약화 — 02가 webhook payload로 다 받아오니 화이트리스트 불필요. 추후 MCP 보조 기능 활용 시 재의미.

## 4. Codex가 채워야 할 작업 (Phase 매핑)

### Phase 1 — Bare-bones bot + EndpointClient ping

채울 곳:
- `src/tvc/source/endpoint.py: EndpointClient` 모든 메서드 — httpx async, timeout 5s, 1회 retry
- `src/tvc/bot/__main__.py: main()` — Settings 로딩, EndpointClient + Analyst 인스턴스화, Telegram Application
- `src/tvc/bot/auth.py: require_authorized()` — chat_id 추출 + 화이트리스트 검증 + 거부 로그
- `src/tvc/bot/handlers.py: handle_start, handle_text, handle_error` — `/start`는 환영 + EndpointClient.health() 결과 표시. text는 echo + 02 health.

검증:
- `uv sync && uv run python -m tvc.bot` → Telegram에서 `/start` → "✅ 02 endpoint connected"
- 비인가 chat_id → 거부 메시지 + 로그 (silent ignore X)
- 02 endpoint 다운 시 → "⚠️ 02 endpoint unreachable" graceful

### Phase 2 — Claude 해석 (Option B 핵심, ADR-0003)

채울 곳:
- `src/tvc/claude_sdk/analyst.py: Analyst.__init__` — system_prompt = analyze_prompt + webhook_spec_md 결합. cache_control 적용.
- `Analyst.analyze_symbol`:
  1. `await self.endpoint.get_latest(ticker, timeframe)` → SignalRecord
  2. `record.payload is None` → graceful 응답 ("최근 알림 없음")
  3. `await self.usage.check_and_record(...)` (AD-3)
  4. `claude_agent_sdk.query(prompt=context_with_payload, options=ClaudeAgentOptions(system_prompt=cached, ...))` 호출
  5. audit_decision != "CLEAN" → ⚠️ prefix
- `bot/handlers.py: handle_text`:
  - 자연어 → ticker (`symbol_map.json` lookup), timeframe (정규식: `위클리`/`weekly`/`주봉` → "W", `1H`/`한시간` → "60")
  - analyst.analyze_symbol → store.put(chat_id, symbol, timeframe) → 응답

검증:
- 사용자가 TV에서 `KRX:005930` (4H) alert 1건 발사 → 02 webhooks 테이블에 row 1개
- Telegram에서 `삼성전자 봐줘` → 37필드 기반 한국어 해석 + audit_decision prefix (필요 시)
- `엔비디아` → NASDAQ:NVDA 매핑 + endpoint 호출 + 응답
- 매핑 실패 → 후보 제시 그래셰풀

### Phase 3 — 컨텍스트 유지 (AD-4 SQLite)

작업:
- `src/tvc/storage.py: SQLiteConversationStore` 구현 — `aiosqlite`. Schema는 docstring 참조.
- 후속 메시지 (`위클리도`, `1H 봐줘`) — `Analyst.analyze_followup`이 `store.get(chat_id)` → 새 timeframe으로 endpoint 재조회
- `capture_screenshot` 명시 요청 시 → `analyze_with_screenshot` (lazy MCP spawn)
- bot 재시작 후 동일 동작 확인

### Phase 4 — 워치리스트 (AD-7, Option B 재설계)

작업:
- `config/watchlist.json` (gitignored) — `[{"ticker": "KRX:005930", "timeframes": ["240", "D"]}, ...]`
- `Analyst.analyze_watchlist`:
  - 모든 (ticker, tf) 조합을 `asyncio.gather`로 동시 endpoint 호출 (mutex 불필요 — endpoint 동시 호출 OK)
  - 응답에서 `action == "BUY"` 종목만 필터 (deterministic, LLM 없음)
  - 발화 N개 모아서 LLM 1회 요약
  - 10종목 처리마다 progress callback
- `handle_watchlist` — 발화만 최종 요약. 일괄 진행 중 단일 질의는 endpoint 동시성 OK라 끼어들기 가능.
- 회귀 검증: 단일 종목 질의 응답이 일괄 추가 후에도 동일 시간/형식

### Phase 5 — 운영 자동화 + (선택) MCP 보조

작업:
- `SQLiteUsageGuard` 임계값 동작 검증 (AD-3)
- `deploy/launchd/com.tvcompanion.bot.plist`로 복사 + 경로 치환 + `launchctl load`
- `caffeinate -d` 운용 가이드를 README에 추가
- (선택) MCP 보조 기능: `analyze_with_screenshot` 채우기 — claude-agent-sdk의 `mcp_servers` 옵션 + `capture_screenshot` 호출. lazy spawn (사용자 명시 요청 시만)
- (선택) MCP가 안 되면 자동으로 disable, "스크린샷 미지원" graceful 응답

## 5. 외부 의존 (Codex가 직접 처리)

```bash
# 의존성 동기화 (uv 권장 — 02와 일치)
cd ~/vault/01_Projects/03_tradingview_companion
uv sync --all-extras

# 단위 테스트 (live 제외)
uv run pytest

# live 통합 테스트 (TV Desktop + Telegram + Anthropic 필요)
uv run pytest -m live
```

## 6. 사용자 prerequisite (Codex 손 밖)

다음은 사용자가 직접 해야 함. Codex는 README와 `.env.example`로 가이드만 제공:

| 항목 | 방법 | 확인 |
|---|---|---|
| TradingView Desktop 설치 | `https://www.tradingview.com/desktop/` | `/Applications/TradingView.app` 존재 |
| 디버그 포트 활성화 | macOS alias `tv='open -a TradingView --args --remote-debugging-port=9222'` | `curl localhost:9222/json/version` 응답 |
| 차트 템플릿 | TV 앱에서 프라이빗 인디케이터 적재 → "Default" 템플릿으로 저장 | 새 종목 오픈 시 인디케이터 자동 적용 |
| Telegram bot | BotFather에서 **새 봇** 발급 (02와 별개, isolation) | bot token 획득 |
| chat_id | @userinfobot에 메시지 → 본인 chat_id 확인 | 정수 ID |
| Anthropic API key | https://console.anthropic.com | sk-ant-... |
| `.env` 채우기 | `cp .env.example .env && chmod 600 .env` 후 값 채움 | 위 모두 입력 |
| `private_indicators.json` | TV에서 인디케이터 우클릭 → Properties → ID 정확히 추출 → JSON 작성 | gitignored |

## 7. 가드레일 (반드시 준수)

- **silent fallback 금지**: 02 endpoint 다운, payload null, MCP 실패 등은 모두 사용자에게 명시 메시지.
- **시크릿 하드코딩 금지**: 모두 `tvc.config.Settings`를 통해서만 접근.
- **외부 호출 모두 timeout**: SDK query 30s, EndpointClient 5s, Telegram 10s.
- **chat_id 화이트리스트 미준수 호출 → 거부 + 로그**, silent ignore 금지.
- **02_audit_safe_signals import 금지** (AD-10): HTTP endpoint 호출만. 코드/import 공유 X. 양방향 의존(02 → 03) 금지.
- **AD-1 (격하)**: MCP는 보조 — `analyze_with_screenshot` 같은 메서드에서만 lazy spawn. Bot startup에 항상 spawn 안 함.
- **AD-2 mutex**: MCP-touching 호출에만 `asyncio.Lock`. 02 endpoint 호출은 동시성 OK (`asyncio.gather`).
- **AD-3 cost cap**: 모든 LLM query 전에 `UsageGuard.check_and_record()` 통과. raise 시 graceful 변환.
- **AD-4 영속성**: chat_id 컨텍스트는 SQLite `data/state.db`. in-memory 단독 금지. SDK `resume` 사용 X (stale 위험).
- **AD-7 deterministic**: 워치리스트는 endpoint 응답 코드 필터 후 LLM 1회만.
- **AD-9 1차 source**: `Analyst.analyze_symbol`의 데이터 source는 항상 EndpointClient 우선. MCP 직접 호출은 명시 메서드만.
- **AD-10 단방향**: 03 → 02만. 02가 03을 호출하지 않음. 02 다운 시 03 graceful degradation.
- **prompt caching**: webhook spec + analyze prompt를 system prompt에 `cache_control={"type": "ephemeral"}` 적용.
- **단위 테스트 격리**: `EndpointClient`는 Protocol로 fake 가능. `claude-agent-sdk.query`는 monkeypatch.
- **매수/매도 추천 응답 금지**: 데이터 해석으로만. analyze_prompt 정책 따름.

## 8. Cross-model 리뷰 규칙 (Tier 3 의무)

`~/vault/01_Projects/CLAUDE.md`에 따라 다음 두 단계는 **사용자가 슬래시 커맨드로 직접 호출**한 후에만 Codex가 코드 작성에 진입한다:

1. **Plan 리뷰 (a)** — 새 Opus 세션에서 `/plan-eng-review`
2. **Plan 리뷰 (b)** — `/codex:rescue` 또는 `/codex:review`

리뷰 차이는 `plans/` 또는 `docs/adr/{NNNN}-review-findings.md`에 머지된 후 plan 확정.

## 9. Code 리뷰 (구현 완료 시점, Tier 3 의무)

- **(a) Opus** `/review` + `/security-review`
- **(b) Codex** `/codex:adversarial-review`
- 결과 차이는 `docs/adr/{NNNN}-review-findings.md`에 기록.

## 10. 한 줄 요약

**Phase 1 → 2 → 3 → 4 → 5 순서로 NotImplementedError를 채우되, 매 phase 끝에 사용자 수동 검증 통과 후 다음 phase 진입.** 모든 외부 호출은 격리된 Protocol을 통해서만, 외부 호출 실패는 명시 안내, 시크릿은 Settings를 통해서만.
