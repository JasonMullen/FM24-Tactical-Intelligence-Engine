from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from fm_engine.fast_data import get_file_signature, list_saved_files, load_fm_file_cached
from fm_engine.signing_engine import (
    CATEGORY_PROFILES,
    PLAYSTYLE_PROFILES,
    add_positions,
    add_scores,
    benchmark_for_goal,
    build_dynamic_budget_plan,
    build_recommendations_by_gap,
    build_sell_upgrade_table,
    build_team_ratings,
    club_realism_context,
    find_column,
    format_money,
    make_safe_df,
    parse_budget_input,
    squad_gaps,
)
from fm_engine.manual_spend_planner import build_manual_spend_budget_plan
from fm_engine.recommendation_filters import apply_recommendation_filters, choose_focused_gaps
from fm_engine.squad_impact_simulator import (
    build_all_database_add_options,
    build_current_squad_options,
    build_recommended_add_options,
    simulate_squad_impact,
)

try:
    from fm_engine.value_cleaner import add_clean_estimated_value_columns
except Exception:
    add_clean_estimated_value_columns = None

try:
    from fm_engine.ui_memory import init_page_memory, save_page_memory
except Exception:
    init_page_memory = None
    save_page_memory = None


st.set_page_config(
    page_title="Recommended Signings",
    page_icon="📝",
    layout="wide",
)

if init_page_memory:
    init_page_memory(__file__)


@st.cache_data(show_spinner="Building realistic signing model...")
def load_model(path_text: str, mtime: float, size: int, min_minutes: int):
    raw = load_fm_file_cached(path_text, mtime, size).copy()

    if add_clean_estimated_value_columns:
        raw = add_clean_estimated_value_columns(raw)

    raw = raw.dropna(axis=0, how="all").dropna(axis=1, how="all").drop_duplicates()

    df = add_positions(raw)
    df = add_scores(df, min_minutes)
    team_ratings = build_team_ratings(df)

    return df, team_ratings


st.title("Recommended Signings")

st.write(
    "Live realistic recommendations based on club strength, target goal, transfer budget, playstyle, squad gaps, and underperformers."
)

saved_files = list_saved_files()

if not saved_files:
    st.info("Upload your FM24 database on the main dashboard first.")
    st.stop()

selected_file = st.sidebar.selectbox(
    "Choose Saved Database",
    saved_files,
    format_func=lambda path: path.name,
    key="rec_saved_database",
)

min_minutes = st.sidebar.number_input(
    "Minimum Minutes For Statistical Fit",
    min_value=0,
    value=300,
    step=100,
    key="rec_min_minutes",
)

path_text, mtime, size = get_file_signature(selected_file)
df, team_ratings = load_model(path_text, mtime, size, int(min_minutes))

if team_ratings.empty:
    st.error("No team ratings could be built. Make sure your database has Club and Position columns.")
    st.stop()

club_options = sorted(team_ratings["Club"].astype(str).unique().tolist())

st.sidebar.header("Mission")

your_club = st.sidebar.selectbox(
    "Your Club",
    club_options,
    key="rec_your_club",
)

target_goal = st.sidebar.selectbox(
    "Target Goal",
    [
        "Win Domestic League",
        "Win UEFA Champions League",
        "Win UEFA Europa League",
        "Win Copa Libertadores",
    ],
    key="rec_target_goal",
)

playstyle = st.sidebar.selectbox(
    "Tactic / Playstyle",
    list(PLAYSTYLE_PROFILES.keys()),
    key="rec_playstyle",
)

realism_mode = st.sidebar.selectbox(
    "Realism Mode",
    ["Balanced", "Strict", "Aggressive"],
    index=0,
    key="rec_realism_mode",
)

top_per_gap = st.sidebar.slider(
    "Top Options Per Squad Gap",
    min_value=3,
    max_value=25,
    value=5,
    step=1,
    key="rec_top_per_gap",
)

search_pool = st.sidebar.selectbox(
    "Candidate Search Pool",
    ["Entire Database", "Same League Only", "Outside Current League"],
    key="rec_search_pool",
)

max_age = st.sidebar.slider(
    "Max Age",
    min_value=16,
    max_value=40,
    value=30,
    step=1,
    key="rec_max_age",
)

