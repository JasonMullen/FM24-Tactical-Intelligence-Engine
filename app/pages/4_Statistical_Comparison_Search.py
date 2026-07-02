from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd
import streamlit as st
from sklearn.metrics.pairwise import cosine_similarity

PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from fm_engine.fast_data import (
    get_file_signature,
    list_saved_files as fast_list_saved_files,
    load_fm_file_cached,
)

UPLOAD_DIR = PROJECT_ROOT / "data" / "uploads"


def load_page_file(path: Path) -> pd.DataFrame:
    path_text, mtime, size = get_file_signature(path)
    return load_fm_file_cached(path_text, mtime, size).copy()

STAT_COLUMNS = [
    "Apps", "Starts", "Mins", "Gls", "Ast", "xG", "xA", "Av Rat",
    "Shots", "ShT", "Tck/90", "Int/90", "Drb/90", "Cr C", "Rec",
    "Gls/90", "xG/90", "xA/90", "Shot/90", "Shot %", "ShT/90",
    "Poss Won/90", "Poss Lost/90", "Ps C/90", "Ps C", "Ps A/90",
    "Ps A", "Pas %", "OP-KP/90", "OP-KP", "OP-Crs C/90",
    "OP-Crs C", "OP-Crs A/90", "OP-Crs A", "OP-Cr %",
    "K Tck/90", "K Tck", "K Ps/90", "K Pas", "Itc",
    "Sprints/90", "Hdr %", "Hdrs W/90", "Hdrs", "Hdrs L/90",
    "xGP/90", "xGP", "xG/shot", "Dist/90", "Distance",
    "Cr C/90", "Crs A/90", "CrA", "CrC/A", "Conv %",
    "Clr/90", "Clear", "CCC", "Ch C/90", "Blk/90", "Blk",
    "Asts/90", "Aer A/90"
]

