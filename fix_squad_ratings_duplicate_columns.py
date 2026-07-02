from pathlib import Path

path = Path("app/pages/10_Squad_And_League_Strength_Ratings.py")
text = path.read_text(encoding="utf-8")

helper = r'''

# ============================================================
# STREAMLIT SAFE DISPLAY HELPERS
# ============================================================

def unique_column_list(columns: list[str]) -> list[str]:
    seen = set()
    clean = []

    for col in columns:
        if col in seen:
            continue

        seen.add(col)
        clean.append(col)

    return clean


def make_streamlit_safe_df(df: pd.DataFrame) -> pd.DataFrame:
    safe_df = df.copy()
    seen = {}
    new_columns = []

    for col in safe_df.columns:
        base = str(col)

        if base not in seen:
            seen[base] = 1
            new_columns.append(base)
        else:
            seen[base] += 1
            new_columns.append(f"{base} [{seen[base]}]")

    safe_df.columns = new_columns

    return safe_df
'''

marker = "# ============================================================\n# STREAMLIT APP"
if "def make_streamlit_safe_df" not in text:
    text = text.replace(marker, helper + "\n\n" + marker)

replacements = {
    "main_cols = [col for col in main_cols if col in filtered_team_ratings.columns]":
    "main_cols = unique_column_list([col for col in main_cols if col in filtered_team_ratings.columns])",

    "display_cols = [col for col in display_cols if col in best_by_league.columns]":
    "display_cols = unique_column_list([col for col in display_cols if col in best_by_league.columns])",

    "category_cols = [col for col in category_cols if col in filtered_team_ratings.columns]":
    "category_cols = unique_column_list([col for col in category_cols if col in filtered_team_ratings.columns])",

    "player_display_cols = [\n        col for col in identity_cols + score_cols\n        if col in df.columns\n    ]":
    "player_display_cols = unique_column_list([\n        col for col in identity_cols + score_cols\n        if col in df.columns\n    ])",

    "filtered_team_ratings[main_cols],":
    "make_streamlit_safe_df(filtered_team_ratings[main_cols]),",

    "best_by_league[display_cols],":
    "make_streamlit_safe_df(best_by_league[display_cols]),",

    "club_xi.sort_values(\"Slot\"),":
    "make_streamlit_safe_df(club_xi.sort_values(\"Slot\")),",

    "filtered_team_ratings[category_cols],":
    "make_streamlit_safe_df(filtered_team_ratings[category_cols]),",

    "player_df,":
    "make_streamlit_safe_df(player_df),",

    "data=filtered_team_ratings[main_cols].to_csv(index=False).encode(\"utf-8\"),":
    "data=make_streamlit_safe_df(filtered_team_ratings[main_cols]).to_csv(index=False).encode(\"utf-8\"),",

    "data=best_by_league[display_cols].to_csv(index=False).encode(\"utf-8\"),":
    "data=make_streamlit_safe_df(best_by_league[display_cols]).to_csv(index=False).encode(\"utf-8\"),",

    "data=player_df.to_csv(index=False).encode(\"utf-8\"),":
    "data=make_streamlit_safe_df(player_df).to_csv(index=False).encode(\"utf-8\"),",
}

for old, new in replacements.items():
    text = text.replace(old, new)

path.write_text(text, encoding="utf-8")
print("Fixed duplicate column display errors in Squad & League Strength Ratings.")