use_value_cap = st.sidebar.checkbox(
    "Use Max Player Value Cap",
    value=False,
    key="rec_use_value_cap",
)

max_value = None

if use_value_cap:
    max_value_text = st.sidebar.text_input(
        "Max Player Value",
        value="100M",
        key="rec_max_value_text",
    )
    max_value = parse_budget_input(max_value_text)

st.sidebar.header("Transfer Budget Planner")

budget_text = st.sidebar.text_input(
    "Transfer Budget",
    value="150,000,000",
    placeholder="Example: 150M or 150,000,000",
    key="rec_transfer_budget_text",
)

transfer_budget = parse_budget_input(budget_text)

st.sidebar.caption(f"Budget read as: {format_money(transfer_budget)}")

planned_spend_text = st.sidebar.text_input(
    "Planned Spend Target",
    value="100,000,000",
    placeholder="Example: 100M or 100,000,000",
    key="rec_planned_spend_target_text",
)

planned_spend_target = parse_budget_input(planned_spend_text)

if planned_spend_target <= 0:
    planned_spend_target = transfer_budget

planned_spend_target = min(float(planned_spend_target), float(transfer_budget))

st.sidebar.caption(f"Planned spend target: {format_money(planned_spend_target)}")

spend_strategy = st.sidebar.selectbox(
    "Spending Strategy",
    ["Conservative", "Balanced", "Aggressive"],
    index=1,
    key="rec_spending_strategy",
)

st.sidebar.caption(
    "Conservative saves money. Balanced uses the budget intelligently. Aggressive pushes closer to the planned spend target."
)

players_to_buy = st.sidebar.slider(
    "Players To Buy",
    min_value=1,
    max_value=10,
    value=3,
    step=1,
    key="rec_players_to_buy",
)

budget_pool_per_gap = st.sidebar.slider(
    "Budget Options Per Gap",
    min_value=5,
    max_value=50,
    value=25,
    step=5,
    key="rec_budget_pool_per_gap",
)

if st.sidebar.button("Clear Signing Recommendation Cache", key="rec_clear_cache"):
    load_model.clear()
    st.rerun()

benchmark, benchmark_teams, benchmark_explanation = benchmark_for_goal(team_ratings, your_club, target_goal)
context = club_realism_context(team_ratings, your_club, target_goal, planned_spend_target)
gaps = squad_gaps(team_ratings, your_club, benchmark)


# ============================================================
# SQUAD GAP + PRICE RANGE TARGETING
# ============================================================

st.sidebar.header("Squad Gap Targeting")

gap_focus_mode = st.sidebar.selectbox(
    "Squad Gap Focus",
    [
        "Auto: Critical/Important gaps only",
        "Auto: Top N biggest gaps",
        "Manual: choose squad areas",
    ],
    index=0,
    key="rec_gap_focus_mode",
)

minimum_gap_to_target = st.sidebar.number_input(
    "Minimum Gap To Target",
    min_value=0.0,
    max_value=50.0,
    value=4.0,
    step=0.5,
    key="rec_minimum_gap_to_target",
)

top_gap_count = st.sidebar.slider(
    "Number Of Squad Gaps To Target",
    min_value=1,
    max_value=len(CATEGORY_PROFILES),
    value=3,
    step=1,
    key="rec_top_gap_count",
)

all_gap_options = gaps["Squad Area"].dropna().astype(str).tolist() if not gaps.empty else list(CATEGORY_PROFILES.keys())

default_focused_gaps = choose_focused_gaps(
    gaps=gaps,
    mode="Auto: Critical/Important gaps only",
    minimum_gap=minimum_gap_to_target,
    top_n=top_gap_count,
    manual_gaps=[],
)

manual_gap_choices = st.sidebar.multiselect(
    "Manual Squad Areas",
    all_gap_options,
    default=[gap for gap in default_focused_gaps if gap in all_gap_options],
    key="rec_manual_gap_choices",
)

focused_gaps = choose_focused_gaps(
    gaps=gaps,
    mode=gap_focus_mode,
    minimum_gap=minimum_gap_to_target,
    top_n=top_gap_count,
    manual_gaps=manual_gap_choices,
)

st.sidebar.caption("Targeting: " + (", ".join(focused_gaps) if focused_gaps else "No squad gaps selected"))

