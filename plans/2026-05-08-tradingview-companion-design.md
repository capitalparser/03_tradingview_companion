# TradingView Companion — Push + Pull 통합 시스템

## Context

**왜 만드는가.** 사용자(김경준, 회계법인 인차지)는 시간이 제약적이며 모바일에서 작업 비중이 높음. 현재 두 가지가 분리되어 있음:
- **Push (이미 운영중, `02_audit_safe_signals`)**: TradingView 매수 시그널 webhook → 감사인 차단 필터 → Telegram 알림 (Fly.io)
- **Pull (없음)**: 즉석에서 "이 종목 차트 어때?"라고 물어보고 답을 받는 인터랙티브 채널

이 둘을 **단일 Telegram 인터페이스**로 통합하고, 거기에 **TradingView MCP**를 결합해서 차트 분석/프라이빗 인디케이터 추출까지 한 채널에서 처리한다.

**무엇이 핵심인가.** TradingView 데스크톱은 사용자 본인 계정으로 로그인된 상태이며, 사용자가 작성한/구독한 **프라이빗 시그널 인디케이터**(진입/청산/돌파 등)가 차트에 적재되어 있음. MCP는 Chrome DevTools Protocol을 통해 **이 프라이빗 인디케이터의 출력값과 alert 시그널까지 그대로 추출 가능** (소스 코드는 못 읽지만 plot/signal/label 모두 OK).

**지금 시점의 결정.**
- 새 프로젝트로 분리: **`~/vault/01_Projects/03_tradingview_companion/`** (가칭 — 사용자 변경 가능)
- 기존 `02_audit_safe_signals`는 그대로 유지 (project isolation 원칙)
- 두 프로젝트는 코드/import 공유 X, 환경변수(Telegram token)만 별도 관리
- GitHub: **public repo** (인디케이터 소스는 어차피 TradingView 서버 측. 민감 파일은 .gitignore)

## Vision (단일 그림)

```
┌─────────────── 모바일 Telegram (단일 인터페이스) ───────────────┐
│                                                                │
│  ⬇ Push (자동)                       ⬆ Pull (인터랙티브)         │
│                                                                │
└────────────┬─────────────────────────────────┬─────────────────┘
             │                                 │
             │                                 │
   ┌─────────▼──────────┐           ┌──────────▼──────────────┐
   │  Fly.io (이미 동작)  │           │  홈 머신 (신규)            │
   │  audit_safe_signals │           │  03_tradingview_companion│
   │                    │           │                         │
   │  TV alert webhook  │           │  Telegram bot (long poll)│
   │  → 감사인 필터      │           │  → Claude SDK            │
   │  → Telegram push   │           │  → tradingview-mcp       │
   │                    │           │  → TV Desktop (CDP 9222) │
   └────────────────────┘           └─────────────────────────┘
             ▲                                 ▲
             │ webhook POST                    │ CDP
             │                                 │
   ┌─────────┴─────────────────────────────────┴─────────────────┐
   │                  TradingView Desktop (홈 머신)                │
   │  - 사용자 로그인 상태                                          │
   │  - 프라이빗 인디케이터 적재된 차트 템플릿                          │
   │  - alert이 webhook으로 발사됨                                  │
   └────────────────────────────────────────────────────────────┘
```

## Goal / Non-goals

### Goal
1. Telegram 단일 인터페이스에서 push 알림과 pull 질의 모두 처리
2. **프라이빗 인디케이터의 plot/signal/label**을 alert(push)와 인터랙티브 분석(pull) 양쪽에서 추출
3. 홈 머신에서 24/7 동작 (또는 trading hours 자동 ON)
4. 코드는 public GitHub OK, 민감 파일은 git ignore
5. project isolation 준수 — 02와 03은 독립

### Non-goals
- 자동매매 / 거래소 API 주문 — 이번 범위 외
- 클라우드에서 TradingView Desktop 실행 (xvfb 등 우회) — 운영 부담 큼, 홈 머신으로
- 02_audit_safe_signals를 03이 import — isolation 위반
- 매수/매도 추천 — 보조 애널리스트 컨셉
- Pine Script 자동 작성 — 다른 시나리오

## 새 프로젝트 구조

