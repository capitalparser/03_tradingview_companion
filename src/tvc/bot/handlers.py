"""Telegram bot 메시지 핸들러.

설계 의도:
- 핸들러는 thin orchestration layer. 비즈니스 로직은 `tvc.claude_sdk.analyst`로 위임.
- 첫 단계: chat_id 인증. 그 다음: 메시지 → analyst.analyze → 응답.
- 컨텍스트(직전 symbol/timeframe)는 chat_id별 in-memory dict (Phase 4).

Phase 1 (echo): /start, 일반 텍스트 → "수신: <원문>" + Claude SDK ping.
Phase 2: /chart <종목>, 자연어 → analyst.analyze_symbol → 응답.
Phase 4: 컨텍스트 후속 질의 ("위클리도", "스크린샷").
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from telegram import Update
    from telegram.ext import ContextTypes


async def handle_start(update: "Update", context: "ContextTypes.DEFAULT_TYPE") -> None:
    """`/start` 명령. 인증 OK인 경우 환영 + 사용 예시. NG는 거부."""
    raise NotImplementedError("Codex: greet authorized user, list available commands")


async def handle_text(update: "Update", context: "ContextTypes.DEFAULT_TYPE") -> None:
    """자연어 메시지 처리. analyst에 위임 후 응답.

    Phase 1: 단순 echo + Claude ping
    Phase 2: 종목 추출 → MCP → 분석 응답
    Phase 4: 직전 컨텍스트 인지 후속 질의
    """
    raise NotImplementedError("Codex: route to analyst with chat_id context")


async def handle_chart(update: "Update", context: "ContextTypes.DEFAULT_TYPE") -> None:
    """`/chart <symbol> [timeframe]` 명령형 진입점."""
    raise NotImplementedError("Codex: parse args, call analyst.analyze_symbol")


async def handle_watchlist(update: "Update", context: "ContextTypes.DEFAULT_TYPE") -> None:
    """`/watchlist` — 사전 등록된 워치리스트 일괄 시그널 체크 (Phase 5)."""
    raise NotImplementedError("Codex: iterate watchlist, batch analyze, summarize")


async def handle_error(update: object, context: "ContextTypes.DEFAULT_TYPE") -> None:
    """Top-level error handler. 사용자에게 graceful 메시지 + structured log."""
    raise NotImplementedError("Codex: log exception, reply 'TV Desktop 켜져있나요?' 등")
