"""Genetic Algorithm team generator — single-match, 2-franchise mode.

Simplified fitness functions:
  - Safe:      Σ adjusted_score_i  − λ × mean(career_std of XI)
  - Explosive: Σ (adjusted_score_i + α × career_std_i)
  - Balanced:  Σ adjusted_score_i   (pure score maximizer)

Team of the Tournament and Monte Carlo are out of scope for this phase.
"""

from __future__ import annotations

import logging
import random
import uuid
from dataclasses import dataclass, field
from typing import Callable

import numpy as np

from backend.services.player_service import PlayerProfile

logger = logging.getLogger(__name__)

# ────────────────────────────────────────────────────────────────────────
# Constraints dataclass
# ────────────────────────────────────────────────────────────────────────

@dataclass
class TeamConstraints:
    budget: float = 100.0
    team_size: int = 11
    max_per_franchise: int = 7          # single-match rule
    min_wk: int = 1
    min_batters: int = 3
    min_bowlers: int = 3
    min_allrounders: int = 1
    population_size: int = 200
    generations: int = 150
    crossover_rate: float = 0.8
    mutation_rate: float = 0.05
    tournament_size: int = 5
    elitism_count: int = 10
    locked_players: list[str] = field(default_factory=list)
    excluded_players: list[str] = field(default_factory=list)
    team_a: str = ""
    team_b: str = ""

    @classmethod
    def from_dict(cls, d: dict) -> "TeamConstraints":
        valid = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        filtered = {k: v for k, v in d.items() if k in valid}
        return cls(**filtered)


# ────────────────────────────────────────────────────────────────────────
# Result types
# ────────────────────────────────────────────────────────────────────────

@dataclass
class TeamResult:
    strategy: str          # "safe" | "explosive" | "balanced"
    players: list[dict]
    captain: dict
    vc: dict
    total_credits: float
    fitness: float
    team_rolling_avg: float
    team_career_std: float


@dataclass
class GenerateResult:
    run_id: str
    safe: TeamResult
    explosive: TeamResult
    balanced: TeamResult
    evolution: dict[str, list[dict]] = field(default_factory=dict)


# ────────────────────────────────────────────────────────────────────────
# Role helpers
# ────────────────────────────────────────────────────────────────────────

_WK_ROLES = {"wicketkeeper", "wk", "wk-batter"}
_BATTER_ROLES = {"batter", "top order batter", "middle order batter", "opening batter"}
_BOWLER_ROLES = {"bowler", "fast bowler", "spin bowler", "pace bowler"}
_AR_ROLES = {"all-rounder", "allrounder", "all rounder", "bowling allrounder", "batting allrounder"}


def _norm_role(role: str) -> str:
    return str(role or "").strip().lower()


def _is_wk(role: str) -> bool:
    return _norm_role(role) in _WK_ROLES


def _is_batter(role: str) -> bool:
    r = _norm_role(role)
    return any(r.startswith(b) for b in _BATTER_ROLES) or r in _BATTER_ROLES


def _is_bowler(role: str) -> bool:
    r = _norm_role(role)
    return any(r.startswith(b) for b in _BOWLER_ROLES) or r in _BOWLER_ROLES


def _is_ar(role: str) -> bool:
    r = _norm_role(role)
    return any(b in r for b in _AR_ROLES)


# ────────────────────────────────────────────────────────────────────────
# Chromosome and GA engine
# ────────────────────────────────────────────────────────────────────────