```
~/vault/01_Projects/03_tradingview_companion/
├── CLAUDE.md                    # 프로젝트 컨텍스트 (Tier 3)
├── CONTEXT.md                   # 도메인 용어
├── README.md                    # 셋업/운영
├── .gitignore                   # 민감 파일 제외
├── .env.example                 # 환경변수 템플릿
├── pyproject.toml or package.json (스택 결정 필요)
├── src/
│   ├── bot/                     # Telegram bot (long-polling)
│   │   ├── handlers.py          # 명령/메시지 핸들러
│   │   └── auth.py              # 사용자 ID 화이트리스트
│   ├── claude/                  # Claude SDK 통합
│   │   └── analyst.py           # 분석 프롬프트 + MCP 호출 wrapper
│   ├── mcp_client/              # tradingview-mcp 호출
│   │   └── chart_ops.py         # 심볼 전환/지표 추출/스크린샷
│   └── resources/
│       ├── symbol_map.json      # 종목명 ↔ ticker (public OK)
│       ├── analyze_prompt.md    # 분석 출력 템플릿 (public OK)
│       └── private_indicators.json   # 화이트리스트 (.gitignore)
├── data/
│   └── (logs, screenshots — .gitignore)
└── deploy/
    └── launchd/                 # macOS launchd plist (자동 시작)
```

## Architecture

### Push 경로 (보강)
- **그대로 유지**: `02_audit_safe_signals`의 webhook → 필터 → Telegram 흐름
- **선택 보강** (out of MVP): 통과한 alert에 대해 03이 차트 스크린샷 생성하는 "screenshot service"를 03에 추가하고, 02가 그걸 호출 — **또는** 02가 alert을 broker(Redis/file)에 적재 → 03이 polling — isolation 원칙 위반 우려 있어 **MVP에서는 안 건드림**
- **권장 MVP 형태**: 워치리스트 종목들의 alert webhook URL을 02_audit_safe_signals와 동일 endpoint에 추가 등록만 — Telegram 메시지 prefix로 구분

### Pull 경로 (신규, 03의 핵심)
1. **사용자 → Telegram**: `삼성전자 봐줘`, `엔비디아 위클리`, `워치리스트 시그널`
2. **bot 핸들러** → 메시지 파싱 → Claude SDK 호출 prompt 구성
3. **Claude SDK** → tradingview-mcp 도구 사용:
   - `chart_set_symbol`, `chart_set_timeframe`
   - `data_get_study_values` (프라이빗 인디케이터 화이트리스트 기반)
   - `chart_get_state` (OHLC, 추세)
   - `capture_screenshot` (옵션)
4. **Claude 해석** → 한국어 답변 생성
5. **bot → Telegram**: 텍스트 + (옵션) 스크린샷 첨부

### 인증
- Telegram bot이 **사용자 본인 chat_id 화이트리스트**만 허용 — 외부 침입 차단
- bot token은 `.env`로 분리, 코드에서는 `os.environ`으로 읽음

## Components

| 부품 | 역할 | 위치 |
|---|---|---|
| `tradingview-mcp` | CDP를 통한 TV Desktop 조종 | `~/code/tradingview-mcp/` (clone) |
| TradingView Desktop | Premium 로그인 + 프라이빗 인디케이터 템플릿 | 홈 머신 (macOS) |
| Telegram bot (Python `python-telegram-bot` 권장) | 메시지 long-polling, 핸들러 라우팅 | `03_tradingview_companion/src/bot/` |
| Claude SDK 통합 | bot 메시지 → MCP 도구 호출 → 답변 생성 | `03_tradingview_companion/src/claude/` |
| 심볼 매핑 사전 | 한국어 종목명 → ticker 변환 | `src/resources/symbol_map.json` |
| 프라이빗 인디케이터 화이트리스트 | study name 목록 + 추출 우선순위 | `src/resources/private_indicators.json` (.gitignore) |
| 분석 프롬프트 템플릿 | "추세/모멘텀/거래량/시그널" 표준 출력 | `src/resources/analyze_prompt.md` |
| launchd plist | macOS 자동 시작 (bot + TV 깨우기) | `deploy/launchd/` |

### 스택 결정 (확정)
- **Python 3.11** — `02_audit_safe_signals`와 일치, 사용자 친숙도, `python-telegram-bot` 안정성
- **`claude-agent-sdk` (Python)** — 구 Claude Code SDK rename, MCP stdio spawn 내장, tool loop 자동, session resume 지원. (검토에서 `anthropic` SDK 직접 사용 대신 채택)
  - 인증: **API key 모드 확정** (Anthropic은 third-party 앱의 claude.ai/Pro/Max OAuth를 명시적으로 금지: "Unless previously approved, Anthropic does not allow third party developers to offer claude.ai login or rate limits for their products, including agents built on the Claude Agent SDK")
  - prompt caching: 정적 분석 프롬프트(analyze_prompt.md)에 적용 → 비용 90% 절감 기대
