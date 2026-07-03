from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))
from fm_engine.ui_memory import init_page_memory, save_page_memory

from fm_engine.fast_data import (
    get_file_signature,
    list_saved_files as fast_list_saved_files,
    load_fm_file_cached,
)

UPLOAD_DIR = PROJECT_ROOT / "data" / "uploads"


def load_page_file(path: Path) -> pd.DataFrame:
    path_text, mtime, size = get_file_signature(path)
    return load_fm_file_cached(path_text, mtime, size).copy()


ROLE_PROFILES = {
    "Ball Playing Defender": {
        "attributes": {
            "Pas": 1.20,
            "Fir": 1.10,
            "Tec": 1.00,
            "Cmp": 1.10,
            "Dec": 1.15,
            "Pos": 1.15,
            "Ant": 1.10,
            "Tck": 1.00,
            "Str": 0.90,
            "Pac": 0.80,
        },
        "description": "A defender who can defend space, stay composed, and progress the ball from the back.",
    },
    "Inverted Fullback": {
        "attributes": {
            "Pas": 1.20,
            "Fir": 1.10,
            "Tec": 1.05,
            "Dec": 1.20,
            "Pos": 1.10,
            "Tea": 1.10,
            "Tck": 0.95,
            "Sta": 1.00,
            "Acc": 0.85,
        },
        "description": "A wide defender who can step inside, support buildup, and help control midfield.",
    },
    "Deep Lying Playmaker": {
        "attributes": {
            "Pas": 1.30,
            "Fir": 1.15,
            "Tec": 1.10,
            "Vis": 1.25,
            "Dec": 1.25,
            "Cmp": 1.15,
            "Ant": 1.00,
            "Tea": 1.00,
            "Pos": 0.90,
        },
        "description": "A midfield hub who receives under pressure and controls the rhythm of possession.",
    },
    "Box To Box Midfielder": {
        "attributes": {
            "Sta": 1.30,
            "Wor": 1.25,
            "Tea": 1.10,
            "Pas": 1.00,
            "Tck": 1.00,
            "OtB": 1.00,
            "Dec": 1.00,
            "Acc": 0.90,
            "Str": 0.85,
        },
        "description": "A high-energy midfielder who contributes in both attack and defense.",
    },
    "Advanced Playmaker": {
        "attributes": {
            "Pas": 1.25,
            "Fir": 1.15,
            "Tec": 1.20,
            "Vis": 1.30,
            "Fla": 1.10,
            "Dec": 1.15,
            "Cmp": 1.05,
            "OtB": 0.95,
            "Dri": 0.95,
        },
        "description": "A creative midfielder who finds final balls and unlocks defensive blocks.",
    },
    "Inside Forward": {
        "attributes": {
            "Dri": 1.20,
            "Fin": 1.15,
            "Fir": 1.05,
            "Tec": 1.10,
            "OtB": 1.15,
            "Acc": 1.05,
            "Pac": 1.05,
            "Cmp": 0.95,
            "Dec": 0.95,
        },
        "description": "A wide attacker who cuts inside to create and score.",
    },
    "Pressing Forward": {
        "attributes": {
            "Wor": 1.30,
            "Sta": 1.20,
            "Agg": 1.05,
            "Ant": 1.00,
            "Acc": 1.00,
            "Pac": 1.00,
            "Fin": 1.00,
            "OtB": 1.05,
            "Tea": 1.10,
        },
        "description": "A forward who leads the press, attacks space, and creates pressure from the front.",
    },
    "Complete Forward": {
        "attributes": {
            "Fin": 1.20,
            "Fir": 1.10,
            "Tec": 1.05,
            "Pas": 0.95,
            "OtB": 1.15,
            "Cmp": 1.05,
            "Dec": 1.00,
            "Pac": 1.00,
            "Str": 1.00,
            "Hea": 0.90,
        },
        "description": "A striker who can score, link play, run channels, and lead the line.",
    },
}


IDENTITY_COLUMNS = [
    "Name",
    "Age",
    "Nat",
    "Club",
    "Division",
    "League",
    "Position",
    "Primary Position",
    "Position Group",
    "Transfer Value",
    "Wage",
]


def base_column_name(col: str) -> str:
    return re.sub(r"__\d+$", "", str(col))


def make_unique_columns(columns) -> list[str]:
    seen = {}
    fixed = []

    for col in columns:
        base = str(col).strip()

        if base == "" or base.lower().startswith("unnamed"):
            base = "Unknown"

        key = base.lower()

        if key not in seen:
            seen[key] = 1
            fixed.append(base)
        else:
            seen[key] += 1
            fixed.append(f"{base}__{seen[key]}")

    return fixed


