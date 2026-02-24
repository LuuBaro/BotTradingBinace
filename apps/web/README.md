# Web Dashboard (Phase 1 - Basic)

Simple HTML dashboard for monitoring the trading bot.

## Running

Since this is a simple HTML file, you can:

1. Open directly in browser:
```bash
# Open in default browser
start apps/web/index.html  # Windows
```

2. Or serve via Python HTTP server:
```bash
cd apps/web
python -m http.server 3000
# Then open http://localhost:3000
```

3. Or use the API server to serve static files (Phase 2+)

## Features (Phase 1)

- Real-time WebSocket connection status
- Active positions count
- Recent events log
- Positions table
- Manual refresh button

## Planned Features (Phase 4)

- Full React/Vite app
- Real-time charts
- Trade history
- Risk config editor
- Manual trading controls
- Performance analytics
