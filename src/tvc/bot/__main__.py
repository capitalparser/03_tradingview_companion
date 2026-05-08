"""Bot entry point. `python -m tvc.bot` 또는 `tvc` 스크립트로 실행.

수명 관리:
- Settings 로딩 (실패 시 즉시 종료, 메시지 명시)
- python-telegram-bot Application 빌드
- 핸들러 등록
- long-polling 시작

종료 시:
- 우아한 shutdown — 진행 중 메시지 처리 후 종료
- MCP 자식 프로세스 정리 (analyst가 관리)
"""
from __future__ import annotations


def main() -> int:
    """Entry point. Returns process exit code."""
    raise NotImplementedError(
        "Codex: load Settings, build Application, register handlers, run_polling, return 0"
    )


if __name__ == "__main__":
    raise SystemExit(main())
