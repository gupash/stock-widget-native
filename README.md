# Stock Widget for macOS

A native macOS desktop widget that tracks stock prices with live updates. Built with Swift (WKWebView) and a Python data server.

![macOS](https://img.shields.io/badge/macOS-14%2B-blue) ![Swift](https://img.shields.io/badge/Swift-5.9-orange) ![Python](https://img.shields.io/badge/Python-3.11-green)

## Features

- **S&P 500 & NASDAQ** index cards at the top
- **Top 10 Gainers/Losers** with sparkline charts
- **All Stocks** tab with 1D/1W/1M/3M/6M timeframes
- **Add/Remove tickers** dynamically
- **Reorder stocks** with ▲/▼ arrows
- **Upcoming Earnings** (next 15 days) on the Top Movers page
- **60-second auto-refresh**
- **Menubar icon** (📈) with Show/Hide/Refresh/Quit
- **Spotlight searchable** — reopen via "Stock Widget"
- Glassmorphism UI, no Dock icon, stays on one Space

## Requirements

- macOS 14+ (Sonoma, Apple Silicon)
- No Xcode required

## Install via Homebrew (Recommended)

```bash
brew install gupash/stock-widget/stock-widget
brew services start stock-widget
stock-widget
```

That's it. Homebrew handles Python, yfinance, Swift compilation, and app installation.

**Manage the service:**
```bash
brew services start stock-widget   # start data server (auto-starts on login)
brew services stop stock-widget    # stop data server
brew services restart stock-widget # restart data server
```

**Launch the widget:**
```bash
stock-widget                       # CLI command
open -a "Stock Widget"             # or via Spotlight → "Stock Widget"
```

**Hide/Show:** Use the 📈 menubar icon → Show Widget / Hide Widget / Quit.

## Stock List

The widget ships with a default list of ~50 stocks (a personal watchlist). You can add or remove tickers directly from the widget UI using the **All Stocks** tab — type a ticker in the text box and click **+ Add**, or click **✕** next to any stock to remove it. Your custom list is saved to `~/.stock-widget-tickers.json` and persists across restarts.

> **Future:** If the widget gains traction, we plan to add support for providing a custom initial stock list (e.g. via a config file or CLI flag) to replace the default set entirely.

## Manual Install

```bash
# Install Python dependency
pip install yfinance

# Compile the app
swiftc -o StockWidget.app/Contents/MacOS/StockWidget main.swift \
  -framework Cocoa -framework WebKit -target arm64-apple-macosx14.0

# Copy HTML to app bundle
mkdir -p StockWidget.app/Contents/Resources
cp widget.html StockWidget.app/Contents/Resources/widget.html
cp Info.plist StockWidget.app/Contents/Info.plist

# Install to Applications (for Spotlight)
cp -R StockWidget.app "/Applications/Stock Widget.app"

# Start
./start.sh
```

## Architecture

| Component | File | Role |
|-----------|------|------|
| Swift App | `main.swift` | Native borderless window, WKWebView, menubar, drag handle |
| Python Server | `server.py` | HTTP API — fetches yfinance data, ticker CRUD, 60s refresh loop |
| HTML UI | `widget.html` | Full UI rendered in WKWebView — indices, tabs, sparklines |
| Launcher | `start.sh` | Convenience script to start server + app |

## License

MIT
