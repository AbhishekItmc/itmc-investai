"""Central configuration for ITMC InvestAI."""
from pathlib import Path

APP_NAME = "ITMC InvestAI"
APP_ICON = "📈"
VERSION = "0.1.0 (Phase 1)"

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
LOG_DIR = BASE_DIR / "logs"
DB_PATH = DATA_DIR / "investai.db"

# Cache TTLs (seconds)
TTL_QUOTE = 120
TTL_HISTORY = 300
TTL_MOVERS = 300
TTL_INFO = 3600

# Benchmark indices shown on the dashboard (yfinance symbols)
INDICES = {
    "NIFTY 50": "^NSEI",
    "SENSEX": "^BSESN",
    "NIFTY Bank": "^NSEBANK",
    "India VIX": "^INDIAVIX",
    "USD/INR": "INR=X",
}

DEFAULT_INDEX = "NIFTY 50"

# Index cards on Home (with sparklines). Missing/unavailable ones are skipped.
SPARK_INDICES_IN = {
    "NIFTY 50": "^NSEI",
    "SENSEX": "^BSESN",
    "BANK NIFTY": "^NSEBANK",
    "FIN NIFTY": "NIFTY_FIN_SERVICE.NS",
    "MIDCAP 100": "NIFTY_MIDCAP_100.NS",
}
SPARK_INDICES_GLOBAL = {
    "S&P 500": "^GSPC",
    "NASDAQ": "^IXIC",
    "Dow Jones": "^DJI",
    "Nikkei 225": "^N225",
    "Hang Seng": "^HSI",
}

# NIFTY 50 constituents (NSE symbols) used for the movers scan.
# Static list — refreshed manually; constituents change a few times a year.
NIFTY50 = [
    "ADANIENT.NS", "ADANIPORTS.NS", "APOLLOHOSP.NS", "ASIANPAINT.NS",
    "AXISBANK.NS", "BAJAJ-AUTO.NS", "BAJFINANCE.NS", "BAJAJFINSV.NS",
    "BEL.NS", "BHARTIARTL.NS", "CIPLA.NS", "COALINDIA.NS", "DRREDDY.NS",
    "EICHERMOT.NS", "GRASIM.NS", "HCLTECH.NS", "HDFCBANK.NS",
    "HDFCLIFE.NS", "HEROMOTOCO.NS", "HINDALCO.NS", "HINDUNILVR.NS",
    "ICICIBANK.NS", "INDUSINDBK.NS", "INFY.NS", "ITC.NS", "JSWSTEEL.NS",
    "KOTAKBANK.NS", "LT.NS", "M&M.NS", "MARUTI.NS", "NESTLEIND.NS",
    "NTPC.NS", "ONGC.NS", "POWERGRID.NS", "RELIANCE.NS", "SBILIFE.NS",
    "SBIN.NS", "SHRIRAMFIN.NS", "SUNPHARMA.NS", "TATACONSUM.NS",
    "TATAMOTORS.NS", "TATASTEEL.NS", "TCS.NS", "TECHM.NS", "TITAN.NS",
    "TRENT.NS", "ULTRACEMCO.NS", "WIPRO.NS",
]

