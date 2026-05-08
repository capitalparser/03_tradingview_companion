"""02_audit_safe_signals read endpoint client.

설계 의도 (ADR-0003 AD-9, AD-10):
- 03 pull 경로의 1차 데이터 소스. 02의 GET /signals/{ticker}?timeframe=...&secret=...
- httpx.AsyncClient. timeout 5s. 1회 retry (지수 backoff). 그 외 실패는 raise.
- 03이 02를 단방향 의존. 코드/import 공유 X, HTTP만.

응답 schema (02가 반환):
  {
    "ticker": "KRX:005930",
    "timeframe": "240",
    "received_at": "2026-05-08T23:45:12+09:00",
    "audit_decision": "CLEAN" | "SKIP" | "MANUAL_VERIFY",
    "payload": { ... 37 fields v6.1 ... }   # null if no recent alert
  }
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SignalRecord:
    """02 read endpoint 응답 정형화.

    payload가 None이면 해당 ticker/timeframe에 최근 alert 없음.
    """

    ticker: str
    timeframe: str
    received_at: str | None
    audit_decision: str | None
    payload: dict[str, Any] | None


class EndpointError(Exception):
    """02 endpoint 호출 실패 (timeout/5xx/network)."""


class EndpointAuthError(EndpointError):
    """secret 불일치 등 401/403."""


class EndpointClient:
    """httpx.AsyncClient wrapper.

    Codex 인계 가드레일:
    - `__aenter__/__aexit__`로 client lifecycle 관리 (또는 process-lifetime singleton).
    - get_latest는 항상 await + timeout. 1회 retry는 504/connection-reset 같은 transient만.
    - 응답 JSON parsing 실패 시 EndpointError raise. silent fallback 금지.
    - audit_decision은 02가 결정 (CLEAN/SKIP/MANUAL_VERIFY) — 03은 변경 X.
    """

    def __init__(self, base_url: str, secret: str, timeout_s: float = 5.0) -> None:
        raise NotImplementedError(
            "Codex: store base_url (strip trailing /), secret, init httpx.AsyncClient with timeout"
        )

    async def __aenter__(self) -> "EndpointClient":
        raise NotImplementedError("Codex: enter httpx.AsyncClient context")

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
        raise NotImplementedError("Codex: close httpx.AsyncClient")

    async def health(self) -> bool:
        """02의 /healthz ping. EndpointClient 시작 시 1회 호출 권장."""
        raise NotImplementedError("Codex: GET /healthz, return True if 200")

    async def get_latest(self, ticker: str, timeframe: str) -> SignalRecord:
        """가장 최근 webhook payload 조회. 없으면 SignalRecord(payload=None)."""
        raise NotImplementedError(
            "Codex: GET /signals/{ticker}?timeframe={tf}&secret={secret}, parse to SignalRecord"
        )
