"""Settings loaded from .env via pydantic-settings.

Codex 인계 가드레일:
- 모든 시크릿은 환경변수에서만 읽음. 코드 하드코딩 금지.
- .env 누락 시 명시적 ValidationError로 실패 (silent default 금지).
- TELEGRAM_AUTHORIZED_CHAT_IDS는 콤마 구분 → 정수 set으로 파싱.
"""
from __future__ import annotations

from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="forbid")

    telegram_bot_token: str = Field(..., alias="TELEGRAM_BOT_TOKEN")
    telegram_authorized_chat_ids: frozenset[int] = Field(..., alias="TELEGRAM_AUTHORIZED_CHAT_IDS")
    anthropic_api_key: str = Field(..., alias="ANTHROPIC_API_KEY")
    anthropic_model: str = Field(default="claude-sonnet-4-6", alias="ANTHROPIC_MODEL")

    # 02 read endpoint (ADR-0003 Option B 1차 데이터 소스)
    audit_signals_base_url: str = Field(..., alias="AUDIT_SIGNALS_BASE_URL")
    audit_signals_secret: str = Field(..., alias="AUDIT_SIGNALS_SECRET")

    # MCP는 부수 기능 (스크린샷 등). 미설치 환경에서도 핵심 동작 OK.
    tv_debug_port: int = Field(default=9222, alias="TV_DEBUG_PORT")
    tv_mcp_server_path: Path | None = Field(default=None, alias="TV_MCP_SERVER_PATH")

    @field_validator("telegram_authorized_chat_ids", mode="before")
    @classmethod
    def _parse_chat_ids(cls, v: object) -> frozenset[int]:
        if isinstance(v, frozenset):
            return v
        if isinstance(v, str):
            return frozenset(int(x.strip()) for x in v.split(",") if x.strip())
        raise TypeError(f"unsupported chat_ids type: {type(v)!r}")