class GeneticTeamGenerator:

    def __init__(self) -> None:
        pass

    def generate(
        self,
        players: list[PlayerProfile],
        constraints: TeamConstraints,
        track_evolution: bool = False,
        progress_callback=None,   # Optional[Callable[[str, int, float], None]]
    ) -> GenerateResult:

        run_id = uuid.uuid4().hex[:8]
        active = [p for p in players if p.is_active and p.player_id not in constraints.excluded_players]

        if len(active) < constraints.team_size:
            raise ValueError(
                f"Not enough active players: {len(active)} < {constraints.team_size}"
            )

        # Validate locked players are available
        locked = [p for p in active if p.player_id in constraints.locked_players]
        if len(locked) < len(constraints.locked_players):
            raise ValueError("Some locked players are inactive or excluded")

        locked_credits = sum(p.credits for p in locked)
        if locked_credits > constraints.budget:
            raise ValueError("Locked players exceed budget")

        results: dict[str, TeamResult] = {}
        evolution: dict[str, list[dict]] = {}

        for strategy, fitness_fn in [
            ("safe", self._fitness_safe),
            ("explosive", self._fitness_explosive),
            ("balanced", self._fitness_balanced),
        ]:
            best_chrom, evo_log = self._run_ga(
                players=active,
                constraints=constraints,
                fitness_fn=fitness_fn,
                track_evolution=track_evolution,
                progress_callback=progress_callback,
                strategy=strategy,
            )
            team_result = self._chromosome_to_result(best_chrom, active, strategy)
            results[strategy] = team_result
            if track_evolution:
                evolution[strategy] = evo_log

        return GenerateResult(
            run_id=run_id,
            safe=results["safe"],
            explosive=results["explosive"],
            balanced=results["balanced"],
            evolution=evolution,
        )

    # ─── Fitness functions ────────────────────────────────────────────────

    @staticmethod
    def _fitness_safe(players: list[PlayerProfile], indices: list[int]) -> float:
        """Σ adjusted_score − λ × mean(career_std)"""
        λ = 1.0
        eps = 1e-9
        total_score = 0.0
        stds: list[float] = []
        for i in indices:
            p = players[i]
            total_score += (p.adjusted_score or 0.0)
            stds.append(p.career_std or 0.0)
        penalty = λ * (np.mean(stds) if stds else 0.0)
        return total_score - penalty

    @staticmethod
    def _fitness_explosive(players: list[PlayerProfile], indices: list[int]) -> float:
        """Σ (adjusted_score + α × career_std)"""
        α = 0.8
        total = 0.0
        for i in indices:
            p = players[i]
            total += (p.adjusted_score or 0.0) + α * (p.career_std or 0.0)
        return total

    @staticmethod
    def _fitness_balanced(players: list[PlayerProfile], indices: list[int]) -> float:
        """Σ adjusted_score — pure score maximizer."""
        return sum((players[i].adjusted_score or 0.0) for i in indices)

    # ─── GA internals ─────────────────────────────────────────────────────

    def _run_ga(
        self,
        players: list[PlayerProfile],
        constraints: TeamConstraints,
        fitness_fn: Callable,
        track_evolution: bool,
        progress_callback=None,
        strategy: str = "",
    ) -> tuple[list[int], list[dict]]:
        pop = self._init_population(players, constraints)
        evo_log: list[dict] = []
        best_chrom: list[int] = pop[0]
        best_fit = -np.inf

        for gen in range(constraints.generations):
            scored = [(self._evaluate(p, players, constraints, fitness_fn), p) for p in pop]
            scored.sort(key=lambda x: x[0], reverse=True)

            if scored[0][0] > best_fit:
                best_fit = scored[0][0]
                best_chrom = scored[0][1][:]

            if track_evolution and gen % 10 == 0:
                evo_log.append({
                    "generation": gen,
                    "fitness": round(best_fit, 2),
                    "team": self._indices_to_names(best_chrom[:constraints.team_size], players),
                    "captain": players[best_chrom[constraints.team_size]].player_name if len(best_chrom) > constraints.team_size else "",
                })

            if progress_callback is not None and gen % 10 == 0:
                try:
                    progress_callback(strategy, gen, round(best_fit, 2))
                except Exception:
                    pass  # never crash the GA because of a broken callback

            # Elitism
            elite = [c for _, c in scored[:constraints.elitism_count]]
            pop_scored = [c for _, c in scored]

            new_pop = elite[:]
            while len(new_pop) < constraints.population_size:
                p1 = self._tournament_select(pop_scored, scored, constraints.tournament_size)
                p2 = self._tournament_select(pop_scored, scored, constraints.tournament_size)
                child = self._crossover(p1, p2, constraints)
                child = self._mutate(child, players, constraints)
                new_pop.append(child)
            pop = new_pop

        return best_chrom, evo_log

    def _init_population(self, players: list[PlayerProfile], c: TeamConstraints) -> list[list[int]]:
        pool = list(range(len(players)))
        locked_indices = [i for i, p in enumerate(players) if p.player_id in c.locked_players]
        pop: list[list[int]] = []

        for _ in range(c.population_size):
            chrom = self._random_chromosome(pool, locked_indices, players, c)
            pop.append(chrom)
        return pop

    def _random_chromosome(
        self, pool: list[int], locked: list[int], players: list[PlayerProfile], c: TeamConstraints
    ) -> list[int]:
        for _ in range(200):  # retry limit
            available = [i for i in pool if i not in locked]
            needed = c.team_size - len(locked)
            if needed < 0:
                chosen = locked[:c.team_size]
            else:
                chosen = locked + random.sample(available, min(needed, len(available)))
            if len(chosen) < c.team_size:
                chosen = chosen + random.choices(available, k=c.team_size - len(chosen))
            chosen = chosen[:c.team_size]

            if self._passes_hard_constraints(chosen, players, c):
                cap = random.randint(0, c.team_size - 1)
                vc_choices = [i for i in range(c.team_size) if i != cap]
                vc = random.choice(vc_choices)
                return chosen + [cap, vc]

        # Fallback: return whatever we have even if constraints not met
        cap = random.randint(0, c.team_size - 1)
        vc = random.randint(0, c.team_size - 1)
        if vc == cap:
            vc = (vc + 1) % c.team_size
        return chosen + [cap, vc]

    def _passes_hard_constraints(
        self, indices: list[int], players: list[PlayerProfile], c: TeamConstraints
    ) -> bool:
        if len(set(indices)) < c.team_size:
            return False

        total_credits = sum(players[i].credits for i in indices)
        if total_credits > c.budget:
            return False

        from collections import Counter
        team_counts = Counter(players[i].team for i in indices)
        if any(cnt > c.max_per_franchise for cnt in team_counts.values()):
            return False

        roles = [players[i].role for i in indices]
        wk_count = sum(1 for r in roles if _is_wk(r))
        bat_count = sum(1 for r in roles if _is_batter(r))
        bowl_count = sum(1 for r in roles if _is_bowler(r))
        ar_count = sum(1 for r in roles if _is_ar(r))

        if wk_count < c.min_wk:
            return False
        if bat_count < c.min_batters:
            return False
        if bowl_count < c.min_bowlers:
            return False
        if ar_count < c.min_allrounders:
            return False

        return True

    def _evaluate(
        self,
        chromosome: list[int],
        players: list[PlayerProfile],
        c: TeamConstraints,
        fitness_fn: Callable,
    ) -> float:
        indices = chromosome[:c.team_size]
        if not self._passes_hard_constraints(indices, players, c):
            return -np.inf
        cap_pos = chromosome[c.team_size]
        vc_pos = chromosome[c.team_size + 1]
        if cap_pos == vc_pos or cap_pos >= c.team_size or vc_pos >= c.team_size:
            return -np.inf
        return fitness_fn(players, indices)

    def _tournament_select(
        self, pop: list[list[int]], scored: list[tuple], k: int
    ) -> list[int]:
        contenders = random.sample(list(enumerate(scored)), min(k, len(scored)))
        best_idx = max(contenders, key=lambda x: scored[x[0]][0])[0]
        return pop[best_idx][:]

    def _crossover(self, p1: list[int], p2: list[int], c: TeamConstraints) -> list[int]:
        if random.random() > c.crossover_rate:
            return p1[:]
        point = random.randint(1, c.team_size - 1)
        child_indices = p1[:point] + [i for i in p2 if i not in p1[:point]]
        child_indices = child_indices[:c.team_size]
        # Pad if short
        available = [i for i in range(len(p1)) if i not in child_indices]
        while len(child_indices) < c.team_size:
            child_indices.append(random.choice(available) if available else 0)
        cap = random.randint(0, c.team_size - 1)
        vc = random.randint(0, c.team_size - 1)
        if vc == cap:
            vc = (vc + 1) % c.team_size
        return child_indices + [cap, vc]

    def _mutate(
        self, chrom: list[int], players: list[PlayerProfile], c: TeamConstraints
    ) -> list[int]:
        if random.random() > c.mutation_rate:
            return chrom
        chrom = chrom[:]
        pool = list(range(len(players)))
        swap_pos = random.randint(0, c.team_size - 1)
        locked_ids = set(c.locked_players)
        if players[chrom[swap_pos]].player_id in locked_ids:
            return chrom
        candidates = [i for i in pool if i not in chrom[:c.team_size]]
        if candidates:
            chrom[swap_pos] = random.choice(candidates)
        return chrom

    # ─── Result building ─────────────────────────────────────────────────

    def _choose_captain_vc(
        self, indices: list[int], players: list[PlayerProfile], strategy: str
    ) -> tuple[int, int]:
        """Pick captain and VC based on strategy-specific scoring."""
        def key_fn(i: int) -> float:
            p = players[i]
            score = p.adjusted_score or 0.0
            std = p.career_std or 0.0
            if strategy == "safe":
                return score / (std + 1e-9)
            elif strategy == "explosive":
                return score + std
            else:
                return score

        ranked = sorted(indices, key=key_fn, reverse=True)
        return ranked[0], ranked[1]

    def _chromosome_to_result(
        self, chrom: list[int], players: list[PlayerProfile], strategy: str
    ) -> TeamResult:
        n = 11  # team_size
        indices = chrom[:n]
        cap_idx, vc_idx = self._choose_captain_vc(indices, players, strategy)

        team_players = []
        for i in indices:
            p = players[i]
            d = {
                "player_id": p.player_id,
                "player_name": p.player_name,
                "team": p.team,
                "role": p.role,
                "credits": p.credits,
                "form_state": p.form_state,
                "form_probs": p.form_probs,
                "career_avg": p.career_avg,
                "career_std": p.career_std,
                "rolling_avg": p.rolling_avg,
                "rolling_window": p.rolling_window,
                "adjusted_score": p.adjusted_score,
                "elo_multiplier": p.elo_multiplier,
                "photo_url": p.photo_url,
                "is_captain": i == cap_idx,
                "is_vc": i == vc_idx,
                "is_active": p.is_active,
            }
            team_players.append(d)

        total_credits = sum(players[i].credits for i in indices)
        fitness = (
            self._fitness_safe(players, indices) if strategy == "safe"
            else self._fitness_explosive(players, indices) if strategy == "explosive"
            else self._fitness_balanced(players, indices)
        )
        rolling_avgs = [players[i].rolling_avg or players[i].career_avg or 0.0 for i in indices]
        stds = [players[i].career_std or 0.0 for i in indices]

        return TeamResult(
            strategy=strategy,
            players=team_players,
            captain=next(p for p in team_players if p["is_captain"]),
            vc=next(p for p in team_players if p["is_vc"]),
            total_credits=round(total_credits, 1),
            fitness=round(fitness, 2),
            team_rolling_avg=round(float(np.mean(rolling_avgs)), 2),
            team_career_std=round(float(np.mean(stds)), 2),
        )

    def _indices_to_names(self, indices: list[int], players: list[PlayerProfile]) -> list[str]:
        return [players[i].player_name for i in indices if i < len(players)]
