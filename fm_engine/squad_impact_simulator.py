
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



def build_all_database_add_options(
    full_df: pd.DataFrame,
    your_club: str,
    recommendations: pd.DataFrame | None = None,
    source_mode: str = "Recommended + Any Database Player",
    search_text: str = "",
    club_filter: str = "All",
    league_filter: str = "All",
    position_filter: str = "All",
    min_price: float = 0,
    max_price: float = 1_000_000_000,
    max_options: int = 500,
) -> dict[str, int]:
    """
    Builds add/sign options from either:
    - recommended players only
    - every player in the database
    - recommended players first, then every database player

    This lets the Squad Impact Simulator test ANY player in the database.
    """

    if full_df is None or full_df.empty:
        return {}

    name_col = find_column(full_df, ["Name", "Player"])
    club_col = find_column(full_df, ["Club"])
    age_col = find_column(full_df, ["Age"])
    pos_col = find_column(full_df, ["Position"])
    league_col = find_column(full_df, ["Division", "League"])

    if not name_col or not club_col:
        return {}

    working = ensure_transfer_costs(full_df.copy())

    # Do not include current-club players as signings.
    working = working[working[club_col].astype(str) != str(your_club)].copy()

    working["Transfer Cost"] = pd.to_numeric(working["Transfer Cost"], errors="coerce")

    working = working[
        working["Transfer Cost"].notna()
        & (working["Transfer Cost"] >= float(min_price))
        & (working["Transfer Cost"] <= float(max_price))
    ].copy()

    if search_text:
        search_text = str(search_text).strip()

        if search_text:
            search_blob = (
                working[name_col].astype(str)
                + " "
                + working[club_col].astype(str)
                + " "
                + working.get(pos_col, pd.Series("", index=working.index)).astype(str)
                + " "
                + working.get(league_col, pd.Series("", index=working.index)).astype(str)
            )

            working = working[
                search_blob.str.contains(search_text, case=False, na=False)
            ].copy()

    if club_filter != "All":
        working = working[working[club_col].astype(str) == str(club_filter)].copy()

    if league_filter != "All" and league_col:
        working = working[working[league_col].astype(str) == str(league_filter)].copy()

    if position_filter != "All":
        if "Primary Position" in working.columns:
            working = working[working["Primary Position"].astype(str) == str(position_filter)].copy()
        elif pos_col:
            working = working[
                working[pos_col].astype(str).str.contains(str(position_filter), case=False, na=False)
            ].copy()

    if working.empty:
        return {}

    # Recommendation priority map.
    rec_priority = {}

    if recommendations is not None and not recommendations.empty:
        for rank, (_, rec) in enumerate(recommendations.reset_index(drop=True).iterrows(), start=1):
            player = str(rec.get("Player", ""))
            club = str(rec.get("Club", ""))

            if player and club:
                rec_priority[(player, club)] = rank

    def recommendation_priority(row):
        key = (str(row.get(name_col, "")), str(row.get(club_col, "")))
        return rec_priority.get(key, 999999)

    working["Recommendation Priority"] = working.apply(recommendation_priority, axis=1)

    if source_mode == "Recommended Players Only":
        working = working[working["Recommendation Priority"] < 999999].copy()

    if working.empty:
        return {}

    # Sort recommended players first, then strongest/highest-quality players.
    sort_cols = ["Recommendation Priority"]

    if "Overall Player Quality" in working.columns:
        working["Overall Player Quality"] = pd.to_numeric(working["Overall Player Quality"], errors="coerce").fillna(0)
        sort_cols.append("Overall Player Quality")

    if "Transfer Cost" in working.columns:
        sort_cols.append("Transfer Cost")

    ascending = []

    for col in sort_cols:
        if col == "Recommendation Priority":
            ascending.append(True)
        else:
            ascending.append(False)

    working = working.sort_values(sort_cols, ascending=ascending).head(int(max_options)).copy()

    options = {}

    for idx, row in working.iterrows():
        player = row.get(name_col, "Unknown")
        club = row.get(club_col, "Unknown")
        age = row.get(age_col, "")
        league = row.get(league_col, "") if league_col else ""
        position = row.get(pos_col, row.get("Primary Position", "")) if pos_col else row.get("Primary Position", "")
        category = best_category_for_row(row)
        value = row.get("Transfer Cost", np.nan)

        area_score = row.get(f"{category} Combined Rating", "")

        try:
            area_score_display = f"{float(area_score):.1f}"
        except Exception:
            area_score_display = str(area_score)

        rec_tag = ""

        if (str(player), str(club)) in rec_priority:
            rec_tag = " | RECOMMENDED"

        label = (
            f"{player} | {club} | Age {age} | {position} | {league} | "
            f"{category}: {area_score_display} | Cost: {format_money(value)}{rec_tag}"
        )

        label = unique_label(label, options)
        options[label] = idx

    return options

