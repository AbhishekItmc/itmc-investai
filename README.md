# ITMC InvestAI — Phase 1

Indian-market (NSE/BSE) dashboard built with Streamlit, yfinance, Plotly and SQLite.

## Run

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Phase 1 features

- **Dashboard** — NIFTY 50, SENSEX, NIFTY Bank, India VIX, USD/INR cards; index chart with selectable period; NIFTY 50 top gainers/losers.
- **Market Explorer** — any NSE/BSE stock (`.NS` auto-appended, use `.BO` for BSE), candlestick + volume chart with moving averages, key stats, fundamentals snapshot.
- **Settings** — OpenAI API key storage (for later phases), cache clearing.

## Phase 2 features

- **Watchlist** — add/remove NSE/BSE symbols (persisted in SQLite), live quote table with price, change, day range, market cap.
- **Technical Analysis** — RSI, MACD, Bollinger Bands, SMA 20/50/200, EMA, ATR, Stochastic; 4-panel chart (price+BB+MAs, volume, RSI, MACD); rule-based indicator readings table (clearly labeled as mechanical calculations, not advice). Indicators are implemented in pure pandas (`services/indicators.py`) — pandas-ta was skipped because it is incompatible with numpy ≥ 2.

## Structure

```
app.py            entry point (st.navigation, dark theme)
config.py         constants: indices, NIFTY 50 list, cache TTLs
pages/            dashboard, market_explorer, settings
services/         market_data.py — cached yfinance wrapper
components/       charts.py (Plotly), ui.py (cards/tables)
database/         db.py — SQLite (settings + future watchlist/portfolio)
utils/            logger.py, formatters.py (₹, Cr/L, Indian grouping)
data/, logs/      created at runtime (SQLite DB, rotating log)
```

## Principles

- Real market data only (yfinance) — nothing fabricated; failures show clear warnings.
- Facts vs AI analysis will be visually separated when AI features arrive (Phase 2+).
- All service calls are wrapped with error handling + logging (`logs/app.log`).

## Roadmap

Phase 3: portfolio management · Phase 4: AI chat, news sentiment, daily reports (OpenAI) · Phase 5: alerts + backtesting.
