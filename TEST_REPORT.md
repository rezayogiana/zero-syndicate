# ZERO SYNDICATE V3 — verified checks

- Python compilation: PASS.
- Node.js syntax checks (quant.js, app.js, Cloudflare proxy): PASS.
- FastAPI TestClient `/api/health`: HTTP 200, version 3.0.
- `/api/astro` 28 Oct 2026 New York: HTTP 200, planetary data available.
- `/api/xauusd/analyze` without OANDA credentials: HTTP 503, no invented prices.
- `/api/xauusd/csv` with generated **synthetic test candles**: HTTP 200, `WAIT` and historical status, never live. Synthetic candles are only for internal testing and are **not** bundled as market data.
- Browser rendering via Playwright `set_content` (local navigation restricted): desktop 1365px and mobile 390px no JavaScript errors; menu hamburger opens; quant panel renders honest backend-unavailable state.
- NOT TESTED: OANDA connectivity / live price permissions, Render deployment on user's account, Gemini model integration, Forex Factory feed in production.
- Order execution intentionally not supported.