- **tradingview-mcp**: Node 서버, SDK의 `mcp_servers` 옵션으로 stdio spawn (직접 spawn 코드 작성 불필요)

## User Flows

### Flow 1: Push (alert → Telegram)
```
TradingView Desktop alert 발화
  → webhook POST → Fly.io audit_safe_signals
  → 감사인 차단 리스트 통과 검증
  → Telegram 메시지: "🟢 BUY 시그널 — 삼성전자 (KRX:005930) | 2026 감사인 통과 | score 7.2"
```
**MVP에서는 추가 작업 거의 없음** — 워치리스트 종목별 alert을 사용자가 TV에서 webhook URL 등록만.

### Flow 2: Pull 단순 질의
```
사용자: 삼성전자 봐줘
  → bot 수신
  → Claude: "삼성전자" → KRX:005930
     → mcp.chart_set_symbol("KRX:005930")
     → mcp.chart_set_timeframe("1D")
     → mcp.data_get_study_values([엔트리_시그널, 청산_시그널, 돌파_시그널, EMA, RSI])
     → mcp.chart_get_state()
  → Claude 해석 → Telegram 응답:
    "삼성전자 (KRX:005930) 일봉
     ━━━━━━━━━━━━━━━━━━━━
     • 가격: 75,200 (+1.2%)
     • 엔트리_시그널: BUY (어제 발화)
     • 돌파_시그널: 미발화
     • 청산_시그널: 미발화
     • EMA20 정배열, RSI 62 (과매수 근접)
     • 거래량 평균 1.4배"
```

### Flow 3: Pull 컨텍스트 유지
```
사용자: (위 응답 직후) 위클리도
  → bot이 직전 컨텍스트(symbol=KRX:005930) 인지
  → mcp.chart_set_timeframe("1W")
  → 같은 인디케이터 재추출 → 비교 응답
```
**구현 노트**: 컨텍스트는 chat_id별 in-memory dict로 시작, 추후 SQLite 가능.

### Flow 4: Pull 워치리스트 일괄
```
사용자: 워치리스트 시그널 체크
  → 사전 등록된 워치리스트 30종목 순회
  → 각 종목 chart_set_symbol → 시그널 추출 → 발화 종목만 응답
  → "🟢 BUY 발화 3종목: 삼성전자, 카카오, 셀트리온 / 🔴 청산 1종목: 네이버"
```

### Flow 5: Pull 스크린샷
```
사용자: 엔비디아 차트 보여줘
  → 차트 전환 → mcp.capture_screenshot()
  → Telegram 사진 메시지로 전송
```

## Setup Steps (one-time)

1. **TradingView Desktop 디버그 포트 활성화** (macOS alias)
   ```bash
   alias tv='open -a "TradingView" --args --remote-debugging-port=9222'
   ```
   검증: `curl http://localhost:9222/json`

2. **차트 템플릿 준비** (TV 앱 측)
   - 프라이빗 인디케이터(엔트리/청산/돌파 등) 적재된 템플릿을 "Default"로 저장

3. **MCP 서버 설치**
   ```bash
   git clone https://github.com/tradesdontlie/tradingview-mcp ~/code/tradingview-mcp
   cd ~/code/tradingview-mcp && npm install
   ```

4. **새 프로젝트 스캐폴드**
   ```bash
   mkdir -p ~/vault/01_Projects/03_tradingview_companion
   cd ~/vault/01_Projects/03_tradingview_companion
   # 파일 구조 생성, pyproject.toml/uv 셋업
   ```

5. **`.env` 작성** (chmod 600, .gitignore)
   ```
   TELEGRAM_BOT_TOKEN=...
   TELEGRAM_AUTHORIZED_CHAT_IDS=...    # 본인 chat_id (콤마 구분)
   ANTHROPIC_API_KEY=...
   TV_DEBUG_PORT=9222
   ```

6. **워치리스트 / 인디케이터 사전 시드**
   - `symbol_map.json`: KOSPI 200 + 사용자 워치리스트 + 미국 빅테크
   - `private_indicators.json`: TV에서 차트 우클릭 → 인디케이터 정확한 study name 확인 후 작성
   - `analyze_prompt.md`: 표준 출력 형식

