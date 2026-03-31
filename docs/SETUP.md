# Local Development Setup [Dev Level]

HedgeVision now runs **local-first** by default:
- Local DB: SQLite
- Local broker: paper mode
- Local intelligence: rule-based (or Ollama)

Supabase, external LLMs, and CCXT exchanges are opt-in.

## Prerequisites

- Python 3.10+
- Node.js 18+
- Redis (optional but recommended for caching/rate limits)
- Docker (optional)

## 1) Backend Setup (Local-First)

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e ".[all]"
```

Create backend env:

```bash
cp api/.env.example api/.env
```

Recommended defaults in `backend/api/.env`:

```ini
DATA_BACKEND=sqlite
DB_PATH=backend/prices.db
ENABLE_EXTERNAL_LLM=false
BROKER_BACKEND=paper
LLM_PROVIDER=ollama
LLM_MODEL=llama3.2
```

Run backend:

```bash
python api/run.py
# or
uvicorn api.main:app --reload
```

Health checks:
- `GET /health`
- `GET /ready`

Both should return quickly in SQLite mode.

## 2) Frontend Setup

```bash
cd frontend-v2
npm install
npm run dev
```

Set `frontend-v2/.env.local`:

```ini
VITE_API_BASE_URL=http://localhost:8000
```

## 3) CLI Setup

Install editable package from repo root:

```bash
pip install -e .
```

Run from any directory:

```bash
hedgevision-cli sync --dry-run
hedgevision-cli intel BTC-USD
hedgevision-cli broker-quote BTC-USD
hedgevision-cli onboard
```

`hedgevision-cli onboard` launches an interactive step-by-step wizard that writes local-first env config.

## 4) Optional Supabase Mode

To switch from SQLite to Supabase:

```ini
DATA_BACKEND=supabase
SUPABASE_URL=...
SUPABASE_ANON_KEY=...
SUPABASE_SERVICE_ROLE_KEY=...
SUPABASE_DB_URL=...
```

## 5) Optional External LLM Providers (BYOK)

```ini
ENABLE_EXTERNAL_LLM=true
LLM_PROVIDER=openai      # rules | cpu | openai | anthropic | ollama
LLM_MODEL=gpt-4o-mini
OPENAI_API_KEY=...
ANTHROPIC_API_KEY=...
OLLAMA_BASE_URL=http://localhost:11434
```

All outbound LLM payloads are sanitized before provider calls.

## 6) Optional Broker via CCXT

```ini
BROKER_BACKEND=ccxt
CCXT_EXCHANGE=binance
CCXT_API_KEY=...
CCXT_API_SECRET=...
```

Then:

```bash
hedgevision-cli broker-quote BTC-USD --backend ccxt --exchange binance
```

## Notes

- `hedgevision-cli sync` in SQLite mode skips Supabase-only analytics subprocess stages.
- Keep `.env` files out of git; use `.env.example` as template only.
- UI onboarding wizard is available at `/onboarding` and includes Ollama + CPU-local model setup.