st.sidebar.header("Player Price Range")

price_range_mode = st.sidebar.selectbox(
    "Price Range Mode",
    [
        "Auto from planned spend",
        "Manual",
    ],
    index=0,
    key="rec_price_range_mode",
)

per_player_spend_target = float(planned_spend_target) / max(int(players_to_buy), 1)

if spend_strategy == "Aggressive":
    auto_min_price = per_player_spend_target * 0.65
    auto_max_price = per_player_spend_target * 2.00
elif spend_strategy == "Conservative":
    auto_min_price = per_player_spend_target * 0.35
    auto_max_price = per_player_spend_target * 1.25
else:
    auto_min_price = per_player_spend_target * 0.50
    auto_max_price = per_player_spend_target * 1.60

auto_min_price = max(auto_min_price, 0)
auto_max_price = min(auto_max_price, float(planned_spend_target))

if price_range_mode == "Auto from planned spend":
    player_min_price = float(auto_min_price)
    player_max_price = float(auto_max_price)

    st.sidebar.caption(
        f"Auto range: {format_money(player_min_price)} to {format_money(player_max_price)} per player"
    )
else:
    min_price_text = st.sidebar.text_input(
        "Minimum Player Price",
        value=f"{int(auto_min_price):,}",
        placeholder="Example: 10M or 10,000,000",
        key="rec_min_player_price_text",
    )

    max_price_text = st.sidebar.text_input(
        "Maximum Player Price",
        value=f"{int(auto_max_price):,}",
        placeholder="Example: 80M or 80,000,000",
        key="rec_max_player_price_text",
    )

    player_min_price = parse_budget_input(min_price_text)
    player_max_price = parse_budget_input(max_price_text)

    if player_max_price <= 0:
        player_max_price = float(planned_spend_target)

    if player_min_price > player_max_price:
        player_min_price, player_max_price = player_max_price, player_min_price

    st.sidebar.caption(
        f"Manual range: {format_money(player_min_price)} to {format_money(player_max_price)} per player"
    )


recommendations = build_recommendations_by_gap(
    df=df,
    team_ratings=team_ratings,
    your_club=your_club,
    target_goal=target_goal,
    playstyle=playstyle,
    benchmark=benchmark,
    context=context,
    transfer_budget=planned_spend_target,
    players_to_buy=players_to_buy,
    max_age=max_age,
    max_value=max_value,
    top_per_gap=top_per_gap,
    search_pool=search_pool,
    realism_mode=realism_mode,
)

budget_recommendations = build_recommendations_by_gap(
    df=df,
    team_ratings=team_ratings,
    your_club=your_club,
    target_goal=target_goal,
    playstyle=playstyle,
    benchmark=benchmark,
    context=context,
    transfer_budget=planned_spend_target,
    players_to_buy=players_to_buy,
    max_age=max_age,
    max_value=None,
    top_per_gap=budget_pool_per_gap,
    search_pool=search_pool,
    realism_mode=realism_mode,
)


# Enforce selected squad gaps and player price range.
recommendations = apply_recommendation_filters(
    recs=recommendations,
    focused_gaps=focused_gaps,
    min_price=player_min_price,
    max_price=player_max_price,
)

budget_recommendations = apply_recommendation_filters(
    recs=budget_recommendations,
    focused_gaps=focused_gaps,
    min_price=player_min_price,
    max_price=player_max_price,
)

sell_df, replacement_df = build_sell_upgrade_table(
    df=df,
    your_club=your_club,
    playstyle=playstyle,
    recs=budget_recommendations,
)

your_row = team_ratings[team_ratings["Club"].astype(str) == str(your_club)].iloc[0]

st.subheader(f"Mission: {your_club} — {target_goal}")

m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Team Rating", f"{float(your_row['Overall Team Rating']):.1f}")
m2.metric("Club Rank", f"{context['Club Rank']}")
m3.metric("Club Band", context["Club Band"])
m4.metric("Spend Target", format_money(planned_spend_target))
m5.metric("Players To Buy", players_to_buy)

st.info(benchmark_explanation)
st.warning(context["Realistic Goal"])

