# Webhook API Reference — 자동매매용 통합시스템 지표 v3.2 (Pine) | Webhook spec v6.1

> 출처: 사용자 첨부 (지표 저자 [LAZY] / 지표견, 2026-04-26)
>
> 본 사본은 03_tradingview_companion이 02 read endpoint로 받는 payload 의미를
> Claude analyst가 해석할 때 참고하기 위해 보관. **편집 금지** — 저자 측 업데이트가
> 있으면 새 버전 파일로 추가하고 본 파일은 삭제하지 않음 (역사 보존).

## 핵심 사실

- **전송 방식**: TradingView Alert → Webhook URL (HTTPS POST)
- **데이터 형식**: JSON UTF-8
- **필드 수**: 37 (v6.1)
- **사용 환경**: Whop의 TradingView 동기화로 받은 자동매매용 통합시스템 지표 + 웹훅
- **02_audit_safe_signals**가 같은 payload 수신 중 (현재 v6.0 = 33필드 schema, atr_* 3필드 미반영)

## 37필드 한 줄 요약

| 필드 | 타입 | 의미 |
|---|---|---|
| `ticker` | str | 종목 심볼 (`AAPL`, `005930`) |
| `name` | str | 종목 이름 |
| `exchange` | str | 거래소 (`NASDAQ`, `KRX`, ``) |
| `timeframe` | str | TF (`240`, `D`, `W`) |
| `action` | str | `BUY` / `SELL` / `CHECK` |
| `type` | str | 시그널 타입 (이모지 포함, `@SR↩` 접미사 가능) |
| `price` | num | 현재가 |
| `sl` | num\|null | 손절가 |
| `rr` | num\|null | 손익비 |
| `desc` | str | 한국어 설명 |
| `market` | str | 시장 상황 (이모지) |
| `ai_summary` | str | AI 종합 평가 (이모지 + 한 줄) |
| `score` | num | 0~99 통합 점수 (GP+Sigma) |
| `status` | str | `Green(GO)` / `Orange(Ready)` / `Red(Wait)` |
| `signal` | str | 활성 태그 공백 구분 (`GP:수급 Sigma:PB `) |
| `conviction` | str | `S` / `A` / `B` / `C` / `D` |
| `momentum` | str | `BUY` / `SELL` / `` |
| `momentum_sl` | num\|null | 모멘텀 SL |
| `momentum_tp` | num\|null | 모멘텀 TP |
| `momentum_bars` | num\|null | 모멘텀 진입 후 봉수 |
| `energy` | num | ATR Multiple (=`atr_multiple`, 호환용) |
| `ema1_dist` | num | EMA1 이격도(%) |
| `candle_type` | str | `양봉` / `음봉` / `도지` |
| `candle_strength` | num | 0~100 (캔들 강도) |
| `ema_touch` | str | `ema1` / `ema2` / `ema3` / `ema1+ema2` / `none` |
| `ema_align` | str | `정배열` / `역배열` / `꼬임` |
| `daily_trend` | enum | **영문** `BULL` / `MIXED` / `BEAR` |
| `daily_ema_aligned` | bool | 일봉 EMA 정배열 |
| `daily_rs` | num | 0~100 일봉 상대강도 |
| `daily_above_200ma` | bool | 200일선 위 여부 |
| `daily_setup_stage` | enum | **영문** `NONE` / `FORMING` / `COMPLETE` (Stage 2 = COMPLETE = VCP 완성) |
| `daily_volume_trend` | enum | **영문** `ACCUMULATION` / `DISTRIBUTION` / `NEUTRAL` |
| `daily_dist_from_high` | num | 52주 고점 대비 거리(%), 0=신고가 |
| `rsi2` | num | 0~100 RSI(2) 단기 |
| `upper_wick_pct` | num | 0~100 윗꼬리 비율 |
| `atr_multiple` | num\|null | ATR 이격 배수 (energy와 동일값, 신규 명명) |
| `atr_dot` | bool | 차트 노란 점(과열봉 경고) 발동 |
| `atr_dot_threshold` | num | Pine 입력값 (기본 7.0) |

## 시그널 카테고리 (action별)

