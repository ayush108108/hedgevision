# Frontend v2 Overview

The React + Vite dashboard lives in this folder. Detailed guides sit under `docs/` so frontend contributors stay oriented without spelunking through the global `docs/` tree.

## Directory Highlights
- `src/` – Feature modules, hooks, and UI components.
- `public/` – Static assets served by Vite.
-- `docs/` – Feature plans, testing strategy, refactor notes, and UI screenshots (under `frontend-v2/docs/`).
-- `TESTING.md` – Entry point that links to `docs/TESTING.md` for the complete testing workflow (see `frontend-v2/docs/TESTING.md`).

## Developer Workflow
1. Install dependencies: `npm install`.
2. Copy `.env.example` to `.env.local` and set `VITE_API_BASE_URL` plus Supabase keys.
3. Run locally: `npm run dev`.
4. See `frontend-v2/docs/FRONTEND_ACTION_PLAN.md` for the current optimization roadmap.

Keep documentation close to the code to reinforce the "100 lines over 1000" ethos—if a doc explains a feature, it belongs beside its implementation.