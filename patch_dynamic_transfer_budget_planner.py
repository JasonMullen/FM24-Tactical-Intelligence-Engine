from pathlib import Path
import re

path = Path("app/pages/11_Recommended_Signings.py")
text = path.read_text(encoding="utf-8")

# ============================================================
# 1. REMOVE DUPLICATE TRANSFER BUDGET NUMBER INPUT
# ============================================================

text = re.sub(
    r'\ntransfer_budget\s*=\s*st\.sidebar\.number_input\(\s*"Transfer Budget"[\s\S]*?\n\)',
    '',
    text,
    count=1,
)

# ============================================================
# 2. MAKE SURE MANUAL TEXT BUDGET INPUT EXISTS
# ============================================================

manual_budget_block = r'''
transfer_budget_text = st.sidebar.text_input(
    "Transfer Budget",
    value="150,000,000",
    placeholder="Example: 150,000,000 or 150M",
    key="recommended_signings_transfer_budget_text",
)

transfer_budget = parse_manual_budget_input(transfer_budget_text)

st.sidebar.caption(f"Budget read as: {format_money(transfer_budget)}")
'''

if "transfer_budget_text = st.sidebar.text_input" not in text:
    marker = "players_to_buy = st.sidebar.slider("

    if marker not in text:
        raise SystemExit("Could not find players_to_buy slider marker.")

    text = text.replace(marker, manual_budget_block + "\n\n" + marker, 1)


# ============================================================
# 3. ADD DYNAMIC BUDGET PLANNER ENGINE
# ============================================================

