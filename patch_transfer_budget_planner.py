from pathlib import Path

path = Path("app/pages/11_Recommended_Signings.py")
text = path.read_text(encoding="utf-8")

budget_helper = r'''

# ============================================================
# TRANSFER BUDGET PLANNER
# ============================================================

def format_money(value) -> str:
    try:
        value = float(value)
    except Exception:
        return "Unknown"

    if pd.isna(value):
        return "Unknown"

    return f"£{value:,.0f}"


def build_transfer_budget_plan(
    recommendations: pd.DataFrame,
    total_budget: float,
    players_to_buy: int,
) -> tuple[pd.DataFrame, dict]:
    if recommendations.empty:
        return pd.DataFrame(), {
            "Total Budget": total_budget,
            "Total Spend": 0,
            "Remaining Budget": total_budget,
            "Players Selected": 0,
            "Message": "No recommendations available.",
        }

    recs = recommendations.copy()

    if "Estimated Value Clean" not in recs.columns:
        return pd.DataFrame(), {
            "Total Budget": total_budget,
            "Total Spend": 0,
            "Remaining Budget": total_budget,
            "Players Selected": 0,
            "Message": "No clean transfer value column found. Rebuild your cache or check value cleaner.",
        }

    recs["Transfer Cost"] = pd.to_numeric(recs["Estimated Value Clean"], errors="coerce")

    # Keep only players with a known price and within the total budget.
    recs = recs[
        recs["Transfer Cost"].notna()
        & (recs["Transfer Cost"] >= 0)
        & (recs["Transfer Cost"] <= total_budget)
    ].copy()

    if recs.empty:
        return pd.DataFrame(), {
            "Total Budget": total_budget,
            "Total Spend": 0,
            "Remaining Budget": total_budget,
            "Players Selected": 0,
            "Message": "No affordable players found inside this budget.",
        }

    recs = recs.drop_duplicates(subset=["Player", "Club"], keep="first")

    for col in [
        "Recommendation Score",
        "Upgrade Over Current Area",
        "Gap Covered %",
        "Squad Gap Value",
        "Gap Priority Order",
    ]:
        if col not in recs.columns:
            recs[col] = 0

        recs[col] = pd.to_numeric(recs[col], errors="coerce").fillna(0)

    # Higher = better. This balances quality, need, upgrade impact, and affordability.
    recs["Budget Efficiency"] = (
        recs["Recommendation Score"] * 0.55
        + recs["Upgrade Over Current Area"].clip(lower=0) * 1.50
        + recs["Gap Covered %"] * 0.20
        + recs["Squad Gap Value"].clip(lower=0) * 2.00
    ) / ((recs["Transfer Cost"] / 1_000_000) + 1)

    recs["Budget Plan Score"] = (
        recs["Recommendation Score"] * 0.50
        + recs["Upgrade Over Current Area"].clip(lower=0) * 1.75
        + recs["Gap Covered %"] * 0.20
        + recs["Squad Gap Value"].clip(lower=0) * 2.25
        + recs["Budget Efficiency"] * 1.50
    ).round(2)

    recs = recs.sort_values(
        ["Gap Priority Order", "Budget Plan Score", "Recommendation Score"],
        ascending=[True, False, False],
    )

    selected_rows = []
    selected_players = set()
    remaining_budget = float(total_budget)

    gap_order = (
        recs[["Recommended For", "Gap Priority Order"]]
        .drop_duplicates()
        .sort_values("Gap Priority Order")
        ["Recommended For"]
        .tolist()
    )

    # First pass: try to buy one player for each major squad gap.
    for gap in gap_order:
        if len(selected_rows) >= players_to_buy:
            break

        pool = recs[
            (recs["Recommended For"].astype(str) == str(gap))
            & (recs["Transfer Cost"] <= remaining_budget)
        ].copy()

        pool = pool[
            ~pool.apply(lambda row: (str(row["Player"]), str(row["Club"])) in selected_players, axis=1)
        ]

        if pool.empty:
            continue

        pick = pool.sort_values(
            ["Budget Plan Score", "Recommendation Score", "Budget Efficiency"],
            ascending=[False, False, False],
        ).iloc[0]

        selected_rows.append(pick)
        selected_players.add((str(pick["Player"]), str(pick["Club"])))
        remaining_budget -= float(pick["Transfer Cost"])

    # Second pass: fill remaining slots with the best affordable players.
    while len(selected_rows) < players_to_buy:
        pool = recs[recs["Transfer Cost"] <= remaining_budget].copy()

        pool = pool[
            ~pool.apply(lambda row: (str(row["Player"]), str(row["Club"])) in selected_players, axis=1)
        ]

        if pool.empty:
            break

        pick = pool.sort_values(
            ["Budget Plan Score", "Recommendation Score", "Budget Efficiency"],
            ascending=[False, False, False],
        ).iloc[0]

        selected_rows.append(pick)
        selected_players.add((str(pick["Player"]), str(pick["Club"])))
        remaining_budget -= float(pick["Transfer Cost"])

    if not selected_rows:
        return pd.DataFrame(), {
            "Total Budget": total_budget,
            "Total Spend": 0,
            "Remaining Budget": total_budget,
            "Players Selected": 0,
            "Message": "Could not build a plan under this budget.",
        }

    plan = pd.DataFrame(selected_rows).reset_index(drop=True)
    plan.insert(0, "Buy Order", plan.index + 1)

    plan["Transfer Cost Display"] = plan["Transfer Cost"].apply(format_money)
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
        "Average Recommendation Score": round(float(plan["Recommendation Score"].mean()), 1),
        "Average Playstyle Fit": round(float(plan["Playstyle Fit"].mean()), 1) if "Playstyle Fit" in plan.columns else 0,
        "Average Upgrade": round(float(plan["Upgrade Over Current Area"].mean()), 1) if "Upgrade Over Current Area" in plan.columns else 0,
        "Message": "Budget plan created.",
    }

    return plan, summary

'''

