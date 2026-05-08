# HANDOFF.md — Codex 인수 가이드

본 프로젝트는 Tier 3 워크플로우에 따라 Claude(Opus)가 **스캐폴드/골격까지**만 작성하고, 실제 코드 구현·테스트·디버깅은 **Codex CLI**가 인수한다. 본 문서는 인수 시점의 모든 입력을 한 곳에 정리한다.

---

## 1. 프로젝트 한 줄

홈 macOS에서 Telegram bot을 long-polling으로 운용하면서, 사용자 메시지를 **Anthropic Claude SDK + tradingview-mcp(stdio spawn)**로 처리하여 **TradingView Desktop**의 차트 상태/프라이빗 인디케이터 출력을 한국어로 해석해 응답한다. 매수/매도 추천 X — 보조 애널리스트.

자매 프로젝트 `02_audit_safe_signals`는 push(alert webhook → Telegram)를 담당하며 본 프로젝트와 코드/import 공유 X (project isolation).

## 2. 입력 자료 (이 순서로 읽을 것)

1. **`CLAUDE.md`** — 프로젝트 시스템 컨텍스트, stack 결정, 출력 스타일.
2. **`CONTEXT.md`** — 도메인 사전 (CDP, study, plot, label, 시그널 인디케이터 등).
3. **`docs/adr/0001-domain-and-architecture-seed.md`** — 5개 핵심 분기와 그 이유.
4. **`plans/2026-05-08-tradingview-companion-design.md`** — 승인된 전체 plan (사용자 ExitPlanMode 승인).
5. **`README.md`** — 외부 시야 한 줄.
6. **(zone 컨벤션)** `~/vault/01_Projects/CLAUDE.md` — Tier 3 의무 워크플로우, cross-model 리뷰 규칙.

## 3. 현재 스캐폴드 상태

```
.
├── CLAUDE.md, CONTEXT.md, README.md, LICENSE
├── HANDOFF.md (본 파일)
├── pyproject.toml (uv-ready)
├── .env.example, .gitignore
├── docs/adr/0001-domain-and-architecture-seed.md
├── plans/2026-05-08-tradingview-companion-design.md
├── src/tvc/
│   ├── config.py                    # 완성 — 시크릿/설정 로딩 (pydantic-settings)
│   ├── bot/
│   │   ├── auth.py                  # 시그니처만 (NotImplementedError)
│   │   ├── handlers.py              # 시그니처만
│   │   └── __main__.py              # 시그니처만
│   ├── claude_sdk/
│   │   └── analyst.py               # 시그니처만 (Protocol + 클래스)
│   ├── mcp_client/
│   │   └── chart_ops.py             # 시그니처만
│   └── resources/
│       ├── symbol_map.json          # 시드 (한국 5종 + 미국 5종)
│       ├── analyze_prompt.md        # 분석 출력 템플릿 (완성)
│       └── private_indicators.example.json  # 사용자가 채울 템플릿
├── tests/
│   ├── conftest.py                  # fake fixture 시그니처
│   └── unit/, integration/
└── deploy/launchd/com.tvcompanion.bot.plist.example
```

## 4. Codex가 채워야 할 작업 (Phase 매핑)

### Phase 1 — Bare-bones bot + Claude SDK echo

채울 곳:
- `src/tvc/bot/__main__.py: main()` — Settings 로딩 → Application 빌드 → 핸들러 등록 → run_polling
- `src/tvc/bot/auth.py: require_authorized()` — chat_id 추출 + 화이트리스트 검증 + structured 거부 로그
- `src/tvc/bot/handlers.py: handle_start, handle_text, handle_error` — Phase 1은 echo + Claude ping 정도
- `src/tvc/claude_sdk/analyst.py: Analyst.__init__` — Anthropic AsyncClient 보유 + system prompt 보유

검증:
- `uv sync && uv run python -m tvc.bot` 실행 후 본인 Telegram에서 `/start` → 환영 응답
- 비인가 chat_id에서 호출 → silent ignore 아님 (거부 메시지 + 로그)

### Phase 2 — MCP 도구 와이어링

채울 곳:
- `src/tvc/mcp_client/chart_ops.py` 모든 메서드 — `mcp` SDK의 stdio_client로 자식 프로세스 spawn, tool 호출
- `src/tvc/claude_sdk/analyst.py: analyze_symbol` — chart_set_symbol → chart_set_timeframe → chart_get_state → data_get_study_values → Claude 호출
- `src/tvc/bot/handlers.py: handle_text` — symbol_map.json으로 종목명 → ticker 변환 → analyst 호출 → 응답

검증:
- TV Desktop이 9222 포트로 켜져 있는 상태에서 `삼성전자 봐줘` → KRX:005930 차트 자동 전환 + 표준 지표 응답
- TV Desktop 미실행 → `ChartOpsCDPDown` raise → handler가 "TV Desktop 켜져있나요?" 안내

### Phase 3 — 프라이빗 인디케이터 화이트리스트

작업:
- 사용자가 `src/tvc/resources/private_indicators.json` 작성 (사용자 prerequisite — `private_indicators.example.json` 참고)
- `Analyst.analyze_symbol`이 화이트리스트 study name을 `chart_ops.get_study_values`에 전달
- 분석 프롬프트에 `private_signals` 컨텍스트 주입 → 시그널 발화 여부가 응답에 포함됨
- 미적재 케이스 → "프라이빗 인디케이터 미적재" 명시 후 표준 지표 fallback

### Phase 4 — chat_id별 컨텍스트

작업:
- `src/tvc/bot/`에 `ConversationStore` 추가 — chat_id → 마지막 (symbol, timeframe) 보유, in-memory dict로 시작
- 후속 메시지 (`위클리도`, `스크린샷`) 처리 — 컨텍스트의 symbol을 재사용하고 timeframe만 변경
- `capture_screenshot` 호출 후 Telegram photo 메시지로 전송

### Phase 5 — 워치리스트 + 자동 시작

작업:
- `src/tvc/resources/watchlist.json` (gitignored) — 사용자 워치리스트 30종목
- `handle_watchlist` — 순회하며 시그널 발화한 종목만 응답에 포함
- `deploy/launchd/com.tvcompanion.bot.plist`로 복사 + 경로 치환 + `launchctl load`
- `caffeinate -d` 또는 `pmset disablesleep` 운용 가이드를 README에 추가

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

- **silent fallback 금지**: TV 미실행, MCP 실패, 프라이빗 인디케이터 미적재 등은 모두 사용자에게 명시 메시지.
- **시크릿 하드코딩 금지**: 모두 `tvc.config.Settings`를 통해서만 접근.
- **외부 호출 모두 timeout**: Claude API 30s, MCP 30s, Telegram 10s.
- **chat_id 화이트리스트 미준수 호출 → 거부 + 로그**, silent ignore 금지.
- **02_audit_safe_signals import 금지**: project isolation. 동일 패턴이 필요하면 03 안에 재구현.
- **외부 의존(MCP, Anthropic, Telegram)은 Protocol로 격리**: 단위 테스트는 fake 사용 (`tests/fakes/`).
- **매수/매도 추천 응답 금지**: 데이터 해석으로만.

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
