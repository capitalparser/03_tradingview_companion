# CLAUDE.md — 03_tradingview_companion

> 프로젝트 컨텍스트. `~/vault/CLAUDE.md` + `~/vault/01_Projects/CLAUDE.md` 위에 누적되어 주입됨.

## 1. Project Mission

Telegram을 단일 인터페이스로 삼아 TradingView Desktop의 차트 상태(특히 사용자 본인의 프라이빗 시그널 인디케이터 출력)를 즉석에서 조회/해석하는 인터랙티브 챗봇. **보조 애널리스트** — 매수/매도 추천 X, 차트 상태 해석 O.

자매 프로젝트 `02_audit_safe_signals`는 push(alert webhook → Telegram), 본 프로젝트는 pull(인터랙티브 질의). 두 프로젝트는 코드/import 공유하지 않으며, 각자 독립적으로 동작한다 (project isolation 원칙).

## 2. Stack

- **Python 3.11** (uv 관리)
- `python-telegram-bot` — long-polling 방식
- `anthropic` SDK — Claude API + MCP 클라이언트
- `tradingview-mcp` (Node, 외부) — stdio로 spawn

## 3. Domain Vocabulary (이 프로젝트 한정)

자세한 도메인 용어는 `CONTEXT.md` 참조. 주요 항목:
- **CDP**: Chrome DevTools Protocol — TV Desktop이 Electron이라 9222 포트로 노출
- **study**: TradingView 차트에 적재된 인디케이터의 internal 명칭. `data_get_study_values`의 입력
- **plot/label**: 인디케이터가 차트에 그리는 출력. 프라이빗 인디케이터의 시그널은 보통 label로 표현됨
- **시그널 인디케이터**: 사용자 워치리스트에 적용된 진입/청산/돌파 등을 표시하는 프라이빗 Pine 스크립트
- **워치리스트**: 사용자가 모니터링하는 30종목 (한국 + 미국)

## 4. Architecture Conventions

- **모든 외부 호출에 timeout 명시** (Claude API 30s, MCP 30s, Telegram 10s)
- **chat_id 화이트리스트 미준수 호출 → 명시적 거부 + 로그**, silent ignore 금지
- **MCP 호출 실패 → 사용자에게 명시적 안내** ("TV Desktop 켜져있나요?"), silent fallback 금지
- **시크릿은 `os.environ`으로만 접근**, 코드에 하드코딩 금지
- **민감 자원** (`private_indicators.json`, `data/`)은 `.gitignore` 강제

## 5. File Layout

```
src/
├── bot/         # Telegram long-polling 핸들러 + 인증
├── claude/      # Claude SDK wrapper + 분석 프롬프트
├── mcp_client/  # tradingview-mcp 호출 추상화
└── resources/   # symbol_map.json, analyze_prompt.md, private_indicators.json (gitignored)
deploy/launchd/  # macOS 자동 시작
data/            # 로그, 스크린샷 (gitignored)
```

## 6. Output Style

- Telegram 응답: 표준 한국어, **결론 먼저** (verdict-first)
- 시그널 발화 여부 → 발화한 것만 명시 (미발화는 생략 가능)
- 가격/지표 수치는 정량적으로
- 추측은 "추정" 명시
- 매수/매도 추천 금지 — 데이터 해석만

## 7. Testing & Verification

- Phase별로 plan(`~/.claude/plans/shimmering-marinating-salamander.md`)의 verification 항목 충족 후 다음 phase로
- 운영 검증은 실제 Telegram 대화로 수동 확인 (자동화된 E2E는 TV Desktop 의존성으로 어려움)

## 8. External Dependencies (수정 금지)

- `~/code/tradingview-mcp/` — clone, 절대 수정 X (upstream PR이 아닌 한)
- TradingView Desktop — 사용자 직접 운영
- Fly.io `02_audit_safe_signals` — 본 프로젝트는 직접 의존하지 않음

## 9. Risks (운영 시 인지)

- TradingView 앱 업데이트 → CDP 호환성 깨질 수 있음 → MCP issue tracker 모니터링
- 프라이빗 인디케이터 study name 변경 → 화이트리스트 동기화 필요
- Anthropic API 비용 → 월 budget cap 권장
- 홈 머신 sleep/down → pull 경로 다운 (push는 영향 없음)
