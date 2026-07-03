from pathlib import Path
import re

sim_path = Path("fm_engine/squad_impact_simulator.py")
page_path = Path("app/pages/11_Recommended_Signings.py")

sim_text = sim_path.read_text(encoding="utf-8")
page_text = page_path.read_text(encoding="utf-8")

# ============================================================
# 1. ADD TROPHY PROBABILITY ENGINE
# ============================================================

probability_engine = r'''

# ============================================================
# TROPHY PROBABILITY IMPACT ENGINE
# ============================================================

def softmax_probability(candidate_rating: float, competitor_ratings: list[float], scale: float = 4.25) -> float:
    """
    Converts squad strength into a rough win probability against a pool of competitors.

    This is not a real betting model. It is a squad-strength probability estimate:
    stronger squad rating = higher chance, but stronger competition lowers the chance.
    """

    try:
        candidate_rating = float(candidate_rating)
    except Exception:
        return 0.0

    clean_competitors = []

    for rating in competitor_ratings:
        try:
            rating = float(rating)
        except Exception:
            continue

        if not pd.isna(rating):
            clean_competitors.append(rating)

    if not clean_competitors:
        return 100.0

    values = np.array(clean_competitors + [candidate_rating], dtype=float)

    # Stable softmax.
    shifted = values - values.max()
    strengths = np.exp(shifted / scale)

    candidate_strength = strengths[-1]
    total_strength = strengths.sum()

    if total_strength <= 0:
        return 0.0

    return round(float(candidate_strength / total_strength * 100), 1)


def build_competition_probability_impact(
    team_ratings: pd.DataFrame,
    your_club: str,
    current_overall: float,
    projected_overall: float,
) -> pd.DataFrame:
    """
    Shows how likely your club is to win the domestic league and UCL before/after transfers.
    """

    if team_ratings is None or team_ratings.empty:
        return pd.DataFrame()

    if "Club" not in team_ratings.columns or "Overall Team Rating" not in team_ratings.columns:
        return pd.DataFrame()

    ratings = team_ratings.copy()
    ratings["Overall Team Rating"] = pd.to_numeric(
        ratings["Overall Team Rating"],
        errors="coerce",
    )

    ratings = ratings[ratings["Overall Team Rating"].notna()].copy()

    your_row = ratings[ratings["Club"].astype(str) == str(your_club)]

    if your_row.empty:
        your_league = "Unknown"
    else:
        your_league = str(your_row.iloc[0].get("League", "Unknown"))

    # Domestic league pool.
    if "League" in ratings.columns and your_league != "Unknown":
        league_pool = ratings[ratings["League"].astype(str) == your_league].copy()
    else:
        league_pool = ratings.copy()

    league_competitors = league_pool[
        league_pool["Club"].astype(str) != str(your_club)
    ]["Overall Team Rating"].dropna().astype(float).tolist()

    current_league_probability = softmax_probability(
        candidate_rating=current_overall,
        competitor_ratings=league_competitors,
        scale=4.00,
    )

    projected_league_probability = softmax_probability(
        candidate_rating=projected_overall,
        competitor_ratings=league_competitors,
        scale=4.00,
    )

    # UCL pool: top 24 strongest teams in the database, excluding your club.
    ucl_pool = ratings[
        ratings["Club"].astype(str) != str(your_club)
    ].sort_values("Overall Team Rating", ascending=False).head(24)

    ucl_competitors = ucl_pool["Overall Team Rating"].dropna().astype(float).tolist()

    current_ucl_probability = softmax_probability(
        candidate_rating=current_overall,
        competitor_ratings=ucl_competitors,
        scale=3.60,
    )

    projected_ucl_probability = softmax_probability(
        candidate_rating=projected_overall,
        competitor_ratings=ucl_competitors,
        scale=3.60,
    )

    records = [
        {
            "Competition": "Domestic League",
            "Competition Pool": your_league,
            "Current Squad Rating": round(float(current_overall), 1),
            "Projected Squad Rating": round(float(projected_overall), 1),
            "Rating Change": round(float(projected_overall) - float(current_overall), 1),
            "Current Win Probability %": current_league_probability,
            "Projected Win Probability %": projected_league_probability,
            "Probability Change": round(projected_league_probability - current_league_probability, 1),
            "Difficulty": "League opponents only",
        },
        {
            "Competition": "UEFA Champions League",
            "Competition Pool": "Top 24 clubs in database",
            "Current Squad Rating": round(float(current_overall), 1),
            "Projected Squad Rating": round(float(projected_overall), 1),
            "Rating Change": round(float(projected_overall) - float(current_overall), 1),
            "Current Win Probability %": current_ucl_probability,
            "Projected Win Probability %": projected_ucl_probability,
            "Probability Change": round(projected_ucl_probability - current_ucl_probability, 1),
            "Difficulty": "Elite continental opponents",
        },
    ]

    return pd.DataFrame(records)


def probability_recommendation_note(probability_table: pd.DataFrame) -> str:
    if probability_table is None or probability_table.empty:
        return "No probability estimate available."

    notes = []

    for _, row in probability_table.iterrows():
        competition = row.get("Competition", "")
        change = row.get("Probability Change", 0)
        projected = row.get("Projected Win Probability %", 0)

        try:
            change = float(change)
            projected = float(projected)
        except Exception:
            continue

        if change >= 5:
            notes.append(f"{competition}: strong improvement to {projected:.1f}%.")
        elif change >= 2:
            notes.append(f"{competition}: useful improvement to {projected:.1f}%.")
        elif change > 0:
            notes.append(f"{competition}: small improvement to {projected:.1f}%.")
        elif change == 0:
            notes.append(f"{competition}: no meaningful change.")
        else:
            notes.append(f"{competition}: this plan may weaken your odds.")

    return " ".join(notes)
'''