7. **macOS 자동 시작**
   - `pmset` 또는 `caffeinate -d`로 sleep 방지 (trading hours만 옵션)
   - launchd plist로 bot 자동 시작 (시스템 로그인 시)
   - TV Desktop은 Login Items에 등록

8. **Telegram alert webhook URL 등록** (TV 측, 푸시 경로)
   - 워치리스트 종목별 alert을 02_audit_safe_signals webhook URL에 발사하도록 등록

## Implementation Phases

**순서 변경 (Codex outside voice 반영)**: 0b (MCP feasibility) → 0a (repo bootstrap). MCP가 프라이빗 인디케이터 출력을 신뢰성 있게 추출 못 하면 전체 plan 무효이므로 ceremony보다 existential test가 먼저.

### Phase 0a → ✅ 이미 완료 (GitHub repo bootstrap)

이번 plan 실행 중 이미 처리됨. https://github.com/capitalparser/03_tradingview_companion 생성 + scaffold 푸시.

### Phase 0b — MCP feasibility (CRITICAL — 진행 전 GO/NO-GO 게이트)

**진정한 Phase 0**. 이 단계 통과 못 하면 Phase 1+ 진행 X.

- [ ] TradingView Desktop 설치 + `--remote-debugging-port=9222` 플래그 launch 검증 (`open -a` 방식이 안 되면 `/Applications/TradingView.app/Contents/MacOS/TradingView` 직접 실행 fallback)
- [ ] `curl localhost:9222/json/version` 정상 응답
- [ ] tradingview-mcp의 `tv_health_check` 도구 직접 호출
- [ ] **결정적 검증**: 사용자 차트에 프라이빗 인디케이터 1개 적재 → MCP `data_get_study_values`로 plot/label 값을 실제로 읽을 수 있는지 raw inspection. **읽을 수 없으면 STOP — plan 폐기 또는 큰 재설계**.
- [ ] tradingview-mcp가 우리 가정한 도구명 (`chart_set_symbol`, `chart_set_timeframe`, `chart_get_state`, `data_get_study_values`, `capture_screenshot`)을 모두 노출하는지 `tv_list_tools` 또는 README로 확인 (가정이 fiction 아닌지)
- [ ] **Goal**: 다음 모든 답이 Yes — (1) TV Desktop CDP launch OK, (2) MCP 연결 OK, (3) 프라이빗 인디케이터 plot/label 값 추출 OK, (4) 가정한 도구명 실재.

### Phase 1 — Bare-bones bot (Telegram echo + Claude SDK)
- [ ] `03_tradingview_companion` 디렉토리 + Python 스캐폴드
- [ ] `.env` 셋업, chat_id 화이트리스트
- [ ] Telegram bot이 메시지 받으면 Claude SDK로 단순 echo 응답
- [ ] **Goal**: bot 인프라 + Claude API 통합 검증

### Phase 2 — MCP 도구 통합
- [ ] Claude SDK가 tradingview-mcp를 stdio로 spawn
- [ ] `삼성전자 봐줘` → 차트 전환 + 표준 지표 추출 + Telegram 응답
- [ ] **Goal**: end-to-end 단순 케이스 동작

### Phase 3 — 프라이빗 인디케이터 화이트리스트
- [ ] 사용자가 차트에서 study name 정확히 추출 → JSON 작성
- [ ] `data_get_study_values`로 프라이빗 시그널 raw 출력 → Telegram에 그대로 표시 (디버그)
- [ ] 분석 프롬프트에서 시그널 발화 여부 해석 추가
- [ ] **Goal**: 프라이빗 시그널이 응답에 포함됨

### Phase 4 — 컨텍스트 유지 + 후속 질의
- [ ] chat_id별 마지막 symbol/timeframe in-memory 저장
- [ ] `위클리도`, `스크린샷` 등 단축 명령 처리
- [ ] **Goal**: 자연스러운 대화 흐름

### Phase 5 — 워치리스트 일괄 + 자동 시작 (재설계)

**Codex outside voice 반영**: 종목당 LLM 호출 X. 결정론적 추출 + 1회 LLM 요약.
- [ ] 워치리스트 30종목 순회: MCP study values 추출만 (LLM 호출 없음)
- [ ] 코드 규칙으로 "BUY 발화 시그널" 필터링 (단순 lookup, deterministic)
- [ ] 발화 종목 N개 모아서 LLM 1회 호출로 자연어 요약
- [ ] 진행 중 5종목당 점진 메시지 ("[3/30] 처리 중") — AD-2
- [ ] launchd plist + caffeinate 셋업
- [ ] **Goal**: 24/7 운영 준비, 일괄 비용 90% 절감

