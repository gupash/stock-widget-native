#!/Users/ashish/.pyenv/versions/3.11.15/bin/python3
"""Lightweight API server for stock widget data."""

import json
import os
import sys
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# Ensure yfinance has a writable cache directory
os.environ.setdefault("XDG_CACHE_HOME", os.path.expanduser("~/.cache"))

CACHE = os.path.expanduser("~/.stock-widget-cache.json")
TICKERS_FILE = os.path.expanduser("~/.stock-widget-tickers.json")

DEFAULT_TICKERS = [
    "ACHR","AMD","ANET","ARQQ","ASTS","AVAV","AVGO","AZN",
    "CEG","CHKP","CRWD","E","GILD","GLOB","GLW","GSAT",
    "IONQ","JNJ","JOBY","LEU","LLY","LRCX","MP","MRK",
    "MRNA","MRVL","NVO","NVS","OKLO","PANW","PFE","PL",
    "PLTR","POET","QBTS","QCOM","QUBT","REMX","RGTI","RIVN",
    "RKLB","RXRX","S","SATS","SERV","SMR","SO","USO","XE","ZS",
]

# Market indices
INDICES = ["^GSPC", "^IXIC"]  # S&P 500, NASDAQ

TIMEFRAMES = {
    "1D": ("1d", "5m"),
    "1W": ("5d", "30m"),
    "1M": ("1mo", "1d"),
    "3M": ("3mo", "1d"),
    "6M": ("6mo", "1wk"),
}

cache_data = {"stocks": [], "indices": [], "earnings": [], "updated": 0}
lock = threading.Lock()


