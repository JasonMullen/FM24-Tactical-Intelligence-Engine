from pathlib import Path
import re

# ============================================================
# 1. CREATE SQUAD IMPACT SIMULATOR MODULE
# ============================================================

sim_path = Path("fm_engine/squad_impact_simulator.py")

sim_path.write_text(r'''
from __future__ import annotations

import pandas as pd
import numpy as np

from fm_engine.signing_engine import (
    CATEGORY_PROFILES,
    find_column,
    format_money,
    make_safe_df,
    pos_mask,
    ensure_transfer_costs,
)


def unique_label(label: str, existing: dict) -> str:
    if label not in existing:
        return label

    count = 2
    new_label = f"{label} [{count}]"

    while new_label in existing:
        count += 1
        new_label = f"{label} [{count}]"

    return new_label


def best_category_for_row(row: pd.Series) -> str:
    position_classes = str(row.get("Position Classes", ""))

    possible_categories = []

    for category, profile in CATEGORY_PROFILES.items():
        accepted = profile["accepted_positions"]

        if any(pos in position_classes for pos in accepted):
            possible_categories.append(category)

    if not possible_categories:
        possible_categories = list(CATEGORY_PROFILES.keys())

    best_category = possible_categories[0]
    best_score = -1

    for category in possible_categories:
        score_col = f"{category} Combined Rating"

        try:
            score = float(row.get(score_col, 0))
        except Exception:
            score = 0

        if score > best_score:
            best_score = score
            best_category = category

    return best_category


def build_current_squad_options(df: pd.DataFrame, your_club: str) -> dict[str, int]:
    if df is None or df.empty:
        return {}

    club_col = find_column(df, ["Club"])
    name_col = find_column(df, ["Name", "Player"])
    age_col = find_column(df, ["Age"])
    pos_col = find_column(df, ["Position"])

    if not club_col or not name_col:
        return {}

    working = ensure_transfer_costs(df.copy())
    squad = working[working[club_col].astype(str) == str(your_club)].copy()

    options = {}

    for idx, row in squad.iterrows():
        player = row.get(name_col, "Unknown")
        age = row.get(age_col, "")
        position = row.get(pos_col, row.get("Primary Position", ""))
        category = best_category_for_row(row)

        score = row.get(f"{category} Combined Rating", "")
        value = row.get("Transfer Cost", np.nan)

        try:
            score_display = f"{float(score):.1f}"
        except Exception:
            score_display = str(score)

        label = (
            f"{player} | Age {age} | {position} | "
            f"{category}: {score_display} | Value: {format_money(value)}"
        )

        label = unique_label(label, options)
        options[label] = idx

    return options


def build_recommended_add_options(full_df: pd.DataFrame, recommendations: pd.DataFrame) -> dict[str, int]:
    if full_df is None or full_df.empty or recommendations is None or recommendations.empty:
        return {}

    name_col = find_column(full_df, ["Name", "Player"])
    club_col = find_column(full_df, ["Club"])
    pos_col = find_column(full_df, ["Position"])

    if not name_col or not club_col:
        return {}

    working = ensure_transfer_costs(full_df.copy())

    options = {}

    for _, rec in recommendations.iterrows():
        player = rec.get("Player", None)
        club = rec.get("Club", None)

        if player is None or club is None:
            continue

        matches = working[
            (working[name_col].astype(str) == str(player))
            & (working[club_col].astype(str) == str(club))
        ]

        if matches.empty:
            continue

        idx = matches.index[0]
        row = matches.loc[idx]

        position = row.get(pos_col, row.get("Primary Position", rec.get("Position", "")))
        recommended_for = rec.get("Recommended For", "Unknown")
        score = rec.get("Recommendation Score", "")
        realism = rec.get("Realism Fit", "")
        cost = rec.get("Transfer Cost", row.get("Transfer Cost", np.nan))

        try:
            score_display = f"{float(score):.1f}"
        except Exception:
            score_display = str(score)

        try:
            realism_display = f"{float(realism):.1f}"
        except Exception:
            realism_display = str(realism)

        label = (
            f"{player} | {club} | {position} | "
            f"Need: {recommended_for} | Score: {score_display} | "
            f"Realism: {realism_display} | Cost: {format_money(cost)}"
        )

        label = unique_label(label, options)
        options[label] = idx

    return options


def rate_team_from_squad(team_df: pd.DataFrame) -> dict:
    ratings = {}

    overall = 0.0

    for category, profile in CATEGORY_PROFILES.items():
        score_col = f"{category} Combined Rating"

        if score_col not in team_df.columns:
            category_score = 0.0
        else:
            candidates = team_df[pos_mask(team_df, profile["accepted_positions"])].copy()

            if candidates.empty:
                category_score = 0.0
            else:
                candidates[score_col] = pd.to_numeric(candidates[score_col], errors="coerce")
                top_players = (
                    candidates[candidates[score_col].notna()]
                    .sort_values(score_col, ascending=False)
                    .head(profile["depth"])
                )

                if top_players.empty:
                    category_score = 0.0
                else:
                    category_score = float(top_players[score_col].mean())

        ratings[f"Combined - {category}"] = round(category_score, 1)
        overall += category_score * profile["weight"]

    ratings["Overall Team Rating"] = round(overall, 1)

    return ratings


def build_category_impact_table(
    current_ratings: dict,
    projected_ratings: dict,
    benchmark: dict[str, float],
) -> pd.DataFrame:
    rows = []

    for category in CATEGORY_PROFILES:
        current_score = float(current_ratings.get(f"Combined - {category}", 0))
        projected_score = float(projected_ratings.get(f"Combined - {category}", 0))
        target_score = float(benchmark.get(category, 70))

        current_gap = round(target_score - current_score, 1)
        projected_gap = round(target_score - projected_score, 1)
        gap_change = round(current_gap - projected_gap, 1)
        rating_change = round(projected_score - current_score, 1)

        if projected_gap <= 0:
            status = "Solved"
        elif projected_gap < current_gap:
            status = "Improved"
        elif projected_gap == current_gap:
            status = "No Change"
        else:
            status = "Worse"

        rows.append(
            {
                "Squad Area": category,
                "Current Rating": round(current_score, 1),
                "Projected Rating": round(projected_score, 1),
                "Rating Change": rating_change,
                "Target Rating": round(target_score, 1),
                "Current Gap": current_gap,
                "Projected Gap": projected_gap,
                "Gap Addressed": gap_change,
                "Status": status,
            }
        )

    table = pd.DataFrame(rows)

    return table.sort_values(
        ["Projected Gap", "Current Gap"],
        ascending=[False, False],
    ).reset_index(drop=True)


def build_selected_players_table(df: pd.DataFrame, indices: list[int], table_type: str) -> pd.DataFrame:
    if df is None or df.empty or not indices:
        return pd.DataFrame()

    name_col = find_column(df, ["Name", "Player"])
    club_col = find_column(df, ["Club"])
    age_col = find_column(df, ["Age"])
    pos_col = find_column(df, ["Position"])

    working = ensure_transfer_costs(df.copy())
    selected = working.loc[[idx for idx in indices if idx in working.index]].copy()

    rows = []

    for _, row in selected.iterrows():
        category = best_category_for_row(row)

        rows.append(
            {
                "Type": table_type,
                "Player": row.get(name_col, "Unknown") if name_col else "Unknown",
                "Age": row.get(age_col, "") if age_col else "",
                "Club": row.get(club_col, "") if club_col else "",
                "Position": row.get(pos_col, row.get("Primary Position", "")) if pos_col else row.get("Primary Position", ""),
                "Best Squad Area": category,
                "Area Rating": row.get(f"{category} Combined Rating", ""),
                "Transfer Value": format_money(row.get("Transfer Cost", np.nan)),
                "Transfer Cost": row.get("Transfer Cost", np.nan),
            }
        )

    return pd.DataFrame(rows)


def simulate_squad_impact(
    df: pd.DataFrame,
    your_club: str,
    benchmark: dict[str, float],
    remove_indices: list[int],
    add_indices: list[int],
    total_budget: float,
) -> dict:
    club_col = find_column(df, ["Club"])

    if not club_col:
        return {
            "error": "No Club column found.",
            "summary": {},
            "category_impact": pd.DataFrame(),
            "removed_players": pd.DataFrame(),
            "added_players": pd.DataFrame(),
        }

    working = ensure_transfer_costs(df.copy())

    current_squad = working[working[club_col].astype(str) == str(your_club)].copy()

    remove_indices = [idx for idx in remove_indices if idx in current_squad.index]
    add_indices = [idx for idx in add_indices if idx in working.index]

    projected_squad = current_squad.drop(index=remove_indices, errors="ignore").copy()

    add_rows = working.loc[add_indices].copy()

    if not add_rows.empty:
        add_rows[club_col] = your_club
        projected_squad = pd.concat([projected_squad, add_rows], ignore_index=False, sort=False)

    current_ratings = rate_team_from_squad(current_squad)
    projected_ratings = rate_team_from_squad(projected_squad)

    category_impact = build_category_impact_table(
        current_ratings=current_ratings,
        projected_ratings=projected_ratings,
        benchmark=benchmark,
    )

    removed_players = build_selected_players_table(
        df=working,
        indices=remove_indices,
        table_type="Removed",
    )

    added_players = build_selected_players_table(
        df=working,
        indices=add_indices,
        table_type="Added",
    )

    incoming_cost = float(pd.to_numeric(added_players.get("Transfer Cost", pd.Series(dtype=float)), errors="coerce").fillna(0).sum()) if not added_players.empty else 0.0
    outgoing_value = float(pd.to_numeric(removed_players.get("Transfer Cost", pd.Series(dtype=float)), errors="coerce").fillna(0).sum()) if not removed_players.empty else 0.0
    net_spend = incoming_cost - outgoing_value

    current_overall = float(current_ratings.get("Overall Team Rating", 0))
    projected_overall = float(projected_ratings.get("Overall Team Rating", 0))

    improved_areas = int((category_impact["Rating Change"] > 0).sum())
    solved_areas = int((category_impact["Status"] == "Solved").sum())
    worse_areas = int((category_impact["Rating Change"] < 0).sum())

    current_major_gaps = int((category_impact["Current Gap"] >= 4).sum())
    projected_major_gaps = int((category_impact["Projected Gap"] >= 4).sum())

    summary = {
        "Current Overall": round(current_overall, 1),
        "Projected Overall": round(projected_overall, 1),
        "Overall Change": round(projected_overall - current_overall, 1),
        "Incoming Cost": incoming_cost,
        "Outgoing Value": outgoing_value,
        "Net Spend": net_spend,
        "Budget After Net Spend": total_budget - net_spend,
        "Improved Areas": improved_areas,
        "Solved Areas": solved_areas,
        "Worse Areas": worse_areas,
        "Current Major Gaps": current_major_gaps,
        "Projected Major Gaps": projected_major_gaps,
    }

    return {
        "error": "",
        "summary": summary,
        "category_impact": category_impact,
        "removed_players": removed_players,
        "added_players": added_players,
    }
''', encoding="utf-8")


