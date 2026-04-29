# Private board game discovery (friends-only)

Short description  
A private site for you and friends that uses the BGG data dump + BGG XML API as canonical data and adds natural-language search, better similarity, and on-demand multi-site price checks.

## Core features
- Natural-text search (embeddings over description + tags + mechanics) combined with keyword/attribute filters.  
- "Similar games" via vector DB (nearest neighbors on combined text+tags).  
- Advanced filters: genre, year, rating, best player count, mechanics, image availability.  
- Wishlist + price-drop alerts.  
- On-demand price search (user-triggered scrape of pricerunner.dk, dba.dk, braetspilspriser.dk, etc.), cached with TTL.  
- YouTube rule-video embeds on game pages.  
- Only show games with >= 50 user ratings (BGG usersrated filter).  
- BGG ID as canonical key; cluster/merge editions by title + year to avoid duplicates.

## Data pipeline (concise)
- Daily download of BGG CSV (baseline data).  
- Track ratings count deltas per game; if ratings change significantly, re-fetch that game's attributes via BGG XML API (thing?id=...&stats=1).  
- Fetch tags/genres/mechanics separately as needed and normalize vocab.  
- Store description, tags, mechanics, images, stats; create embeddings and save in vector DB.  
- Batch and backoff API calls; rely on CSV to minimize requests.

## Search & similarity approach
- Build embeddings from description + concatenated tags + mechanics.  
- Combine vector similarity for relevance with filter-based precision (genre/year/rating).  
- Cache vectors and nearest-neighbor results; refresh when underlying data changes (e.g., big ratings jump).

## Price search & normalization
- User clicks "search prices" -> enqueue background job to scrape configured sources.  
- Normalize results: currency, condition (new/used), edition matching, shipping heuristics.  
- Match listings to canonical BGG ID by title/year/image heuristics and dedupe.  
- Cache results per user/game with configurable TTL (e.g., 6–24h).

## Operational notes / constraints
- Private, friends-only: no heavy moderation required.  
- Use BGG CSV as primary bulk source; use XML API selectively for stats/updates.  
- Handle edition/title deduplication carefully.  
- Expect price-scrape fragility — keep it user-triggered and cached.  
- Respect BGG API limits (batching/backoff) even for private use.

## Suggested tech (brief)
- Postgres (metadata) + Redis (cache)  
- Vector DB: Pinecone / Weaviate / Milvus  
- Embeddings: OpenAI (prototype) or local LLMs  
- Backend: FastAPI / Node (XML parsing)  
- Background workers: Celery / RQ / BullMQ  
- Frontend: React (Vite)

## Next practical step
1. Implement daily CSV downloader + ratings-change detector.  
2. Build ingest job that re-fetches changed games and writes normalized records + embeddings.