st.caption(
    f"Active filters → Squad gaps: {', '.join(focused_gaps)} | "
    f"Player price range: {format_money(player_min_price)} to {format_money(player_max_price)}"
)


view = st.radio(
    "Recommended Signings View",
    [
        "Dynamic Budget Plan",
        "Squad Impact Simulator",
        "Top Recommended Signings",
        "Sell / Upgrade Candidates",
        "Realism Context",
        "Squad Gaps",
        "Benchmark Teams",
        "All Candidate Scores",
    ],
    horizontal=True,
    key="rec_view",
)

if view == "Dynamic Budget Plan":
    st.subheader("Dynamic Transfer Budget Plan")

    st.write(
        f"Build a realistic spending plan for **{your_club}** with **{format_money(transfer_budget)} total budget** "
        f"and a manual planned spend target of **{format_money(planned_spend_target)}** "
        f"to buy **{players_to_buy} player(s)** for **{target_goal}** using **{playstyle}**."
    )

    plan, alternatives, summary = build_dynamic_budget_plan(
        budget_recommendations,
        planned_spend_target,
        players_to_buy,
    )

    total_budget_left = max(float(transfer_budget) - float(summary["spend"]), 0)
    spend_limit_left = max(float(planned_spend_target) - float(summary["spend"]), 0)

    b1, b2, b3, b4, b5 = st.columns(5)
    b1.metric("Transfer Budget", format_money(transfer_budget))
    b2.metric("Spend Target", format_money(planned_spend_target))
    b3.metric("Planned Spend", format_money(summary["spend"]))
    b4.metric("Total Budget Left", format_money(total_budget_left))
    b5.metric("Players Selected", len(plan))

    st.caption(f"Spend limit left: {format_money(spend_limit_left)}")

    if plan.empty:
        st.warning(summary["message"])
        st.info(
            "If no plan appears, your selected squad gaps or player price range may be too restrictive. "
            "Try widening the price range, lowering Minimum Gap To Target, or switching Squad Gap Focus to Manual."
        )

        if budget_recommendations.empty:
            st.error("No recommendation pool was built. Try Aggressive realism mode, higher max age, or Entire Database.")
        else:
            st.caption(f"Recommendation pool exists: {len(budget_recommendations)} players. The issue is price/budget filtering.")
    else:
        if players_to_buy == 1:
            st.success(
                f"Best single-player move: buy **{plan.iloc[0]['Player']}** "
                f"for about **{plan.iloc[0]['Transfer Cost Display']}**."
            )
        else:
            st.success(
                f"Recommended {len(plan)}-player plan: spend **{format_money(summary['spend'])}** "
                f"out of your manual planned spend target of **{format_money(planned_spend_target)}**. "
                f"Total budget left: **{format_money(total_budget_left)}**."
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
            "Total Budget Remaining Display",
            "Planned Spend Remaining Display",
            "Quality Score",
            "Recommendation Score",
            "Realism Fit",
            "Budget Plan Score",
            "Value Efficiency",
            "Playstyle Fit",
            "Upgrade Over Current Area",
            "Why Recommended",
        ]

        plan_cols = [col for col in plan_cols if col in plan.columns]

        st.markdown("### Recommended Spending Plan")
        st.dataframe(make_safe_df(plan[plan_cols]), use_container_width=True, height=560)

        if "Recommended For" in plan.columns:
            st.markdown("### Squad Areas Fixed")
            hit = plan["Recommended For"].astype(str).value_counts().reset_index()
            hit.columns = ["Squad Gap Addressed", "Players Bought"]
            st.dataframe(make_safe_df(hit), use_container_width=True, height=220)

        st.markdown("### Best Affordable Alternatives")
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
            "Realism Fit",
            "Value Efficiency",
            "Playstyle Fit",
        ]
        alt_cols = [col for col in alt_cols if col in alternatives.columns]

        st.dataframe(make_safe_df(alternatives[alt_cols]), use_container_width=True, height=460)

        st.download_button(
            "Download Dynamic Budget Plan CSV",
            make_safe_df(plan).to_csv(index=False).encode("utf-8"),
            file_name=f"{your_club.replace(' ', '_')}_dynamic_budget_plan.csv",
            mime="text/csv",
        )