### BUY
- `💰 정석 진입` (눌림목/지지)
- `🚀 돌파 진입` (볼밴/저항선)
- `⚡ 공격 진입` (역추세)
- `🔼 피라미딩 추매`
- `📈 모멘텀 BUY`
- `PEG Pullback` / `PEG Rebreak`

### SELL
- `💸 최종 청산` / `💣 돌파 청산`
- `🔪 1차/2차 분할청산`
- `🎯 TP1/TP2 달성`
- `🚫 진입 무효` (v5.0+ 즉시 매도 X, 봉마감 대기 권장)
- `📉 모멘텀 SELL`
- `🏁 상승 모멘텀 종료` (v5.0+ 차등 매도 권장)
- `PEG Invalid`

### CHECK
- `🛠️ 셋업 형성 중` / `⚡️ VCP 형성`
- `✂️ 부분 익절고려` / `🏉 급등 후 풀백` / `⚠️ 과열 경고`
- `📈 박스권 돌파` / `📉 박스권 이탈`
- `PEG Start` / `PEG Expired`
- `🏁 하락 모멘텀 종료`
- `✅ 진입 확정` / `⛔ 진입 만료` (v5.0 신규, 봉마감 확정 결과)

## 분석에 핵심적인 필드 (03 analyze_prompt 우선순위)

1. **action + type**: 무엇이 발화했는가
2. **conviction (S/A/B/C/D)**: 인디케이터의 자체 확신 등급 (D면 매수 차단 권장)
3. **score (0~99)**: 통합 점수
4. **status**: Green(GO) / Orange(Ready) / Red(Wait)
5. **daily_trend + daily_above_200ma**: 일봉 추세 게이트 (BEAR이면 매수 자제)
6. **daily_setup_stage**: COMPLETE면 교과서적 매수 대기
7. **market**: 시장 정렬
8. **ai_summary**: 인디케이터의 자체 자연어 요약
9. **rsi2 / upper_wick_pct / atr_dot**: 단기 과매수/역망치/과열봉 필터

## 사용자(03 운영자) 활용 패턴

03이 02 endpoint로 payload를 받으면:
- **차트 plot 추출 불필요** — webhook이 더 풍부한 정보 제공
- audit-safety는 02가 이미 적용 (또는 03이 별도 차단 리스트 참조)
- Claude는 37필드를 컨텍스트로 받아서 한국어 해석만 생성
- 매수/매도 추천 금지는 동일 정책 (보조 애널리스트 컨셉)

## 변경 이력 요약 (저자 release notes 발췌)

| 버전 | 날짜 | 핵심 변경 |
|---|---|---|
| v1.0 | 2026-02-24 | 15필드 |
| v2.0 | 2026-03-10 | +energy, ema1_dist (17) |
| v3.0 | 2026-03-13 | +momentum_*, candle_*, ema_* (24) |
| v4.0 | 2026-03-16 | +conviction (25), Discord 제거 |
| v5.0 | 2026-03-25 | +daily_* 7필드 (31), 진입무효/모멘텀종료 정책 변경, ✅ 진입 확정/⛔ 진입 만료 신호 추가 |
| v6.0 | 2026-04-08 | +rsi2, upper_wick_pct (33), 청산 SR Flip 접미사 |
| v6.1 | 2026-04-26 | +atr_multiple, atr_dot, atr_dot_threshold (37), daily_* 영문 enum 정정 |

## 02 측 적합성

- 현 02 schema = v6.0 33필드. v6.1의 atr_* 3필드만 누락
- Pydantic `extra="ignore"` 가정 (03은 새 필드 도착 시 unknown으로 받게 됨 — 02 측 우선 schema update 필요)
- 02의 raw payload 저장 미동작 → 02 측 작업 필요 (Option B 의존)

## IP 보호

저자 [LAZY]가 명시한 비공개 항목:
- 내부 함수명/변수명/알고리즘 로직
- 시그널 발생 조건의 구체적 파라미터
- 확신 등급 산정의 세부 기준
- GP/Sigma 스코어링 로직

→ **03 코드/문서에서 위 내부 구조를 추정/노출하지 말 것**. 본 spec은 사용자 본인이 자동매매를 위해 받은 사양서이며, 03은 그 출력을 read-only로 활용.
