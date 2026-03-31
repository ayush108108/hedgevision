# HedgeVision

> Open-source statistical arbitrage engine. One fragment of a much larger autonomous trading ecosystem.

**HedgeVision** is a full-stack quantitative trading platform built around statistical arbitrage strategies. Python backend (FastAPI) + React frontend. Discover, backtest, and simulate pairs trading strategies — runs fully locally with SQLite, no external dependencies required.

This is part of something much bigger. A fully agentic, autonomous trading system called **SuperIntel** is being built — HedgeVision is just the first piece going public. More OSS projects from this ecosystem are coming soon.

> Waitlist opens very soon. Stay tuned.
>
> Contact: [ayushverma108108@gmail.com](mailto:ayushverma108108@gmail.com) | [join@correlatex.com](mailto:join@correlatex.com)
>
> Follow the build: [ayushv.dev](https://ayushv.dev) | [github.com/ayush108108](https://github.com/ayush108108)

---

## Key Features

- **Local-First Architecture**: Run everything locally with SQLite — no external services required
- **Statistical Arbitrage Focus**: Built-in cointegration analysis, correlation tracking, and pairs discovery
- **Dual-Backend Support**: SQLite for local dev, Supabase/PostgreSQL for production scaling
- **Paper Trading**: Simulate strategies with realistic order execution before going live
- **Real-Time Dashboard**: React + Vite frontend with live analytics and market intelligence
- **Flexible LLM Integration**: Support for multiple LLM providers (rules, Ollama, OpenAI, Anthropic)
- **Broker Abstraction**: Paper broker by default, CCXT for live exchange connectivity (when enabled)
- **CLI & MCP Tools**: Command-line interface and Model Context Protocol server for automation

---

## Quick Start (5 minutes)

### Prerequisites

- Python 3.10+
- Node.js 16+
- Git

### Set Up Locally

1. **Clone and install**:

```bash
git clone https://github.com/ayush108108/hedgevision.git
cd hedgevision
pip install -e ".[all]"
```

2. **Start the Backend** (from repo root):

```bash
uvicorn backend.api.main:app --reload
# API runs on http://localhost:8000
```

3. **Start the Frontend** (in new terminal, from `frontend-v2/`):

```bash
cd frontend-v2
npm install
npm run dev
# Dashboard on http://localhost:3000
```

4. **Sync market data**:

```bash
hedgevision-cli sync --help
# or
python scripts/pipelines/daily_eod_pipeline.py --dry-run
```

You now have a fully functional local setup with SQLite backend and paper trading.

---

## Documentation

| Level | Doc | Description |
| :--- | :--- | :--- |
| **[Dev]** | [Setup Guide](docs/SETUP.md) | Start here. Complete local environment setup. |
| **[Prod]** | [Architecture](docs/ARCHITECTURE.md) | System design, data flow, component interaction, DB schema. |
| **[Prod]** | [Deployment](docs/DEPLOYMENT.md) | Docker orchestration, staging and production guides. |
| **[Adhoc]** | [Scripts & Tools](docs/SCRIPTS.md) | Data pipelines, backfills, and maintenance scripts. |
| **[Dev]** | [Contributing](CONTRIBUTING.md) | Guidelines for contributing to the codebase. |

---

## Configuration

### Local Development (Default)

```ini
# backend/api/.env (copy from .env.example)
DATA_BACKEND=sqlite
BROKER_BACKEND=paper
ENABLE_EXTERNAL_LLM=false
```

### Production (Optional)

```ini
# Enable Supabase
DATA_BACKEND=supabase
SUPABASE_URL=your-url
SUPABASE_ANON_KEY=your-key

# Enable live trading (CCXT)
BROKER_BACKEND=ccxt
EXCHANGE_NAME=binance

# Enable external LLM
ENABLE_EXTERNAL_LLM=true
LLM_PROVIDER=openai
OPENAI_API_KEY=your-key
```

See [.env.example](backend/api/.env.example) for all options.

---

## Testing

```bash
# Python tests with coverage
pytest --cov=hedgevision

# By marker
pytest -m unit
pytest -m integration

# Frontend tests
cd frontend-v2 && npm test
```

---

## Contributing

Contributions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines — code style (Black, ESLint), testing requirements (90%+ coverage), commit conventions, and PR process.

Found a bug or have a feature request? Open an [issue](https://github.com/ayush108108/hedgevision/issues). For security vulnerabilities, see [SECURITY.md](SECURITY.md).

---

## What's Coming

HedgeVision is the first public piece of **SuperIntel** — an autonomous, fully agentic trading system with far more moving parts than what you see here. Think of this as the quantitative core, made open.

More OSS projects from this ecosystem are dropping soon. If you want to be early:

- Watch this repo
- Follow [ayush108108](https://github.com/ayush108108) on GitHub
- Check [ayushv.dev](https://ayushv.dev) for updates
- Drop a mail at [join@correlatex.com](mailto:join@correlatex.com)

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

*Built in public. More coming.*