elif view == "Squad Impact Simulator":
    st.subheader("Squad Impact Simulator")

    st.write(
        """
        Test transfers before committing. Remove current players, add recommended players,
        and see whether the move actually improves your squad gaps.
        """
    )

    st.info(
        "This simulator uses your current active filters: squad gap focus, price range, realism mode, budget, and playstyle."
    )

    if budget_recommendations.empty:
        st.warning(
            "No recommended signing pool is available. Widen the price range, switch to Aggressive realism, "
            "or choose more squad gaps."
        )
    else:
        remove_options = build_current_squad_options(df, your_club)

        st.markdown("### Add / Sign Any Player In Database")

        add_source_mode = st.selectbox(
            "Signing Pool",
            [
                "Recommended + Any Database Player",
                "Recommended Players Only",
                "Any Database Player",
            ],
            index=0,
            key="impact_add_source_mode",
        )

        filter_col_1, filter_col_2, filter_col_3, filter_col_4 = st.columns(4)

        with filter_col_1:
            add_search_text = st.text_input(
                "Search Any Player / Club",
                value="",
                placeholder="Example: Ricci, Torino, Brazil, DM",
                key="impact_add_search_text",
            )

        club_col = find_column(df, ["Club"])
        league_col = find_column(df, ["Division", "League"])

        with filter_col_2:
            if club_col:
                club_options = ["All"] + sorted(
                    df[club_col].dropna().astype(str).unique().tolist()
                )
            else:
                club_options = ["All"]

            add_club_filter = st.selectbox(
                "Filter Club",
                club_options,
                key="impact_add_club_filter",
            )

        with filter_col_3:
            if league_col:
                league_options = ["All"] + sorted(
                    df[league_col].dropna().astype(str).unique().tolist()
                )
            else:
                league_options = ["All"]

            add_league_filter = st.selectbox(
                "Filter League",
                league_options,
                key="impact_add_league_filter",
            )

        with filter_col_4:
            position_options = ["All"]

            if "Primary Position" in df.columns:
                position_options += sorted(
                    df["Primary Position"].dropna().astype(str).unique().tolist()
                )

            add_position_filter = st.selectbox(
                "Filter Position",
                position_options,
                key="impact_add_position_filter",
            )

        price_col_1, price_col_2, price_col_3 = st.columns(3)

        with price_col_1:
            add_min_price_text = st.text_input(
                "Minimum Signing Price",
                value="0",
                placeholder="Example: 5M",
                key="impact_add_min_price_text",
            )

        with price_col_2:
            add_max_price_text = st.text_input(
                "Maximum Signing Price",
                value=f"{int(transfer_budget):,}",
                placeholder="Example: 80M",
                key="impact_add_max_price_text",
            )

        with price_col_3:
            max_add_options = st.slider(
                "Max Player Options Shown",
                min_value=50,
                max_value=1000,
                value=300,
                step=50,
                key="impact_max_add_options",
            )

        add_min_price = parse_budget_input(add_min_price_text)
        add_max_price = parse_budget_input(add_max_price_text)

        if add_max_price <= 0:
            add_max_price = float(transfer_budget)

        if add_min_price > add_max_price:
            add_min_price, add_max_price = add_max_price, add_min_price

        add_options = build_all_database_add_options(
            full_df=df,
            your_club=your_club,
            recommendations=budget_recommendations,
            source_mode=add_source_mode,
            search_text=add_search_text,
            club_filter=add_club_filter,
            league_filter=add_league_filter,
            position_filter=add_position_filter,
            min_price=add_min_price,
            max_price=add_max_price,
            max_options=max_add_options,
        )

        st.caption(
            f"Add/sign pool: {len(add_options)} players | "
            f"Price range: {format_money(add_min_price)} to {format_money(add_max_price)}"
        )

        col_a, col_b = st.columns(2)

        with col_a:
            selected_remove_labels = st.multiselect(
                "Players To Remove / Sell",
                list(remove_options.keys()),
                key="impact_remove_players",
            )

        with col_b:
            selected_add_labels = st.multiselect(
                "Players To Add / Sign",
                list(add_options.keys()),
                key="impact_add_players",
            )

        remove_indices = [remove_options[label] for label in selected_remove_labels]
        add_indices = [add_options[label] for label in selected_add_labels]

        impact = simulate_squad_impact(
            df=df,
            your_club=your_club,
            benchmark=benchmark,
            remove_indices=remove_indices,
            add_indices=add_indices,
            total_budget=transfer_budget,
        )

        if impact["error"]:
            st.error(impact["error"])
        else:
            summary = impact["summary"]

            m1, m2, m3, m4, m5 = st.columns(5)

            m1.metric("Current Rating", f"{summary['Current Overall']:.1f}")
            m2.metric("Projected Rating", f"{summary['Projected Overall']:.1f}", f"{summary['Overall Change']:+.1f}")
            m3.metric("Net Spend", format_money(summary["Net Spend"]))
            m4.metric("Budget After Moves", format_money(summary["Budget After Net Spend"]))
            m5.metric("Major Gaps Left", summary["Projected Major Gaps"], f"{summary['Current Major Gaps'] - summary['Projected Major Gaps']:+d}")

            st.markdown("### Will This Address My Areas Of Need?")

            category_impact = impact["category_impact"]

            need_cols = [
                "Squad Area",
                "Current Rating",
                "Projected Rating",
                "Rating Change",
                "Target Rating",
                "Current Gap",
                "Projected Gap",
                "Gap Addressed",
                "Status",
            ]

            st.dataframe(
                make_safe_df(category_impact[need_cols]),
                use_container_width=True,
                height=430,
            )

            solved = category_impact[category_impact["Status"] == "Solved"]
            improved = category_impact[category_impact["Status"] == "Improved"]
            worse = category_impact[category_impact["Status"] == "Worse"]

            if not solved.empty:
                st.success(
                    "Solved areas: " + ", ".join(solved["Squad Area"].astype(str).tolist())
                )

            if not improved.empty:
                st.info(
                    "Improved areas: " + ", ".join(improved["Squad Area"].astype(str).tolist())
                )

            if not worse.empty:
                st.warning(
                    "Warning: these areas got worse after removals/additions: "
                    + ", ".join(worse["Squad Area"].astype(str).tolist())
                )

            st.markdown("### Players Added")

            if impact["added_players"].empty:
                st.caption("No players added yet.")
            else:
                st.dataframe(
                    make_safe_df(impact["added_players"]),
                    use_container_width=True,
                    height=260,
                )

            st.markdown("### Players Removed")

            if impact["removed_players"].empty:
                st.caption("No players removed yet.")
            else:
                st.dataframe(
                    make_safe_df(impact["removed_players"]),
                    use_container_width=True,
                    height=260,
                )

            st.download_button(
                "Download Squad Impact Table CSV",
                make_safe_df(category_impact).to_csv(index=False).encode("utf-8"),
                file_name=f"{your_club.replace(' ', '_')}_squad_impact.csv",
                mime="text/csv",
            )