### ~~Phase 6 (선택) — Push 경로 보강~~  *(제거, 별도 spec으로 분리)*
plan-eng-review에서 결정: ADR-0001 isolation 원칙과의 갈등이 명확하지 않고 가치 검증 미흡. MVP 운영 1-2개월 후 패턴이 보이면 별도 spec으로 재검토.

## Architecture Decisions (plan-eng-review)

`plan-eng-review` 결과 반영된 결정. 코드 구현 시 반드시 준수.

### AD-1. MCP 자식 프로세스 라이프사이클 — Bot startup 1회 spawn + health check 보강
- `bot/__main__.py`가 `claude-agent-sdk`의 `mcp_servers` 옵션으로 tradingview-mcp를 1회 spawn, bot lifetime 동안 영구 보유
- launchd `KeepAlive=true`로 bot crash → 자동 재시작 → MCP 자동 재spawn
- **AD-1.1 (Codex outside voice 반영) — Health check + controlled respawn**: 매 query 직전에 가벼운 health probe (예: `tv_health_check` 또는 `chart_get_state` 단순 호출). 30s timeout 또는 명백한 CDP 단절 감지 시 SDK 재초기화 → 자식 MCP 재spawn. bot 자체는 살아 있으면서 MCP만 wedge되는 silent-fail 경로 차단.
- **금지**: per-request spawn (응답 0.5-2s 지연), 자체 supervisor (복잡도 비례 가치 없음)

### AD-2. 동시성 — Mutex 직렬화 + 점진 응답
- TV Desktop은 단일 차트만 동시 표시. 모든 MCP 호출은 단일 `asyncio.Lock`으로 직렬화
- 동시 사용자 질의는 큐에 적재 + "X종목 처리 중" 피드백
- 워치리스트 일괄(30종목): 5종목씩 잠정 응답 ("BUY 3종목 수신 중...") → 최종 요약. 종목당 4초 추정 → 약 2분 소요
- **금지**: TV 차트를 "보이지 않게" 두는 트릭 (CDP가 active chart에 의존)

### AD-3. API 비용 보호 — 이중 방어 (Codex 반영 후 정밀화)
- **코드 cap (1차)**: SQLite `data/usage.db`에 **per-query 단위가 아니라 SDK 콜백으로 토큰별 누적**. Agent SDK tool loop는 user message 1건당 N model call 발생 가능 → SDK의 `on_message` 또는 streaming response의 token count를 그대로 누적. KST midnight reset (사용자 거주지 기준).
  - WARN: `daily_input_tokens >= 800K` 또는 `daily_usd_estimate >= $5` → "오늘 사용량 한도 근접 — 계속할까요?" 사용자 확인
  - HARD STOP: `daily_input_tokens >= 2M` 또는 `daily_usd_estimate >= $10` → "한도 초과, 내일 다시" 거부
- **estimate USD는 가이드라인일 뿐**: 실제 비용은 input/output/cache hit 비율로 다름. estimate 함수는 보수적(상한 추정)으로 → 실제 < estimate 보장.
- **콘솔 cap (2차, backstop)**: Anthropic Console에서 월 USD 한도 (사용자 prerequisite — 안전한 catastrophic 보호).
- KST 자정 reset 명시 (NYSE 거래는 KST 23:30~06:00 → reset 시점이 NYSE 한가운데 떨어짐 — 의도적: 사용자가 KST에 살므로 24h cycle은 KST 자정 기준이 자연스러움).

### AD-4. 컨텍스트 영속화 — SQLite (Codex 반영 후 보수화)
- `data/state.db`에 `chat_id → (last_symbol, last_timeframe, updated_at)` 저장 (session_id는 logging용, **resume에는 사용하지 않음**)
- bot 재시작/crash 후에도 "위클리도" 후속 질의 동작 — symbol을 직접 재드라이브 (chart_set_symbol → chart_set_timeframe)
- TV가 다른 차트를 표시 중일 가능성 항상 가정 → "위클리도" 처리 시 무조건 chart_set_symbol(last_symbol) 먼저
- 30일 미사용 row는 cleanup cron으로 제거
- **SDK `resume` 비활성화 (Codex 반영)**: 시간 지난 LLM 대화 상태를 resume하면 stale chart 컨텍스트/recommendation이 새 응답에 섞일 위험. session_id는 logging만, 매 응답은 fresh. 손해는 prompt cache hit 약화 정도.

