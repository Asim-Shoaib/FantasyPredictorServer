# DraftGenius — Backend API Reference

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Running the Server](#running-the-server)
3. [Data Files Required](#data-files-required)
4. [API Endpoints](#api-endpoints)
5. [Key Data Models](#key-data-models)
6. [Genetic Algorithm](#genetic-algorithm)
7. [HMM Form Prediction](#hmm-form-prediction)
8. [Credit Engine](#credit-engine)
9. [Data Pipeline](#data-pipeline)

---

## Architecture Overview

DraftGenius is a Flask API backend that serves a React/Vite frontend. All API routes are prefixed with `/api/`. The frontend Vite dev server proxies `/api/*` to the Flask server at port 5000 so the browser never issues cross-origin requests.

```
Browser / React SPA
        │
        │  /api/* (proxied in dev by Vite; direct in prod)
        ▼
  Flask (port 5000)
        │
   ┌────┴────────────────────────────────────────────────┐
   │ data_cache (singleton, loaded once at startup)      │
   │   • ELO CSV (pandas DataFrame)                      │
   │   • roster JSON (player → team mapping)             │
   │   • role_cache JSON                                 │
   │   • player_profiles JSON (photo URLs)               │
   │   • credits_override / active_overrides JSON        │
   │   • HMMPredictor (models/hmm_form_models.joblib +   │
   │                    models/per_player/*.joblib)       │
   └────────────────────────────────────────────────────┘
        │
   ┌────┴──────────────────────────────────────────────┐
   │ player_service.build_all_player_profiles()        │
   │   • HMMPredictor.predict() → form_state, probs    │
   │   • Elo multiplier (clamped z-score)              │
   │   • CreditEngine.compute() → credits 6.5–10.5    │
   └────────────────────────────────────────────────────┘
        │
   ┌────┴──────────────────────────────────────────────┐
   │ GeneticTeamGenerator.generate()                   │
   │   • 3 strategies: safe / explosive / balanced     │
   │   • 200 chromosomes × 150 generations (default)  │
   │   • SSE progress stream (optional)                │
   └────────────────────────────────────────────────────┘
```

**Component summary**

| Component | Technology | Role |
|---|---|---|
| API server | Flask 3.x + flask-cors | HTTP / SSE |
| Data layer | pandas + numpy | ELO CSV ingestion |
| Form prediction | hmmlearn HMM | State classification (cold / avg / hot) |
| Elo rating | Custom EloEngine | Per-player strength multiplier |
| Optimiser | Custom Genetic Algorithm | Team selection (3 strategies) |
| Frontend | React 18 + Vite + TypeScript | UI (served separately) |

---

## Running the Server

### Development (two terminals)

```bash
# Terminal 1 — Flask backend
python run.py

# Terminal 2 — Vite dev server (proxies /api → :5000)
cd frontend && npm run dev
```

### Development (single terminal)

```bash
python run.py --with-frontend
```

### Command-line flags

| Flag | Default | Description |
|---|---|---|
| `--port PORT` | `5000` | Flask listen port |
| `--with-frontend` | off | Also launch `npm run dev` in `frontend/` |
| `--update-data` | off | Download latest Cricsheet data and rebuild ELO CSV before starting |
| `--retrain-models` | off | Delete cached per-player HMM joblib files so they re-fit on next predict |

### Environment variables

| Variable | Default | Description |
|---|---|---|
| `PORT` | `5000` | Alternative way to set the Flask port (overridden by `--port`) |

---

## Data Files Required

All paths are relative to the project root (`src/`).

| File | Required | Description |
|---|---|---|
| `data/all_leagues_player_match_elo.csv` | **Yes** | Master ELO CSV — primary data source for all player stats |
| `models/hmm_form_models.joblib` | **Yes** | Pre-trained general (role-level) HMM artifact |
| `data/psl_2026_roster_overrides.json` | Recommended | Manual player → team mapping; inferred from ELO CSV if absent |
| `data/people.csv` | For photos | Cricsheet identifier → ESPN cricinfo ID mapping |
| `models/per_player/*.joblib` | Auto-generated | Per-player HMM models fitted on first predict; cached on disk |
| `data/output/role_cache.json` | Auto-generated | player_id → role mapping produced by the pipeline |
| `data/output/player_profiles.json` | Optional | player_id → ESPN photo URL cache |
| `data/credits_override.json` | Optional | Manual credit values that override the CreditEngine |
| `data/active_overrides.json` | Optional | Benched/available status overrides per player |
| `data/constraints.json` | Optional | Persisted constraint settings saved via `POST /api/constraints` |

### ELO CSV required columns

| Column | Type | Description |
|---|---|---|
| `player_id` | str | Cricsheet identifier (e.g. `4acd8fc4`) |
| `player_name` | str | Display name |
| `team` | str | Franchise name |
| `match_id` | str | Cricsheet match ID |
| `match_date` | date | Match date |
| `league` | str | League key (`psl`, `ipl`, etc.) |
| `fantasy_points` | float | Total fantasy points for this match |
| `batting_points` | float | Batting component |
| `bowling_points` | float | Bowling component |
| `fielding_points` | float | Fielding component |
| `player_elo_post` | float | Elo rating after this match |
| `opposition` | str | Opposing team name |

---

## API Endpoints

### Health

#### `GET /api/health`

Returns server status.

**Response**

```json
{
  "status": "ok",
  "version": "1.0.0"
}
```

---

### Match / Franchises

#### `GET /api/match/teams`

Returns sorted list of all PSL franchise names derived from the roster JSON (or inferred from the ELO CSV if the roster is absent).

**Response** — `string[]`

```json
["Islamabad United", "Karachi Kings", "Lahore Qalandars", "Multan Sultans", "Peshawar Zalmi", "Quetta Gladiators"]
```

---

### Players

#### `GET /api/players`

Returns full `PlayerProfile` objects for all (or a filtered subset of) roster players.

**Query parameters**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `team_a` | string | No | First franchise name |
| `team_b` | string | No | Second franchise name |

When both `team_a` and `team_b` are supplied the pool is restricted to exactly those two franchises and the Elo calibration is computed against that match pool only.

**Response** — `PlayerProfile[]` (see [PlayerProfile](#playerprofile) below)

```json
[
  {
    "player_id": "4acd8fc4",
    "player_name": "Babar Azam",
    "team": "Karachi Kings",
    "role": "Batter",
    "credits": 10.5,
    "is_active": true,
    "form_state": "hot",
    "form_probs": [0.05, 0.20, 0.75],
    "form_source": "short_term",
    "career_avg": 38.4,
    "career_std": 22.1,
    "career_variance": 488.4,
    "rolling_avg": 44.2,
    "rolling_window": 10,
    "rolling_fallback": false,
    "adjusted_score": 47.6,
    "elo_post": 1724.3,
    "elo_multiplier": 1.077,
    "matches_in_history": 84,
    "photo_url": "https://p.imgci.com/db/PICTURES/CMS/..."
  }
]
```

---

#### `GET /api/players/<player_id>/history`

Returns the last 20 match records for a player.

**Path parameter** — `player_id`: Cricsheet identifier string.

**Response** — array of match records

```json
[
  {
    "match_date": "2026-03-01",
    "opposition": "Lahore Qalandars",
    "fantasy_points": 72.0,
    "batting_points": 56.0,
    "bowling_points": 8.0,
    "fielding_points": 8.0,
    "player_elo_post": 1731.2
  }
]
```

Fields present depend on which columns exist in the ELO CSV. Records are sorted most-recent first.

---

### Admin — Player Photos

#### `POST /api/admin/fetch-photos`

Fetches ESPN headshot URLs for all roster players and updates the in-memory `player_profiles` cache and `data/output/player_profiles.json`.

Requires `data/people.csv` to be present for the Cricsheet identifier → ESPN cricinfo ID mapping.

**Response**

```json
{
  "fetched": 45,
  "with_photo": 38,
  "unmapped": 7
}
```

---

#### `GET /api/admin/photo-status`

Returns photo coverage counts for the current roster.

**Response**

```json
{
  "total": 52,
  "with_photo": 38,
  "missing": 14
}
```

---

### Constraints

#### `GET /api/constraints`

Returns the current constraint settings (saved values merged over defaults).

**Response** — `TeamConstraints` as a flat JSON object (see [TeamConstraints](#teamconstraints) below)

```json
{
  "budget": 100.0,
  "team_size": 11,
  "min_per_franchise": 4,
  "max_per_franchise": 7,
  "min_wk": 1,
  "max_wk": 1,
  "min_batters": 3,
  "max_batters": 6,
  "min_bowlers": 3,
  "max_bowlers": 6,
  "min_allrounders": 1,
  "max_allrounders": 4,
  "population_size": 200,
  "generations": 150,
  "crossover_rate": 0.8,
  "mutation_rate": 0.05,
  "tournament_size": 5,
  "elitism_count": 10,
  "locked_players": [],
  "excluded_players": [],
  "team_a": "",
  "team_b": ""
}
```

---

#### `POST /api/constraints`

Saves constraint overrides. Only fields supplied in the request body are updated; all others retain their previous values.

**Request body** — partial `TeamConstraints` object

```json
{
  "budget": 95.0,
  "min_batters": 4,
  "locked_players": ["4acd8fc4"]
}
```

The endpoint also accepts the frontend-facing aliases listed in the table below.

| Alias (frontend) | Maps to |
|---|---|
| `batter_min` / `batter_max` | `min_batters` / `max_batters` |
| `bowler_min` / `bowler_max` | `min_bowlers` / `max_bowlers` |
| `allrounder_min` / `allrounder_max` | `min_allrounders` / `max_allrounders` |
| `wicketkeeper_min` / `wicketkeeper_max` | `min_wk` / `max_wk` |
| `per_team_min` / `per_team_max` | `min_per_franchise` / `max_per_franchise` |

**Response** — merged constraint object (same shape as `GET /api/constraints`)

---

### Roster Management

#### `POST /api/roster/bench/<player_id>`

Marks a player as benched. Benched players are excluded from the GA pool (`is_active = false`).

**Response**

```json
{ "player_id": "4acd8fc4", "benched": true }
```

---

#### `POST /api/roster/reinstate/<player_id>`

Reinstates a benched player.

**Response**

```json
{ "player_id": "4acd8fc4", "benched": false }
```

---

#### `GET /api/roster/status`

Returns all active_overrides entries.

**Response** — `{ [player_id]: { benched: boolean } }`

```json
{
  "4acd8fc4": { "benched": false },
  "9f2e1b3a": { "benched": true }
}
```

---

### Team Generation

Two generation modes are available: **synchronous** (blocking, returns result immediately) and **async + SSE** (starts a background thread and streams progress events).

---

#### `POST /api/generate-teams` — Synchronous

Runs the GA for all three strategies synchronously and returns when complete. Suitable for testing; may time out on slow servers for large populations.

**Request body**

```json
{
  "team_a": "Karachi Kings",
  "team_b": "Lahore Qalandars",
  "constraints": {
    "budget": 100.0,
    "locked_players": ["4acd8fc4"]
  },
  "track_evolution": false
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `team_a` | string | Yes | First franchise |
| `team_b` | string | Yes | Second franchise |
| `constraints` | object | No | Partial constraint overrides (merged with saved constraints) |
| `track_evolution` | boolean | No | Store per-generation snapshots accessible via `GET /api/evolution/<run_id>` |

**Response** — `GenerateResponse`

```json
{
  "run_id": "a3f7c901",
  "match": { "team_a": "Karachi Kings", "team_b": "Lahore Qalandars" },
  "safe": { ... },
  "explosive": { ... },
  "balanced": { ... },
  "evolution_available": false
}
```

Each of `safe`, `explosive`, `balanced` is a `TeamResult` object (see [TeamResult](#teamresult)).

**Error responses**

| Status | Condition |
|---|---|
| `400` | `team_a` or `team_b` missing |
| `400` | Fewer than 11 active players available |
| `400` | Budget / locked player constraint violation |

---

#### `POST /api/generate-teams-start` — Async

Starts a GA run in a background thread and returns a `run_id` immediately.

**Request body** — same shape as `POST /api/generate-teams` (except `track_evolution` is not supported)

**Response**

```json
{ "run_id": "b8e2d4f9aa1c" }
```

`run_id` is a 12-character hex string.

**Error responses**

| Status | Condition |
|---|---|
| `400` | `team_a` or `team_b` missing |

---

#### `GET /api/stream/<run_id>` — SSE Stream

Server-Sent Events stream for a running GA job. Connect immediately after `POST /api/generate-teams-start`.

**Response** — `text/event-stream`

Each SSE frame is a JSON object on the `data:` line.

**Event types**

**`progress`** — emitted every 10 generations per strategy

```json
{
  "type": "progress",
  "strategy": "safe",
  "generation": 50,
  "fitness": 312.45
}
```

**`complete`** — emitted once when all three strategies finish

```json
{
  "type": "complete",
  "run_id": "b8e2d4f9aa1c",
  "match": { "team_a": "Karachi Kings", "team_b": "Lahore Qalandars" },
  "safe": { ... },
  "explosive": { ... },
  "balanced": { ... }
}
```

**`error`** — emitted if the GA fails or the 2-minute timeout is exceeded

```json
{
  "type": "error",
  "error": "Not enough active players: 9"
}
```

Stream terminates after `complete` or `error`. A 2-minute server-side timeout fires if the queue produces no events.

---

#### `GET /api/evolution/<run_id>`

Returns per-generation evolution snapshots captured during a synchronous run when `track_evolution: true` was set.

**Response**

```json
{
  "safe": [
    {
      "generation": 0,
      "fitness": 280.1,
      "team": ["Babar Azam", "Shaheen Shah Afridi", "..."],
      "captain": "Babar Azam"
    },
    { "generation": 10, "fitness": 298.7, ... }
  ],
  "explosive": [ ... ],
  "balanced": [ ... ]
}
```

Snapshots are recorded every 10 generations.

**Error response**

| Status | Condition |
|---|---|
| `404` | `run_id` not found or `track_evolution` was not set |

---

## Key Data Models

### PlayerProfile

| Field | Type | Description |
|---|---|---|
| `player_id` | `str` | Cricsheet identifier |
| `player_name` | `str` | Display name |
| `team` | `str` | PSL franchise |
| `role` | `str` | Playing role from role_cache (e.g. `"Batter"`, `"Bowler"`, `"All-Rounder"`) |
| `credits` | `float` | Fantasy credit value (6.5–10.5, step 0.5) |
| `is_active` | `bool` | False if manually benched |
| `form_state` | `str` | HMM predicted state: `"cold"`, `"avg"`, `"hot"`, or `"unknown"` |
| `form_probs` | `float[3]` | Transition probabilities `[P_cold, P_avg, P_hot]` for next appearance |
| `form_source` | `str` | `"general"` (role-level HMM) or `"short_term"` (per-player HMM) |
| `career_avg` | `float\|null` | Mean fantasy points over all career matches |
| `career_std` | `float\|null` | Standard deviation over career |
| `career_variance` | `float\|null` | Variance over career |
| `rolling_avg` | `float\|null` | Mean over last 3–10 matches |
| `rolling_window` | `int` | Actual window size used (3–10) |
| `rolling_fallback` | `bool` | True if rolling_avg unavailable (< 3 matches); career_avg used instead |
| `adjusted_score` | `float\|null` | `rolling_avg × elo_multiplier` (primary fitness signal) |
| `elo_post` | `float\|null` | Most recent Elo rating |
| `elo_multiplier` | `float` | Elo strength multiplier clamped to [0.75, 1.40] |
| `matches_in_history` | `int` | Total career matches in ELO CSV |
| `photo_url` | `str\|null` | ESPN CDN headshot URL |

---

### TeamConstraints

| Field | Type | Default | Description |
|---|---|---|---|
| `budget` | `float` | `100.0` | Maximum total credits for the XI |
| `team_size` | `int` | `11` | Number of players in the team |
| `min_per_franchise` | `int` | `4` | Minimum players from each franchise |
| `max_per_franchise` | `int` | `7` | Maximum players from each franchise |
| `min_wk` | `int` | `1` | Minimum wicket-keepers |
| `max_wk` | `int` | `11` | Maximum wicket-keepers |
| `min_batters` | `int` | `3` | Minimum batters |
| `max_batters` | `int` | `11` | Maximum batters |
| `min_bowlers` | `int` | `3` | Minimum bowlers |
| `max_bowlers` | `int` | `11` | Maximum bowlers |
| `min_allrounders` | `int` | `1` | Minimum all-rounders |
| `max_allrounders` | `int` | `11` | Maximum all-rounders |
| `population_size` | `int` | `200` | GA chromosome population per strategy |
| `generations` | `int` | `150` | GA generations per strategy |
| `crossover_rate` | `float` | `0.8` | Probability of crossover vs. cloning parent |
| `mutation_rate` | `float` | `0.05` | Probability of mutating a chromosome |
| `tournament_size` | `int` | `5` | Tournament selection sample size |
| `elitism_count` | `int` | `10` | Number of top chromosomes carried forward unchanged |
| `locked_players` | `str[]` | `[]` | player_ids that must appear in every generated team |
| `excluded_players` | `str[]` | `[]` | player_ids that must not appear in any generated team |
| `team_a` | `str` | `""` | First franchise (set automatically by generate endpoints) |
| `team_b` | `str` | `""` | Second franchise |

---

### TeamResult

| Field | Type | Description |
|---|---|---|
| `strategy` | `str` | `"safe"`, `"explosive"`, or `"balanced"` |
| `players` | `object[]` | Array of 11 player dicts (PlayerProfile fields + `is_captain`, `is_vc`) |
| `captain` | `object` | The player dict for the captain |
| `vc` | `object` | The player dict for the vice-captain |
| `total_credits` | `float` | Sum of credits for the XI |
| `fitness` | `float` | Raw GA fitness score (0.0 in current build; deprecated) |
| `expected_score` | `float` | `Σ adjusted_score` for all 11 players |
| `ceiling_score` | `float` | `Σ adjusted_score × (1 + P_hot)` — optimistic projection |
| `floor_score` | `float` | `Σ adjusted_score × (1 - P_cold)` — conservative projection |
| `team_rolling_avg` | `float` | Mean rolling_avg across the XI |
| `team_career_std` | `float` | 0.0 (deprecated field) |
| `team_hot_prob` | `float` | 0.0 (deprecated field) |

Each player dict in `players` extends `PlayerProfile` with:

| Extra field | Type | Description |
|---|---|---|
| `is_captain` | `bool` | True for the captain |
| `is_vc` | `bool` | True for the vice-captain |

---

## Genetic Algorithm

`GeneticTeamGenerator` in `backend/services/team_generator.py` runs three independent GA passes — one per strategy — on the same player pool.

### Chromosome encoding

Each chromosome is a list of `team_size + 2` integers: `[p0, p1, ..., p10, cap_pos, vc_pos]` where each `pN` is an index into the active player list, `cap_pos` is the index (0–10) of the captain, and `vc_pos` is the index of the vice-captain.

### Initialisation

`_init_population` generates `population_size` chromosomes. Each chromosome is built greedily:

1. Locked players are inserted first.
2. Remaining candidates are shuffled and added one by one, skipping any that would breach role maximums, the budget cap, or franchise limits.
3. A final `_passes_hard_constraints` check validates all minimums.
4. If 500 attempts fail (e.g. impossible budget) a random fallback chromosome is used.

### Fitness functions

All three functions iterate over the 11 player indices and accumulate a score using the player's `adjusted_score` (rolling average × Elo multiplier) weighted by HMM transition probabilities:

| Strategy | Formula per player | Effect |
|---|---|---|
| **Safe** | `adjusted_score × (1 − P_cold)` | Minimises downside; penalises cold-form players |
| **Explosive** | `adjusted_score × (1 + P_hot)` | Maximises upside; rewards hot-form players |
| **Balanced** | `adjusted_score × (1 + 0.5 × P_hot − 0.5 × P_cold)` | Blend of both |

`P_cold`, `P_hot` are the first and third elements of `form_probs` (transition probabilities to the next state).

### Constraint enforcement

Chromosomes that violate hard constraints return `-inf` fitness and are never selected. Soft constraint violations during mutation/crossover are discarded after 20 attempts; the parent is returned unchanged.

Hard constraints checked on every evaluation:

- Unique player indices (no duplicates)
- Total credits ≤ budget
- Per-franchise counts within [min_per_franchise, max_per_franchise]
- Role counts within their respective [min, max] bounds

### Selection, crossover, mutation

| Operation | Method |
|---|---|
| Selection | Tournament selection — sample `tournament_size` chromosomes, take the best |
| Crossover | Single-point splice; child inherits prefix from parent 1 + non-overlapping suffix from parent 2; up to 20 retry attempts for validity |
| Mutation | Swap one random non-locked player for a random player not in the team; up to 20 retry attempts for validity |
| Elitism | Top `elitism_count` chromosomes copied unchanged to next generation |

### Captain / VC selection

After the GA converges, `_choose_captain_vc` re-ranks all 11 players using the same per-strategy value function and assigns the top two as captain and vice-captain respectively.

---

## HMM Form Prediction

`HMMPredictor` in `backend/core/hmm/predictor.py` is the unified entry point. It selects between two underlying models based on career match count.

### Model selection

| Condition | Model used | Source label |
|---|---|---|
| History length ≥ 15 matches | `ShortTermHMM` (per-player) | `"short_term"` |
| 3–14 matches | `GeneralHMM` (role-level) | `"general"` |
| 0–2 matches | No prediction | `"general"` with `state = "unknown"` |

### GeneralHMM (role-level)

Loaded from `models/hmm_form_models.joblib`. A single pre-trained `CategoricalHMM` exists per playing role (e.g. `"Batter"`, `"Bowler"`, `"All-Rounder"`). Unknown or missing roles fall back to `"All-Rounder"`.

Prediction steps:

1. Discretise `history_points` into observation bins using role-specific `obs_bin_edges`.
2. Run Viterbi decoding to get the current state index.
3. Read the transition row for that state → `form_probs = [P_cold, P_avg, P_hot]`.

### ShortTermHMM (per-player)

A `CategoricalHMM` with 3 components (`cold` / `avg` / `hot`) is fitted on the player's full career history and persisted to `models/per_player/<player_id>.joblib`.

- Fitted once then loaded from disk on subsequent calls.
- If the player accumulates 10 or more new matches since training (`_RETRAIN_THRESHOLD = 10`), the model file is deleted and re-fitted automatically.
- 5 random restarts (`_N_RESTARTS = 5`) are used during fitting; the run with the highest log-likelihood wins.
- States are sorted by their probability of emitting the highest observation bin so that state 0 is always `"cold"` and state 2 is always `"hot"`.
- A separate **windowed** decode over the last 15 matches (`_RECENT_WINDOW`) produces `windowed_probs`. The predictor prefers `windowed_probs` over full-career `probs` when both are available.

### Elo multiplier

```
z = (elo_post − pool_mean) / (2 × pool_std)
elo_multiplier = clip(1 + z, 0.75, 1.40)
```

`pool_mean` and `pool_std` are recalibrated per-match via `calibrate_to_pool()`, which restricts the Elo distribution to the two franchises in the selected match. This prevents cross-league Elo inflation and gives elite PSL players full multiplier headroom relative to their match opponents.

### adjusted_score

```
adjusted_score = (rolling_avg or career_avg) × elo_multiplier
```

Rolling average uses up to the last 10 matches (minimum 3). If fewer than 3 career matches exist, `career_avg` is used and `rolling_fallback = true` is set.

---

## Credit Engine

`CreditEngine` in `backend/services/credit_engine.py` derives a fantasy credit value in the range 6.5–10.5 (step 0.5) for each player.

### Algorithm

1. Use `rolling_avg` as the base signal; fall back to `career_avg` if unavailable.
2. Compute the player's percentile rank within the match pool (`all_avgs`).
3. Map percentile to a credit step via 8 thresholds: `[10, 20, 30, 45, 60, 72, 83, 92]` → 9 buckets → `[6.5, 7.0, 7.5, 8.0, 8.5, 9.0, 9.5, 10.0, 10.5]`.
4. Apply Elo adjustment: +0.5 credits if `elo_multiplier > 1.1`; −0.5 credits if `elo_multiplier < 0.9`.
5. If `credits_override.json` contains the player_id, skip all computation and return the override value.

Default credit when no history is available: **8.0**.

---

## Data Pipeline

The pipeline is invoked via the CLI module and is separate from the Flask server. It converts Cricsheet-style match JSON files into the ELO CSV that the server reads.

### Quick rebuild

```bash
python -m backend.cli
```

### Download + rebuild

```bash
python -m backend.cli --update-data
```

Or via the run.py launcher:

```bash
python run.py --update-data
```

### CLI flags

| Flag | Default | Description |
|---|---|---|
| `--root-dir DIR` | `.` | Workspace root |
| `--people-csv PATH` | `data/people.csv` | Cricsheet people.csv for name↔ID mapping |
| `--output-csv PATH` | `data/output/all_leagues_player_match.csv` | Intermediate scored CSV (pre-Elo) |
| `--update-data` | off | Download new match data from Cricsheet |
| `--cutoff-years N` | `5` | Ignore matches older than N years (0 = no cutoff) |
| `--leagues KEYS` | all | Comma-separated league keys: `psl,ipl,bbl,bpl,cpl,sa20,ilt20,lpl` |
| `--force-pipeline` | off | Re-run full pipeline even if no new data was downloaded |
| `--fetch-photos` | off | Fetch ESPN headshots after pipeline completes |

### Pipeline stages

1. **Download** (`CricsheetUpdater`) — fetches ZIP archives from Cricsheet, unpacks new match JSONs.
2. **Parse** (`MatchParser` + `SmartMatchCache`) — converts each match JSON to player-level fantasy point records. Already-parsed matches are read from `.cache/final_results_cache.parquet` (never re-parsed).
3. **Score** (`Pipeline.run()`) — applies fantasy scoring rules (bat/bowl/field) to the parsed records.
4. **Form features** (`FormFeatureBuilder`) — adds rolling average and streak columns.
5. **Elo** (`EloEngine`) — computes chronological per-player Elo ratings across all leagues and writes the final `data/all_leagues_player_match_elo.csv`.
6. **Photos** (`ProfileFetcher`, optional) — fetches ESPN CDN headshot URLs and writes `data/output/player_profiles.json`.

### SmartMatchCache

`backend/utils/smart_cache.py` maintains a Parquet file at `.cache/final_results_cache.parquet`. On each pipeline run it:

- Loads the set of already-cached `match_id`s from the Parquet index.
- Parses only new match files (O(new) not O(all)).
- Appends new records and drops duplicates on `(match_id, player_id)` before writing.
- Is a no-op when nothing new was parsed.
