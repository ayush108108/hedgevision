# HedgeVision

> An open-source statistical arbitrage platform for quantitative trading research and development.

**HedgeVision** is a full-stack quantitative trading platform designed around statistical arbitrage strategies. It combines a powerful Python backend (FastAPI) with a modern React frontend to provide researchers, traders, and developers with tools to discover, backtest, and simulate trading pairs strategies locally or in the cloud.

## 🎯 Key Features

- **Local-First Architecture**: Run everything locally with SQLite — no external services required
- **Statistical Arbitrage Focus**: Built-in cointegration analysis, correlation tracking, and pairs discovery
- **Dual-Backend Support**: SQLite for local development, Supabase/PostgreSQL for production scaling
- **Paper Trading**: Simulate trading strategies with realistic order execution before going live
- **Real-Time Dashboard**: React + Vite frontend with live analytics and market intelligence
- **Flexible LLM Integration**: Support for multiple LLM providers (rules, Ollama, OpenAI, Anthropic)
- **Broker Abstraction**: Paper broker by default, CCXT for live exchange connectivity (when enabled)
- **CLI & MCP Tools**: Command-line interface and Model Context Protocol server for automation


## 📂 Project Structure

```bash
.
├── CONTRIBUTING.md
├── README.md
├── assets_mapping_yfi
├── backend
│   ├── Dockerfile
│   ├── Dockerfile.audit-test
│   ├── Supabase_schema
│   ├── __init__.py
│   ├── agents
│   │   └── market_intel.py
│   ├── api
│   │   ├── __init__.py
│   │   ├── audit
│   │   ├── cli
│   │   ├── main.py
│   │   ├── repositories
│   │   ├── routers
│   │   ├── run.py
│   │   ├── services
│   │   └── utils
│   ├── check_db_status.py
│   ├── clients
│   │   ├── base_client.py
│   │   ├── ccxt_client.py
│   │   └── yfinance_client.py
│   ├── docker-compose.audit-test.yml
│   ├── requirements.txt
│   ├── run.py
│   ├── run_market_intel_demo.py
│   └── scripts
├── config
│   └── asset_universe_master.yaml
├── docs
│   ├── ARCHITECTURE.md
│   ├── DEPLOYMENT.md
│   ├── SCRIPTS.md
│   └── SETUP.md
├── frontend-v2
│   ├── Dockerfile
│   ├── README.md
│   ├── TESTING.md
│   ├── index.html
│   ├── nginx.conf
│   ├── package.json
│   ├── postcss.config.cjs
│   ├── public
│   ├── src
│   │   ├── App.tsx
│   │   ├── assets
│   │   ├── auth
│   │   ├── components
│   │   ├── config
│   │   ├── constants
│   │   ├── hooks
│   │   ├── main.tsx
│   │   ├── pages
│   │   ├── services
│   │   ├── state
│   │   ├── test
│   │   ├── themes
│   │   ├── types
│   │   ├── utils
│   │   └── vite-env.d.ts
│   ├── tailwind.config.cjs
│   ├── tailwind.config.js
│   ├── tsconfig.json
│   ├── vite.config.ts
│   └── vitest.config.ts
├── holiday_data
├── pyproject.toml
├── pytest.ini
├── requirements.txt
├── scripts
│   ├── README.md
│   ├── apply_schema.py
│   ├── bootstrap_assets_timescale.py
│   ├── cleanup_disabled_assets.py
│   ├── comprehensive_multi_tier_eda.py
│   ├── compute_rolling_metrics_standalone.py
│   ├── data_validation_checks.sql
│   ├── db
│   ├── debug
│   ├── etl
│   ├── extract_assets_list.py
│   ├── master_all_time_workflow.py
│   ├── pipelines
│   ├── populate_cointegration.py
│   ├── precompute_correlations.py
│   ├── preflight_check.py
│   ├── quick_cleanup_db.py
│   ├── run_population_workflow.py
│   ├── setup
│   ├── simple_validation.py
│   ├── smoke_import.py
│   ├── test_ci_workflows.py
│   ├── truncate_db.py
│   ├── validate_docs_layout.py
│   └── validate_yfinance_tickers.py
├── tests
│   ├── README.md
│   ├── UNIT_TEST_COMPLETION_SUMMARY.md
│   ├── conftest.py
│   ├── test_*.py
│   └── __pycache__
└── tools
    └── generate_asset_mapping_md.py
```

## 📚 Documentation Index

Our documentation is structured by operational level:

| Level | Doc | Description |
| :--- | :--- | :--- |
| **[Dev Level]** | [**Setup Guide**](docs/SETUP.md) | **start here**. Complete local environment setup (Python, Node, Docker). |
| **[Prod Level]** | [**Architecture**](docs/ARCHITECTURE.md) | System design, data flow, component interaction, and database schema. |
| **[Prod Level]** | [**Deployment**](docs/DEPLOYMENT.md) | Staging and Production deployment guides, Docker orchestration, and CI/CD. |
| **[Adhoc Level]** | [**Scripts & Tools**](docs/SCRIPTS.md) | Guide to the `scripts/` directory for data pipelines, backfills, and maintenance. |
| **[Dev Level]** | [**Contributing**](CONTRIBUTING.md) | Guidelines for contributing to the codebase. |

## 🚀 Quick Start (5 minutes)

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
   # In another terminal
   hedgevision-cli sync --help
   # or
   python scripts/pipelines/daily_eod_pipeline.py --dry-run
   ```

✅ **You now have a fully functional local setup** with SQLite backend and paper trading.

## 🔧 Common Commands

### Backend

```bash
# Development server
uvicorn backend.api.main:app --reload

# Run tests
pytest

# Lint & format
black --line-length 100 .
isort --profile black --line-length 100 .
flake8 .
```

### Frontend

```bash
# Development server
cd frontend-v2 && npm run dev

# Build
npm run build

# Tests
npm test

# Lint
npm run lint
```

### Data Pipeline

```bash
# Sync daily data
python scripts/pipelines/daily_eod_pipeline.py

# Via CLI
hedgevision-cli sync

# Dry-run mode
hedgevision-cli sync --dry-run
```

## 🔐 Configuration

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

## 🧪 Testing

```bash
# Python tests with coverage
pytest --cov=hedgevision

# By marker
pytest -m unit
pytest -m integration

# Frontend tests
cd frontend-v2 && npm test
```

## 🤝 Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines:
- Code style (Black, ESLint)
- Testing requirements (90%+ coverage)
- Commit conventions
- PR process

## 🐛 Reporting Issues

Found a bug or have a feature request? Open an [issue](https://github.com/ayush108108/hedgevision/issues).

For security vulnerabilities, please see [SECURITY.md](SECURITY.md).

## 📖 Learning Resources

- **[Pairs Trading 101](https://en.wikipedia.org/wiki/Pairs_trading)**: Statistical arbitrage fundamentals
- **[Cointegration & Stationarity](https://en.wikipedia.org/wiki/Cointegration)**: Core quant concepts
- **[FastAPI Docs](https://fastapi.tiangolo.com/)**: Backend API framework
- **[React + Vite](https://vitejs.dev/)**: Frontend build & dev tools

## 📜 License

This project is licensed under the MIT License — see [LICENSE](LICENSE) for details.

## 🙋 Support

- **Documentation**: See [docs/](docs/) directory
- **Issues**: [GitHub Issues](https://github.com/ayush108108/hedgevision/issues)
- **Discussions**: [GitHub Discussions](https://github.com/ayush108108/hedgevision/discussions)

---

**Built with ❤️ for the open-source quant community.**
