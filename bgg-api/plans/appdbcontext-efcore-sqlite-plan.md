## Plan: Finish AppDbContext EF Core (SQLite)

Complete the EF Core model so it cleanly builds on SQLite and supports search/filter/recommendation use-cases. This adds missing DbSets, configures relationships explicitly (including self-referencing recommendations), and adds a small set of pragmatic indexes/uniqueness constraints.

**Phases**
1. **Phase 1: DbSets + model-build safety**
    - **Objective:** Ensure EF model builds reliably by adding all `DbSet<>`s and explicitly handling properties EF can’t map.
    - **Files/Functions to Modify/Create:**
        - Src/Data/AppDbContext.cs (`OnModelCreating`)
    - **Tests to Write:**
        - bgg-api.Tests: `Model_builds_and_creates_schema` (SQLite in-memory)
    - **Steps:**
        1. Add `DbSet<>` for all entity types in `Src/Entities/*`.
        2. Configure `BoardGame` to ignore `Honors`, `Subdomains`, and `PlayerCountPollVotes` (dictionary), since they’re frontend-only / non-relational.
        3. Add `BoardGame` → `AlternativeName` one-to-many.
        4. Run the new test to confirm model builds and `EnsureCreated()` succeeds.

2. **Phase 2: Relationships (1:M, M:M, self-reference)**
    - **Objective:** Define the relationships EF conventions might not infer correctly and prevent cascade-cycle problems in SQLite.
    - **Files/Functions to Modify/Create:**
        - Src/Data/AppDbContext.cs (`OnModelCreating`)
    - **Tests to Write:**
        - bgg-api.Tests: `Recommendations_are_non_cascading` (delete behavior smoke test)
    - **Steps:**
        1. Configure one-to-many dependents: `Credit`, `Expansion`, `Reimplements`, `Rank`, `ShopOffer`, `BoardgameVersion`, `PlayerCountPollVote`.
        2. Configure many-to-many join tables for `Categories`, `Mechanics`, `Families`, `Types` using `UsingEntity` with composite keys.
        3. Configure `BoardGameRecommendation` with two FKs to `BoardGame` and `DeleteBehavior.Restrict`/`NoAction`.

3. **Phase 3: Indexes + uniqueness for API queries**
    - **Objective:** Add the minimal indexes and uniqueness constraints that matter for search/filter and recommendation lookups.
    - **Files/Functions to Modify/Create:**
        - Src/Data/AppDbContext.cs (`OnModelCreating`)
    - **Tests to Write:**
        - bgg-api.Tests: `Lookup_names_are_unique` (Category/Mechanic/Family/Type)
    - **Steps:**
        1. Add unique indexes on `Name` for `Category`, `Mechanic`, `Family`, `BoardgameType`.
        2. Add key indexes on `BoardGame` for common filters (e.g., `Name`, `YearPublished`, `HasDanishVersion`, rating fields).
        3. Add recommendation uniqueness/indexes: unique `(SeedBoardGameId, RecommendedBoardGameId)` and FK indexes.
        4. Add `Rank` uniqueness: unique `(BoardGameId, Category)`.
        5. Run `dotnet test` to confirm all tests pass.

**Open Questions**
1. None (decisions made: `AlternativeName` is a table; `Honors`/`Subdomains` ignored; player-count scores stored via `PlayerCountPollVote`; lookup names unique).
