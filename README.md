# DraftGenius 🏏

> **AI-powered PSL 2026 fantasy XI builder** — pick a match, pick two franchises, get three optimised teams in seconds.

DraftGenius combines **Hidden Markov Model (HMM) form prediction**, a **T20-tuned Elo rating engine**, and a **Genetic Algorithm (GA) team optimizer** into a full-stack application. The React frontend is served by the **Vite dev server** which proxies all `/api` calls to Flask — no build step needed during development.

---

## Quick Start

### Prerequisites

| Tool | Version |
|---|---|
| Python | ≥ 3.10 |
| pip | latest |
| Node.js + npm | ≥ 18 |

```bash
# Install Python dependencies
pip install -r requirements.txt

# Install frontend dependencies (first time only)
cd frontend && npm install && cd ..
```

**Terminal 1 — backend API:**
```bash
python run.py
```

**Terminal 2 — frontend dev server:**
```bash
cd frontend && npm run dev
```

Open **http://localhost:5173** in your browser. Vite proxies all `/api/*` requests to Flask at port 5000.

> **Single-terminal shortcut:** `python run.py --with-frontend` launches both together.

---

## Data Files Required

The following files must be present before starting. They are **not** included in the repository due to size.

| Path | Description | Size |
|---|---|---|
| `data/all_leagues_player_match_elo.csv` | Full match history with Elo columns — the core dataset | ~35 MB |
| `data/psl_2026_roster_overrides.json` | PSL 2026 franchise → player mapping | small |
| `data/people.csv` | Cricsheet player registry (name ↔ ID mapping) | small |
| `models/hmm_form_models.joblib` | Pre-trained role-level HMM (bundled) | ~30 KB |

Optional:

| Path | Description |
|---|---|
| `data/output/role_cache.json` | ESPN-scraped role cache (player_id → role) |
| `data/output/player_profiles.json` | ESPN photo URL cache |
| `data/credits_override.json` | Manual credit overrides for specific players |
| `data/active_overrides.json` | Persisted bench/reinstate state |
| `data/constraints.json` | Persisted GA constraint settings |

---

## run.py — CLI Reference

```
python run.py [OPTIONS]
```

| Flag | Default | Description |
|---|---|---|
| `--port PORT` | `5000` | Flask API port to listen on |
| `--with-frontend` | off | Also launch `npm run dev` in `frontend/` alongside the backend |
| `--update-data` | off | Download latest match data from Cricsheet, then re-run the Elo pipeline |
| `--retrain-models` | off | Delete all cached per-player HMM models so they are re-fitted at next startup |

### Startup sequence

```
parse args
  → [--update-data]    CricsheetUpdater + Pipeline + EloEngine
  → [--retrain-models] delete models/per_player/*.joblib
  → check_data_files()     (warn if critical CSVs / JSONs missing)
  → init_cache()           (load all data into memory)
  → create_app()           (register Flask blueprints)
  → [--with-frontend]  launch Vite dev server subprocess
  → app.run()
```

---

## Project Layout

