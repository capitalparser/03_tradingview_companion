"""SQLite-backed persistence (AD-3 usage cap, AD-4 conversation context).

스키마:
- conversations(chat_id INTEGER PK, last_symbol TEXT, last_timeframe TEXT,
                last_session_id TEXT, updated_at INTEGER)
- usage(date TEXT PK, request_count INTEGER, input_tokens INTEGER,
        output_tokens INTEGER, estimated_usd REAL)

Codex 인계 가드레일:
- 단일 SQLite 파일 (`data/state.db`) — concurrent 접근은 asyncio + 단일 process라
  큰 락 필요 없지만 `aiosqlite` 권장. 파일 손상 감지 시 backup 후 재생성 + 본인 chat_id alert.
- date 기준 reset은 KST 자정 (사용자 거주지 기준, plan에 명시).
- get/put은 idempotent. put은 UPSERT.
"""
from __future__ import annotations

from pathlib import Path
from typing import Protocol


class ConversationStore(Protocol):
    async def get(self, chat_id: int) -> tuple[str, str, str | None] | None: ...
    async def put(self, chat_id: int, symbol: str, timeframe: str, session_id: str) -> None: ...


class UsageGuard(Protocol):
    async def check_and_record(self, estimated_input_tokens: int) -> None: ...


class SQLiteConversationStore:
    """ConversationStore 실 구현."""

    def __init__(self, db_path: Path) -> None:
        raise NotImplementedError("Codex: open aiosqlite, ensure schema, store path")

    async def get(self, chat_id: int) -> tuple[str, str, str | None] | None:
        raise NotImplementedError("Codex: SELECT last_symbol, last_timeframe, last_session_id")

    async def put(self, chat_id: int, symbol: str, timeframe: str, session_id: str) -> None:
        raise NotImplementedError("Codex: UPSERT with updated_at = strftime('%s')")


class SQLiteUsageGuard:
    """UsageGuard 실 구현. AD-3 이중 cap의 코드 측."""

    # 임계는 Settings에서 주입 (하드코딩 X, .env에서 변경 가능)
    def __init__(
        self,
        db_path: Path,
        warn_requests: int = 200,
        warn_usd: float = 5.0,
        hard_requests: int = 500,
        hard_usd: float = 10.0,
    ) -> None:
        raise NotImplementedError("Codex: open aiosqlite, ensure schema, store thresholds")

    async def check_and_record(self, estimated_input_tokens: int) -> None:
        """현재 KST 날짜 row를 SELECT, 임계 비교, 위반 시 raise CostCapExceeded.

        통과 시 row를 increment. 모델 가격은 별도 상수로 정의 (Sonnet 4.6 기준).
        """
        raise NotImplementedError(
            "Codex: get_today_kst, SELECT counters, compare, raise on hard cap, return on warn"
        )
