# CONTEXT.md — Domain Vocabulary

본 프로젝트에서 사용하는 도메인 용어. CLAUDE.md cascade와 함께 참조.

## TradingView 측

| 용어 | 정의 |
|---|---|
| **TV Desktop** | TradingView가 배포하는 Electron 기반 데스크톱 앱. 본 프로젝트의 모든 차트 데이터 source |
| **CDP** | Chrome DevTools Protocol. Electron 앱이 `--remote-debugging-port=9222`로 노출 |
| **study** | 차트에 적재된 인디케이터의 internal identifier. TV 앱의 우클릭 → "Properties" → ID에서 확인 가능 |
| **plot** | 인디케이터가 차트에 그리는 시리즈(라인/막대). 시계열 값을 가짐 |
| **label** | 인디케이터가 특정 시점에 그리는 텍스트 마커. 진입/청산 시그널 표현에 자주 사용 |
| **alert** | 조건 충족 시 발화하는 TV 측 이벤트. webhook URL POST 가능 (Premium 이상) |
| **시그널 인디케이터** | 본 프로젝트 한정 용어. 사용자가 작성한/구독한 진입·청산·돌파 표시 프라이빗 Pine 스크립트 |
| **invite-only** | 저자가 초대한 사용자만 차트에 적재 가능한 인디케이터. 출력만 보이고 소스는 protected |

## 시스템 측

| 용어 | 정의 |
|---|---|
| **MCP** | Model Context Protocol. Claude SDK가 외부 도구 서버를 호출하는 표준 |
| **tradingview-mcp** | `tradesdontlie/tradingview-mcp`. CDP를 통해 TV Desktop을 조종하는 MCP 서버 |
| **push 경로** | TV alert → Fly.io webhook → Telegram. `02_audit_safe_signals` 책임 |
| **pull 경로** | Telegram 메시지 → 홈 머신 bot → MCP → TV Desktop → 응답. 본 프로젝트 책임 |
| **워치리스트** | 사용자가 모니터링하는 종목 집합. KOSPI 200 일부 + 미국 빅테크 + 사용자 선정 |
| **화이트리스트** | (1) chat_id 화이트리스트: bot 인증, (2) 인디케이터 화이트리스트: 추출 대상 study 목록 |

## 운영 측

| 용어 | 정의 |
|---|---|
| **trading hours** | KRX 09:00-15:30 KST + NYSE 23:30-06:00 KST. 24/7 운영 시 의미 없으나 비용 절감 모드에서 의미 |
| **홈 머신** | 사용자 macOS 데스크톱/노트북. TV Desktop + bot이 실행되는 곳 |
| **caffeinate** | macOS sleep 방지 명령. `caffeinate -d`는 디스플레이 sleep만 막음, `-i`는 idle sleep |
| **launchd** | macOS의 init 시스템. 시스템 로그인 시 bot 자동 시작에 사용 |