### AD-5. Phase 6 (Push 보강) — 본 plan에서 제거
- 운영 경험 1-2개월 누적 후 별도 spec으로 재검토. ADR-0001 isolation 원칙 유지.

### AD-6. Telegram bot 정체성 — 02와 같은 봇, token 공유 (Codex 반영)
- 02_audit_safe_signals와 **같은 Telegram bot token, 같은 chat**. Single Telegram interface vision 진정 달성.
- ADR-0001의 isolation 원칙 업데이트: "코드/import는 분리, **Telegram bot token은 명시적 공유 자원**" 예외 명시.
- 운영: 02는 push (Fly.io), 03은 pull (홈 머신). 같은 bot이지만 다른 process가 다른 endpoint를 쓰므로 token 공유로 충돌 X (Telegram bot은 long-polling을 한 process에만 허용 — 03이 long-poll, 02는 push only로 send 메서드만 호출, 충돌 없음).
- **단**: bot token revoke/rotate 시 양쪽 동시에 .env 갱신 필요. 운영 메모.

### AD-7. 워치리스트 = 결정론적 추출 + 1회 LLM 요약 (Codex 반영)
- 30종목 순회: 각 종목당 MCP `data_get_study_values` 호출하여 정수/문자열 값만 추출 (**LLM 호출 없음**)
- 발화 필터링은 코드 (예: `if entry_signal == "BUY": fired.append(...)`) — 결정론적
- 발화 종목 N개를 모아서 LLM 1회 호출로 자연어 요약
- 비용: 30 × LLM → 1 × LLM. 약 90%-97% 절감 (큰 차이)
- 시간: TV 차트 전환은 여전히 종목당 ~3-4s. 30 × 4s = 약 2분 (변하지 않음). 절감은 비용에서.

### AD-8. 결정론적 audit-safety 게이트 (Codex 반영, 신규)
- 02_audit_safe_signals는 차단 리스트 기반 BUY 차단을 명시. 03은 같은 종목을 pull로 답하면 정책 drift.
- **결정**: 03도 동일 차단 리스트(`02/config/blocked_auditors.yaml` 또는 그 사본)를 참조하여, 차단 종목에 대한 분석 응답에 **명시적 audit-safety 경고 prefix** 부착. 분석 자체는 거부하지 않음 (정보 제공).
- 차단 리스트는 **수동 동기화** (코드 import 금지). `config/blocked_auditors.yaml`을 별도로 관리하고, 02 측 변경이 있을 때마다 사용자가 두 곳을 수동 갱신. 정책 변경 reasoning은 ADR로 관리.

## Edge Cases

- **TV Desktop 미실행/sleep** → bot이 명시적 안내 메시지, silently fail 금지
- **CDP 포트 미활성** → bot 시작 시점에 health check, 실패 시 본인 chat_id로 alert
- **프라이빗 인디케이터 study name 변경** → 화이트리스트 mismatch → 표준 지표만 fallback + 알림
- **심볼 매핑 실패** → 후보 제시 (`삼성전자 → KRX:005930? KOSPI:005930?`)
- **TV 유료 플랜 만료** → Premium-only 데이터 누락 명시
- **Anthropic API rate/quota** → 비용 모니터링 (월 사용량 제한 설정 권장)
- **Telegram bot이 외부에 노출** → chat_id 화이트리스트 미준수 호출 거부 + 로그
- **MCP 호출 timeout** (TV Desktop 응답 지연) → 30초 timeout 후 graceful fail
- **TradingView 앱 업데이트로 CDP 호환성 깨짐** → MCP 서버 issue tracker 모니터링 (외부 의존 리스크)
- **워치리스트 일괄 중 사용자 단일 질의** → 큐 우선순위 (단일이 일괄 사이에 끼어들기) 또는 거부 ("일괄 처리 중, X종목 남음")
- **API daily cap 도달** → graceful "오늘 사용량 한도" 메시지, 다음날 자동 reset (UTC midnight 기준 vs KST 자정 명시 필요)
- **SQLite state.db 손상** → bot 시작 시 schema 검증 후 손상이면 backup 후 재생성 + 본인 chat_id로 알림
- **스크린샷 데이터 leak** (Codex 반영) → `capture_screenshot`은 임시 파일에 저장 후 Telegram 송신 즉시 unlink. `data/screenshots/` 영구 저장 X (계정 UI / 워치리스트 / 차트 layout이 trade secret 가능)
- **CDP localhost:9222 보안** (Codex 반영) → 같은 머신의 다른 process가 차트 세션 inspect/control 가능. 신뢰할 수 없는 프로세스/사용자가 같은 macOS에 없는 환경 가정. 가정 깨질 시 firewall 또는 SSH tunnel only 권장.
- **TV alert webhook 시점 ↔ 03 pull 충돌** → push와 pull이 같은 Telegram chat에 메시지 전송 → user 입장에서 시각적 noise. 메시지 prefix로 구분 (Push는 `🔔` Pull은 `📊`).