if "def build_transfer_budget_plan(" not in text:
    marker = "@st.cache_data(show_spinner=\"Building recommended signing model...\")"
    text = text.replace(marker, budget_helper + "\n\n" + marker, 1)

old_sidebar = '''if use_value_cap:
    max_value_millions = st.sidebar.number_input(
        "Max Estimated Value £M",
        min_value=0.0,
        value=50.0,
        step=5.0,
    )
'''

new_sidebar = '''if use_value_cap:
    max_value_millions = st.sidebar.number_input(
        "Max Estimated Value £M",
        min_value=0.0,
        value=50.0,
        step=5.0,
    )

st.sidebar.header("Transfer Budget Planner")

transfer_budget = st.sidebar.number_input(
    "Transfer Budget",
    min_value=0,
    value=150_000_000,
    step=5_000_000,
    format="%d",
)

players_to_buy = st.sidebar.slider(
    "Players To Buy",
    min_value=1,
    max_value=10,
    value=4,
    step=1,
)

budget_pool_per_gap = st.sidebar.slider(
    "Budget Options Per Squad Gap",
    min_value=5,
    max_value=50,
    value=20,
    step=5,
)
'''

if old_sidebar in text and "Transfer Budget Planner" not in text:
    text = text.replace(old_sidebar, new_sidebar, 1)

old_recs = '''recommendations = build_signing_recommendations(
    df=df,
    team_ratings=team_ratings,
    your_club=your_club,
    target_competition=target_competition,
    playstyle=playstyle,
    benchmark=benchmark,
    max_age=int(max_age),
    max_value_millions=max_value_millions,
    top_n=int(top_n),
    search_pool=search_pool,
)
'''

new_recs = '''recommendations = build_signing_recommendations(
    df=df,
    team_ratings=team_ratings,
    your_club=your_club,
    target_competition=target_competition,
    playstyle=playstyle,
    benchmark=benchmark,
    max_age=int(max_age),
    max_value_millions=max_value_millions,
    top_n=int(top_n),
    search_pool=search_pool,
)

budget_recommendations = build_signing_recommendations(
    df=df,
    team_ratings=team_ratings,
    your_club=your_club,
    target_competition=target_competition,
    playstyle=playstyle,
    benchmark=benchmark,
    max_age=int(max_age),
    max_value_millions=None,
    top_n=int(budget_pool_per_gap),
    search_pool=search_pool,
)
'''