dynamic_engine = r'''

# ============================================================
# DYNAMIC TRANSFER BUDGET PLANNER ENGINE
# ============================================================

def dynamic_safe_df(df: pd.DataFrame) -> pd.DataFrame:
    safe = df.copy()
    seen = {}
    cols = []

    for col in safe.columns:
        base = str(col)

        if base not in seen:
            seen[base] = 1
            cols.append(base)
        else:
            seen[base] += 1
            cols.append(f"{base} [{seen[base]}]")

    safe.columns = cols
    return safe


def dynamic_format_money(value) -> str:
    try:
        if value is None or pd.isna(value):
            return "Unknown"

        return f"£{float(value):,.0f}"
    except Exception:
        return "Unknown"


try:
    format_money
except NameError:
    format_money = dynamic_format_money


def get_best_available_cost_column(recs: pd.DataFrame) -> str | None:
    possible_cols = [
        "Transfer Cost",
        "Transfer Value Clean",
        "Estimated Value Clean",
        "Transfer Value Clean £M",
        "Estimated Value Clean £M",
        "Estimated Value £M",
    ]

    for col in possible_cols:
        if col in recs.columns:
            return col

    return None


def prepare_budget_candidates(recommendations: pd.DataFrame, total_budget: float) -> pd.DataFrame:
    if recommendations.empty:
        return pd.DataFrame()

    recs = recommendations.copy()

    cost_col = get_best_available_cost_column(recs)

    if cost_col is None:
        return pd.DataFrame()

    if cost_col.endswith("£M") or cost_col == "Estimated Value £M":
        recs["Transfer Cost"] = pd.to_numeric(recs[cost_col], errors="coerce") * 1_000_000
    else:
        recs["Transfer Cost"] = pd.to_numeric(recs[cost_col], errors="coerce")

    recs = recs[
        recs["Transfer Cost"].notna()
        & (recs["Transfer Cost"] >= 0)
        & (recs["Transfer Cost"] <= total_budget)
    ].copy()

    # Exclude Not For Sale players unless the user has a massive budget.
    if total_budget < 1_000_000_000:
        recs = recs[recs["Transfer Cost"] < 1_000_000_000].copy()

    if recs.empty:
        return recs

    recs = recs.drop_duplicates(subset=["Player", "Club"], keep="first").copy()

    numeric_defaults = {
        "Recommendation Score": 0,
        "Candidate Category Rating": 0,
        "Candidate Attribute Fit": 0,
        "Candidate Statistical Fit": 0,
        "Playstyle Fit": 50,
        "Upgrade Over Current Area": 0,
        "Gap Covered %": 0,
        "Squad Gap Value": 0,
        "Gap Priority Order": 99,
    }

    for col, default in numeric_defaults.items():
        if col not in recs.columns:
            recs[col] = default

        recs[col] = pd.to_numeric(recs[col], errors="coerce").fillna(default)

    recs["Transfer Cost Display"] = recs["Transfer Cost"].apply(format_money)

    recs["Quality Score"] = (
        recs["Recommendation Score"] * 0.42
        + recs["Candidate Category Rating"] * 0.22
        + recs["Playstyle Fit"] * 0.18
        + recs["Upgrade Over Current Area"].clip(lower=0) * 1.65
        + recs["Squad Gap Value"].clip(lower=0) * 2.25
        + recs["Gap Covered %"] * 0.08
    ).round(2)

    recs["Value Efficiency"] = (
        recs["Quality Score"] / ((recs["Transfer Cost"] / 1_000_000) + 1)
    ).round(3)

    recs["Budget Share %"] = (
        recs["Transfer Cost"] / total_budget * 100
    ).round(1)

    return recs


def score_single_player_budget_plan(recs: pd.DataFrame, total_budget: float) -> pd.DataFrame:
    recs = recs.copy()

    recs["Price Range Fit"] = (
        100 - ((recs["Transfer Cost"] / total_budget).clip(upper=1) * 10)
    ).round(1)

    recs["Budget Plan Score"] = (
        recs["Quality Score"] * 0.82
        + recs["Value Efficiency"] * 2.25
        + recs["Price Range Fit"] * 0.05
        + recs["Squad Gap Value"].clip(lower=0) * 1.75
    ).round(2)

    return recs.sort_values(
        ["Budget Plan Score", "Quality Score", "Recommendation Score"],
        ascending=[False, False, False],
    )


def score_multi_player_budget_plan(recs: pd.DataFrame, total_budget: float, players_to_buy: int) -> pd.DataFrame:
    recs = recs.copy()

    target_price = total_budget / max(players_to_buy, 1)

    recs["Target Price"] = target_price

    recs["Price Range Fit"] = (
        100 - (
            (recs["Transfer Cost"] - target_price).abs()
            / max(target_price, 1)
            * 45
        )
    ).clip(lower=0, upper=100).round(1)

    recs["Budget Plan Score"] = (
        recs["Quality Score"] * 0.68
        + recs["Value Efficiency"] * 4.50
        + recs["Price Range Fit"] * 0.12
        + recs["Squad Gap Value"].clip(lower=0) * 2.00
        - recs["Gap Priority Order"] * 0.35
    ).round(2)

    return recs.sort_values(
        ["Budget Plan Score", "Quality Score", "Recommendation Score"],
        ascending=[False, False, False],
    )


def build_dynamic_transfer_budget_plan(
    recommendations: pd.DataFrame,
    total_budget: float,
    players_to_buy: int,
) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    from itertools import combinations

    total_budget = float(total_budget)
    players_to_buy = int(players_to_buy)

    candidates = prepare_budget_candidates(recommendations, total_budget)

    if candidates.empty:
        summary = {
            "Total Budget": total_budget,
            "Total Spend": 0,
            "Remaining Budget": total_budget,
            "Players Selected": 0,
            "Message": "No affordable players found inside this budget.",
        }

        return pd.DataFrame(), pd.DataFrame(), summary

    # One-player mode: pick the best single player under the full budget.
    if players_to_buy <= 1:
        ranked = score_single_player_budget_plan(candidates, total_budget)
        plan = ranked.head(1).copy()
        plan.insert(0, "Buy Order", 1)

    # Combination mode for 2-4 players.
    elif players_to_buy <= 4:
        ranked = score_multi_player_budget_plan(candidates, total_budget, players_to_buy)

        # Keep this pool tight enough to be fast but deep enough to find strong combinations.
        pool_size = 70 if players_to_buy <= 3 else 55
        pool = ranked.head(pool_size).copy().reset_index(drop=True)

        best_combo = None
        best_combo_score = -1

        for combo_indexes in combinations(range(len(pool)), players_to_buy):
            combo = pool.iloc[list(combo_indexes)].copy()
            total_cost = float(combo["Transfer Cost"].sum())

            if total_cost > total_budget:
                continue

            unique_gaps = combo["Recommended For"].astype(str).nunique()
            avg_quality = float(combo["Quality Score"].mean())
            avg_plan_score = float(combo["Budget Plan Score"].mean())
            avg_playstyle = float(combo["Playstyle Fit"].mean())
            spend_ratio = total_cost / total_budget

            # This rewards quality first, then need coverage, then sensible spend.
            combo_score = (
                avg_plan_score * 1.00
                + avg_quality * 0.55
                + avg_playstyle * 0.15
                + unique_gaps * 5.00
                + spend_ratio * 4.00
            )

            if combo_score > best_combo_score:
                best_combo_score = combo_score
                best_combo = combo.copy()

        if best_combo is None:
            # Fallback: greedy if no exact combo works.
            selected = []
            remaining = total_budget
            used_players = set()

            for _, row in ranked.iterrows():
                player_key = (str(row["Player"]), str(row["Club"]))

                if player_key in used_players:
                    continue

                if float(row["Transfer Cost"]) <= remaining:
                    selected.append(row)
                    used_players.add(player_key)
                    remaining -= float(row["Transfer Cost"])

                if len(selected) >= players_to_buy:
                    break

            plan = pd.DataFrame(selected)
        else:
            plan = best_combo

        plan = plan.sort_values(
            ["Gap Priority Order", "Budget Plan Score"],
            ascending=[True, False],
        ).reset_index(drop=True)

        plan.insert(0, "Buy Order", plan.index + 1)

    # Larger plans: use a dynamic greedy approach.
    else:
        ranked = score_multi_player_budget_plan(candidates, total_budget, players_to_buy)
        selected = []
        remaining = total_budget
        used_players = set()

        for _, row in ranked.iterrows():
            player_key = (str(row["Player"]), str(row["Club"]))

            if player_key in used_players:
                continue

            if float(row["Transfer Cost"]) <= remaining:
                selected.append(row)
                used_players.add(player_key)
                remaining -= float(row["Transfer Cost"])

            if len(selected) >= players_to_buy:
                break

        plan = pd.DataFrame(selected).reset_index(drop=True)

        if not plan.empty:
            plan.insert(0, "Buy Order", plan.index + 1)

    if plan.empty:
        summary = {
            "Total Budget": total_budget,
            "Total Spend": 0,
            "Remaining Budget": total_budget,
            "Players Selected": 0,
            "Message": "Could not build a plan under this budget.",
        }

        return pd.DataFrame(), candidates, summary

    plan["Cumulative Spend"] = plan["Transfer Cost"].cumsum()
    plan["Cumulative Spend Display"] = plan["Cumulative Spend"].apply(format_money)
    plan["Budget Remaining After Deal"] = total_budget - plan["Cumulative Spend"]
    plan["Budget Remaining Display"] = plan["Budget Remaining After Deal"].apply(format_money)

    total_spend = float(plan["Transfer Cost"].sum())

    summary = {
        "Total Budget": total_budget,
        "Total Spend": total_spend,
        "Remaining Budget": total_budget - total_spend,
        "Players Selected": len(plan),
        "Average Quality Score": round(float(plan["Quality Score"].mean()), 1),
        "Average Playstyle Fit": round(float(plan["Playstyle Fit"].mean()), 1),
        "Average Recommendation Score": round(float(plan["Recommendation Score"].mean()), 1),
        "Message": "Dynamic budget plan created.",
    }

    affordable_options = candidates.sort_values(
        ["Quality Score", "Recommendation Score", "Value Efficiency"],
        ascending=[False, False, False],
    ).head(50)

    return plan, affordable_options, summary
'''

