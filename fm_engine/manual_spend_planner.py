from __future__ import annotations

from itertools import combinations

import numpy as np
import pandas as pd


try:
    from fm_engine.signing_engine import ensure_transfer_costs, format_money
except Exception:
    def format_money(value) -> str:
        try:
            if value is None or pd.isna(value):
                return "Unknown"
            return f"£{float(value):,.0f}"
        except Exception:
            return "Unknown"

    def ensure_transfer_costs(df: pd.DataFrame) -> pd.DataFrame:
        out = df.copy()

        if "Transfer Cost" not in out.columns:
            out["Transfer Cost"] = np.nan

        out["Transfer Cost"] = pd.to_numeric(out["Transfer Cost"], errors="coerce")
        out["Transfer Cost Display"] = out["Transfer Cost"].apply(format_money)

        return out


def spending_strategy_settings(spend_strategy: str) -> dict:
    strategy = str(spend_strategy or "Balanced").strip()

    if strategy == "Conservative":
        return {
            "target_spend_ratio": 0.65,
            "minimum_spend_ratio": 0.45,
            "minimum_individual_ratio": 0.20,
            "spend_closeness_weight": 0.45,
            "value_weight": 2.75,
        }

    if strategy == "Aggressive":
        return {
            "target_spend_ratio": 0.94,
            "minimum_spend_ratio": 0.78,
            "minimum_individual_ratio": 0.45,
            "spend_closeness_weight": 0.90,
            "value_weight": 1.35,
        }

    return {
        "target_spend_ratio": 0.82,
        "minimum_spend_ratio": 0.62,
        "minimum_individual_ratio": 0.33,
        "spend_closeness_weight": 0.70,
        "value_weight": 1.90,
    }


def prepare_manual_spend_pool(
    recs: pd.DataFrame,
    total_budget: float,
    planned_spend_target: float,
    players_to_buy: int,
    spend_strategy: str,
) -> pd.DataFrame:
    pool = ensure_transfer_costs(recs.copy())

    pool["Transfer Cost"] = pd.to_numeric(pool["Transfer Cost"], errors="coerce")

    pool = pool[
        pool["Transfer Cost"].notna()
        & (pool["Transfer Cost"] > 0)
        & (pool["Transfer Cost"] <= planned_spend_target)
    ].copy()

    if planned_spend_target < 1_000_000_000:
        pool = pool[pool["Transfer Cost"] < 1_000_000_000].copy()

    if pool.empty:
        return pool

    if "Player" in pool.columns and "Club" in pool.columns:
        pool = pool.drop_duplicates(subset=["Player", "Club"], keep="first").copy()

    for col, default in {
        "Quality Score": 0,
        "Recommendation Score": 0,
        "Realism Fit": 50,
        "Squad Gap Value": 0,
        "Gap Priority Order": 99,
        "Playstyle Fit": 50,
        "Upgrade Over Current Area": 0,
    }.items():
        if col not in pool.columns:
            pool[col] = default

        pool[col] = pd.to_numeric(pool[col], errors="coerce").fillna(default)

    settings = spending_strategy_settings(spend_strategy)

    target_total_spend = planned_spend_target * settings["target_spend_ratio"]
    minimum_total_spend = planned_spend_target * settings["minimum_spend_ratio"]
    target_price_per_player = target_total_spend / max(players_to_buy, 1)
    minimum_individual_price = target_price_per_player * settings["minimum_individual_ratio"]

    pool["Transfer Cost Display"] = pool["Transfer Cost"].apply(format_money)

    pool["Value Efficiency"] = (
        pool["Quality Score"] / ((pool["Transfer Cost"] / 1_000_000) + 1)
    ).round(3)

    pool["Budget Share %"] = (
        pool["Transfer Cost"] / max(total_budget, 1) * 100
    ).round(1)

    pool["Planned Spend Share %"] = (
        pool["Transfer Cost"] / max(planned_spend_target, 1) * 100
    ).round(1)

    pool["Target Price Fit"] = (
        100
        - (
            (pool["Transfer Cost"] - target_price_per_player).abs()
            / max(target_price_per_player, 1)
            * 55
        )
    ).clip(lower=0, upper=100).round(1)

    pool["Too Cheap Penalty"] = (
        (minimum_individual_price - pool["Transfer Cost"]).clip(lower=0)
        / max(minimum_individual_price, 1)
        * 35
    ).round(1)

    pool["Manual Spend Plan Score"] = (
        pool["Quality Score"] * 0.42
        + pool["Recommendation Score"] * 0.18
        + pool["Realism Fit"] * 0.17
        + pool["Target Price Fit"] * 0.18
        + pool["Value Efficiency"] * settings["value_weight"]
        + pool["Squad Gap Value"].clip(lower=0) * 1.35
        - pool["Gap Priority Order"] * 0.15
        - pool["Too Cheap Penalty"] * 0.40
    ).round(2)

    pool.attrs["target_total_spend"] = target_total_spend
    pool.attrs["minimum_total_spend"] = minimum_total_spend
    pool.attrs["target_price_per_player"] = target_price_per_player
    pool.attrs["minimum_individual_price"] = minimum_individual_price
    pool.attrs["spend_strategy"] = spend_strategy

    return pool