IDENTITY_COLUMNS = [
    "Name", "Age", "Nat", "Club", "Division", "League", "Position",
    "Primary Position", "Position Group", "Transfer Value", "Value", "Wage"
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


def find_column(df: pd.DataFrame, possible_names: list[str]) -> str | None:
    wanted = {name.lower() for name in possible_names}

    for col in df.columns:
        if base_column_name(col).lower() in wanted:
            return col

    return None


def get_existing_stats(df: pd.DataFrame) -> list[str]:
    wanted = {col.lower() for col in STAT_COLUMNS}
    stats = []

    for col in df.columns:
        if base_column_name(col).lower() in wanted and col not in stats:
            stats.append(col)

    return stats


def get_identity_cols(df: pd.DataFrame) -> list[str]:
    cols = []

    for wanted in IDENTITY_COLUMNS:
        match = find_column(df, [wanted])
        if match and match not in cols:
            cols.append(match)

    return cols


def apply_filters(df: pd.DataFrame) -> pd.DataFrame:
    filtered = df.copy()

    st.sidebar.subheader("Search Pool Filters")

    league_col = find_column(filtered, ["Division", "League"])
    club_col = find_column(filtered, ["Club"])
    position_col = find_column(filtered, ["Position", "Primary Position", "Position Group"])
    age_col = find_column(filtered, ["Age"])

    if league_col:
        values = sorted(filtered[league_col].dropna().astype(str).unique().tolist())
        selected = st.sidebar.multiselect("Leagues / Divisions", values)
        if selected:
            filtered = filtered[filtered[league_col].astype(str).isin(selected)]

    if club_col:
        values = sorted(filtered[club_col].dropna().astype(str).unique().tolist())
        selected = st.sidebar.multiselect("Clubs", values)
        if selected:
            filtered = filtered[filtered[club_col].astype(str).isin(selected)]

    if position_col:
        values = sorted(filtered[position_col].dropna().astype(str).unique().tolist())
        selected = st.sidebar.multiselect("Positions / Position Groups", values)
        if selected:
            filtered = filtered[filtered[position_col].astype(str).isin(selected)]

    if age_col:
        age_num = pd.to_numeric(filtered[age_col], errors="coerce")
        if age_num.notna().any():
            min_age = int(age_num.min())
            max_age = int(age_num.max())
            selected_range = st.sidebar.slider(
                "Age Range",
                min_value=min_age,
                max_value=max_age,
                value=(min_age, max_age),
            )
            filtered = filtered[age_num.between(selected_range[0], selected_range[1], inclusive="both")]

    return filtered


def build_stat_matrix(df: pd.DataFrame, stat_cols: list[str]) -> pd.DataFrame:
    matrix = df[stat_cols].apply(pd.to_numeric, errors="coerce")
    matrix = matrix.fillna(matrix.median(numeric_only=True))
    matrix = matrix.fillna(0)
    return matrix


def find_similar_by_stats(
    df: pd.DataFrame,
    target_index: int,
    stat_cols: list[str],
    top_n: int,
) -> pd.DataFrame:
    matrix = build_stat_matrix(df, stat_cols)
    target_vector = matrix.loc[[target_index]]

    scores = cosine_similarity(target_vector, matrix)[0]

    result = df.copy()
    result["Statistical Similarity Score"] = scores
    result["Statistical Similarity %"] = (scores * 100).round(1)

    result = result[result.index != target_index]
    result = result.sort_values("Statistical Similarity Score", ascending=False)

    return result.head(top_n)


def build_stat_comparison(
    df: pd.DataFrame,
    target_index: int,
    comparison_index: int,
    stat_cols: list[str],
    name_col: str,
) -> pd.DataFrame:
    target_name = df.loc[target_index, name_col]
    comparison_name = df.loc[comparison_index, name_col]

    rows = []

    for col in stat_cols:
        target_value = pd.to_numeric(df.loc[target_index, col], errors="coerce")
        comparison_value = pd.to_numeric(df.loc[comparison_index, col], errors="coerce")

        rows.append(
            {
                "Statistic": base_column_name(col),
                str(target_name): target_value,
                str(comparison_name): comparison_value,
                "Difference": comparison_value - target_value
                if pd.notna(target_value) and pd.notna(comparison_value)
                else None,
            }
        )

    return pd.DataFrame(rows)


st.set_page_config(
    page_title="Statistical Comparison Search",
    page_icon="📊",
    layout="wide",
)

st.title("Statistical Comparison Search")

st.write(
    """
    Search a player and find the most statistically similar players based on selected performance stats.
    This is separate from attribute similarity.
    """
)

saved_files = fast_list_saved_files()

if not saved_files:
    st.info("Upload your FM24 database on the main dashboard first.")
    st.stop()

selected_file = st.sidebar.selectbox(
    "Choose Saved Database",
    saved_files,
    format_func=lambda path: path.name,
)

df = load_page_file(selected_file)
name_col = find_column(df, ["Name", "Player"])

if not name_col:
    st.error("No Name column found.")
    st.stop()

existing_stats = get_existing_stats(df)

if not existing_stats:
    st.error("No stat columns found in this file.")
    st.stop()

default_stats = [
    col for col in existing_stats
    if base_column_name(col) in ["Av Rat", "Gls/90", "Asts/90", "xG/90", "xA/90", "Pas %", "Tck/90", "Int/90"]
]

if not default_stats:
    default_stats = existing_stats[:8]

selected_stats = st.sidebar.multiselect(
    "Stats Used For Comparison",
    existing_stats,
    default=default_stats,
)

top_n = st.sidebar.slider("Number of Similar Players", 5, 100, 25, step=5)

search_text = st.text_input("Search Player Name")

if not search_text:
    st.info("Type a player name to begin.")
    st.stop()

matches = df[df[name_col].astype(str).str.contains(search_text, case=False, na=False)].copy()

if matches.empty:
    st.warning("No matching players found.")
    st.stop()

club_col = find_column(df, ["Club"])
position_col = find_column(df, ["Position"])

label = matches[name_col].astype(str)

if club_col:
    label = label + " | " + matches[club_col].astype(str)

if position_col:
    label = label + " | " + matches[position_col].astype(str)

matches["Search Label"] = label

selected_label = st.selectbox("Choose Player", matches["Search Label"].tolist())
target_index = matches[matches["Search Label"] == selected_label].index[0]
target_name = df.loc[target_index, name_col]

search_pool = apply_filters(df)

if target_index not in search_pool.index:
    search_pool = pd.concat([df.loc[[target_index]], search_pool], axis=0)

similar_df = find_similar_by_stats(
    search_pool,
    target_index=target_index,
    stat_cols=selected_stats,
    top_n=top_n,
)

identity_cols = get_identity_cols(similar_df)
display_cols = identity_cols + ["Statistical Similarity %"] + selected_stats
display_cols = [col for col in display_cols if col in similar_df.columns]

st.subheader(f"Most Statistically Similar Players to {target_name}")

with st.expander("Target Player Stats", expanded=True):
    st.dataframe(
        df.loc[[target_index], identity_cols + selected_stats],
        use_container_width=True,
        height=150,
    )

st.dataframe(
    similar_df[display_cols],
    use_container_width=True,
    height=650,
)

st.download_button(
    label="Download Statistical Comparison Results",
    data=similar_df[display_cols].to_csv(index=False).encode("utf-8"),
    file_name=f"statistical_comparison_{str(target_name).replace(' ', '_')}.csv",
    mime="text/csv",
)

st.subheader("Direct Stat Comparison")

if not similar_df.empty:
    options = (
        similar_df[name_col].astype(str)
        + " | "
        + similar_df["Statistical Similarity %"].astype(str)
        + "%"
    ).tolist()

    selected_comparison = st.selectbox("Choose Player To Compare", options)
    comparison_index = similar_df.index[options.index(selected_comparison)]

    comparison_df = build_stat_comparison(
        df=df,
        target_index=target_index,
        comparison_index=comparison_index,
        stat_cols=selected_stats,
        name_col=name_col,
    )

    st.dataframe(comparison_df, use_container_width=True, height=650)
