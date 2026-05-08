"""chat_id 화이트리스트 인증.

설계 의도:
- 본인 사용 단독 봇. 외부 침입 차단이 핵심.
- 비인가 호출은 silent ignore 금지 — 명시적 거부 메시지 + 로그 (구조 로그).
- 인증은 모든 핸들러의 진입 첫 단계. raise 또는 early-return.
"""
from __future__ import annotations

from collections.abc import Callable, Coroutine
from functools import wraps
from typing import Any, ParamSpec, TypeVar

P = ParamSpec("P")
R = TypeVar("R")


class UnauthorizedChatError(Exception):
    """Raised when an inbound message comes from an unauthorized chat_id."""

    def __init__(self, chat_id: int) -> None:
        super().__init__(f"unauthorized chat_id={chat_id}")
        self.chat_id = chat_id


def require_authorized(
    authorized: frozenset[int],
) -> Callable[
    [Callable[P, Coroutine[Any, Any, R]]],
    Callable[P, Coroutine[Any, Any, R]],
]:
    """Decorator that aborts a Telegram handler if chat_id is not whitelisted.

    The wrapped handler is expected to be `async def handler(update, context, ...)`
    where `update.effective_chat.id` resolves to an int.

    Implementation: Codex.
    """

    def decorator(
        fn: Callable[P, Coroutine[Any, Any, R]],
    ) -> Callable[P, Coroutine[Any, Any, R]]:
        @wraps(fn)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            raise NotImplementedError("Codex: extract chat_id from update, validate, log on deny")

        return wrapper

    return decorator
