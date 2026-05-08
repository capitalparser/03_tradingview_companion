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

### 스택 결정 (제안)
- **Python 3.11** — `02_audit_safe_signals`와 일치, 사용자 친숙도, `python-telegram-bot` 안정성
- **Claude SDK**: `anthropic` Python SDK — MCP 클라이언트 통합 잘 됨
- **tradingview-mcp**: Node 서버, Python에서 stdio로 spawn

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

큰 시스템이므로 작은 단위로 분할. 각 phase는 별도 spec/plan으로 ExitPlanMode → 사용자 승인 후 진행 권장.

### Phase 0a — GitHub repo bootstrap
- [ ] vault 측 디렉토리 생성: `~/vault/01_Projects/03_tradingview_companion/`
- [ ] 초기 파일: `README.md`(stub), `.gitignore`(Python 표준 + `.env`, `data/`, `private_indicators.json`, `*.png`), `.env.example`, `LICENSE` (MIT 가정)
- [ ] `git init` + initial commit
- [ ] `gh repo create` — **public**, 이름 후보 `03_tradingview_companion` (vault dir와 일치) 또는 사용자가 다른 이름 선호 시 변경
- [ ] `git push -u origin main`
- [ ] **Goal**: 빈 repo + 안전한 `.gitignore`가 origin에 박혀있음 — 이후 모든 작업은 이 repo 안에서

### Phase 0b — Setup verification (수동, 코드 X)
- [ ] TradingView Desktop CDP 9222 포트 동작 확인 (`curl`)
- [ ] tradingview-mcp 클론 + 단일 도구 직접 호출 (`chart_set_symbol`)
- [ ] **Goal**: MCP가 데스크톱을 실제로 조종하는지 육안 확인

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

### Phase 5 — 워치리스트 일괄 + 자동 시작
- [ ] 워치리스트 30종목 일괄 시그널 체크 명령
- [ ] launchd plist + caffeinate 셋업
- [ ] **Goal**: 24/7 운영 준비

### Phase 6 (선택) — Push 경로 보강
- [ ] alert 통과 시 03이 차트 스크린샷 생성하는 별도 endpoint
- [ ] 02_audit_safe_signals에서 이걸 호출하도록 추가 (단, isolation 신중)

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
2. **Phase 1**: Telegram에서 `/start` → bot 응답 / 비인가 chat_id 무시
3. **Phase 2**: `삼성전자 봐줘` → TV 차트 자동 전환 + 표준 지표 응답
4. **Phase 3**: 프라이빗 시그널 발화 종목 → 응답에 시그널 발화 여부 명시
5. **Phase 4**: 후속 `위클리도` → 같은 종목 timeframe만 변경된 응답
6. **Phase 5**: `워치리스트 시그널` → 30종목 일괄 처리 + 발화만 필터
7. **운영 검증**: 홈 머신 lid close → bot 계속 응답 (caffeinate 동작)
8. **Push 검증**: TV alert 발화 → Fly.io webhook → Telegram 푸시 도착 (이미 동작 중)

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
- **ToS 회색지대**: 본인 자동화는 사실상 묵인이지만, repo public 공개 시 TV 측 클레임 리스크 미미하게 존재
- **홈 머신 의존**: 인터넷 끊김/하드웨어 장애 시 pull 경로 다운 (push는 Fly.io에서 동작 유지)
- **API 비용**: Telegram 질의가 잦으면 Anthropic API 비용 증가 — 월 budget 모니터링 필요
- **인디케이터 이름 변경**: TV 앱 업데이트 또는 인디케이터 저자 변경으로 study name이 바뀌면 화이트리스트 갱신 필요
