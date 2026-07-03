from pathlib import Path
import re

manual_module = Path("fm_engine/manual_spend_planner.py")
page_path = Path("app/pages/11_Recommended_Signings.py")

manual_module.write_text(r'''
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


def build_manual_spend_budget_plan(
    recs: pd.DataFrame,
    total_budget: float,
    planned_spend_target: float,
    players_to_buy: int,
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

    pool = ensure_transfer_costs(recs.copy())
    pool["Transfer Cost"] = pd.to_numeric(pool["Transfer Cost"], errors="coerce")

    pool = pool[
        pool["Transfer Cost"].notna()
        & (pool["Transfer Cost"] >= 0)
        & (pool["Transfer Cost"] <= planned_spend_target)
    ].copy()

    if planned_spend_target < 1_000_000_000:
        pool = pool[pool["Transfer Cost"] < 1_000_000_000].copy()

    if pool.empty:
        return pd.DataFrame(), pd.DataFrame(), {
            "spend": 0,
            "left": total_budget,
            "target_left": planned_spend_target,
            "message": "No affordable realistic players found inside your planned spend target.",
        }

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

    target_price_per_player = planned_spend_target / max(players_to_buy, 1)

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
            * 45
        )
    ).clip(lower=0, upper=100).round(1)

    if players_to_buy <= 1:
        pool["Spend Target Fit"] = (
            100
            - (
                (pool["Transfer Cost"] - planned_spend_target).abs()
                / max(planned_spend_target, 1)
                * 35
            )
        ).clip(lower=0, upper=100).round(1)

        pool["Manual Spend Plan Score"] = (
            pool["Quality Score"] * 0.48
            + pool["Recommendation Score"] * 0.20
            + pool["Realism Fit"] * 0.14
            + pool["Spend Target Fit"] * 0.14
            + pool["Squad Gap Value"].clip(lower=0) * 1.35
        ).round(2)

        plan = (
            pool.sort_values(
                ["Manual Spend Plan Score", "Quality Score", "Recommendation Score"],
                ascending=False,
            )
            .head(1)
            .copy()
        )

        plan.insert(0, "Buy Order", 1)

    elif players_to_buy <= 4:
        pool["Manual Spend Plan Score"] = (
            pool["Quality Score"] * 0.44
            + pool["Recommendation Score"] * 0.18
            + pool["Realism Fit"] * 0.15
            + pool["Target Price Fit"] * 0.12
            + pool["Value Efficiency"] * 2.00
            + pool["Squad Gap Value"].clip(lower=0) * 1.50
            - pool["Gap Priority Order"] * 0.15
        ).round(2)

        pool = (
            pool.sort_values(
                ["Manual Spend Plan Score", "Quality Score", "Recommendation Score"],
                ascending=False,
            )
            .head(60)
            .reset_index(drop=True)
        )

        best_combo = None
        best_score = -999999999

        for indexes in combinations(range(len(pool)), players_to_buy):
            combo = pool.iloc[list(indexes)].copy()
            total_cost = float(combo["Transfer Cost"].sum())

            if total_cost > planned_spend_target:
                continue

            spend_ratio = total_cost / max(planned_spend_target, 1)
            spend_closeness = max(100 - abs(1 - spend_ratio) * 100, 0)

            unique_gaps = (
                combo["Recommended For"].astype(str).nunique()
                if "Recommended For" in combo.columns
                else 1
            )

            avg_quality = float(combo["Quality Score"].mean())
            avg_realism = float(combo["Realism Fit"].mean())
            avg_recommendation = float(combo["Recommendation Score"].mean())
            avg_playstyle = float(combo["Playstyle Fit"].mean())

            combo_score = (
                avg_quality * 1.00
                + avg_recommendation * 0.35
                + avg_realism * 0.30
                + avg_playstyle * 0.20
                + spend_closeness * 0.65
                + unique_gaps * 5.00
            )

            if combo_score > best_score:
                best_score = combo_score
                best_combo = combo.copy()

        if best_combo is None:
            selected = []
            remaining = planned_spend_target
            used_players = set()

            for _, row in pool.iterrows():
                key = (str(row.get("Player", "")), str(row.get("Club", "")))

                if key in used_players:
                    continue

                cost = float(row["Transfer Cost"])

                if cost <= remaining:
                    selected.append(row)
                    used_players.add(key)
                    remaining -= cost

                if len(selected) >= players_to_buy:
                    break

            plan = pd.DataFrame(selected)
        else:
            plan = best_combo

        if not plan.empty:
            plan = plan.sort_values(
                ["Gap Priority Order", "Manual Spend Plan Score"],
                ascending=[True, False],
            ).reset_index(drop=True)

            plan.insert(0, "Buy Order", plan.index + 1)

    else:
        pool["Manual Spend Plan Score"] = (
            pool["Quality Score"] * 0.42
            + pool["Recommendation Score"] * 0.18
            + pool["Realism Fit"] * 0.15
            + pool["Target Price Fit"] * 0.12
            + pool["Value Efficiency"] * 2.75
            + pool["Squad Gap Value"].clip(lower=0) * 1.35
        ).round(2)

        selected = []
        remaining = planned_spend_target
        used_players = set()

        for _, row in pool.sort_values("Manual Spend Plan Score", ascending=False).iterrows():
            key = (str(row.get("Player", "")), str(row.get("Club", "")))

            if key in used_players:
                continue

            cost = float(row["Transfer Cost"])

            if cost <= remaining:
                selected.append(row)
                used_players.add(key)
                remaining -= cost

            if len(selected) >= players_to_buy:
                break

        plan = pd.DataFrame(selected).reset_index(drop=True)

        if not plan.empty:
            plan.insert(0, "Buy Order", plan.index + 1)

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
''', encoding="utf-8")

page_text = page_path.read_text(encoding="utf-8")

page_text = page_text.replace(
    "    build_manual_spend_budget_plan,\n",
    "",
)

if "from fm_engine.manual_spend_planner import build_manual_spend_budget_plan" not in page_text:
    insert_after = "from fm_engine.signing_engine import (\n"

    if insert_after not in page_text:
        raise SystemExit("Could not find signing_engine import block.")

    # Add separate import after the whole signing_engine import block.
    end_marker = ")\n\ntry:\n    from fm_engine.value_cleaner"

    if end_marker in page_text:
        page_text = page_text.replace(
            end_marker,
            ")\nfrom fm_engine.manual_spend_planner import build_manual_spend_budget_plan\n\ntry:\n    from fm_engine.value_cleaner",
            1,
        )
    else:
        page_text = page_text.replace(
            "from fm_engine.signing_engine import (",
            "from fm_engine.signing_engine import (",
            1,
        )
        page_text = "from fm_engine.manual_spend_planner import build_manual_spend_budget_plan\n" + page_text

page_path.write_text(page_text, encoding="utf-8")

print("Fixed manual spend planner import by moving function into separate module.")
