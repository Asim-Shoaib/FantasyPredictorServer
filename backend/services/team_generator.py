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
    min_per_franchise: int = 4
    max_per_franchise: int = 7          # single-match rule
    min_wk: int = 1
    max_wk: int = 11
    min_batters: int = 3
    max_batters: int = 11
    min_bowlers: int = 3
    max_bowlers: int = 11
    min_allrounders: int = 1
    max_allrounders: int = 11
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
        mapping = {
            "batter_min": "min_batters",
            "batter_max": "max_batters",
            "allrounder_min": "min_allrounders",
            "allrounder_max": "max_allrounders",
            "wicketkeeper_min": "min_wk",
            "wicketkeeper_max": "max_wk",
            "bowler_min": "min_bowlers",
            "bowler_max": "max_bowlers",
            "per_team_min": "min_per_franchise",
            "per_team_max": "max_per_franchise",
        }

        def _coerce_int(v):
            try:
                return int(v)
            except Exception:
                return v

        filtered = {}
        for k, v in d.items():
            key = mapping.get(k, k)
            if key in valid:
                if key.endswith("_min") or key.endswith("_max") or key in {"team_size", "population_size", "generations", "tournament_size", "elitism_count", "min_per_franchise", "max_per_franchise"}:
                    filtered[key] = _coerce_int(v)
                else:
                    filtered[key] = v

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
    expected_score: float
    ceiling_score: float
    floor_score: float
    team_rolling_avg: float
    team_career_std: float
    team_hot_prob: float


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