if "def build_competition_probability_impact(" not in sim_text:
    sim_text = sim_text.rstrip() + "\n\n" + probability_engine + "\n"

sim_path.write_text(sim_text, encoding="utf-8")


# ============================================================
# 2. PATCH IMPORT IN RECOMMENDED SIGNINGS PAGE
# ============================================================

if "build_competition_probability_impact" not in page_text:
    page_text = page_text.replace(
        "    build_current_squad_options,\n",
        "    build_competition_probability_impact,\n    build_current_squad_options,\n",
        1,
    )

if "probability_recommendation_note" not in page_text:
    page_text = page_text.replace(
        "    simulate_squad_impact,\n",
        "    simulate_squad_impact,\n    probability_recommendation_note,\n",
        1,
    )


# ============================================================
# 3. ADD PROBABILITY DISPLAY TO SQUAD IMPACT SIMULATOR
# ============================================================

probability_ui = r'''
            st.markdown("### Trophy Probability Impact")

            probability_table = build_competition_probability_impact(
                team_ratings=team_ratings,
                your_club=your_club,
                current_overall=summary["Current Overall"],
                projected_overall=summary["Projected Overall"],
            )

            if probability_table.empty:
                st.info("No probability estimate available.")
            else:
                league_row = probability_table[
                    probability_table["Competition"] == "Domestic League"
                ]

                ucl_row = probability_table[
                    probability_table["Competition"] == "UEFA Champions League"
                ]

                p1, p2, p3, p4 = st.columns(4)

                if not league_row.empty:
                    league = league_row.iloc[0]
                    p1.metric(
                        "League Win Chance",
                        f"{float(league['Projected Win Probability %']):.1f}%",
                        f"{float(league['Probability Change']):+.1f} pts",
                    )
                    p2.metric(
                        "Current League Chance",
                        f"{float(league['Current Win Probability %']):.1f}%",
                    )

                if not ucl_row.empty:
                    ucl = ucl_row.iloc[0]
                    p3.metric(
                        "UCL Win Chance",
                        f"{float(ucl['Projected Win Probability %']):.1f}%",
                        f"{float(ucl['Probability Change']):+.1f} pts",
                    )
                    p4.metric(
                        "Current UCL Chance",
                        f"{float(ucl['Current Win Probability %']):.1f}%",
                    )

                st.dataframe(
                    make_safe_df(probability_table),
                    use_container_width=True,
                    height=220,
                )

                st.caption(
                    "Probability is an estimated squad-strength model, not a guarantee. "
                    "It compares your current/projected squad rating against your league and a UCL-level top-24 club pool."
                )

                st.success(probability_recommendation_note(probability_table))

'''

if "### Trophy Probability Impact" not in page_text:
    marker = '            st.markdown("### Will This Address My Areas Of Need?")'

    if marker not in page_text:
        raise SystemExit("Could not find Squad Impact Simulator insertion point.")

    page_text = page_text.replace(
        marker,
        probability_ui + "\n" + marker,
        1,
    )

page_path.write_text(page_text, encoding="utf-8")

print("Added league and UCL probability impact to Squad Impact Simulator.")
