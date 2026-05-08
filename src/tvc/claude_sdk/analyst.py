"""Claude SDK 통합 — 분석 오케스트레이터.

설계 의도:
- bot handler가 호출하는 단일 진입점: `analyze_symbol(symbol, timeframe, ...)`
- 내부에서 Anthropic SDK + tradingview-mcp(stdio spawn)를 결합
- MCP 도구 호출 결과를 Claude에 컨텍스트로 전달, 자연어 응답 생성
- 외부 의존(SDK, MCP)은 Protocol로 격리해서 단위 테스트에 fake 주입 가능

상태 관리:
- analyst 인스턴스는 process-lifetime 단일. MCP 자식 프로세스를 보유.
- chat_id별 컨텍스트(직전 symbol)는 별도 ConversationStore에 저장 (Phase 4).
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class AnalysisResult:
    """analyst.analyze_symbol 응답.

    text: Telegram에 보낼 한국어 요약 (verdict-first).
    screenshot_path: 사용자가 스크린샷을 요청한 경우 절대 경로, 아니면 None.
    raw_indicators: 디버그/로그용 study → value 맵.
    """

    text: str
    screenshot_path: str | None
    raw_indicators: dict[str, object]


class ChartOps(Protocol):
    """tradingview-mcp 호출 추상화. `tvc.mcp_client.chart_ops.MCPChartOps`가 실 구현."""

    async def set_symbol(self, symbol: str) -> None: ...
    async def set_timeframe(self, timeframe: str) -> None: ...
    async def get_state(self) -> dict[str, object]: ...
    async def get_study_values(self, study_names: Sequence[str]) -> dict[str, object]: ...
    async def capture_screenshot(self, path: str) -> str: ...


class Analyst:
    """Claude SDK + MCP 결합 분석기.

    Codex 인계 가드레일:
    - `__init__`은 dependencies 주입만 (SDK client, ChartOps, prompt template, ...).
    - `analyze_symbol`은 항상 timeout 명시 (총 30s 권장). MCP 호출 timeout은 ChartOps 측 책임.
    - 실패 시 raise 하고 handler에서 graceful 메시지 변환. 응답 텍스트 silent fallback 금지.
    - Claude API 호출 시 prompt caching 사용 (분석 프롬프트는 정적이므로 cache hit 기대).
    """

    def __init__(self, chart_ops: ChartOps, model: str, system_prompt: str) -> None:
        raise NotImplementedError("Codex: store deps, init Anthropic AsyncClient")

    async def analyze_symbol(
        self,
        symbol: str,
        timeframe: str = "1D",
        include_screenshot: bool = False,
        private_indicators: Sequence[str] = (),
    ) -> AnalysisResult:
        """1) chart_set_symbol/timeframe 2) get_state + get_study_values 3) Claude로 해석."""
        raise NotImplementedError("Codex: orchestrate MCP calls + Claude completion")
