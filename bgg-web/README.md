# bgg-web

Minimal single-page React app for a read-only boardgame search + recommender.

## Local dev
Prereqs:
- Backend API running at `http://localhost:8443`
- `pnpm`

Commands:
- `pnpm install`
- `pnpm dev`

The frontend calls `/api/...` and Vite proxies to the backend (see [vite.config.ts](vite.config.ts)).

## Docs
- Project plan: [docs/PLAN.md](docs/PLAN.md)
