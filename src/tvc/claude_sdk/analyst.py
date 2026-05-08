"""Claude Agent SDK 통합 — 분석 오케스트레이터 (Option B, ADR-0003).

설계 의도 (AD-3, AD-4, AD-9):
- 1차 데이터 소스: `EndpointClient.get_latest()` (02의 webhook payload, 37필드 v6.1)
- Claude Agent SDK는 자연어 해석에만 사용. tool loop는 단순함 (MCP 보조 기능 시만)
- 모든 query 전 UsageGuard 체크 (AD-3 cost cap)
- chat_id별 (last_symbol, last_timeframe)은 ConversationStore (AD-4)
- session_id는 logging만, SDK resume 비활성 (stale chart context 위험)
- MCP는 보조 (스크린샷 요청 시 lazy spawn, lock 적용)
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from tvc.source.endpoint import EndpointClient, SignalRecord
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
    """Option B 기반 분석기.

    Codex 인계 가드레일:
    - `__init__`은 dependencies 주입만 (EndpointClient, ConversationStore, UsageGuard, system_prompt, model).
    - `analyze_symbol`은 EndpointClient.get_latest()를 1차 호출. payload 누락 시 graceful 응답.
    - Claude `query()` 호출 시 system_prompt = analyze_prompt + webhook spec (정적, cache_control=ephemeral).
    - 응답 텍스트는 절대 silent fallback 금지. EndpointError → handler graceful 변환.
    - audit_decision = SKIP/MANUAL_VERIFY → 응답 첫 줄에 ⚠️ prefix.
    - MCP는 보조 — `analyze_with_screenshot()` 같은 별도 메서드에서만 lazy spawn + lock.
    """

    def __init__(
        self,
        endpoint: EndpointClient,
        store: ConversationStore,
        usage: UsageGuard,
        system_prompt: str,
        webhook_spec_md: str,
        model: str = "claude-sonnet-4-6",
    ) -> None:
        raise NotImplementedError(
            "Codex: store deps, build ClaudeAgentOptions with cache_control system_prompt"
        )

    async def analyze_symbol(
        self,
        chat_id: int,
        symbol: str,
        timeframe: str = "240",  # v6.1 webhook의 timeframe 표기 ('240' = 4H, 'D' = daily, 'W' = weekly)
    ) -> AnalysisResult:
        """1) EndpointClient.get_latest 2) usage cap 체크 3) Claude query() 4) 응답."""
        raise NotImplementedError(
            "Codex: get_latest, if payload None return graceful, else build context (37 fields + audit + spec), query, return"
        )

    async def analyze_followup(
        self,
        chat_id: int,
        timeframe_or_command: str,
    ) -> AnalysisResult:
        """후속 질의 ('위클리도'). store에서 last_symbol 조회 + 새 timeframe으로 endpoint 재조회."""
        raise NotImplementedError(
            "Codex: load (symbol, _) from store, call analyze_symbol with new timeframe"
        )

    async def analyze_watchlist(
        self,
        chat_id: int,
        watchlist: Sequence[tuple[str, str]],  # [(ticker, timeframe), ...]
        progress_callback: object,
    ) -> AnalysisResult:
        """워치리스트 일괄 (AD-7 deterministic + 1회 LLM).

        1) 각 종목 EndpointClient.get_latest (mutex 불필요 — endpoint는 동시 호출 OK)
        2) 발화 시그널 (action == "BUY") 코드 필터 — LLM 호출 X
        3) 발화 종목 N개 모아서 LLM 1회 요약
        4) progress_callback은 10종목 처리마다 호출
        """
        raise NotImplementedError(
            "Codex: gather endpoint calls, filter action=='BUY', single LLM summary"
        )

    async def analyze_with_screenshot(
        self,
        chat_id: int,
        symbol: str,
        timeframe: str = "240",
    ) -> AnalysisResult:
        """MCP 보조 기능 — capture_screenshot 포함. lazy spawn (사용자 명시 요청 시만)."""
        raise NotImplementedError(
            "Codex: optional MCP path. Spawn tradingview-mcp lazily, capture_screenshot, attach to result"
        )
