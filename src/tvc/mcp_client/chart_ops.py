"""tradingview-mcp 호출 래퍼.

설계 의도:
- MCP 자식 프로세스를 stdio로 spawn하고, tool_use 응답을 정형화해서 반환.
- analyst가 사용하는 ChartOps Protocol의 단일 실 구현체.
- 호출은 모두 async, 30s timeout 강제.
- TV Desktop이 응답하지 않으면 명확한 예외 (`ChartOpsTimeout`, `ChartOpsCDPDown`).

런타임 의존:
- `mcp` Python 패키지 (Model Context Protocol SDK)
- 외부 Node 서버 경로는 Settings에서 받음
"""
from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any


class ChartOpsError(Exception):
    """Base for chart_ops failures."""


class ChartOpsTimeout(ChartOpsError):
    """MCP/CDP didn't respond in time."""


class ChartOpsCDPDown(ChartOpsError):
    """TradingView Desktop is not running with --remote-debugging-port=9222."""


class MCPChartOps:
    """analyst.ChartOps Protocol의 실 구현.

    Codex 인계 가드레일:
    - `__aenter__/__aexit__`로 MCP 자식 프로세스 라이프사이클 관리.
    - 각 메서드는 단일 MCP tool_call에 대응. 매핑은 docstring에 명시.
    - CDP 비활성 감지 시 `ChartOpsCDPDown` raise (handler가 사용자에게 안내).
    - 응답 JSON 파싱은 pydantic 모델로 검증 (느슨하게 받지 말 것).
    """

    def __init__(self, server_path: Path, debug_port: int = 9222) -> None:
        raise NotImplementedError("Codex: prep stdio spawn args, store config")

    async def __aenter__(self) -> "MCPChartOps":
        raise NotImplementedError("Codex: spawn MCP via mcp.client.stdio_client")

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
        raise NotImplementedError("Codex: terminate MCP process gracefully")

    # MCP tool: chart_set_symbol
    async def set_symbol(self, symbol: str) -> None:
        raise NotImplementedError("Codex: call chart_set_symbol tool")

    # MCP tool: chart_set_timeframe
    async def set_timeframe(self, timeframe: str) -> None:
        raise NotImplementedError("Codex: call chart_set_timeframe tool")

    # MCP tool: chart_get_state
    async def get_state(self) -> dict[str, Any]:
        raise NotImplementedError("Codex: return parsed state dict")

    # MCP tool: data_get_study_values
    async def get_study_values(self, study_names: Sequence[str]) -> dict[str, Any]:
        raise NotImplementedError("Codex: call data_get_study_values, return name → value")

    # MCP tool: capture_screenshot
    async def capture_screenshot(self, path: str) -> str:
        raise NotImplementedError("Codex: invoke screenshot tool, return saved path")
