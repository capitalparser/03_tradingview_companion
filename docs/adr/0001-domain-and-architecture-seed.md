# ADR-0001 — Domain & Architecture Seed

- **Status**: Accepted
- **Date**: 2026-05-08
- **Decision driver**: Tier 3 새 프로젝트 진입 시 도메인 모델 + 아키텍처 분기 일괄 기록

## Context

TradingView Desktop의 Chrome DevTools Protocol(CDP, port 9222)을 활용하는 외부 MCP 서버(`tradesdontlie/tradingview-mcp`)를 발견. 사용자(김경준)는 자매 프로젝트 `02_audit_safe_signals`에서 이미 TradingView alert webhook → 감사인 차단 필터 → Telegram 알림 인프라를 Fly.io에서 운영중. 두 프로젝트 모두 **본인 단독 사용자**, **모바일 우선**, **trade-secret-adjacent 데이터 다룸**.

## 핵심 분기 (왜 A 대신 B를 택했는가)

### 분기 1: Push 단독 강화 vs Push + Pull 통합

- **A. 02 강화만** (push만, alert webhook에 워치리스트 종목 추가)
- **B. 신규 03 프로젝트로 pull 인터랙티브 추가** ✅ **선택**

이유:
- 사용자의 본질적 요구는 "지금 이 종목 어때?"라고 물어볼 수 있는 인터랙티브 채널
- Push만으로는 알림이 와서야 인지 — 능동적 질의 불가
- MCP가 차트 직접 조종을 가능케 함 → pull의 가치 잠금 해제

### 분기 2: Alert을 MCP로 받기 vs Webhook으로 받기

- **A. MCP로 alert streaming/polling**
- **B. Webhook 분리, MCP는 차트 검증만** ✅ **선택**

이유:
- TradingView alert은 webhook URL POST를 공식 지원 — 안정적/즉시
- MCP를 alert 수신 채널로 쓰면 24/7 polling 부담 + TV Desktop 항상 ON 강제
- **02_audit_safe_signals가 이미 webhook 인프라 보유** → 재발명 회피

### 분기 3: 02와 코드 공유 vs Project Isolation

- **A. 02의 telegram/auditor/pipeline 모듈 import 재활용**
- **B. 완전 분리, project isolation 준수** ✅ **선택 (with AD-6 예외)**

이유:
- vault 메모리 정책: "sibling 01_Projects/* are independent; no shared bots, env, or imports"
- 02는 Fly.io stateless service, 03은 홈 머신 long-running bot — 운영 모델/배포 토폴로지가 다름
- 의존이 양방향이 되면 한쪽 장애가 다른 쪽 전파

**Update 2026-05-09 (ADR-0002 AD-6)**: 코드/import 분리는 유지. 단 **Telegram bot token은 명시적 공유 자원** (single Telegram interface vision 진정 달성). bot token .env 양쪽에 동일 값. 03이 long-poll, 02는 send only — 한 token에 한 long-poll process만 허용하므로 충돌 X. token revoke/rotate 시 양쪽 동시 갱신 필요 (운영 메모).

또한 차단 리스트(config/blocked_auditors.yaml)는 동일 정책을 manual sync. 코드 import는 여전히 금지. 자동 동기화 패턴은 TODOS.md TODO-3.

**Update 2026-05-09 (ADR-0003 AD-10) — webhook payload sharing**: 03이 02의 read-only HTTP endpoint(`GET /signals/{ticker}`)를 호출하는 단방향 의존 허용. webhook v6.1 spec 발견 후 pull 경로의 데이터 source가 MCP 차트 추출에서 02 webhook payload로 pivot. 02 → 03 의존은 여전히 금지 (양방향 차단). 코드 import 금지는 그대로. audit-safety 정책도 02 결정을 payload로 받아 표시 → AD-8의 manual sync 부담 사라짐. ADR-0003 참조.

### 분기 4: 클라우드 vs 홈 머신

- **A. 클라우드에 TV Desktop xvfb 헤드리스 실행**
- **B. 홈 머신(macOS)에서 24/7** ✅ **선택**

이유:
- xvfb + Electron 헤드리스는 운영 부담 큼, TV ToS도 더 회색
- 홈 머신은 caffeinate + launchd로 안정 운용 가능
- pull 경로만 홈에 의존, push는 Fly.io에서 계속 동작 → 홈 다운 시 push는 무영향

### 분기 5: ~/.claude.json MCP 등록 vs 프로젝트 내부 stdio spawn

- **A. ~/.claude.json에 tradingview MCP 등록 (Claude Code도 직접 사용)**
- **B. 프로젝트 Python 코드가 자체적으로 MCP를 stdio spawn** ✅ **선택 (MVP)**

이유:
- 본 프로젝트의 진입점은 Telegram bot이지 Claude Code가 아님
- 환경 의존을 ~/.claude.json에 두면 다른 Claude Code 세션이 부수 영향
- Python 프로세스가 MCP 자식 프로세스로 spawn하면 bot 라이프사이클과 일치
- (선택 보강) 추후 Claude Code 인터랙티브 디버깅 시 ~/.claude/.mcp.json에 별도 등록 가능

## 도메인 시드 (vocabulary)

| 용어 | 정의 |
|---|---|
| **CDP** | Chrome DevTools Protocol. Electron의 디버그 인터페이스 |
| **study** | TradingView 차트에 적재된 인디케이터의 internal identifier |
| **plot/label** | 인디케이터가 차트에 그리는 출력 (시계열 / 텍스트 마커) |
| **시그널 인디케이터** | 사용자가 보유한 진입/청산/돌파 표시 프라이빗 Pine 스크립트 |
| **invite-only** | 저자가 초대한 사용자만 차트에 적재 가능 — 출력만 보이고 소스 protected |
| **push 경로** | TV alert → Fly.io webhook → Telegram (02_audit_safe_signals) |
| **pull 경로** | Telegram → 홈 bot → MCP → TV Desktop → 응답 (본 프로젝트) |
| **워치리스트** | 사용자 모니터링 종목 집합 — 인터랙티브/일괄 처리 단위 |

## 비범위 (의도적 배제)

- 자동매매 / 거래소 API 주문
- 매수/매도 추천 — 보조 애널리스트 컨셉
- 02_audit_safe_signals 통합 webhook payload 처리 (push는 02 책임)
- Pine Script 자동 작성 (다른 시나리오)
- 다중 사용자 / SaaS

## 알려진 위험

- **TradingView 앱 업데이트** → CDP 호환성 깨질 수 있음 (외부 의존)
- **ToS 회색지대** → 본인 자동화는 사실상 묵인이지만 public repo 공개로 미미한 클레임 리스크
- **인디케이터 study name 변경** → 화이트리스트 동기화 필요
- **Anthropic API 비용** → 잦은 질의 시 월 budget 초과 가능

## 참조

- 승인된 plan: `plans/2026-05-08-tradingview-companion-design.md`
- 외부 MCP: https://github.com/tradesdontlie/tradingview-mcp (★2.7k, MIT)
- 형제 프로젝트: `~/vault/01_Projects/02_audit_safe_signals/`