def load_tickers():
    if os.path.exists(TICKERS_FILE):
        try:
            with open(TICKERS_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return DEFAULT_TICKERS[:]


def save_tickers(tickers):
    with open(TICKERS_FILE, "w") as f:
        json.dump(tickers, f)


def fetch_stocks():
    import yfinance as yf
    global cache_data
    tickers = load_tickers()
    stocks = {}
    indices = []

    try:
        tf_data = {}
        for tf_key, (period, interval) in TIMEFRAMES.items():
            tf_data[tf_key] = yf.download(
                " ".join(tickers), period=period, interval=interval,
                group_by="ticker", progress=False
            )

        # Fetch indices separately for reliability
        idx_tf_data = {}
        for tf_key, (period, interval) in TIMEFRAMES.items():
            idx_tf_data[tf_key] = yf.download(
                " ".join(INDICES), period=period, interval=interval,
                group_by="ticker", progress=False
            )

        # Process indices
        for idx_sym in INDICES:
            try:
                entry = {"ticker": idx_sym, "name": "S&P 500" if "GSPC" in idx_sym else "NASDAQ", "timeframes": {}}
                for tf_key, hist in idx_tf_data.items():
                    df = hist[idx_sym] if idx_sym in hist.columns.get_level_values(0) else None
                    if df is None or df.empty:
                        continue
                    closes = df["Close"].dropna().tolist()
                    if len(closes) < 2:
                        continue
                    price = float(closes[-1])
                    start = float(closes[0])
                    change_pct = ((price - start) / start) * 100
                    step = max(1, len(closes) // 20)
                    spark = closes[::step]
                    entry["timeframes"][tf_key] = {
                        "change_pct": round(change_pct, 2),
                        "sparkline": [round(float(v), 2) for v in spark],
                    }
                    if tf_key == "1D":
                        entry["price"] = round(price, 2)
                if "price" in entry:
                    indices.append(entry)
            except Exception:
                continue

        # Process stocks
        for t in tickers:
            try:
                entry = {"ticker": t, "timeframes": {}}
                for tf_key, hist in tf_data.items():
                    df = hist[t] if t in hist.columns.get_level_values(0) else None
                    if df is None or df.empty:
                        continue
                    closes = df["Close"].dropna().tolist()
                    if len(closes) < 2:
                        continue
                    price = float(closes[-1])
                    start = float(closes[0])
                    if start <= 0:
                        continue
                    change_pct = ((price - start) / start) * 100
                    # Sanity bounds: reject clearly erroneous values
                    max_reasonable = {"1D": 50, "1W": 80, "1M": 150, "3M": 300, "6M": 500}
                    if abs(change_pct) > max_reasonable.get(tf_key, 500):
                        continue
                    step = max(1, len(closes) // 20)
                    spark = closes[::step]
                    entry["timeframes"][tf_key] = {
                        "change_pct": round(change_pct, 2),
                        "sparkline": [round(float(v), 2) for v in spark],
                    }
                    if tf_key == "1D":
                        entry["price"] = round(price, 2)

                if "price" not in entry:
                    for tf_key in TIMEFRAMES:
                        if tf_key in entry["timeframes"]:
                            df = tf_data[tf_key][t]
                            entry["price"] = round(float(df["Close"].dropna().iloc[-1]), 2)
                            break

                if "price" in entry and entry["timeframes"]:
                    stocks[t] = entry
            except Exception:
                continue

        # Fix daily with prev close (more reliable than intraday start)
        daily2 = yf.download(" ".join(tickers), period="5d", interval="1d",
                             group_by="ticker", progress=False)
        for t in stocks.keys():
            try:
                ddf = daily2[t] if t in daily2.columns.get_level_values(0) else None
                if ddf is None:
                    continue
                closes = ddf["Close"].dropna()
                if len(closes) >= 2:
                    prev_close = float(closes.iloc[-2])
                    price = stocks[t]["price"]
                    if prev_close > 0:
                        daily_change = ((price - prev_close) / prev_close) * 100
                        if abs(daily_change) <= 50:
                            stocks[t]["timeframes"]["1D"]["change_pct"] = round(daily_change, 2)
            except Exception:
                continue

        daily2_idx = yf.download(" ".join(INDICES), period="5d", interval="1d",
                                 group_by="ticker", progress=False)
        for idx_entry in indices:
            try:
                t = idx_entry["ticker"]
                ddf = daily2_idx[t] if t in daily2_idx.columns.get_level_values(0) else None
                if ddf is None:
                    continue
                closes = ddf["Close"].dropna()
                if len(closes) >= 2:
                    prev_close = float(closes.iloc[-2])
                    price = idx_entry["price"]
                    if prev_close > 0:
                        daily_change = ((price - prev_close) / prev_close) * 100
                        if abs(daily_change) <= 20:
                            idx_entry["timeframes"]["1D"]["change_pct"] = round(daily_change, 2)
            except Exception:
                continue
    except Exception as e:
        print(f"Fetch error: {e}", file=sys.stderr)
        return

    result = list(stocks.values())
    with lock:
        # Preserve earnings from previous fetch (avoid intermittent disappearance)
        prev_earnings = cache_data.get("earnings", [])
        cache_data = {
            "stocks": result,
            "indices": indices if indices else cache_data.get("indices", []),
            "earnings": prev_earnings,
            "updated": time.time(),
        }
    try:
        with open(CACHE, "w") as f:
            json.dump(cache_data, f)
    except Exception:
        pass


def fetch_earnings():
    """Fetch upcoming earnings dates for all tracked tickers."""
    import yfinance as yf
    from datetime import datetime, timedelta
    tickers = load_tickers()
    now = datetime.now()
    cutoff = now + timedelta(days=15)
    earnings = []
    for t in tickers:
        try:
            tk = yf.Ticker(t)
            dates = tk.earnings_dates
            if dates is None or dates.empty:
                continue
            for dt_idx in dates.index:
                dt = dt_idx.to_pydatetime().replace(tzinfo=None)
                if now.date() <= dt.date() <= cutoff.date():
                    eps_est = None
                    try:
                        val = dates.loc[dt_idx, "EPS Estimate"]
                        if val is not None and str(val) != 'nan':
                            eps_est = round(float(val), 2)
                    except Exception:
                        pass
                    earnings.append({
                        "ticker": t,
                        "date": dt.strftime("%Y-%m-%d"),
                        "time": dt.strftime("%H:%M") if dt.hour > 0 else None,
                        "eps_estimate": eps_est,
                    })
                    break  # only next upcoming date per ticker
        except Exception:
            continue
    earnings.sort(key=lambda x: x["date"])
    return earnings


def refresh_loop():
    while True:
        fetch_stocks()
        try:
            earns = fetch_earnings()
            with lock:
                cache_data["earnings"] = earns
            try:
                with open(CACHE, "w") as f:
                    json.dump(cache_data, f)
            except Exception:
                pass
        except Exception as e:
            print(f"Earnings fetch error: {e}", file=sys.stderr)
        time.sleep(60)


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/api/stocks':
            with lock:
                data = json.dumps(cache_data)
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(data.encode())
        elif self.path == '/api/tickers':
            tickers = load_tickers()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(tickers).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == '/api/tickers/add':
            length = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(length))
            ticker = body.get('ticker', '').upper().strip()
            if ticker:
                tickers = load_tickers()
                if ticker not in tickers:
                    tickers.append(ticker)
                    save_tickers(tickers)
                    # Trigger refresh in background
                    threading.Thread(target=fetch_stocks, daemon=True).start()
                self._json_response({"ok": True, "tickers": tickers})
            else:
                self._json_response({"ok": False, "error": "No ticker"}, 400)
        elif parsed.path == '/api/tickers/remove':
            length = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(length))
            ticker = body.get('ticker', '').upper().strip()
            tickers = load_tickers()
            if ticker in tickers:
                tickers.remove(ticker)
                save_tickers(tickers)
            self._json_response({"ok": True, "tickers": tickers})
        else:
            self.send_response(404)
            self.end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def _json_response(self, data, code=200):
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def log_message(self, format, *args):
        pass


if __name__ == '__main__':
    if os.path.exists(CACHE):
        try:
            with open(CACHE) as f:
                cache_data = json.load(f)
        except Exception:
            pass

    threading.Thread(target=refresh_loop, daemon=True).start()
    print("Stock API server on http://127.0.0.1:5051", file=sys.stderr)
    HTTPServer(('127.0.0.1', 5051), Handler).serve_forever()
