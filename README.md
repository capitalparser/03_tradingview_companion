# 03_tradingview_companion

Telegram-first chart analyst for TradingView Desktop, powered by [tradingview-mcp](https://github.com/tradesdontlie/tradingview-mcp) (Chrome DevTools Protocol) and the Anthropic Claude SDK.

## What it does

Single Telegram interface for both **push** (alert webhooks → Fly.io filter → Telegram, handled by sibling project `02_audit_safe_signals`) and **pull** (interactive "이 종목 어때?" queries that this project handles by driving TradingView Desktop locally).

```
[Mobile Telegram]
       │
       ▼
[Telegram bot — this project, runs at home]
       │
       ▼
[Anthropic Claude SDK] ──tools──► [tradingview-mcp Node server]
                                          │
                                          │ Chrome DevTools Protocol :9222
                                          ▼
                                   [TradingView Desktop, logged-in]
                                   (private indicators preloaded)
```

The bot reads chart state, study (indicator) values, and signal labels from your own TradingView Desktop session — including outputs of private/invite-only indicators you have access to. Indicator source code stays on TradingView's servers; only rendered outputs are read.

## Status

Early. See `~/.claude/plans/shimmering-marinating-salamander.md` for the design doc and phased plan.

## Setup (sketch)

1. TradingView Desktop with `--remote-debugging-port=9222` flag, logged-in, default chart template loaded with your indicators.
2. Clone `tradesdontlie/tradingview-mcp` to `~/code/`, `npm install`.
3. Copy `.env.example` to `.env`, fill in Telegram bot token, your chat ID, and Anthropic API key.
4. `uv sync && uv run python -m bot` (Phase 1+).

## Constraints

- Requires TradingView Premium (Desktop app + webhook alerts).
- Home machine must be awake (caffeinate / `pmset disablesleep`) for the pull path.
- Push path is independent and runs on Fly.io via `02_audit_safe_signals`.

## Disclaimer

개인 자동화 용도. TradingView 데스크톱의 미공식 Chrome DevTools Protocol을 활용하므로 TradingView 약관 회색지대에 해당함. 상업적 사용/재배포/대량 운용은 TradingView ToS를 별도로 검토할 것. 본 프로젝트는 매수/매도 추천을 하지 않으며 투자 손실에 대한 책임을 지지 않는다.

## License

MIT