def score_plan_combo(
    combo: pd.DataFrame,
    planned_spend_target: float,
    target_total_spend: float,
    minimum_total_spend: float,
    spend_strategy: str,
) -> float:
    total_cost = float(combo["Transfer Cost"].sum())

    if total_cost > planned_spend_target:
        return -999999999

    settings = spending_strategy_settings(spend_strategy)

    spend_closeness = (
        100
        - abs(total_cost - target_total_spend)
        / max(target_total_spend, 1)
        * 100
    )

    spend_closeness = max(spend_closeness, 0)

    underspend_penalty = 0

    if total_cost < minimum_total_spend:
        underspend_penalty = (
            (minimum_total_spend - total_cost)
            / max(minimum_total_spend, 1)
            * 85
        )

    unique_gaps = (
        combo["Recommended For"].astype(str).nunique()
        if "Recommended For" in combo.columns
        else 1
    )

    avg_quality = float(combo["Quality Score"].mean())
    avg_recommendation = float(combo["Recommendation Score"].mean())
    avg_realism = float(combo["Realism Fit"].mean())
    avg_playstyle = float(combo["Playstyle Fit"].mean())
    avg_manual_score = float(combo["Manual Spend Plan Score"].mean())

    return (
        avg_quality * 1.00
        + avg_recommendation * 0.38
        + avg_realism * 0.32
        + avg_playstyle * 0.20
        + avg_manual_score * 0.40
        + spend_closeness * settings["spend_closeness_weight"]
        + unique_gaps * 5.00
        - underspend_penalty
    )


def build_single_player_plan(
    pool: pd.DataFrame,
    planned_spend_target: float,
    target_total_spend: float,
    minimum_total_spend: float,
    spend_strategy: str,
) -> pd.DataFrame:
    candidates = pool.copy()

    candidates["Spend Target Fit"] = (
        100
        - (
            (candidates["Transfer Cost"] - target_total_spend).abs()
            / max(target_total_spend, 1)
            * 65
        )
    ).clip(lower=0, upper=100).round(1)

    candidates["Single Player Plan Score"] = (
        candidates["Quality Score"] * 0.46
        + candidates["Recommendation Score"] * 0.20
        + candidates["Realism Fit"] * 0.16
        + candidates["Spend Target Fit"] * 0.23
        + candidates["Squad Gap Value"].clip(lower=0) * 1.15
        - candidates["Too Cheap Penalty"] * 0.45
    ).round(2)

    stronger_price_pool = candidates[candidates["Transfer Cost"] >= minimum_total_spend].copy()

    if stronger_price_pool.empty:
        stronger_price_pool = candidates

    plan = (
        stronger_price_pool.sort_values(
            ["Single Player Plan Score", "Quality Score", "Recommendation Score"],
            ascending=False,
        )
        .head(1)
        .copy()
    )

    plan.insert(0, "Buy Order", 1)

    return plan