# Company-name aliases -> NSE base symbol (for search & AI symbol detection)
ALIASES = {
    "infosys": "INFY", "reliance": "RELIANCE", "reliance industries": "RELIANCE",
    "tcs": "TCS", "tata consultancy": "TCS", "wipro": "WIPRO",
    "hdfc bank": "HDFCBANK", "hdfc": "HDFCBANK", "icici": "ICICIBANK",
    "icici bank": "ICICIBANK", "sbi": "SBIN", "state bank": "SBIN",
    "tata motors": "TATAMOTORS", "tata steel": "TATASTEEL",
    "tech mahindra": "TECHM", "airtel": "BHARTIARTL", "bharti airtel": "BHARTIARTL",
    "itc": "ITC", "maruti": "MARUTI", "maruti suzuki": "MARUTI",
    "sun pharma": "SUNPHARMA", "kotak": "KOTAKBANK", "kotak bank": "KOTAKBANK",
    "axis bank": "AXISBANK", "axis": "AXISBANK", "bajaj finance": "BAJFINANCE",
    "bajaj finserv": "BAJAJFINSV", "hcl": "HCLTECH", "hcl tech": "HCLTECH",
    "adani ports": "ADANIPORTS", "adani": "ADANIENT", "adani enterprises": "ADANIENT",
    "titan": "TITAN", "asian paints": "ASIANPAINT", "nestle": "NESTLEIND",
    "cipla": "CIPLA", "dr reddy": "DRREDDY", "larsen": "LT", "l&t": "LT",
    "ultratech": "ULTRACEMCO", "power grid": "POWERGRID", "coal india": "COALINDIA",
    "hindustan unilever": "HINDUNILVR", "hul": "HINDUNILVR", "ongc": "ONGC",
    "ntpc": "NTPC", "jsw steel": "JSWSTEEL", "hindalco": "HINDALCO",
    "eicher": "EICHERMOT", "hero": "HEROMOTOCO", "hero motocorp": "HEROMOTOCO",
    "bajaj auto": "BAJAJ-AUTO", "mahindra": "M&M", "m&m": "M&M",
    "apollo hospitals": "APOLLOHOSP", "apollo": "APOLLOHOSP", "trent": "TRENT",
    "grasim": "GRASIM", "sbi life": "SBILIFE", "hdfc life": "HDFCLIFE",
    "shriram finance": "SHRIRAMFIN", "tata consumer": "TATACONSUM",
    "indusind": "INDUSINDBK", "indusind bank": "INDUSINDBK", "bel": "BEL",
    "bharat electronics": "BEL",
}

# Sector groupings within NIFTY 50 (for peer comparison)
SECTOR_MAP = {
    "IT": ["TCS.NS", "INFY.NS", "HCLTECH.NS", "WIPRO.NS", "TECHM.NS"],
    "Private Banks": ["HDFCBANK.NS", "ICICIBANK.NS", "KOTAKBANK.NS", "AXISBANK.NS", "INDUSINDBK.NS"],
    "PSU / SBI": ["SBIN.NS"],
    "NBFC & Insurance": ["BAJFINANCE.NS", "BAJAJFINSV.NS", "SBILIFE.NS", "HDFCLIFE.NS", "SHRIRAMFIN.NS"],
    "Auto": ["MARUTI.NS", "M&M.NS", "TATAMOTORS.NS", "BAJAJ-AUTO.NS", "EICHERMOT.NS", "HEROMOTOCO.NS"],
    "Pharma & Health": ["SUNPHARMA.NS", "CIPLA.NS", "DRREDDY.NS", "APOLLOHOSP.NS"],
    "Energy & Power": ["RELIANCE.NS", "ONGC.NS", "COALINDIA.NS", "NTPC.NS", "POWERGRID.NS"],
    "Metals": ["TATASTEEL.NS", "JSWSTEEL.NS", "HINDALCO.NS"],
    "FMCG": ["HINDUNILVR.NS", "ITC.NS", "NESTLEIND.NS", "TATACONSUM.NS"],
    "Infra & Cement": ["LT.NS", "ADANIPORTS.NS", "ADANIENT.NS", "GRASIM.NS", "ULTRACEMCO.NS"],
    "Consumer": ["TITAN.NS", "TRENT.NS", "ASIANPAINT.NS"],
    "Telecom": ["BHARTIARTL.NS"],
    "Defence & Others": ["BEL.NS"],
}

# Period -> sensible default interval for charts
PERIOD_INTERVALS = {
    "1d": "5m",
    "5d": "15m",
    "1mo": "1d",
    "6mo": "1d",
    "1y": "1d",
    "5y": "1wk",
    "max": "1mo",
}