elif view == "Top Recommended Signings":
    st.subheader("Top Realistic Recommended Signings By Squad Gap")

    if recommendations.empty:
        st.warning("No realistic recommendations found. Try Aggressive realism mode, increasing max age, or using a larger budget.")
    else:
        st.dataframe(make_safe_df(gaps), use_container_width=True, height=250)

        cols = [
            "Gap Rank",
            "Player",
            "Age",
            "Club",
            "League",
            "Position",
            "Recommended For",
            "Recommendation Score",
            "Quality Score",
            "Realism Fit",
            "Candidate Category Rating",
            "Playstyle Fit",
            "Upgrade Over Current Area",
            "Gap Covered %",
            "Global Player Quality Rank",
            "Transfer Cost Display",
            "Why Recommended",
        ]

        for index, gap in enumerate(gaps["Squad Area"].tolist()):
            gap_recs = recommendations[recommendations["Recommended For"] == gap].copy()

            if gap_recs.empty:
                continue

            with st.expander(f"{gap} — Top {top_per_gap} Realistic Options", expanded=index < 3):
                show_cols = [col for col in cols if col in gap_recs.columns]
                st.dataframe(make_safe_df(gap_recs[show_cols]), use_container_width=True, height=340)

        st.download_button(
            "Download Recommended Signings CSV",
            make_safe_df(recommendations).to_csv(index=False).encode("utf-8"),
            file_name=f"{your_club.replace(' ', '_')}_realistic_recommended_signings.csv",
            mime="text/csv",
        )

