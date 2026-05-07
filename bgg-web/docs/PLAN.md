# bgg-web — Minimal Boardgame Search + Recommender

## Goal
Build a minimal React website that **only reads** data from the existing Flask API (GET-only):

- Search for boardgames by term
- Select a game to fetch the **full** game dataset
- Fetch and show **recommendations** for the selected game

## Non-goals (for this MVP)
- Authentication, users, or write endpoints
- Multiple pages/routes
- Persistent state (no DB in the frontend)
- Complex UI features (filters, sorting, pagination)

## Backend API (contract)
Base URL (local dev): `http://localhost:8443`

Endpoints used by the UI:

- `GET /search/<term>?n=10` → `GameCard[]`
- `GET /games/<id>` → `FullGame`
- `GET /recommend/<id>?n=5` → `GameCard[]`

Notes:
- `GameCard` is a reduced representation (list view)
- `FullGame` is the full dataset (detail view)

### Data shapes (as used by the UI)
The exact backend payload can evolve; the frontend relies on a small stable subset.

`GameCard` (used in search results + recommendations):
- `id: string`
- `name: string`
- `thumbnail: string | null`
- `short_description: string | null`
- `year_published: number | null`
- `min_players/max_players: number | null`
- `min_playing_time/max_playing_time: number | null`
- `rating: number | null`
- `weight: number | null`
- `ranks: { category, rank, bayes_average }[]`

`FullGame` (used in selected game detail):
- `id, name`
- `image | thumbnail`
- `year_published, min/max players, min/max playtime`
- `rating, bayes_rating, weight`
- `categories: string[]` (optional)
- `mechanics: string[]` (optional)
- `description: string` (HTML-ish string; rendered as plain text in MVP)
- `url: string` (optional external link)

## UX (two pages)
The UI is split into two pages for clarity:

- Search page (`/`) — search + results
- Game page (`/game/:id`) — full game + recommendations

### Interaction flow
1. User enters a search term and clicks **Search**
2. UI calls `GET /search/<term>?n=10` and lists results as cards
3. User clicks a card → navigates to `/game/:id`
4. Game page fires in parallel:
   - `GET /games/<id>` for full details
   - `GET /recommend/<id>?n=5` for recommendations
5. Recommendations render as cards; clicking one navigates to `/game/:id` for that game

### Loading/error behavior
- Search and detail requests have independent loading/error states
- Requests are aborted when a new search or selection happens (prevents stale updates)

## Frontend architecture
Tech:
- React + TypeScript + Vite
- pnpm for package management

Key decisions:
- `react-router-dom` with two routes (`/` and `/game/:id`)
- A tiny typed API client wrapper around `fetch`
- Backend description HTML is rendered as **plain text** by stripping tags (safe default)

Shared UI:
- A single reusable `GameCard` component used for both search results and recommendation lists

## Local development
Prereqs:
- Node.js (LTS recommended)
- pnpm
- Backend API running at `http://localhost:8443`

Commands:
- Install: `pnpm install`
- Dev server: `pnpm dev`
- Lint: `pnpm lint`
- Build: `pnpm build`
- Preview build: `pnpm preview`

### API wiring (dev proxy)
In dev, the app calls `/api/...` and Vite proxies to the backend.

- Proxy is configured in [vite.config.ts](../vite.config.ts)
- Default target: `http://localhost:8443`
- Override target with env var: `VITE_API_PROXY_TARGET=http://localhost:8443 pnpm dev`

### API wiring (production)
For production builds (where you likely don’t want a dev proxy), set:

- `VITE_API_BASE_URL` to the backend origin, e.g. `https://your-backend.example.com`

The frontend will then call:
- `https://your-backend.example.com/search/...`
- `https://your-backend.example.com/games/...`
- `https://your-backend.example.com/recommend/...`

If you instead deploy behind a reverse proxy, you can keep using a same-origin `/api` prefix and forward it server-side.

## Project structure
- `src/api/` — API types + fetch wrapper
- `src/components/` — shared UI (reusable `GameCard`)
- `src/pages/` — `SearchPage` and `GamePage`
- `src/lib/` — small utilities (e.g. HTML→text)
- `src/App.tsx` — routes
- `api-samples/` — captured example payloads from the backend
- `scripts/` — helpers (e.g. fetch & write api samples)

## What to build next (optional)
If you decide to expand beyond the MVP:
- Autocomplete (`GET /autocomplete/<term>?n=5`)
- Search debounce + “search as you type”
- Caching (React Query) to avoid refetching the same game repeatedly
- Small card layout improvements (rank display, rating display)
