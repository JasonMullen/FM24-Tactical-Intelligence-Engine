from pathlib import Path
import re

engine_path = Path("fm_engine/signing_engine.py")
page_path = Path("app/pages/11_Recommended_Signings.py")

engine_text = engine_path.read_text(encoding="utf-8")
page_text = page_path.read_text(encoding="utf-8")

# ============================================================
# 1. ADD TRUE MANUAL PLANNED SPEND ENGINE
# ============================================================

new_engine = r'''

def build_manual_spend_budget_plan(
    recs: pd.DataFrame,
    total_budget: float,
    planned_spend_target: float,
    players_to_buy: int,
) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """
    Builds a plan that tries to spend close to the user's manually entered planned spend target.

    Example:
    - Total budget: 150M
    - Planned spend target: 50M
    - Players to buy: 3

    The engine tries to find the best 3-player combination near 50M,
    not merely the cheapest 3 players under 50M.
    """

    if recs.empty:
        return pd.DataFrame(), pd.DataFrame(), {
            "spend": 0,
            "left": total_budget,
            "target_left": planned_spend_target,
            "message": "No realistic recommendations available.",
        }

    total_budget = float(total_budget)
    planned_spend_target = float(planned_spend_target)
    players_to_buy = int(players_to_buy)

    if planned_spend_target <= 0:
        planned_spend_target = total_budget

    planned_spend_target = min(planned_spend_target, total_budget)

    pool = ensure_transfer_costs(recs)
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

    pool = pool.drop_duplicates(subset=["Player", "Club"]).copy()

    for col in [
        "Quality Score",
        "Recommendation Score",
        "Realism Fit",
        "Squad Gap Value",
        "Gap Priority Order",
        "Playstyle Fit",
        "Upgrade Over Current Area",
    ]:
        if col not in pool.columns:
            pool[col] = 0

        pool[col] = pd.to_numeric(pool[col], errors="coerce").fillna(0)

    target_price_per_player = planned_spend_target / max(players_to_buy, 1)

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

    # Single player mode: best player under planned target, while preferring players
    # who actually use a meaningful part of the target.
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

    # 2-4 players: search combinations and reward being close to manual planned spend.
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
            spend_closeness = 100 - abs(1 - spend_ratio) * 100
            spend_closeness = max(spend_closeness, 0)

            unique_gaps = combo["Recommended For"].astype(str).nunique()
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
                key = (str(row["Player"]), str(row["Club"]))

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

    # 5+ players: greedy, but still tries to spend near the target.
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
            key = (str(row["Player"]), str(row["Club"]))

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
'''

if "def build_manual_spend_budget_plan(" not in engine_text:
    engine_text = engine_text.rstrip() + "\n\n" + new_engine + "\n"

engine_path.write_text(engine_text, encoding="utf-8")


# ============================================================
# 2. PATCH RECOMMENDED SIGNINGS PAGE IMPORT
# ============================================================

if "build_manual_spend_budget_plan" not in page_text:
    page_text = page_text.replace(
        "build_dynamic_budget_plan,",
        "build_dynamic_budget_plan,\n    build_manual_spend_budget_plan,",
        1,
    )


# ============================================================
# 3. MAKE SURE SIDEBAR HAS MANUAL PLANNED SPEND TARGET
# ============================================================

planned_spend_block = r'''
planned_spend_text = st.sidebar.text_input(
    "Planned Spend Target",
    value="50,000,000",
    placeholder="Example: 50M or 50,000,000",
    key="rec_planned_spend_target_text",
)

planned_spend_target = parse_budget_input(planned_spend_text)

if planned_spend_target <= 0:
    planned_spend_target = transfer_budget

planned_spend_target = min(float(planned_spend_target), float(transfer_budget))

st.sidebar.caption(f"Planned spend target: {format_money(planned_spend_target)}")
'''

