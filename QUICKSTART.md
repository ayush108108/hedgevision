# HedgeVision Quick Start Guide

**Get up and running in under 5 minutes.**

## Prerequisites

```bash
python --version  # 3.10+
node --version    # 16+
```

## 1. Installation

```bash
# Clone the repository
git clone https://github.com/ayush108108/hedgevision.git
cd hedgevision

# Install all dependencies (Python + Node)
make install
```

## 2. Start the Application

```bash
# Start both backend and frontend
make dev
```

This will:
- Start the backend API on `http://localhost:8000`
- Start the frontend on `http://localhost:3000`
- Open API docs at `http://localhost:8000/docs`

**Dashboard**: Open `http://localhost:3000` in your browser

## 3. Initial Data Setup (Optional)

The app runs with SQLite by default. To populate with sample data:

```bash
# Check database status
make db-status

# Sync latest market data (requires internet)
make db-sync

# Or run a specific data import
hedgevision-cli sync --help
```

## 4. Explore the Features

### Core Pages

1. **Correlation Screener** (`/correlation`)
   - Find correlated asset pairs
   - Filter by correlation threshold
   - Real-time correlation matrix

2. **Cointegration Analysis** (`/cointegration`)
   - Statistical cointegration tests
   - Engle-Granger and Johansen tests
   - Half-life calculations

3. **Pair Analysis** (`/pair-analysis`)
   - Detailed pair statistics
   - Z-score and spread charts
   - Rolling metrics visualization
   - Regression analysis

4. **Backtest Engine** (`/backtest`)
   - Mean-reversion strategy backtesting
   - Configurable entry/exit thresholds
   - Performance metrics (Sharpe, Sortino, Max DD)
   - Trade history and equity curves

5. **Trading Signals** (`/signals`)
   - AI-powered market intelligence
   - Structured verdict analysis
   - Coming soon: Live signal generation

## 5. Configuration

### Local SQLite (Default)

No configuration needed. Works out of the box.

### Optional: Enable Supabase

```bash
# Create backend/api/.env
cp backend/api/.env.example backend/api/.env

# Edit .env
DATA_BACKEND=supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
```

### Optional: Enable LLM Providers

```bash
# In backend/api/.env
ENABLE_EXTERNAL_LLM=true
LLM_PROVIDER=openai  # or: anthropic, ollama, cpu

# Add API keys
OPENAI_API_KEY=sk-...
# or
ANTHROPIC_API_KEY=sk-ant-...
```

## 6. Common Tasks

```bash
# View all available commands
make help

# Run tests
make test

# Lint and format code
make lint
make format

# Reset database (⚠️  WARNING: deletes all data)
make db-reset

# Docker deployment
make build
make up
```

## 7. Troubleshooting

### Backend won't start

```bash
# Check Python version
python --version  # Should be 3.10+

# Reinstall dependencies
pip install -e ".[all]"

# Check for port conflicts
lsof -i :8000
```

### Frontend won't build

```bash
# Check Node version
node --version  # Should be 16+

# Clean and reinstall
cd frontend-v2
rm -rf node_modules package-lock.json
npm install
```

### No data showing in UI

```bash
# Check database
make db-status

# Sync market data
make db-sync

# Or populate test data
python scripts/setup/init_db.py
```

### Metrics not showing

```bash
# Generate rolling metrics
python scripts/populate_sqlite_metrics.py

# Or use Supabase backend for pre-computed metrics
# (See Configuration section above)
```

## 8. Next Steps

- **Read the docs**: [ARCHITECTURE.md](docs/ARCHITECTURE.md)
- **Explore the API**: http://localhost:8000/docs
- **Run tests**: `make test`
- **Contribute**: [CONTRIBUTING.md](CONTRIBUTING.md)

## 9. Getting Help

- **Issues**: https://github.com/ayush108108/hedgevision/issues
- **Email**: ayushverma108108@gmail.com
- **Docs**: [README.md](README.md)

---

**Ready to trade? Start with the Correlation Screener to find promising pairs!**