## 보안 / 운영

- `.env`는 git ignore + chmod 600
- Telegram bot token은 BotFather에서 발급, 노출 시 즉시 revoke
- chat_id 화이트리스트 미준수 호출은 명시 거부 + 로그
- `private_indicators.json`은 git ignore (인디케이터 이름이 trade secret 가능성)
- 추출된 시그널 값/스크린샷은 `data/`에 저장하되 git ignore
- Public GitHub repo여도 위 파일들이 안 올라가면 안전

## Critical Files (생성/수정)

### 신규 (03_tradingview_companion/)
- `CLAUDE.md`, `CONTEXT.md`, `README.md`
- `.gitignore`, `.env.example`
- `pyproject.toml`
- `src/bot/handlers.py`, `src/bot/auth.py`
- `src/claude/analyst.py`
- `src/mcp_client/chart_ops.py`
- `src/resources/symbol_map.json`
- `src/resources/analyze_prompt.md`
- `src/resources/private_indicators.json` (.gitignore)
- `deploy/launchd/com.tvcompanion.bot.plist`

### 외부 (사용자 작업, 수정 X)
- `~/code/tradingview-mcp/` (clone, 수정 X)
- `~/.claude.json` 또는 `.mcp.json` (선택 — Claude Code에서도 직접 호출하려면)
- TradingView 앱 측: 차트 템플릿, alert webhook URL 등록

### 02_audit_safe_signals (MVP에서는 무수정)
- 워치리스트 alert webhook URL은 사용자가 TV 측에서 직접 추가만

## Verification

End-to-end 검증 (Phase별 누적):

1. **Phase 0**: `curl localhost:9222/json` 정상 응답
2. **Phase 1**: Telegram에서 `/start` → bot 응답 / 비인가 chat_id **명시 거부 메시지** (silent ignore X) / `data/usage.db` 자동 생성
3. **Phase 2**: `삼성전자 봐줘` → TV 차트 자동 전환 + 표준 지표 응답 / MCP 자식 프로세스 single-spawn 확인 (`ps aux | grep server.js`로 1개)
4. **Phase 3**: 프라이빗 시그널 발화 종목 → 응답에 시그널 발화 여부 명시 / 화이트리스트 미적재 시 "프라이빗 인디케이터 미적재" graceful 응답
5. **Phase 4**: 후속 `위클리도` → 같은 종목 timeframe만 변경된 응답 / **bot 재시작 후에도 동일 동작** (SQLite 영속성 확인)
6. **Phase 5**: `워치리스트 시그널` → 30종목 일괄 처리 + 5종목당 점진 응답 + 발화만 최종 요약 / 일괄 중 단일 질의 → 큐 또는 거부 메시지
7. **회귀 (Phase 5 ↔ Phase 2)**: 워치리스트 코드 추가 후 단일 종목 질의 (Phase 2 회귀)가 동일 응답 시간/형식 유지하는지 확인
8. **API cap 검증**: usage.db 강제로 임계 set → bot 응답이 graceful "한도 근접" 메시지인지
9. **운영 검증**: 홈 머신 lid close → bot 계속 응답 (caffeinate 동작) / launchd로 bot 강제 kill → 자동 재시작 + MCP 재spawn 확인
10. **Push 검증**: TV alert 발화 → Fly.io webhook → Telegram 푸시 도착 (이미 동작 중)

## Open Questions

- [ ] **프로젝트 이름** — `03_tradingview_companion` OK? 다른 이름 선호?
- [ ] **스택** — Python 권장 (02와 일치, `python-telegram-bot` 안정), 다른 선호?
- [ ] **24/7 운영 범위** — 항상? trading hours만? (KRX 09-15:30 + NYSE 23:30-06:00 KST)
- [ ] **워치리스트 시드** — 어떤 종목 30개로 시작?
- [ ] **프라이빗 인디케이터 study name** — 사용자가 차트에서 정확한 이름 추출 (Phase 3에 필수 입력)
- [ ] **응답 톤** — 표준 한국어 가정. 음슴체 옵션?
- [ ] **Telegram bot** — 02와 같은 봇 재활용? 새 봇? (project isolation 권장 → 새 봇)
- [ ] **Phase 6 push 보강** — MVP 후 별도 spec으로 분리해서 검토