def load_file(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()

    if suffix == ".csv":
        df = pd.read_csv(path)

    elif suffix in [".xlsx", ".xls"]:
        df = pd.read_excel(path)

    elif suffix in [".html", ".htm"]:
        tables = pd.read_html(path)
        df = max(tables, key=lambda table: table.shape[0] * table.shape[1])

    else:
        raise ValueError("Unsupported file type.")

    df.columns = make_unique_columns(df.columns)
    df = df.dropna(axis=0, how="all")
    df = df.dropna(axis=1, how="all")
    df = df.drop_duplicates()

    return df


def find_column(df: pd.DataFrame, possible_names: list[str]) -> str | None:
    wanted = {name.lower() for name in possible_names}

    for col in df.columns:
        if base_column_name(col).lower() in wanted:
            return col

    return None


def score_player_for_role(row: pd.Series, role_name: str) -> float:
    role = ROLE_PROFILES[role_name]
    weighted_total = 0.0
    weight_sum = 0.0

    for attr, weight in role["attributes"].items():
        matching_col = None

        for col in row.index:
            if base_column_name(col) == attr:
                matching_col = col
                break

        if matching_col is None:
            continue

        value = pd.to_numeric(row[matching_col], errors="coerce")

        if pd.isna(value):
            continue

        weighted_total += float(value) * weight
        weight_sum += weight

    if weight_sum == 0:
        return 0.0

    average_out_of_20 = weighted_total / weight_sum
    score_out_of_100 = (average_out_of_20 / 20) * 100

    return round(score_out_of_100, 1)


def add_role_fit_score(df: pd.DataFrame, role_name: str) -> pd.DataFrame:
    df = df.copy()

    score_col = f"{role_name} Fit Score"
    df[score_col] = df.apply(lambda row: score_player_for_role(row, role_name), axis=1)

    return df.sort_values(score_col, ascending=False)


def classify_position(position: str) -> str:
    text = str(position).upper().replace(" ", "")

    if "GK" in text:
        return "Goalkeeper"

    if any(x in text for x in ["D(C)", "DC"]):
        return "Center Back"

    if any(x in text for x in ["D(R)", "D(L)", "DR", "DL", "WB"]):
        return "Fullback / Wingback"

    if "DM" in text:
        return "Defensive Midfielder"

    if any(x in text for x in ["M(C)", "MC"]):
        return "Central Midfielder"

    if any(x in text for x in ["AM(C)", "AMC"]):
        return "Attacking Midfielder"

    if any(x in text for x in ["AM(R)", "AM(L)", "AML", "AMR", "M(R)", "M(L)"]):
        return "Wide Player"

    if any(x in text for x in ["ST", "SC", "CF"]):
        return "Striker"

    return "Unknown"


def add_position_group(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    position_col = find_column(df, ["Position", "Positions"])

    if position_col:
        df["Position Group"] = df[position_col].apply(classify_position)
    else:
        df["Position Group"] = "Unknown"

    return df


def get_display_columns(df: pd.DataFrame, score_col: str) -> list[str]:
    cols = []

    for wanted in IDENTITY_COLUMNS:
        match = find_column(df, [wanted])
        if match and match not in cols:
            cols.append(match)

    if score_col in df.columns:
        cols.append(score_col)

    role_attrs = set()
    for role in ROLE_PROFILES.values():
        role_attrs.update(role["attributes"].keys())

    for col in df.columns:
        if base_column_name(col) in role_attrs and col not in cols:
            cols.append(col)

    return cols


st.set_page_config(
    page_title="Role Fit Scouting",
    page_icon="🎯",
    layout="wide",
)

init_page_memory(__file__)

st.title("Role Fit Scouting")

st.write(
    """
    This page ranks players by how well they fit a tactical role.
    The score is based on FM attributes weighted by role importance.
    """
)

saved_files = sorted(
    [
        file for file in UPLOAD_DIR.iterdir()
        if file.suffix.lower() in [".csv", ".xlsx", ".xls", ".html", ".htm"]
    ],
    key=lambda file: file.stat().st_mtime,
    reverse=True,
)

if not saved_files:
    st.info("Upload a player database on the main dashboard first.")
    st.stop()

selected_file = st.sidebar.selectbox(
    "Choose Saved Player Database",
    saved_files,
    format_func=lambda path: path.name,
)

role_name = st.sidebar.selectbox(
    "Choose Tactical Role",
    list(ROLE_PROFILES.keys()),
)

top_n = st.sidebar.slider(
    "Number of Players to Show",
    min_value=10,
    max_value=200,
    value=50,
    step=10,
)

df = load_page_file(selected_file)
df = add_position_group(df)

league_col = find_column(df, ["Division", "League"])
position_group_col = find_column(df, ["Position Group"])
age_col = find_column(df, ["Age"])

if league_col:
    leagues = sorted(df[league_col].dropna().astype(str).unique().tolist())
    selected_leagues = st.sidebar.multiselect("Leagues / Divisions", leagues)

    if selected_leagues:
        df = df[df[league_col].astype(str).isin(selected_leagues)]

if position_group_col:
    groups = sorted(df[position_group_col].dropna().astype(str).unique().tolist())
    selected_groups = st.sidebar.multiselect("Position Groups", groups)

    if selected_groups:
        df = df[df[position_group_col].astype(str).isin(selected_groups)]

if age_col:
    numeric_age = pd.to_numeric(df[age_col], errors="coerce")

    if numeric_age.notna().any():
        min_age = int(numeric_age.min())
        max_age = int(numeric_age.max())

        age_range = st.sidebar.slider(
            "Age Range",
            min_value=min_age,
            max_value=max_age,
            value=(min_age, max_age),
        )

        df = df[numeric_age.between(age_range[0], age_range[1], inclusive="both")]

score_col = f"{role_name} Fit Score"
ranked_df = add_role_fit_score(df, role_name)

st.subheader(role_name)
st.write(ROLE_PROFILES[role_name]["description"])

st.metric("Players Analyzed", f"{len(ranked_df):,}")

display_cols = get_display_columns(ranked_df, score_col)

st.dataframe(
    ranked_df[display_cols].head(top_n),
    use_container_width=True,
    height=650,
)

st.download_button(
    label="Download Role Fit Rankings",
    data=ranked_df[display_cols].to_csv(index=False).encode("utf-8"),
    file_name=f"{role_name.lower().replace(' ', '_')}_rankings.csv",
    mime="text/csv",
)

save_page_memory(__file__)
