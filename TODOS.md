# TODOs — Deferred items

승인된 plan에서 의도적으로 후순위로 미룬 작업들. Codex outside voice (2026-05-09)에서 raise된 항목 중 MVP 외 것 + 운영 진입 후 패턴 보고 결정할 것.

## 운영 진입 후 (1-2개월)

### TODO-1: Phase 6 — Push 경로 보강 재검토 (AD-5)
- **What**: 02_audit_safe_signals webhook 통과 alert에 03이 차트 스크린샷 첨부하는 endpoint
- **Why**: 모바일 사용자가 alert 받자마자 차트 컨텍스트 보고 싶음
- **Pros**: UX 향상, push의 정보 밀도 증가
- **Cons**: ADR-0001 isolation 갈등 — 02→03 호출 vs webhook fan-out 패턴 결정 필요
- **Context**: 본 plan에서는 AD-5로 제거. 운영 1-2개월 후 actual 사용 패턴 보고 가치 평가.
- **Depends on**: Phase 1-5 안정 운영, 02 측 webhook 변경 가능성 검토

### TODO-2: 워치리스트 사전 fetch + 캐시 (cron pre-fetch)
- **What**: trading hours 5분 간격으로 워치리스트 study values를 SQLite에 캐싱
- **Why**: 인터랙티브 워치리스트 응답 즉시화 (현재 ~2분)
- **Pros**: 응답 즉시 (캐시 히트), TV 처리 부담 분산 (배치)
- **Cons**: TV Desktop이 주기적 자동 차트 회전 → 사용자 시야 방해. NYSE+KRX 둘 다 cover시 24/7 거의 풀 부하.
- **Context**: AD-2 brainstorming에서 거부됐으나 워치리스트가 자주 쓰이면 재평가.

### TODO-3: 03 → 02 audit-safety 정책 자동 동기화
- **What**: `config/blocked_auditors.yaml`을 02에서 자동 가져오기
- **Why**: AD-8 수동 동기화는 drift 위험
- **Pros**: 두 프로젝트 정책 정합성 보장
- **Cons**: ADR-0001 isolation 위반 가능성. 02 side가 어떻게 expose 할지 결정 필요 (config repo? gist? cron pull?)
- **Context**: AD-8에서 manual sync로 시작. drift가 실제로 문제 되면 검토.

## 안정 후

### TODO-4: 인디케이터 study name 자동 discovery
- **What**: 차트에 적재된 study를 MCP로 list, 사용자에게 multi-choice 노출 → 화이트리스트 자동 작성
- **Why**: 수동 study name 입력은 brittle (Codex 지적)
- **Pros**: setup UX 개선, study name 변경 시 재발견 가능
- **Cons**: tradingview-mcp가 list_studies tool을 노출하는지 검증 필요
- **Context**: Phase 3에서 manual whitelist로 시작. 자동화 가치 검증 후.

### TODO-5: Pine Script 자동 작성 루프
- **What**: 자연어 → Pine 인디케이터 작성 → MCP 컴파일 → 디버깅 자동
- **Why**: 사용자가 새 시그널 인디케이터 만들 때 효율
- **Cons**: 별도 시나리오. 본 plan의 보조 애널리스트 컨셉 외.
- **Context**: brainstorming에서 별도 시나리오로 분리.

### TODO-6: Symbol fuzzy 매칭 LLM 위임
- **What**: 정적 dict 대신 LLM이 사용자 자연어 → ticker 결정 (예: "삼전" → KRX:005930)
- **Pros**: 입력 유연성
- **Cons**: 매번 API 호출 비용, 일관성 X
- **Context**: 정적 dict 시작. 사용 패턴 본 후 결정.

### TODO-7: 멀티 사용자 지원 / SaaS화
- **Cons**: 본 plan은 1인 사용 전제 (chat_id 화이트리스트). 다인 지원은 인증/세션/cost-per-user 모두 새 설계.
- **Context**: 본 plan 명시 non-goal.

## 운영 메모 (소규모)

### TODO-8: macOS lid-close 안정성 검증
- `caffeinate -d` + clamshell 모드 실제 동작 확인. 인터넷 연결/Bluetooth keyboard 의존 여부.
- 안 되면 미니 PC home server 옵션.

### TODO-9: TradingView Desktop 업데이트 ↔ CDP 호환성 회귀
- 분기마다 수동 검증 cycle 정의.
- 깨졌을 때 fallback (이전 TV 버전 freeze, 또는 상응하는 자동 PR PR을 MCP repo에 모니터링).

### TODO-10: prompt caching 실측 ROI
- AD-3 정밀화 후, 1주 운영 데이터로 cache hit ratio 측정. 5% 미만이면 caching 코드 제거 고려.