```
DraftGeniusServer/
├── run.py                          ← Single entry point (see above)
├── requirements.txt                ← Python dependencies
│
├── data/                           ← All data files (NOT in repo)
│   ├── all_leagues_player_match_elo.csv   ← 35 MB match history + Elo
│   ├── people.csv                         ← Cricsheet player registry
│   ├── psl_2026_roster_overrides.json     ← PSL 2026 franchise mapping
│   ├── credits_override.json              ← Manual credit overrides
│   ├── active_overrides.json              ← Bench/reinstate state (auto-written)
│   ├── constraints.json                   ← Saved GA settings (auto-written)
│   └── output/
│       ├── role_cache.json                ← ESPN role cache
│       └── player_profiles.json           ← ESPN photo URL cache
│
├── models/
│   ├── hmm_form_models.joblib             ← Pre-trained role-level HMM
│   ├── hmm_relative_form_models.joblib    ← Relative form variant
│   └── per_player/                        ← Auto-created per-player HMMs
│
├── backend/
│   ├── app.py                             ← Flask factory (API + SPA)
│   ├── data_cache.py                      ← Startup data loader / singletons
│   ├── cli.py                             ← Data pipeline CLI (--update-data)
│   │
│   ├── core/
│   │   ├── elo_engine.py                  ← T20 Elo engine
│   │   ├── scoring.py                     ← Fantasy points calculator
│   │   ├── form_features.py               ← Rolling-avg feature builder
│   │   └── hmm/
│   │       ├── general_hmm.py             ← Role-level HMM wrapper
│   │       ├── short_term_hmm.py          ← Per-player short-term HMM
│   │       └── predictor.py               ← Unified HMMPredictor (used by backend)
│   │
│   ├── services/
│   │   ├── player_service.py              ← Builds PlayerProfile list
│   │   ├── team_generator.py              ← Genetic Algorithm optimizer
│   │   ├── credit_engine.py               ← Auto-derives fantasy credits
│   │   ├── role_resolver.py               ← ESPN role resolver
│   │   └── profile_fetcher.py             ← ESPN photo fetcher
│   │
│   ├── routes/
│   │   ├── players.py                     ← /api/players, /api/players/<id>/history
│   │   ├── teams.py                       ← /api/generate-teams, /api/stream/<run_id>
│   │   ├── match.py                       ← /api/match/teams
│   │   ├── roster.py                      ← /api/roster/bench, /api/roster/reinstate
│   │   └── constraints.py                 ← /api/constraints
│   │
│   ├── jobs/
│   │   ├── data_updater.py                ← Cricsheet ZIP downloader (ETag-aware)
│   │   ├── match_parser.py                ← Cricsheet JSON → rows
│   │   ├── match_loader.py                ← Loads raw match rows
│   │   ├── pipeline.py                    ← Orchestrates parse → score → Elo
│   │   └── fantasy_elo_pipeline.py        ← Thin wrapper
│   │
│   ├── utils/
│   │   ├── config.py                      ← PipelineConfig dataclass
│   │   ├── models.py                      ← Shared type definitions
│   │   └── smart_cache.py                 ← Simple TTL cache helper
│   │
│   └── static/                            ← Built React SPA (served at /)
│
└── frontend/                              ← React + Vite + TypeScript source
    ├── src/
    │   ├── main.tsx                       ← React entry point
    │   ├── App.tsx                        ← Router + franchise CSS vars
    │   ├── pages/
    │   │   ├── Home.tsx                   ← Match selector page
    │   │   ├── Match.tsx                  ← Player pool / war room page
    │   │   └── Results.tsx                ← Generated teams results page
    │   ├── components/
    │   │   ├── players/                   ← Player card components
    │   │   ├── warroom/                   ← War-room panel components
    │   │   └── evolution/                 ← GA evolution chart
    │   ├── api/                           ← Typed fetch wrappers
    │   ├── hooks/                         ← Custom React hooks
    │   ├── types/                         ← TypeScript interfaces
    │   ├── constants/                     ← Franchise colours / config
    │   └── lib/                           ← Shared utilities
    ├── vite.config.ts                     ← Vite build → backend/static/
    └── tailwind.config.ts
```

---

## How It Works — Full Pipeline

### 1. Data Ingestion (`--update-data`)

```
Cricsheet.org (ZIP archives)
  ↓  ETag-aware HTTP download (CricsheetUpdater)
  ↓  Extract new JSON match files only
  ↓  Parse each match: batting / bowling / fielding rows (match_parser.py)
  ↓  Merge with people.csv for stable player IDs
  ↓  Apply FantasyPointsCalculator scoring rules
  ↓  Run EloEngine.apply() across all leagues chronologically
  ↓  Write → data/all_leagues_player_match_elo.csv
```

Supported leagues: **PSL, IPL, BBL, BPL, CPL, SA20, ILT20, LPL** (configurable via `--leagues`).

### 2. Fantasy Points Scoring (`backend/core/scoring.py`)

| Action | Points |
|---|---|
| Run scored | +1 |
| Four | +4 |
| Six | +6 |
| Milestone bonus (25/50/75/100) | +4 / +8 / +12 / +16 |
| Wicket | +30 |
| LBW / Bowled bonus | +8 |
| Wicket haul (3W/4W/5W) | +4 / +8 / +12 |
| Maiden over | +12 |
| Dot ball | +1 |
| Catch | +8 (3+ catches = +4 bonus) |
| Stumping | +12 |
| Direct run-out | +12 |
| Indirect run-out | +6 |
| Economy rate bonus/penalty | ±2 to ±6 |
| Strike rate bonus/penalty | ±2 to ±6 |

### 3. T20 Elo Engine (`backend/core/elo_engine.py`)

The Elo engine is purpose-built for T20 cricket — it converges fast and handles the noisy, high-variance nature of the format.

**Key design choices:**