def _role_bucket(role: str) -> str:
    r = _norm_role(role)
    if not r:
        return "bat"
    if "wicket" in r or "keeper" in r or r in {"wk", "wkb", "wkt", "wicket-keeper", "wicketkeeper"}:
        return "wk"
    if "all" in r or "allround" in r:
        return "ar"
    if "bowl" in r or "bowler" in r or any(k in r for k in ["pace", "spin", "fast", "medium"]):
        return "bowl"
    if "bat" in r or "batter" in r:
        return "bat"
    return "bat"


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
    def _get_probs(p: PlayerProfile) -> tuple[float, float, float]:
        """Returns (P_cold, P_avg, P_hot). Defaults to [0.33, 0.34, 0.33] if unknown."""
        probs = p.form_probs or []
        if len(probs) >= 3:
            return float(probs[0]), float(probs[1]), float(probs[2])
        return 0.33, 0.34, 0.33

    @staticmethod
    def _fitness_safe(players: list[PlayerProfile], indices: list[int]) -> float:
        """Minimizes P_cold: Score * (1 - P_cold)"""
        total = 0.0
        for i in indices:
            p = players[i]
            p_cold, _, _ = GeneticTeamGenerator._get_probs(p)
            total += (p.adjusted_score or 0.0) * (1.0 - p_cold)
        return total

    @staticmethod
    def _fitness_explosive(players: list[PlayerProfile], indices: list[int]) -> float:
        """Maximizes P_hot: Score * (1 + P_hot)"""
        total = 0.0
        for i in indices:
            p = players[i]
            _, _, p_hot = GeneticTeamGenerator._get_probs(p)
            total += (p.adjusted_score or 0.0) * (1.0 + p_hot)
        return total

    @staticmethod
    def _fitness_balanced(players: list[PlayerProfile], indices: list[int]) -> float:
        """Mixes both: Score * (1 + 0.5*P_hot - 0.5*P_cold)"""
        total = 0.0
        for i in indices:
            p = players[i]
            p_cold, _, p_hot = GeneticTeamGenerator._get_probs(p)
            multiplier = 1.0 + (0.5 * p_hot) - (0.5 * p_cold)
            total += (p.adjusted_score or 0.0) * multiplier
        return total

    # ─── GA internals ─────────────────────────────────────────────────────
    def _calculate_constraint_penalty(self, indices: list[int], players: list[PlayerProfile], c: TeamConstraints) -> float:
        penalty = 0.0
        
        # 1. Uniqueness (Prevent duplicate players)
        unique_players = set(indices)
        if len(unique_players) < c.team_size:
            penalty += (c.team_size - len(unique_players)) * 1000
            
        # 2. Budget
        total_credits = sum(players[i].credits for i in indices)
        if total_credits > c.budget:
            penalty += (total_credits - c.budget) * 1000
            
        # 3. Franchise limits
        from collections import Counter
        team_counts = Counter(players[i].team for i in indices)
        if c.team_a and c.team_b:
            for team in (c.team_a, c.team_b):
                cnt = team_counts.get(team, 0)
                if cnt < c.min_per_franchise: penalty += (c.min_per_franchise - cnt) * 1000
                if cnt > c.max_per_franchise: penalty += (cnt - c.max_per_franchise) * 1000
                
        # 4. Role limits
        roles = [players[i].role for i in indices]
        buckets = [_role_bucket(r) for r in roles]
        wk_count = sum(1 for b in buckets if b == "wk")
        bat_count = sum(1 for b in buckets if b == "bat")
        bowl_count = sum(1 for b in buckets if b == "bowl")
        ar_count = sum(1 for b in buckets if b == "ar")
        
        if wk_count < c.min_wk: penalty += (c.min_wk - wk_count) * 1000
        if wk_count > c.max_wk: penalty += (wk_count - c.max_wk) * 1000
        if bat_count < c.min_batters: penalty += (c.min_batters - bat_count) * 1000
        if bat_count > c.max_batters: penalty += (bat_count - c.max_batters) * 1000
        if bowl_count < c.min_bowlers: penalty += (c.min_bowlers - bowl_count) * 1000
        if bowl_count > c.max_bowlers: penalty += (bowl_count - c.max_bowlers) * 1000
        if ar_count < c.min_allrounders: penalty += (c.min_allrounders - ar_count) * 1000
        if ar_count > c.max_allrounders: penalty += (ar_count - c.max_allrounders) * 1000
        
        return penalty
    
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
                
                # UPDATE THIS LINE: Add 'players' as the third argument
                child = self._crossover(p1, p2, players, constraints)
                
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
        for _ in range(500):
            chosen = locked[:]
            available = [i for i in pool if i not in locked]
            random.shuffle(available) # Mix up the pool
            
            for candidate in available:
                if len(chosen) == c.team_size:
                    break
                    
                temp = chosen + [candidate]
                
                # 1. Fast-fail Maximum Roles
                roles = [_role_bucket(players[i].role) for i in temp]
                if roles.count("wk") > c.max_wk: continue
                if roles.count("bat") > c.max_batters: continue
                if roles.count("bowl") > c.max_bowlers: continue
                if roles.count("ar") > c.max_allrounders: continue
                
                # 2. Fast-fail Budget
                if sum(players[i].credits for i in temp) > c.budget: continue
                
                # 3. Fast-fail Franchise limits
                t_counts = {}
                for i in temp:
                    t_counts[players[i].team] = t_counts.get(players[i].team, 0) + 1
                if any(cnt > c.max_per_franchise for cnt in t_counts.values()): continue
                
                chosen.append(candidate)
                
            # If we successfully built 11 players, do a final strict check (validates minimums)
            if len(chosen) == c.team_size and self._passes_hard_constraints(chosen, players, c):
                cap = random.randint(0, c.team_size - 1)
                vc_choices = [i for i in range(c.team_size) if i != cap]
                vc = random.choice(vc_choices)
                return chosen + [cap, vc]
                
        # Fallback if constraints are impossible (e.g. Budget 40)
        chosen = random.sample(pool, c.team_size)
        return chosen + [0, 1]

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
        if c.team_a and c.team_b:
            for team in (c.team_a, c.team_b):
                cnt = team_counts.get(team, 0)
                if cnt < c.min_per_franchise or cnt > c.max_per_franchise:
                    return False
        else:
            if any(cnt > c.max_per_franchise for cnt in team_counts.values()):
                return False
            if c.min_per_franchise > 0 and any(cnt < c.min_per_franchise for cnt in team_counts.values()):
                return False

        roles = [players[i].role for i in indices]
        buckets = [_role_bucket(r) for r in roles]
        wk_count = sum(1 for b in buckets if b == "wk")
        bat_count = sum(1 for b in buckets if b == "bat")
        bowl_count = sum(1 for b in buckets if b == "bowl")
        ar_count = sum(1 for b in buckets if b == "ar")

        if wk_count < c.min_wk or wk_count > c.max_wk:
            return False
        if bat_count < c.min_batters or bat_count > c.max_batters:
            return False
        if bowl_count < c.min_bowlers or bowl_count > c.max_bowlers:
            return False
        if ar_count < c.min_allrounders or ar_count > c.max_allrounders:
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

    def _crossover(self, p1: list[int], p2: list[int], players: list[PlayerProfile], c: TeamConstraints) -> list[int]:
        if random.random() > c.crossover_rate:
            return p1[:]
            
        # Try to find a valid crossover splice
        for _ in range(20):
            point = random.randint(1, c.team_size - 1)
            child_indices = p1[:point] + [i for i in p2 if i not in p1[:point]]
            child_indices = child_indices[:c.team_size]
            
            # Pad if short
            available = [i for i in range(len(players)) if i not in child_indices]
            while len(child_indices) < c.team_size:
                child_indices.append(random.choice(available) if available else 0)
                
            # Accept if valid
            if self._passes_hard_constraints(child_indices, players, c):
                cap = random.randint(0, c.team_size - 1)
                vc = (cap + 1) % c.team_size
                return child_indices + [cap, vc]
                
        # If crossover is invalid, clone the parent
        return p1[:]

    def _mutate(
        self, chrom: list[int], players: list[PlayerProfile], c: TeamConstraints
    ) -> list[int]:
        if random.random() > c.mutation_rate:
            return chrom
            
        pool = list(range(len(players)))
        locked_ids = set(c.locked_players)
        
        # Try to find a mutation that is mathematically VALID
        for _ in range(20):
            new_chrom = chrom[:]
            swap_pos = random.randint(0, c.team_size - 1)
            
            if players[new_chrom[swap_pos]].player_id in locked_ids:
                continue
                
            candidates = [i for i in pool if i not in new_chrom[:c.team_size]]
            if not candidates:
                break
                
            new_chrom[swap_pos] = random.choice(candidates)
            
            # If the mutation keeps the team valid, accept it instantly!
            if self._passes_hard_constraints(new_chrom[:c.team_size], players, c):
                return new_chrom
                
        return chrom # Return un-mutated if no valid mutation found

    # ─── Result building ─────────────────────────────────────────────────

    def _choose_captain_vc(
        self, indices: list[int], players: list[PlayerProfile], strategy: str
    ) -> tuple[int, int]:
        """Pick captain and VC based on strategy-specific multiplicative scoring."""
        def key_fn(i: int) -> float:
            p = players[i]
            score = p.adjusted_score or 0.0
            
            # Fetch the full spectrum of probabilities
            p_cold, p_avg, p_hot = GeneticTeamGenerator._get_probs(p)
            
            if strategy == "safe":
                # Safe: Value = Score * (1 - P_cold)
                return score * (1.0 - p_cold)
                
            elif strategy == "explosive":
                # Explosive: Value = Score * (1 + P_hot)
                return score * (1.0 + p_hot)
                
            else:
                # Balanced: Value = Score * (1 + 0.5*P_hot - 0.5*P_cold)
                multiplier = 1.0 + (0.5 * p_hot) - (0.5 * p_cold)
                return score * multiplier

        # Sort the 11 player indices based on their strategic value, highest to lowest
        ranked = sorted(indices, key=key_fn, reverse=True)
        
        # Rank 1 gets Captain (index 0), Rank 2 gets Vice-Captain (index 1)
        return ranked[0], ranked[1]

    def _chromosome_to_result(
        self, chrom: list[int], players: list[PlayerProfile], strategy: str
    ) -> TeamResult:
        n = 11  # team_size
        indices = chrom[:n]
        cap_idx, vc_idx = self._choose_captain_vc(indices, players, strategy)

        team_players = []
        team_expected = 0.0
        floor = 0.0
        ceiling = 0.0

        for i in indices:
            p = players[i]
            score = p.adjusted_score or 0.0
            p_cold, p_avg, p_hot = GeneticTeamGenerator._get_probs(p)
            
            # The new Multiplicative Stats
            team_expected += score
            floor += score * (1.0 - p_cold)
            ceiling += score * (1.0 + p_hot)

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
                "elo_post": p.elo_post,
                "elo_multiplier": p.elo_multiplier,
                "photo_url": p.photo_url,
                "is_captain": i == cap_idx,
                "is_vc": i == vc_idx,
                "is_active": p.is_active,
            }
            team_players.append(d)

        total_credits = sum(players[i].credits for i in indices)
        rolling_avgs = [players[i].rolling_avg or players[i].career_avg or 0.0 for i in indices]

        return TeamResult(
            strategy=strategy,
            players=team_players,
            captain=next(p for p in team_players if p["is_captain"]),
            vc=next(p for p in team_players if p["is_vc"]),
            total_credits=round(total_credits, 1),
            fitness=0.0, # We don't need to display raw fitness anymore
            expected_score=round(team_expected, 2),
            ceiling_score=round(ceiling, 2),
            floor_score=round(floor, 2),
            team_rolling_avg=round(float(np.mean(rolling_avgs)), 2),
            team_career_std=0.0, # Deprecated metric
            team_hot_prob=0.0,   # Deprecated metric
        )
    
    def _indices_to_names(self, indices: list[int], players: list[PlayerProfile]) -> list[str]:
        return [players[i].player_name for i in indices if i < len(players)]
