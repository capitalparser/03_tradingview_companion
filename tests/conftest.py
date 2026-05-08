"""Pytest fixtures.

Codex 인계 노트:
- 외부 의존(MCP, Anthropic, Telegram)은 모두 fake로 격리.
- live 마커가 붙은 테스트만 실제 외부 호출. 기본 deselect.
- in-memory ChartOps fake를 conftest에서 제공해서 단위 테스트 일관성 확보.
"""
from __future__ import annotations

import pytest


@pytest.fixture
def fake_chart_ops() -> object:
    """In-memory ChartOps fake. Codex가 정의."""
    raise NotImplementedError("Codex: implement in tests/fakes/chart_ops.py and import here")