# ============================================================
# 2. PATCH RECOMMENDED SIGNINGS PAGE
# ============================================================

page_path = Path("app/pages/11_Recommended_Signings.py")
text = page_path.read_text(encoding="utf-8")

# Add import.
sim_import = '''from fm_engine.squad_impact_simulator import (
    build_current_squad_options,
    build_recommended_add_options,
    simulate_squad_impact,
)
'''

if "from fm_engine.squad_impact_simulator import" not in text:
    if "from fm_engine.recommendation_filters import apply_recommendation_filters, choose_focused_gaps\n" in text:
        text = text.replace(
            "from fm_engine.recommendation_filters import apply_recommendation_filters, choose_focused_gaps\n",
            "from fm_engine.recommendation_filters import apply_recommendation_filters, choose_focused_gaps\n" + sim_import,
            1,
        )
    elif "from fm_engine.manual_spend_planner import build_manual_spend_budget_plan\n" in text:
        text = text.replace(
            "from fm_engine.manual_spend_planner import build_manual_spend_budget_plan\n",
            "from fm_engine.manual_spend_planner import build_manual_spend_budget_plan\n" + sim_import,
            1,
        )
    else:
        pattern = r"from fm_engine\.signing_engine import \([\s\S]*?\)\n"
        match = re.search(pattern, text)

        if not match:
            raise SystemExit("Could not find import location.")

        text = text[:match.end()] + sim_import + text[match.end():]


# Add view option.
if '"Squad Impact Simulator"' not in text:
    text = text.replace(
        '''"Dynamic Budget Plan",
        "Top Recommended Signings",''',
        '''"Dynamic Budget Plan",
        "Squad Impact Simulator",
        "Top Recommended Signings",''',
        1,
    )


# Add view block.
simulator_block = r'''
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
        add_options = build_recommended_add_options(df, budget_recommendations)

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

'''

if 'elif view == "Squad Impact Simulator":' not in text:
    marker = 'elif view == "Top Recommended Signings":'

    if marker not in text:
        raise SystemExit("Could not find Top Recommended Signings view marker.")

    text = text.replace(
        marker,
        simulator_block + "\n" + marker,
        1,
    )


page_path.write_text(text, encoding="utf-8")

print("Added Squad Impact Simulator.")