## Risks

- **외부 의존**: tradingview-mcp가 미공식 CDP 활용 — TV 앱 업데이트로 깨질 수 있음
- **ToS 회색지대**: 본인 자동화는 사실상 묵인이지만, repo public 공개 시 TV 측 클레임 리스크 미미하게 존재 → README에 disclaimer 명시 ("개인 자동화 용도, 상업적 사용 시 TradingView ToS 별도 검토 필요")
- **홈 머신 의존**: 인터넷 끊김/하드웨어 장애 시 pull 경로 다운 (push는 Fly.io에서 동작 유지)
- **API 비용**: AD-3 이중 cap으로 보호. 코드 cap이 graceful, 콘솔 cap은 backstop. **Pro/Max OAuth 우회 불가** (Anthropic이 third-party 앱에 명시 금지)
- **인디케이터 이름 변경**: TV 앱 업데이트 또는 인디케이터 저자 변경으로 study name이 바뀌면 화이트리스트 갱신 필요

## NOT in scope (의도적 deferral)

- **Phase 6 Push 보강** — AD-5, TODO-1로 deferral
- **워치리스트 cron pre-fetch** — TODO-2
- **02 ↔ 03 audit policy 자동 동기화** — TODO-3 (manual sync로 시작, AD-8)
- **인디케이터 자동 discovery** — TODO-4 (manual whitelist로 시작)
- **Pine Script 자동 작성** — out of scope
- **Symbol fuzzy LLM 위임** — TODO-6 (정적 dict로 시작)
- **멀티 사용자 / SaaS** — out of scope (1인 사용 전제)
- **클라우드에 TV Desktop 헤드리스** — out of scope (홈 머신 macOS)
- **자동매매 / 거래소 API 주문** — out of scope

## What already exists (재활용 vs 재구축)

- **Telegram bot 인프라 (02_audit_safe_signals)** — 같은 token 공유 (AD-6). chat_id 동일, send 메서드 02도 호출 가능
- **차단 리스트 (02 `config/blocked_auditors.yaml`)** — 03이 manual copy로 재사용 (AD-8). 코드 import 금지.
- **kreports DART 데이터** — 03 MVP 외. 차후 펀더멘털 컨텍스트 통합 시.
- **Fly.io webhook endpoint (02)** — 03이 직접 활용하지 않음. push는 02 책임.
- **tradingview-mcp (외부, MIT)** — clone, 절대 수정 X. SDK가 자동 spawn 관리.

## GSTACK REVIEW REPORT

| Review | Trigger | Why | Runs | Status | Findings |
|--------|---------|-----|------|--------|----------|
| CEO Review | `/plan-ceo-review` | Scope & strategy | 0 | — | (skipped — scope locked in brainstorming) |
| Codex Review | `codex exec` outside voice | Independent 2nd opinion | 1 | issues_found | 28 findings, 4 cross-model tensions resolved, 12 minor auto-applied, 7 deferred to TODOS.md |
| Eng Review | `/plan-eng-review` | Architecture & tests (required) | 1 | clean | 16 findings, 5 architecture decisions (AD-1~5) accepted, 3 additional (AD-6~8) added post-Codex |
| Design Review | `/plan-design-review` | UI/UX gaps | 0 | — | (n/a — no UI surface) |
| DX Review | `/plan-devex-review` | Developer experience gaps | 0 | — | (skipped) |

- **CODEX**: 28 findings raised, 4 cross-model tensions surfaced via AskUserQuestion, all resolved by user. Minor issues auto-applied (token-counted cap, KST reset, screenshot ephemeral, advice-shaped wording, config/ relocation). 7 deferral items captured as TODOs.
- **CROSS-MODEL**: Significant overlap on phase ordering, MCP feasibility risk, watchlist LLM economics, AD-1 health-check gap. User accepted Codex framing on all 4. Outside voice strengthened plan substantially.
- **UNRESOLVED**: 0 (all decisions explicit).
- **VERDICT**: ENG CLEARED + OUTSIDE VOICE INTEGRATED — ready for Codex implementation handoff. Phase 0b (MCP feasibility GO/NO-GO) is the next gate.