if "planned_spend_target = parse_budget_input(planned_spend_text)" not in page_text:
    marker = 'st.sidebar.caption(f"Budget read as: {format_money(transfer_budget)}")'

    if marker not in page_text:
        raise SystemExit("Could not find budget caption marker in page.")

    page_text = page_text.replace(
        marker,
        marker + "\n\n" + planned_spend_block,
        1,
    )


# ============================================================
# 4. USE PLANNED SPEND TARGET FOR REALISM + RECOMMENDATIONS
# ============================================================

page_text = page_text.replace(
    "context = club_realism_context(team_ratings, your_club, target_goal, transfer_budget)",
    "context = club_realism_context(team_ratings, your_club, target_goal, planned_spend_target)",
)

page_text = page_text.replace(
    "transfer_budget=transfer_budget,",
    "transfer_budget=planned_spend_target,",
)


# ============================================================
# 5. USE MANUAL SPEND PLAN ENGINE IN DYNAMIC BUDGET PLAN VIEW
# ============================================================

page_text = page_text.replace(
    '''    plan, alternatives, summary = build_dynamic_budget_plan(
        budget_recommendations,
        transfer_budget,
        players_to_buy,
    )''',
    '''    plan, alternatives, summary = build_manual_spend_budget_plan(
        budget_recommendations,
        total_budget=transfer_budget,
        planned_spend_target=planned_spend_target,
        players_to_buy=players_to_buy,
    )''',
)

page_text = page_text.replace(
    '''    st.write(
        f"Build a realistic spending plan for **{your_club}** with **{format_money(transfer_budget)}** "
        f"to buy **{players_to_buy} player(s)** for **{target_goal}** using **{playstyle}**."
    )''',
    '''    st.write(
        f"Build a realistic spending plan for **{your_club}** with **{format_money(transfer_budget)} total budget** "
        f"and a manual planned spend target of **{format_money(planned_spend_target)}** "
        f"to buy **{players_to_buy} player(s)** for **{target_goal}** using **{playstyle}**."
    )''',
)


# ============================================================
# 6. UPDATE TOP METRIC AND BUDGET PLAN METRICS
# ============================================================

page_text = page_text.replace(
    'm4.metric("Budget", format_money(transfer_budget))',
    'm4.metric("Spend Target", format_money(planned_spend_target))',
)

old_metric_block = '''    b1, b2, b3, b4 = st.columns(4)
    b1.metric("Transfer Budget", format_money(transfer_budget))
    b2.metric("Planned Spend", format_money(summary["spend"]))
    b3.metric("Budget Left", format_money(summary["left"]))
    b4.metric("Players Selected", len(plan))
'''

new_metric_block = '''    b1, b2, b3, b4, b5 = st.columns(5)
    b1.metric("Transfer Budget", format_money(transfer_budget))
    b2.metric("Spend Target", format_money(planned_spend_target))
    b3.metric("Planned Spend", format_money(summary["spend"]))
    b4.metric("Target Left", format_money(summary["target_left"]))
    b5.metric("Players Selected", len(plan))
'''

if old_metric_block in page_text:
    page_text = page_text.replace(old_metric_block, new_metric_block, 1)


# ============================================================
# 7. UPDATE SUCCESS MESSAGE + DISPLAY COLUMNS
# ============================================================

page_text = page_text.replace(
    '''            st.success(
                f"Recommended {len(plan)}-player plan: spend **{format_money(summary['spend'])}** "
                f"and keep **{format_money(summary['left'])}**."
            )''',
    '''            st.success(
                f"Recommended {len(plan)}-player plan: spend **{format_money(summary['spend'])}** "
                f"out of your manual planned spend target of **{format_money(planned_spend_target)}**. "
                f"Total budget left: **{format_money(summary['left'])}**."
            )''',
)

page_text = page_text.replace(
    '"Budget Remaining Display",',
    '"Total Budget Remaining Display",\n            "Planned Spend Remaining Display",',
)

page_path.write_text(page_text, encoding="utf-8")

print("Manual planned spend target now controls the budget plan.")