if old_recs in text and "budget_recommendations = build_signing_recommendations" not in text:
    text = text.replace(old_recs, new_recs, 1)

old_tabs = '''tab1, tab2, tab3, tab4 = st.tabs(
    [
        "Top Recommended Signings",
        "Squad Gaps",
        "Benchmark Teams",
        "All Candidate Scores",
    ]
)
'''

new_tabs = '''tab1, tab2, tab3, tab4, tab5 = st.tabs(
    [
        "Top Recommended Signings",
        "Squad Gaps",
        "Benchmark Teams",
        "All Candidate Scores",
        "Transfer Budget Plan",
    ]
)
'''

if old_tabs in text:
    text = text.replace(old_tabs, new_tabs, 1)

tab5_block = r'''
with tab5:
    st.subheader("Transfer Budget Plan")

    st.write(
        f"""
        Build a transfer plan for **{your_club}** with a budget of **{format_money(transfer_budget)}**
        and **{players_to_buy} player(s)** to target **{target_competition}** using
        **{playstyle}**.
        """
    )

    budget_plan, budget_summary = build_transfer_budget_plan(
        recommendations=budget_recommendations,
        total_budget=float(transfer_budget),
        players_to_buy=int(players_to_buy),
    )

    b1, b2, b3, b4 = st.columns(4)

    b1.metric("Transfer Budget", format_money(budget_summary["Total Budget"]))
    b2.metric("Planned Spend", format_money(budget_summary["Total Spend"]))
    b3.metric("Budget Left", format_money(budget_summary["Remaining Budget"]))
    b4.metric("Players Selected", budget_summary["Players Selected"])

    if budget_plan.empty:
        st.warning(budget_summary["Message"])
    else:
        st.success(
            f"Recommended plan: buy {budget_summary['Players Selected']} player(s), "
            f"spend {format_money(budget_summary['Total Spend'])}, "
            f"and keep {format_money(budget_summary['Remaining Budget'])} remaining."
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
            "Cumulative Spend Display",
            "Budget Remaining Display",
            "Recommendation Score",
            "Budget Plan Score",
            "Budget Efficiency",
            "Candidate Category Rating",
            "Playstyle Fit",
            "Upgrade Over Current Area",
            "Gap Covered %",
            "Why Recommended",
        ]

        plan_cols = [col for col in plan_cols if col in budget_plan.columns]

        st.dataframe(
            make_streamlit_safe_df(budget_plan[plan_cols]),
            use_container_width=True,
            height=520,
        )

        st.markdown("### Spending Logic")

        gaps_hit = (
            budget_plan["Recommended For"]
            .astype(str)
            .value_counts()
            .reset_index()
        )

        gaps_hit.columns = ["Squad Gap Addressed", "Players Bought"]

        st.dataframe(
            make_streamlit_safe_df(gaps_hit),
            use_container_width=True,
            height=220,
        )

        st.download_button(
            label="Download Transfer Budget Plan CSV",
            data=make_streamlit_safe_df(budget_plan).to_csv(index=False).encode("utf-8"),
            file_name=f"{your_club.replace(' ', '_')}_transfer_budget_plan.csv",
            mime="text/csv",
        )

        st.markdown(
            """
            ### How the plan works

            The planner tries to:
            1. Fix your biggest squad gaps first.
            2. Stay inside your budget.
            3. Match your selected playstyle.
            4. Avoid buying duplicate players.
            5. Balance quality, upgrade impact, and value for money.
            """
        )

'''

if "with tab5:" not in text:
    marker = "\nif tactic:\n"
    if marker in text:
        text = text.replace(marker, "\n" + tab5_block + "\nif tactic:\n", 1)
    else:
        marker = "\nsave_page_memory(__file__)"
        text = text.replace(marker, "\n" + tab5_block + marker, 1)

path.write_text(text, encoding="utf-8")
print("Added Transfer Budget Plan feature to Recommended Signings.")