| Feature | Detail |
|---|---|
| Base K-factor | **64** (vs. chess's 32) — T20 form changes fast |
| Adaptive K | K starts at `2× base` for new players, decays toward `0.75× base` after 30+ games |
| Re-entry boost | +50% K if a player returns after >6 months away |
| Associate damping | K × 0.15 when both teams are associate nations |
| Inactivity decay | −2.5 Elo/month after 4-month grace, floored at 1100 |
| Actual score | Sigmoid of `(player_pts − match_avg_pts) / 40` → bounds result to [0, 1] |
| Expected score | Standard Elo formula: `1 / (1 + 10^((opponent_avg_elo − player_elo) / 400))` |
| Elo → multiplier | z-score: `(elo − mean) / (2 × std)`, clamped to **[0.75, 1.40]** |
| Pool calibration | z-score is re-computed relative to the two franchises in the current match |

### 4. HMM Form Prediction (`backend/core/hmm/`)

Two-tier HMM system:

| Tier | Class | Used when |
|---|---|---|
| **General** | `GeneralHMM` | Player has < 15 matches, uses role-level model (`hmm_form_models.joblib`) |
| **Per-player** | `ShortTermHMM` | Player has ≥ 15 matches, fits / loads a personal model from `models/per_player/` |

The unified `HMMPredictor` (used by the Flask backend) outputs:

```
{
  "state":         "hot" | "avg" | "cold" | "unknown",
  "probs":         [p_hot, p_avg, p_cold],
  "source":        "short_term" | "general",
  "career_avg":    float,
  "career_std":    float,
  "rolling_avg":   float,   # last 4–5 matches
  "rolling_window": int,
  "elo_post":      float,
  "elo_multiplier": float,  # [0.75, 1.40]
  "adjusted_score": float   # rolling_avg × elo_multiplier
}
```

Per-player models persist to `models/per_player/` — no re-training on restart unless `--retrain-models` is passed.

### 5. Credit Engine (`backend/services/credit_engine.py`)

Credits are auto-derived from performance data on a **6.5 – 10.5** scale (0.5 steps):

1. Compute each player's percentile rank within the match-pool (rolling avg or career avg)
2. Map percentile to a credit bucket via fixed thresholds
3. Adjust ±0.5 based on Elo multiplier (>1.1 → bump up; <0.9 → bump down)
4. Manual `credits_override.json` always takes precedence

### 6. Genetic Algorithm (`backend/services/team_generator.py`)

The GA runs **three independent optimisations** in sequence — one per strategy:

| Strategy | Fitness function | Captain logic |
|---|---|---|
| **Safe** | `Σ adjusted_score − 1.0 × mean(career_std)` | Highest score/std ratio |
| **Explosive** | `Σ (adjusted_score + 0.8 × career_std)` | Highest score + std |
| **Balanced** | `Σ adjusted_score` | Highest adjusted score |

**GA parameters (defaults):**

| Parameter | Value |
|---|---|
| Population size | 200 |
| Generations | 150 |
| Crossover rate | 0.80 |
| Mutation rate | 0.05 |
| Tournament size | 5 |
| Elitism count | 10 |

**Hard constraints checked on every chromosome:**

- Exactly 11 unique players
- Total credits ≤ 100
- Max 7 players from one franchise
- Min 1 wicketkeeper, 3 batters, 3 bowlers, 1 all-rounder

The GA runs in a **background thread** and streams progress to the frontend via **Server-Sent Events (SSE)** at `/api/stream/<run_id>`.

---

## API Reference

### Core Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/health` | Server liveness check — `{"status": "ok", "version": "1.0.0"}` |
| `GET` | `/api/match/teams` | List all available PSL franchise names |
| `GET` | `/api/players?team_a=X&team_b=Y` | Full player pool for a match (with Elo, form, credits) |
| `GET` | `/api/players/<id>/history` | Last 20 match records for a player |

### Team Generation

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/generate-teams` | Synchronous — runs GA, returns all 3 teams when done |
| `POST` | `/api/generate-teams-start` | Async — starts GA in background, returns `{"run_id": "..."}` immediately |
| `GET` | `/api/stream/<run_id>` | SSE stream — yields `progress` events then a final `complete` event |
| `GET` | `/api/evolution/<run_id>` | GA evolution snapshots (if `track_evolution=true` was passed) |

#### `POST /api/generate-teams` request body

```json
{
  "team_a": "Lahore Qalandars",
  "team_b": "Karachi Kings",
  "track_evolution": false,
  "constraints": {
    "budget": 100,
    "max_per_franchise": 7,
    "locked_players": ["player-id-1"],
    "excluded_players": []
  }
}
```

#### Response shape

```json
{
  "run_id": "abc123",
  "match": { "team_a": "...", "team_b": "..." },
  "safe":      { "strategy": "safe",      "players": [...], "captain": {...}, "vc": {...}, "total_credits": 98.5, "fitness": 312.4, "team_rolling_avg": 42.1, "team_career_std": 18.3 },
  "explosive": { "strategy": "explosive", "players": [...], ... },
  "balanced":  { "strategy": "balanced",  "players": [...], ... }
}
```

### Roster Management

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/roster/bench/<id>` | Mark a player as inactive (persists to `active_overrides.json`) |
| `POST` | `/api/roster/reinstate/<id>` | Re-activate a benched player |

### Constraints

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/constraints` | Return saved GA constraints |
| `POST` | `/api/constraints` | Save GA constraints (persists to `data/constraints.json`) |

---

## Frontend

The React SPA has three pages:

| Page | Route | Description |
|---|---|---|
| **Home** | `/` | Franchise selector — pick Team A and Team B |
| **Match / War Room** | `/match` | Browse the player pool; bench/reinstate players; lock players into the lineup |
| **Results** | `/results` | View the Safe / Explosive / Balanced teams; see captain/VC picks and player stats |

**Tech stack:**

- React 18 + TypeScript + React Router v6
- Vite 5 dev server (proxies `/api` → Flask on port 5000)
- Vanilla CSS + CSS custom properties for franchise theming
- Recharts for evolution graphs
- Framer Motion for animations
- Lucide React for icons

Franchise **primary colours** are injected as CSS custom properties (`--team-a`, `--team-b`) at the app root, making the whole UI theme-aware per match.

---

## Running in Development

```bash
# Terminal 1 — Flask API (port 5000)
python run.py

# Terminal 2 — Vite dev server with hot-reload (port 5173)
cd frontend
npm run dev
```

Access the app at **http://localhost:5173**. Vite forwards all `/api/*` requests to Flask automatically — no CORS configuration needed in the browser.

**Single-terminal shortcut:**
```bash
python run.py --with-frontend
```

---

## Data Update Pipeline

To pull the latest match data from Cricsheet and rebuild the Elo CSV:

```bash
python run.py --update-data
```

This runs `CricsheetUpdater` which:
1. Downloads ZIP archives for each league (ETag-aware — skips unchanged archives)
2. Extracts only new JSON match files into `data/<league>_male_json/`
3. Parses and scores every new match via `FantasyPointsCalculator`
4. Re-runs `EloEngine.apply()` across all leagues in chronological order
5. Writes the updated CSV to `data/all_leagues_player_match_elo.csv`

You can target specific leagues with the CLI directly:

```bash
python -m backend.cli --update-data --leagues psl,ipl --cutoff-years 5
```

---

## Configuration Summary

### GA Constraints (`data/constraints.json`)

```json
{
  "budget": 100,
  "team_size": 11,
  "max_per_franchise": 7,
  "min_wk": 1,
  "min_batters": 3,
  "min_bowlers": 3,
  "min_allrounders": 1,
  "population_size": 200,
  "generations": 150,
  "crossover_rate": 0.8,
  "mutation_rate": 0.05,
  "tournament_size": 5,
  "elitism_count": 10,
  "locked_players": [],
  "excluded_players": []
}
```

### Elo Engine Parameters (`EloEngine` defaults)

```python
EloEngine(
    initial_elo=1500,
    base_k=64,
    adaptive_k=True,
    associate_damping=0.15,
    fantasy_scale=40,
    decay_monthly=2.5,
    decay_grace_months=4,
    decay_floor=1100,
)
```

### Credits Override (`data/credits_override.json`)

```json
{
  "player-id": 9.5
}
```

---

## Python Dependencies

```
flask>=3.1.0
flask-cors>=6.0.0
pandas>=2.0.0
numpy>=1.24.0
joblib>=1.3.0
hmmlearn>=0.3.3
scikit-learn>=1.3.0
scipy>=1.11.0
aiohttp>=3.9.0
tqdm>=4.65.0
```

---

## Architecture Diagram

```
Browser (http://localhost:5173)
  │
  ▼
Vite Dev Server  (:5173)
  ├── /src/**     → Served from frontend/src/ with hot-reload
  └── /api/**     → Proxied to Flask (:5000)
        │
        ▼
      Flask (backend/app.py)  (:5000)
        ├── /api/*          → API blueprints (players, teams, roster, constraints, match)
        │
        ├── data_cache.py        (singleton data loaded once at startup)
        │     ├── ELO CSV  →  pandas DataFrame
        │     ├── Roster JSON
        │     ├── Role cache
        │     └── HMMPredictor
        │
        ├── player_service.py    (builds PlayerProfile per roster player)
        │     ├── HMMPredictor.predict()  →  form state + adjusted_score
        │     └── CreditEngine.compute()  →  credits
        │
        └── team_generator.py   (GeneticTeamGenerator)
              ├── _fitness_safe()
              ├── _fitness_explosive()
              └── _fitness_balanced()
```
