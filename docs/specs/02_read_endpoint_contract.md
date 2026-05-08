# 02 Read Endpoint Contract — for 02_audit_safe_signals

> 03_tradingview_companion이 의존하는 02 측 신규 작업 명세 (ADR-0003 AD-11). 02 cwd에서 별도 spec/plan으로 진행 권장. 본 문서는 contract만 정의 — 03이 무엇을 받기를 기대하는지.

## 변경 범위 (02 측)

### A. webhook.py — atr_* 3필드 추가 (~5분)

현 schema는 v6.0 (33필드). v6.1 새 3필드를 받아서 보존.

```python
# domain/webhook.py 추가
class WebhookPayload(BaseModel):
    # ... 기존 33필드 ...
    atr_multiple: float | None = None   # v6.1: ATR 이격 배수
    atr_dot: bool = False               # v6.1: 과열봉 경고 발동
    atr_dot_threshold: float = 7.0      # v6.1: Pine 입력 임계값
```

`extra="ignore"` 가정. 기존 봇은 영향 없음.

### B. state.db — webhooks 테이블 신규 (~10분)

```sql
CREATE TABLE IF NOT EXISTS webhooks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    type TEXT NOT NULL,
    payload_json TEXT NOT NULL,         -- raw JSON 전체
    audit_decision TEXT NOT NULL,        -- CLEAN | SKIP | MANUAL_VERIFY
    audit_reason TEXT,
    received_at INTEGER NOT NULL         -- unix epoch
);

CREATE INDEX IF NOT EXISTS idx_webhooks_ticker_tf
    ON webhooks(ticker, timeframe, received_at DESC);

CREATE INDEX IF NOT EXISTS idx_webhooks_received
    ON webhooks(received_at);
```

INSERT 시점: `pipeline/handle_webhook.py`의 dedup 통과 후. audit decision 판정 후 audit_decision/reason도 함께.

TTL cleanup (선택): 별도 cron이 `received_at < now - 30days` 삭제. MVP는 무제한 보존.

### C. server.py — GET /signals 라우트 추가 (~10분)

```python
@app.get("/signals/{ticker}")
async def latest_signal(
    ticker: str,
    timeframe: str = Query(...),
    secret: str = Query(...),
):
    if not secrets.compare_digest(secret, settings.webhook_secret):
        raise HTTPException(401)
    row = await db.fetch_one(
        "SELECT type, payload_json, audit_decision, audit_reason, received_at "
        "FROM webhooks WHERE ticker = ? AND timeframe = ? "
        "ORDER BY received_at DESC LIMIT 1",
        (ticker, timeframe),
    )
    if row is None:
        return {
            "ticker": ticker,
            "timeframe": timeframe,
            "received_at": None,
            "audit_decision": None,
            "payload": None,
        }
    return {
        "ticker": ticker,
        "timeframe": timeframe,
        "received_at": iso_kst(row["received_at"]),
        "audit_decision": row["audit_decision"],
        "payload": json.loads(row["payload_json"]),
    }
```

## Auth

기존 `webhook_secret` 환경변수 재사용. 별도 `read_secret` 도입은 불필요 (단일 사용자, public repo 아닌 Fly.io 비공개 endpoint).

## 응답 형식 (확정)

```json
{
  "ticker": "KRX:005930",
  "timeframe": "240",
  "received_at": "2026-05-08T23:45:12+09:00",
  "audit_decision": "CLEAN",
  "audit_reason": null,
  "payload": {
    "ticker": "005930",
    "name": "삼성전자",
    "exchange": "KRX",
    "timeframe": "240",
    "action": "BUY",
    "type": "💰 정석 진입 @SR↩",
    "...": "(37 fields total)"
  }
}
```

`payload`는 v6.1 그대로 (37필드). 03이 webhook spec 참조해서 의미 해석.

## 거부된 옵션 (의도적)

- **POST /signals (03 → 02 push)**: 03이 02의 webhook handler에 직접 발사. 양방향 의존 위반.
- **multiple ticker batch endpoint** (`POST /signals/bulk`): MVP에선 단순화. 03이 30개 GET을 동시 호출하면 충분 (Tokyo region 100ms × 30 동시 = 약 200ms).
- **WebSocket / SSE 실시간 stream**: pull 모델이 충분. push는 02→Telegram이 이미 처리.
- **decisions.jsonl 노출**: 별도 endpoint 후 검토. payload 자체에 audit_decision 포함되면 충분.

## 03 측 검증 시점 (Phase 0b GO/NO-GO)

1. 02 deploy 후 `curl https://02.fly.dev/healthz` → 200 OK
2. 사용자가 1종목 alert을 TV에서 발사 → 02 webhooks 테이블에 row 1개 확인
3. `curl https://02.fly.dev/signals/KRX:005930?timeframe=240&secret=...` → JSON 정상 + 37필드
4. 03 홈 머신에서 같은 호출 → latency 측정 (Tokyo→Seoul 100ms 이하 기대)

위 4개 모두 통과 = Phase 0b GO. 하나라도 실패 시 02 디버그.
