"""Claude Agent SDK 통합 — 분석 오케스트레이터.

설계 의도 (plan-eng-review AD-1, AD-2, AD-3, AD-4):
- bot handler가 호출하는 단일 진입점: `analyze_symbol(...)`, `analyze_watchlist(...)`
- claude-agent-sdk(`query`)가 tool loop와 MCP stdio spawn을 자동 처리
- MCP 자식 프로세스는 SDK가 보유. Bot startup에 1회 spawn, lifetime 동안 영구 (AD-1)
- 모든 MCP 호출은 `_lock: asyncio.Lock`으로 직렬화 (AD-2 mutex)
- 호출 전 UsageGuard 체크 (AD-3 cost cap), 위반 시 raise CostCapExceeded
- Claude session_id를 ConversationStore에 기록해서 SDK `resume` 옵션으로 복원 (AD-4)
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from tvc.storage import ConversationStore, UsageGuard


@dataclass(frozen=True)
class AnalysisResult:
    """analyst.analyze_symbol 응답.

    text: Telegram에 보낼 한국어 요약 (verdict-first).
    screenshot_path: 사용자가 스크린샷을 요청한 경우 절대 경로, 아니면 None.
    raw_indicators: 디버그/로그용 study → value 맵.
    session_id: SDK가 발급한 session id (ConversationStore에 저장).
    """

    text: str
    screenshot_path: str | None
    raw_indicators: dict[str, object]
    session_id: str


class CostCapExceeded(Exception):
    """일일 API cap 초과 (AD-3). handler가 graceful 메시지로 변환."""


class Analyst:
    """Claude Agent SDK 기반 분석기.

    Codex 인계 가드레일:
    - `__init__`은 dependencies 주입만 (mcp_server_path, system_prompt, ConversationStore, UsageGuard).
    - SDK는 `query()` 함수형. `ClaudeAgentOptions`에 `mcp_servers={"tradingview": {...}}`로 지정 → SDK가 자동 spawn (AD-1).
    - 모든 MCP-touching 메서드는 `async with self._lock:` (AD-2).
    - 분석 system_prompt는 정적 → SDK의 prompt cache 활용 (Anthropic API caching).
    - 응답 텍스트는 절대 silent fallback 금지. MCP 실패 시 `ChartOpsError` 그대로 raise → handler 변환.
    """

    def __init__(
        self,
        mcp_server_path: Path,
        tv_debug_port: int,
        system_prompt: str,
        store: ConversationStore,
        usage: UsageGuard,
        model: str = "claude-sonnet-4-6",
    ) -> None:
        raise NotImplementedError(
            "Codex: store deps, init asyncio.Lock, build ClaudeAgentOptions with mcp_servers"
        )

    async def analyze_symbol(
        self,
        chat_id: int,
        symbol: str,
        timeframe: str = "1D",
        include_screenshot: bool = False,
        private_indicators: Sequence[str] = (),
    ) -> AnalysisResult:
        """단일 종목 분석. SDK query() 호출, MCP 도구는 자동 사용."""
        raise NotImplementedError(
            "Codex: build prompt (symbol/timeframe/indicators), call query() with resume=session_id from store, return AnalysisResult"
        )

    async def analyze_followup(
        self,
        chat_id: int,
        timeframe_or_command: str,
    ) -> AnalysisResult:
        """후속 질의 ('위클리도', '스크린샷'). store에서 last_symbol 조회 + SDK resume."""
        raise NotImplementedError(
            "Codex: load (symbol, _, session_id) from store, call query() with resume"
        )

    async def analyze_watchlist(
        self,
        chat_id: int,
        watchlist: Sequence[str],
        progress_callback: object,
    ) -> AnalysisResult:
        """워치리스트 일괄 (AD-2 점진 응답).

        progress_callback은 5종목 처리 끝마다 호출되어 Telegram 점진 메시지 송신.
        """
        raise NotImplementedError(
            "Codex: iterate watchlist with lock, call progress_callback every 5, summarize firing only"
        )