if "def build_dynamic_transfer_budget_plan(" not in text:
    marker = "@st.cache_data"

    if marker in text:
        text = text.replace(marker, dynamic_engine + "\n\n" + marker, 1)
    else:
        marker = "# ============================================================\n# STREAMLIT APP"
        if marker in text:
            text = text.replace(marker, dynamic_engine + "\n\n" + marker, 1)
        else:
            text += "\n\n" + dynamic_engine


# ============================================================
# 4. REPLACE TRANSFER BUDGET TAB CONTENT
# ============================================================

new_budget_view = r'''
with tab5:
    st.subheader("Dynamic Transfer Budget Plan")

    source_recommendations = (
        budget_recommendations
        if "budget_recommendations" in globals()
        else recommendations
    )

    budget_plan, affordable_options, budget_summary = build_dynamic_transfer_budget_plan(
        recommendations=source_recommendations,
        total_budget=float(transfer_budget),
        players_to_buy=int(players_to_buy),
    )

    st.write(
        f"""
        Build a smart spending plan for **{your_club}** with **{format_money(transfer_budget)}**
        to buy **{players_to_buy} player(s)** for **{target_competition}** using **{playstyle}**.
        """
    )

    b1, b2, b3, b4 = st.columns(4)

    b1.metric("Transfer Budget", format_money(budget_summary["Total Budget"]))
    b2.metric("Planned Spend", format_money(budget_summary["Total Spend"]))
    b3.metric("Budget Left", format_money(budget_summary["Remaining Budget"]))
    b4.metric("Players Selected", budget_summary["Players Selected"])

    if budget_plan.empty:
        st.warning(budget_summary["Message"])
    else:
        if int(players_to_buy) == 1:
            st.success(
                f"Best single-player move: buy **{budget_plan.iloc[0]['Player']}** "
                f"for about **{budget_plan.iloc[0]['Transfer Cost Display']}**."
            )
        else:
            st.success(
                f"Recommended {len(budget_plan)}-player plan: spend "
                f"**{format_money(budget_summary['Total Spend'])}** and keep "
                f"**{format_money(budget_summary['Remaining Budget'])}**."
            )

        plan_cols = [
            "Buy Order",
            "Player",
            "Age",
            "Club",
            "League",
            "Position",
            "Recommended For",
            "Transfer Cost Display",
            "Budget Share %",
            "Cumulative Spend Display",
            "Budget Remaining Display",
            "Quality Score",
            "Recommendation Score",
            "Budget Plan Score",
            "Value Efficiency",
            "Candidate Category Rating",
            "Playstyle Fit",
            "Upgrade Over Current Area",
            "Gap Covered %",
            "Why Recommended",
        ]

        plan_cols = [col for col in plan_cols if col in budget_plan.columns]

        st.markdown("### Recommended Spending Plan")

        st.dataframe(
            dynamic_safe_df(budget_plan[plan_cols]),
            use_container_width=True,
            height=520,
        )

        st.markdown("### What This Plan Fixes")

        if "Recommended For" in budget_plan.columns:
            gaps_hit = (
                budget_plan["Recommended For"]
                .astype(str)
                .value_counts()
                .reset_index()
            )

            gaps_hit.columns = ["Squad Gap Addressed", "Players Bought"]

            st.dataframe(
                dynamic_safe_df(gaps_hit),
                use_container_width=True,
                height=220,
            )

        st.markdown("### Best Affordable Alternatives In Your Budget")

        alt_cols = [
            "Player",
            "Age",
            "Club",
            "League",
            "Position",
            "Recommended For",
            "Transfer Cost Display",
            "Budget Share %",
            "Quality Score",
            "Recommendation Score",
            "Value Efficiency",
            "Playstyle Fit",
            "Upgrade Over Current Area",
        ]

        alt_cols = [col for col in alt_cols if col in affordable_options.columns]

        st.dataframe(
            dynamic_safe_df(affordable_options[alt_cols]),
            use_container_width=True,
            height=450,
        )

        st.download_button(
            label="Download Dynamic Transfer Budget Plan CSV",
            data=dynamic_safe_df(budget_plan).to_csv(index=False).encode("utf-8"),
            file_name=f"{your_club.replace(' ', '_')}_dynamic_transfer_budget_plan.csv",
            mime="text/csv",
        )

        st.markdown(
            """
            ### Dynamic Logic

            - **1 player selected** = finds the best single player under your full budget.
            - **2-4 players selected** = searches for the best combination under the budget.
            - **5+ players selected** = uses a fast greedy plan focused on quality, value, and squad needs.
            - The plan prioritizes your biggest squad gaps, but it will still choose elite quality if the budget allows it.
            """
        )
'''

if "with tab5:" in text:
    start = text.find("with tab5:")

    possible_ends = [
        text.find("\nif tactic:", start),
        text.find("\nif save_page_memory", start),
        text.find("\nsave_page_memory(__file__)", start),
    ]

    possible_ends = [end for end in possible_ends if end != -1]

    if possible_ends:
        end = min(possible_ends)
        text = text[:start] + new_budget_view + "\n" + text[end:]
    else:
        text = text[:start] + new_budget_view

elif 'elif view == "Transfer Budget Plan":' in text:
    start = text.find('elif view == "Transfer Budget Plan":')
    end = text.find("\nif save_page_memory", start)

    replacement = new_budget_view.replace("with tab5:", 'elif view == "Transfer Budget Plan":')

    if end != -1:
        text = text[:start] + replacement + "\n" + text[end:]
    else:
        text = text[:start] + replacement

else:
    raise SystemExit("Could not find Transfer Budget Plan tab/view to replace.")

path.write_text(text, encoding="utf-8")
print("Dynamic transfer budget planner patched successfully.")
