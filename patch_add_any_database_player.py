from pathlib import Path
import re

sim_path = Path("fm_engine/squad_impact_simulator.py")
page_path = Path("app/pages/11_Recommended_Signings.py")

sim_text = sim_path.read_text(encoding="utf-8")
page_text = page_path.read_text(encoding="utf-8")

# ============================================================
# 1. ADD FUNCTION: ADD/SIGN ANY PLAYER IN DATABASE
# ============================================================

new_function = r'''

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
'''

if "def build_all_database_add_options(" not in sim_text:
    sim_text = sim_text.rstrip() + "\n\n" + new_function + "\n"

sim_path.write_text(sim_text, encoding="utf-8")


# ============================================================
# 2. PATCH PAGE IMPORT
# ============================================================

if "build_all_database_add_options" not in page_text:
    page_text = page_text.replace(
        "    build_current_squad_options,\n",
        "    build_all_database_add_options,\n    build_current_squad_options,\n",
        1,
    )


# ============================================================
# 3. PATCH SQUAD IMPACT SIMULATOR UI
# ============================================================

old_block = '''        remove_options = build_current_squad_options(df, your_club)
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
'''

new_block = '''        remove_options = build_current_squad_options(df, your_club)

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
'''

if old_block not in page_text:
    raise SystemExit("Could not find Squad Impact Simulator add/remove block to patch.")

page_text = page_text.replace(old_block, new_block, 1)

page_path.write_text(page_text, encoding="utf-8")

print("Squad Impact Simulator can now add/sign any player in the database.")