elif view == "Sell / Upgrade Candidates":
    st.subheader("Players To Sell / Upgrade")

    st.write(
        "This finds players whose attribute strength is higher than their statistical performance. "
        "These are players who look good on paper but are not producing enough."
    )

    if sell_df.empty:
        st.success("No major underperforming sell/upgrade candidates found.")
    else:
        sell_cols = [
            "Sell Rank",
            "Player",
            "Age",
            "Position",
            "Best Role Area",
            "Attribute Strength",
            "Statistical Performance",
            "Underperformance Gap",
            "Combined Rating",
            "Playstyle Fit",
            "Estimated Value",
            "Sell / Upgrade Score",
            "Reason",
        ]

        sell_cols = [col for col in sell_cols if col in sell_df.columns]
        st.dataframe(make_safe_df(sell_df[sell_cols]), use_container_width=True, height=520)

        st.markdown("### Upgrade Options For Each Sell Candidate")

        for _, row in sell_df.head(10).iterrows():
            player = row["Player"]
            options = replacement_df[replacement_df["Replace"].astype(str) == str(player)].copy()

            with st.expander(f"Replace {player} — {row['Best Role Area']}", expanded=False):
                if options.empty:
                    st.info("No realistic replacement found in the current recommendation pool.")
                else:
                    st.dataframe(make_safe_df(options), use_container_width=True, height=280)

elif view == "Realism Context":
    st.subheader("Realism Context")
    st.dataframe(make_safe_df(pd.DataFrame([context])), use_container_width=True, height=220)

    st.markdown(
        """
        ### How realism works

        - Lower-strength clubs are filtered away from top-5 or top-20 world players.
        - Stronger clubs can access higher-value and higher-quality players.
        - Budget affects the price range.
        - Target goal affects ambition, but the app keeps recommendations realistic.
        - Burnley and Blu-neri should not receive the exact same list unless their squad strength, budget, and goal are similar.
        """
    )

elif view == "Squad Gaps":
    st.subheader("Squad Gaps Against Target Level")
    st.dataframe(make_safe_df(gaps), use_container_width=True, height=520)

elif view == "Benchmark Teams":
    st.subheader("Benchmark Teams")
    cols = ["Club", "League", "Overall Team Rating"] + [f"Combined - {category}" for category in CATEGORY_PROFILES]
    cols = [col for col in cols if col in benchmark_teams.columns]
    st.dataframe(make_safe_df(benchmark_teams[cols]), use_container_width=True, height=560)

elif view == "All Candidate Scores":
    st.subheader("All Candidate Scores")

    club_col = find_column(df, ["Club"])
    name_col = find_column(df, ["Name", "Player"])
    league_col = find_column(df, ["Division", "League"])

    show = df[df[club_col].astype(str) != str(your_club)].copy() if club_col else df.copy()

    search = st.text_input("Search Player", key="rec_candidate_search")

    if search and name_col:
        show = show[show[name_col].astype(str).str.contains(search, case=False, na=False)]

    sort_options = ["Overall Player Quality", f"{playstyle} Playstyle Fit", "Transfer Cost"]

    for category in CATEGORY_PROFILES:
        sort_options.append(f"{category} Combined Rating")

    sort_options = [col for col in sort_options if col in show.columns]

    sort_col = st.selectbox("Sort By", sort_options, key="rec_candidate_sort")

    if sort_col:
        show = show.sort_values(sort_col, ascending=False)

    display_cols = [
        name_col,
        "Age",
        club_col,
        league_col,
        "Position",
        "Primary Position",
        "Overall Player Quality",
        "Global Player Quality Rank",
        "Transfer Value Raw",
        "Transfer Value Clean",
        "Transfer Value Display",
        "Transfer Cost Display",
        f"{playstyle} Playstyle Fit",
    ]

    for category in CATEGORY_PROFILES:
        display_cols.append(f"{category} Combined Rating")

    display_cols = [col for col in display_cols if col and col in show.columns]

    rows = st.slider("Rows To Show", 25, 1000, 100, 25, key="rec_candidate_rows")
    st.dataframe(make_safe_df(show[display_cols].head(rows)), use_container_width=True, height=620)

if save_page_memory:
    save_page_memory(__file__)
