from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(PROJECT_ROOT))

from fm_engine.role_profiles import ROLE_PROFILES

UPLOAD_DIR = PROJECT_ROOT / "data" / "uploads"

IDENTITY_COLUMNS = [
    "Name", "Age", "Nat", "Club", "Division", "League",
    "Position", "Transfer Value", "Value", "Wage"
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


def find_column(df: pd.DataFrame, possible_names: list[str]) -> str | None:
    wanted = {name.lower() for name in possible_names}

    for col in df.columns:
        if base_column_name(col).lower() in wanted:
            return col

    return None


def list_saved_files() -> list[Path]:
    allowed = {".csv", ".xlsx", ".xls", ".html", ".htm"}

    if not UPLOAD_DIR.exists():
        return []

    return sorted(
        [file for file in UPLOAD_DIR.iterdir() if file.suffix.lower() in allowed],
        key=lambda file: file.stat().st_mtime,
        reverse=True,
    )


def load_file(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".csv":
        df = pd.read_csv(path)
    elif path.suffix.lower() in [".xlsx", ".xls"]:
        df = pd.read_excel(path)
    elif path.suffix.lower() in [".html", ".htm"]:
        tables = pd.read_html(path)
        df = max(tables, key=lambda table: table.shape[0] * table.shape[1])
    else:
        raise ValueError("Unsupported file type.")

    df.columns = make_unique_columns(df.columns)
    df = df.dropna(axis=0, how="all")
    df = df.dropna(axis=1, how="all")
    df = df.drop_duplicates()
    return df


def get_identity_cols(df: pd.DataFrame) -> list[str]:
    cols = []

    for wanted in IDENTITY_COLUMNS:
        match = find_column(df, [wanted])
        if match and match not in cols:
            cols.append(match)

    return cols


def get_matching_column(df: pd.DataFrame, base_name: str) -> str | None:
    for col in df.columns:
        if base_column_name(col) == base_name:
            return col
    return None


def weighted_attribute_score(row: pd.Series, role_name: str) -> float:
    weights = ROLE_PROFILES[role_name]["attributes"]

    total = 0.0
    weight_total = 0.0

    for attr, weight in weights.items():
        col = None

        for candidate in row.index:
            if base_column_name(candidate) == attr:
                col = candidate
                break

        if col is None:
            continue

        value = pd.to_numeric(row[col], errors="coerce")

        if pd.isna(value):
            continue

        total += float(value) * weight
        weight_total += weight

    if weight_total == 0:
        return 0.0

    return round(((total / weight_total) / 20) * 100, 1)


def percentile_score(series: pd.Series, higher_is_better: bool = True) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")

    if numeric.notna().sum() <= 1:
        return pd.Series([50.0] * len(series), index=series.index)

    ranks = numeric.rank(pct=True) * 100

    if not higher_is_better:
        ranks = 100 - ranks

    return ranks.fillna(50)


def add_role_performance_score(df: pd.DataFrame, role_name: str) -> pd.DataFrame:
    df = df.copy()

    attr_col = f"{role_name} Attribute Fit"
    stat_col = f"{role_name} Stat Performance"
    final_col = f"{role_name} Final Performance Score"

    df[attr_col] = df.apply(lambda row: weighted_attribute_score(row, role_name), axis=1)

    stat_names = ROLE_PROFILES[role_name].get("stats", [])
    available_stats = []

    for stat in stat_names:
        match = get_matching_column(df, stat)
        if match:
            available_stats.append(match)

    if available_stats:
        stat_scores = []

        lower_is_better = {"Poss Lost/90", "Fls", "Conc", "G. Mis"}

        for stat in available_stats:
            base = base_column_name(stat)
            stat_scores.append(
                percentile_score(df[stat], higher_is_better=base not in lower_is_better)
            )

        stat_matrix = pd.concat(stat_scores, axis=1)
        df[stat_col] = stat_matrix.mean(axis=1).round(1)
    else:
        df[stat_col] = 50.0

    df[final_col] = (
        df[attr_col] * 0.60
        + df[stat_col] * 0.40
    ).round(1)

    return df.sort_values(final_col, ascending=False)


def apply_filters(df: pd.DataFrame) -> pd.DataFrame:
    filtered = df.copy()

    st.sidebar.subheader("Filters")

    league_col = find_column(filtered, ["Division", "League"])
    club_col = find_column(filtered, ["Club"])
    position_col = find_column(filtered, ["Position"])
    age_col = find_column(filtered, ["Age"])
    mins_col = find_column(filtered, ["Mins"])

    if league_col:
        values = sorted(filtered[league_col].dropna().astype(str).unique().tolist())
        selected = st.sidebar.multiselect("Leagues / Divisions", values)
        if selected:
            filtered = filtered[filtered[league_col].astype(str).isin(selected)]

    if position_col:
        values = sorted(filtered[position_col].dropna().astype(str).unique().tolist())
        selected = st.sidebar.multiselect("Positions", values)
        if selected:
            filtered = filtered[filtered[position_col].astype(str).isin(selected)]

    if club_col:
        values = sorted(filtered[club_col].dropna().astype(str).unique().tolist())
        selected = st.sidebar.multiselect("Clubs", values)
        if selected:
            filtered = filtered[filtered[club_col].astype(str).isin(selected)]

    if age_col:
        age_num = pd.to_numeric(filtered[age_col], errors="coerce")
        if age_num.notna().any():
            min_age = int(age_num.min())
            max_age = int(age_num.max())
            age_range = st.sidebar.slider("Age Range", min_age, max_age, (min_age, max_age))
            filtered = filtered[age_num.between(age_range[0], age_range[1], inclusive="both")]

    if mins_col:
        min_minutes = st.sidebar.number_input(
            "Minimum Minutes",
            min_value=0,
            value=300,
            step=100,
        )

        mins = pd.to_numeric(filtered[mins_col], errors="coerce")
        filtered = filtered[mins.fillna(0) >= min_minutes]

    return filtered


st.set_page_config(
    page_title="Top 10 Role Performers",
    page_icon="🏆",
    layout="wide",
)

st.title("Top 10 Performing Players by Role")

st.write(
    """
    This page ranks the best performers in each role using:
    - 60% role attribute fit
    - 40% role-relevant performance stats
    """
)

saved_files = list_saved_files()

if not saved_files:
    st.info("Upload your FM24 database on the main dashboard first.")
    st.stop()

selected_file = st.sidebar.selectbox(
    "Choose Saved Database",
    saved_files,
    format_func=lambda path: path.name,
)

df = load_file(selected_file)
df = apply_filters(df)

role_categories = sorted(set(role["category"] for role in ROLE_PROFILES.values()))

selected_category = st.sidebar.selectbox(
    "Role Category",
    ["All"] + role_categories,
)

available_roles = list(ROLE_PROFILES.keys())

if selected_category != "All":
    available_roles = [
        role_name for role_name, role in ROLE_PROFILES.items()
        if role["category"] == selected_category
    ]

selected_roles = st.sidebar.multiselect(
    "Choose Roles",
    available_roles,
    default=available_roles[:1],
)

if not selected_roles:
    st.info("Choose at least one role.")
    st.stop()

identity_cols = get_identity_cols(df)

for role_name in selected_roles:
    ranked_df = add_role_performance_score(df, role_name)

    attr_col = f"{role_name} Attribute Fit"
    stat_col = f"{role_name} Stat Performance"
    final_col = f"{role_name} Final Performance Score"

    role_stat_cols = []

    for stat in ROLE_PROFILES[role_name].get("stats", []):
        match = get_matching_column(ranked_df, stat)
        if match and match not in role_stat_cols:
            role_stat_cols.append(match)

    display_cols = identity_cols + [final_col, attr_col, stat_col] + role_stat_cols
    display_cols = [col for col in display_cols if col in ranked_df.columns]

    st.subheader(f"Top 10 — {role_name}")
    st.caption(ROLE_PROFILES[role_name]["description"])

    st.dataframe(
        ranked_df[display_cols].head(10),
        use_container_width=True,
        height=400,
    )
