# HedgeVision

> **Open-source statistical arbitrage platform.** Local-first with optional Supabase scaling.

**HedgeVision** is a production-ready quantitative trading platform for stat-arb strategies. Python backend (FastAPI) + React frontend (Vite/TypeScript). Discover cointegrated pairs, backtest strategies, and run paper trading simulations — **zero external dependencies required**.

Built for **local development by default**. SQLite, paper broker, and rule-based intel run out of the box. Supabase (Postgres), external LLMs (OpenAI/Anthropic/Ollama), and live exchange brokers (CCXT) are **explicit opt-ins**.

This is part of **SuperIntel** — a fully autonomous trading ecosystem. HedgeVision is the first public component. More OSS modules dropping soon.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Node 16+](https://img.shields.io/badge/node-16+-green.svg)](https://nodejs.org/)

---

## 🚀 Quick Start (3 Commands)

### Prerequisites

```bash
# Verify you have:
python --version  # 3.10+
node --version    # 16+
```

### Installation & Setup

```bash
# 1. Clone and install dependencies
git clone https://github.com/ayush108108/hedgevision.git
cd hedgevision
make install

# 2. Start backend + frontend
make dev

# 3. Open dashboard
# → http://localhost:3000 (Frontend)
# → http://localhost:8000/docs (API Docs)
```

**That's it.** You now have a fully functional local setup with SQLite and paper trading.

---

## 📋 Common Commands

```bash
# Development
make dev             # Start backend + frontend (Ctrl+C to stop)
make backend-dev     # Backend only
make frontend-dev    # Frontend only

# Database
make db-status       # Check DB tables and record counts
make db-sync         # Fetch latest market data
make db-reset        # Reset database (⚠️  WARNING: deletes all data)

# Testing
make test            # Run all tests (Python + Frontend)
make test-coverage   # Generate coverage report

# Code Quality
make lint            # Lint Python + Frontend
make format          # Auto-format all code

# Docker (Optional)
make build           # Build containers
make up              # Start containers
make down            # Stop containers
make logs            # View logs

# Help
make help            # Show all commands
```

---

## 🏗️ Architecture

### Local-First Design

| Component | Local Default | Optional Upgrade |
|----------|--------------|------------------|
| **Database** | SQLite (`backend/prices.db`) | Supabase (Postgres) |
| **Broker** | Paper (simulated) | CCXT (live exchanges) |
| **LLM** | Rules (no LLM) | OpenAI / Anthropic / Ollama |
| **Cache** | In-memory | Redis |

### Stack

- **Backend**: FastAPI + Pydantic + SQLite/Supabase
- **Frontend**: React 18 + TypeScript + Vite + TailwindCSS
- **Charts**: Lightweight Canvas + Recharts
- **State**: Zustand (persisted to localStorage)
- **Data Fetching**: TanStack Query (react-query)
- **Testing**: Pytest (90%+ coverage) + Vitest

### Directory Structure

```
hedgevision/
├── hedgevision/        # Core package (models, LLM, broker, pipelines)
├── backend/api/        # FastAPI routers + services + middleware
├── frontend-v2/        # React dashboard
├── scripts/            # Data pipelines, setup, maintenance
├── tests/              # Python tests (pytest)
├── config/             # Asset universe, benchmarks
├── docs/               # Architecture, deployment, scripts
└── Makefile            # All commands (local + Docker)
```

---

## ⚙️ Configuration

### Environment Files

Copy the example files to get started:

```bash
cp backend/api/.env.example backend/api/.env
cp frontend-v2/.env.example frontend-v2/.env.local  # Optional
```

### Local Development (Default)

```ini
# backend/api/.env
DATA_BACKEND=sqlite                    # Use local SQLite
DB_PATH=backend/prices.db              # Database location
BROKER_BACKEND=paper                   # Simulated trading
ENABLE_EXTERNAL_LLM=false              # No LLM required
LLM_PROVIDER=rules                     # Rule-based intel
```

**No external services required.** This is production-ready for local dev and testing.

### Optional: Supabase Upgrade

```ini
DATA_BACKEND=supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_DB_URL=postgresql://...       # For analytics
```

### Optional: Live Trading

```ini
BROKER_BACKEND=ccxt
EXCHANGE_NAME=binance
CCXT_API_KEY=your-key
CCXT_API_SECRET=your-secret
```

### Optional: LLM Providers

```ini
ENABLE_EXTERNAL_LLM=true
LLM_PROVIDER=openai                    # or: anthropic, ollama, cpu

# OpenAI
OPENAI_API_KEY=sk-...

# Anthropic
ANTHROPIC_API_KEY=sk-ant-...

# Ollama (local)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3
```

See [backend/api/.env.example](backend/api/.env.example) for all options.

---

## 🧪 Testing

### Run Tests

```bash
# All tests (Python + Frontend)
make test

# Python only
make test-python
pytest tests/ -v

# Frontend only
make test-frontend
cd frontend-v2 && npm test

# Coverage report
make test-coverage
# Opens htmlcov/index.html
```

### Test Markers

```bash
pytest -m unit           # Unit tests only
pytest -m integration    # Integration tests
pytest -m real_api       # Tests requiring live APIs (skipped by default)
```

### Coverage Requirement

Python tests enforce **90%+ coverage** on the `hedgevision/` package. CI will fail below this threshold.

---

## 📊 Features

### Core Modules

| Feature | Status | Description |
|---------|--------|-------------|
| **Correlation Screener** | ✅ Live | Find correlated asset pairs across crypto/equities |
| **Cointegration Analysis** | ✅ Live | Statistical tests (Engle-Granger, Johansen) |
| **Pair Analysis** | ✅ Live | Z-score, spread, regression, half-life |
| **Backtest Engine** | ✅ Live | Mean-reversion strategy backtesting |
| **Market Intelligence** | ✅ Live | Rule-based + LLM-powered insights |
| **Paper Trading** | ✅ Live | Simulated order execution |

### Optional Features (Env Flags)

```bash
# Enable optional pages (frontend-v2/.env.local)
VITE_FEATURE_BACKTEST=true
VITE_FEATURE_PORTFOLIO=true
VITE_FEATURE_NEWS=true
VITE_FEATURE_CALCULATOR=true
```

### Coming Soon

- **Live Trading Signals**: AI-powered entry/exit recommendations
- **Risk Management**: Position sizing, stop-loss automation
- **Multi-Strategy Support**: Momentum, volatility, arbitrage
- **WebSocket Feeds**: Real-time price updates

---

## 🐳 Docker Deployment

### Development

```bash
make build           # Build containers
make up              # Start services
make logs            # View logs
make down            # Stop services
```

### Production

```bash
make build-prod      # Build with production config
make up-prod         # Start production stack
make health          # Check service health
```

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for full deployment guide.

---

## 📚 Documentation

| Doc | Purpose |
|-----|---------|
| [CLAUDE.md](CLAUDE.md) | AI assistant guidance (project overview, commands, conventions) |
| [SETUP.md](docs/SETUP.md) | Detailed local environment setup |
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design, data flow, DB schema |
| [DEPLOYMENT.md](docs/DEPLOYMENT.md) | Docker orchestration, production deployment |
| [SCRIPTS.md](docs/SCRIPTS.md) | Data pipelines, backfills, maintenance |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Code style, testing, PR process |
| [SECURITY.md](SECURITY.md) | Vulnerability reporting |

---

## 🤝 Contributing

Contributions welcome! Please follow these guidelines:

### Code Style

- **Python**: Black (line-length 100), isort, flake8, mypy strict
- **Frontend**: ESLint, Prettier, TypeScript strict
- **Run**: `make format` before committing

### Testing

- Write tests for all new features
- Maintain 90%+ coverage on `hedgevision/` package
- Mark tests: `@pytest.mark.unit`, `@pytest.mark.integration`

### Pull Requests

1. Fork the repo
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Make changes and add tests
4. Run `make lint` and `make test`
5. Commit with clear messages
6. Push and open a PR

### Issues

- **Bugs**: Include steps to reproduce, expected vs actual behavior
- **Features**: Describe use case and proposed solution
- **Security**: Email [ayushverma108108@gmail.com](mailto:ayushverma108108@gmail.com) directly

---

## 🛡️ Security

HedgeVision includes security hardening:

- **API Key Sanitization**: All outbound payloads scrubbed of secrets
- **Rate Limiting**: Middleware protects against abuse
- **CORS**: Configurable origin allowlist
- **Input Validation**: Pydantic strict models with extra="forbid"
- **SQL Injection Protection**: Parameterized queries throughout

Found a vulnerability? See [SECURITY.md](SECURITY.md) for responsible disclosure.

---

## 📜 License

MIT License — see [LICENSE](LICENSE) for details.

Free to use, modify, and distribute. No warranties. Use at your own risk.

---

## 🌐 Community & Support

- **Issues**: [github.com/ayush108108/hedgevision/issues](https://github.com/ayush108108/hedgevision/issues)
- **Email**: [ayushverma108108@gmail.com](mailto:ayushverma108108@gmail.com)
- **Twitter/X**: [@ayushv_dev](https://twitter.com/ayushv_dev)
- **Website**: [ayushv.dev](https://ayushv.dev)

---

## 🚀 What's Next

HedgeVision is the **first public module** of **SuperIntel** — a fully autonomous, multi-agent trading system with far more components than what you see here.

More OSS releases from this ecosystem coming soon:

- Execution engine with smart order routing
- Multi-strategy portfolio optimizer
- Risk management framework
- Market microstructure analytics

**Want early access?**

- ⭐ Star this repo
- 👁️ Watch for updates
- 📧 Email [join@correlatex.com](mailto:join@correlatex.com)

---

*Built in public. More coming. Fork it, break it, make it better.*

