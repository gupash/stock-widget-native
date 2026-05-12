#!/bin/bash
# Start Stock Widget — data server + native app

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON="/Users/ashish/.pyenv/versions/3.11.15/bin/python3"

# Start data server if not already running
if ! curl -s http://127.0.0.1:5051/api/stocks > /dev/null 2>&1; then
    nohup "$PYTHON" "$SCRIPT_DIR/server.py" > /tmp/stock-widget-server.log 2>&1 &
    echo "Started data server (PID: $!)"
    sleep 2
else
    echo "Data server already running"
fi

# Launch the app
open "/Applications/Stock Widget.app"
echo "Widget launched"