def build_combo_plan(
    pool: pd.DataFrame,
    planned_spend_target: float,
    players_to_buy: int,
    target_total_spend: float,
    minimum_total_spend: float,
    spend_strategy: str,
) -> pd.DataFrame:
    pool = (
        pool.sort_values(
            ["Manual Spend Plan Score", "Quality Score", "Recommendation Score"],
            ascending=False,
        )
        .head(75)
        .reset_index(drop=True)
    )

    best_combo = None
    best_score = -999999999

    for indexes in combinations(range(len(pool)), players_to_buy):
        combo = pool.iloc[list(indexes)].copy()
        score = score_plan_combo(
            combo=combo,
            planned_spend_target=planned_spend_target,
            target_total_spend=target_total_spend,
            minimum_total_spend=minimum_total_spend,
            spend_strategy=spend_strategy,
        )

        if score > best_score:
            best_score = score
            best_combo = combo.copy()

    if best_combo is None or best_combo.empty:
        return pd.DataFrame()

    best_combo = best_combo.sort_values(
        ["Gap Priority Order", "Manual Spend Plan Score"],
        ascending=[True, False],
    ).reset_index(drop=True)

    best_combo.insert(0, "Buy Order", best_combo.index + 1)

    return best_combo


def build_large_squad_plan(
    pool: pd.DataFrame,
    planned_spend_target: float,
    players_to_buy: int,
    target_total_spend: float,
    target_price_per_player: float,
    minimum_individual_price: float,
) -> pd.DataFrame:
    selected = []
    used_players = set()
    remaining = planned_spend_target

    pool = pool.copy()

    for slot in range(players_to_buy):
        remaining_slots = players_to_buy - len(selected)

        if remaining_slots <= 0:
            break

        desired_price = min(remaining / remaining_slots, target_price_per_player * 1.35)

        available = pool[pool["Transfer Cost"] <= remaining].copy()

        if available.empty:
            break

        available = available[
            ~available.apply(
                lambda row: (str(row.get("Player", "")), str(row.get("Club", ""))) in used_players,
                axis=1,
            )
        ].copy()

        if available.empty:
            break

        strong_available = available[available["Transfer Cost"] >= minimum_individual_price].copy()

        if not strong_available.empty:
            available = strong_available

        selected_gaps = {
            str(row.get("Recommended For", ""))
            for row in selected
        }

        available["Slot Price Fit"] = (
            100
            - (
                (available["Transfer Cost"] - desired_price).abs()
                / max(desired_price, 1)
                * 55
            )
        ).clip(lower=0, upper=100).round(1)

        available["Gap Diversity Bonus"] = available["Recommended For"].apply(
            lambda gap: 8 if str(gap) not in selected_gaps else 0
        )

        available["Live Pick Score"] = (
            available["Quality Score"] * 0.40
            + available["Recommendation Score"] * 0.18
            + available["Realism Fit"] * 0.16
            + available["Slot Price Fit"] * 0.26
            + available["Gap Diversity Bonus"]
            - available["Too Cheap Penalty"] * 0.45
        ).round(2)

        pick = available.sort_values(
            ["Live Pick Score", "Manual Spend Plan Score", "Quality Score"],
            ascending=False,
        ).iloc[0]

        selected.append(pick)
        used_players.add((str(pick.get("Player", "")), str(pick.get("Club", ""))))
        remaining -= float(pick["Transfer Cost"])

    plan = pd.DataFrame(selected).reset_index(drop=True)

    if not plan.empty:
        plan.insert(0, "Buy Order", plan.index + 1)

    return plan


def finalize_plan(
    plan: pd.DataFrame,
    pool: pd.DataFrame,
    total_budget: float,
    planned_spend_target: float,
) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    if plan.empty:
        return pd.DataFrame(), pool, {
            "spend": 0,
            "left": total_budget,
            "target_left": planned_spend_target,
            "message": "Could not build a plan under your manual planned spend target.",
        }

    plan["Cumulative Spend"] = plan["Transfer Cost"].cumsum()
    plan["Cumulative Spend Display"] = plan["Cumulative Spend"].apply(format_money)

    plan["Total Budget Remaining After Deal"] = total_budget - plan["Cumulative Spend"]
    plan["Total Budget Remaining Display"] = plan["Total Budget Remaining After Deal"].apply(format_money)

    plan["Planned Spend Remaining After Deal"] = planned_spend_target - plan["Cumulative Spend"]
    plan["Planned Spend Remaining Display"] = plan["Planned Spend Remaining After Deal"].apply(format_money)

    total_spend = float(plan["Transfer Cost"].sum())

    summary = {
        "spend": total_spend,
        "left": total_budget - total_spend,
        "target_left": planned_spend_target - total_spend,
        "message": "Manual planned spend plan created.",
    }

    alternatives = (
        pool.sort_values(
            ["Quality Score", "Recommendation Score", "Realism Fit"],
            ascending=False,
        )
        .head(75)
        .copy()
    )

    return plan, alternatives, summary


def build_manual_spend_budget_plan(
    recs: pd.DataFrame,
    total_budget: float,
    planned_spend_target: float,
    players_to_buy: int,
    spend_strategy: str = "Balanced",
) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    if recs is None or recs.empty:
        return pd.DataFrame(), pd.DataFrame(), {
            "spend": 0,
            "left": total_budget,
            "target_left": planned_spend_target,
            "message": "No realistic recommendations available.",
        }

    total_budget = float(total_budget or 0)
    planned_spend_target = float(planned_spend_target or 0)
    players_to_buy = int(players_to_buy or 1)

    if total_budget <= 0:
        return pd.DataFrame(), pd.DataFrame(), {
            "spend": 0,
            "left": 0,
            "target_left": 0,
            "message": "Transfer budget must be greater than 0.",
        }

    if planned_spend_target <= 0:
        planned_spend_target = total_budget

    planned_spend_target = min(planned_spend_target, total_budget)

    pool = prepare_manual_spend_pool(
        recs=recs,
        total_budget=total_budget,
        planned_spend_target=planned_spend_target,
        players_to_buy=players_to_buy,
        spend_strategy=spend_strategy,
    )

    if pool.empty:
        return pd.DataFrame(), pd.DataFrame(), {
            "spend": 0,
            "left": total_budget,
            "target_left": planned_spend_target,
            "message": "No affordable realistic players found inside your planned spend target.",
        }

    target_total_spend = pool.attrs["target_total_spend"]
    minimum_total_spend = pool.attrs["minimum_total_spend"]
    target_price_per_player = pool.attrs["target_price_per_player"]
    minimum_individual_price = pool.attrs["minimum_individual_price"]

    if players_to_buy <= 1:
        plan = build_single_player_plan(
            pool=pool,
            planned_spend_target=planned_spend_target,
            target_total_spend=target_total_spend,
            minimum_total_spend=minimum_total_spend,
            spend_strategy=spend_strategy,
        )

    elif players_to_buy <= 4:
        plan = build_combo_plan(
            pool=pool,
            planned_spend_target=planned_spend_target,
            players_to_buy=players_to_buy,
            target_total_spend=target_total_spend,
            minimum_total_spend=minimum_total_spend,
            spend_strategy=spend_strategy,
        )

    else:
        plan = build_large_squad_plan(
            pool=pool,
            planned_spend_target=planned_spend_target,
            players_to_buy=players_to_buy,
            target_total_spend=target_total_spend,
            target_price_per_player=target_price_per_player,
            minimum_individual_price=minimum_individual_price,
        )

    return finalize_plan(
        plan=plan,
        pool=pool,
        total_budget=total_budget,
        planned_spend_target=planned_spend_target,
    )
