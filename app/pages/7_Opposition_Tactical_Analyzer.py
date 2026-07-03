from __future__ import annotations

import json
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

sys.path.append(str(PROJECT_ROOT))

from fm_engine.role_profiles import ROLE_PROFILES

UPLOAD_DIR = PROJECT_ROOT / "data" / "uploads"


def load_page_file(path: Path) -> pd.DataFrame:
    path_text, mtime, size = get_file_signature(path)
    return load_fm_file_cached(path_text, mtime, size).copy()
TACTICS_DIR = PROJECT_ROOT / "configs" / "saved_tactics"


# ============================================================
# ATTRIBUTE / STAT GROUPS
# ============================================================

ATTACKING_ATTRIBUTES = {
    "Fin": 1.25,
    "OtB": 1.20,
    "Cmp": 1.10,
    "Acc": 1.00,
    "Pac": 1.00,
    "Fir": 0.95,
    "Tec": 0.95,
}

CREATIVE_ATTRIBUTES = {
    "Pas": 1.25,
    "Vis": 1.30,
    "Tec": 1.10,
    "Fir": 1.05,
    "Dec": 1.15,
    "Cmp": 1.00,
    "Fla": 0.95,
}

WIDE_THREAT_ATTRIBUTES = {
    "Pac": 1.15,
    "Acc": 1.15,
    "Dri": 1.20,
    "Cro": 1.20,
    "OtB": 1.00,
    "Tec": 0.95,
}

DEFENSIVE_ATTRIBUTES = {
    "Tck": 1.20,
    "Mar": 1.10,
    "Pos": 1.20,
    "Ant": 1.10,
    "Cnt": 1.05,
    "Str": 0.90,
    "Pac": 0.85,
}

PRESSING_ATTRIBUTES = {
    "Wor": 1.30,
    "Sta": 1.20,
    "Agg": 1.10,
    "Ant": 1.05,
    "Tea": 1.05,
    "Acc": 1.00,
}

PHYSICAL_ATTRIBUTES = {
    "Pac": 1.20,
    "Acc": 1.20,
    "Sta": 1.00,
    "Str": 0.90,
    "Agi": 0.95,
    "Bal": 0.90,
}

ATTACKING_STATS = [
    "Gls/90", "xG/90", "Shot/90", "ShT/90", "Conv %", "Gls", "xG"
]

CREATIVE_STATS = [
    "Asts/90", "xA/90", "OP-KP/90", "Ch C/90", "OP-KP", "Ch C", "xA"
]

WIDE_STATS = [
    "Cr C/90", "OP-Crs C/90", "Crs A/90", "CrA", "Drb/90", "Asts/90"
]

DEFENSIVE_STATS = [
    "Tck/90", "Int/90", "Poss Won/90", "Clear", "Blk/90", "Hdr %"
]


# ============================================================
# BASIC HELPERS
# ============================================================

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


def list_saved_tactics() -> list[Path]:
    if not TACTICS_DIR.exists():
        return []

    return sorted(TACTICS_DIR.glob("*.json"))


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


def load_tactic(path: Path | None) -> dict:
    if path is None:
        return {}

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ============================================================
# POSITION CLASSIFICATION
# ============================================================

POSITION_ORDER = [
    "GK", "CB", "RB", "LB", "RWB", "LWB",
    "DM", "CM", "RM", "LM", "AM", "RW", "LW", "ST"
]


def normalize_position_text(position_text: str) -> str:
    text = str(position_text).upper()
    text = text.replace(" ", "")
    text = text.replace("-", "")
    return text


def has_position(text: str, patterns: list[str]) -> bool:
    return any(pattern in text for pattern in patterns)


def classify_position_classes(position_text: str) -> list[str]:
    text = normalize_position_text(position_text)
    found = []

    if has_position(text, ["GK"]):
        found.append("GK")

    if has_position(text, ["D(C)", "DC", "SW"]):
        found.append("CB")

    if has_position(text, ["D(R)", "DR"]):
        found.append("RB")

    if has_position(text, ["D(L)", "DL"]):
        found.append("LB")

    if has_position(text, ["WB(R)", "WBR"]):
        found.append("RWB")

    if has_position(text, ["WB(L)", "WBL"]):
        found.append("LWB")

    if has_position(text, ["DM", "DM(C)"]):
        found.append("DM")

    if has_position(text, ["M(C)", "MC"]):
        found.append("CM")

    if has_position(text, ["M(R)", "MR"]):
        found.append("RM")

    if has_position(text, ["M(L)", "ML"]):
        found.append("LM")

    if has_position(text, ["AM(C)", "AMC"]):
        found.append("AM")

    if has_position(text, ["AM(R)", "AMR"]):
        found.append("RW")

    if has_position(text, ["AM(L)", "AML"]):
        found.append("LW")

    if has_position(text, ["ST", "ST(C)", "SC", "CF"]):
        found.append("ST")

    clean = []

    for pos in POSITION_ORDER:
        if pos in found and pos not in clean:
            clean.append(pos)

    return clean


def primary_position_from_classes(position_classes: list[str]) -> str:
    if not position_classes:
        return "Unknown"

    priority = [
        "GK", "ST", "AM", "RW", "LW", "CM", "DM",
        "CB", "RB", "LB", "RWB", "LWB", "RM", "LM"
    ]

    for pos in priority:
        if pos in position_classes:
            return pos

    return position_classes[0]


def position_line_from_classes(position_classes: list[str]) -> str:
    if not position_classes:
        return "Unknown"

    if "GK" in position_classes:
        return "Goalkeeper"

    if any(pos in position_classes for pos in ["CB", "RB", "LB", "RWB", "LWB"]):
        return "Defense"

    if any(pos in position_classes for pos in ["DM", "CM", "RM", "LM", "AM"]):
        return "Midfield"

    if any(pos in position_classes for pos in ["RW", "LW", "ST"]):
        return "Attack"

    return "Unknown"


def add_position_classification(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    position_col = find_column(df, ["Position", "Positions"])

    if not position_col:
        df["Position Classes"] = "Unknown"
        df["Primary Position"] = "Unknown"
        df["Position Line"] = "Unknown"
        return df

    classes_series = df[position_col].apply(classify_position_classes)

    df["Position Classes"] = classes_series.apply(
        lambda classes: ", ".join(classes) if classes else "Unknown"
    )

    df["Primary Position"] = classes_series.apply(primary_position_from_classes)
    df["Position Line"] = classes_series.apply(position_line_from_classes)

    return df


# ============================================================
# SCORING
# ============================================================

def find_attr_column(df_or_row, attr: str) -> str | None:
    columns = df_or_row.index if isinstance(df_or_row, pd.Series) else df_or_row.columns

    for col in columns:
        if base_column_name(col) == attr:
            return col

    return None


def weighted_attribute_score(row: pd.Series, weights: dict[str, float]) -> float:
    total = 0.0
    weight_total = 0.0

    for attr, weight in weights.items():
        col = find_attr_column(row, attr)

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


def get_matching_stat_columns(df: pd.DataFrame, stat_names: list[str]) -> list[str]:
    cols = []

    for stat in stat_names:
        for col in df.columns:
            if base_column_name(col) == stat and col not in cols:
                cols.append(col)

    return cols


def stat_score(df: pd.DataFrame, stat_names: list[str]) -> pd.Series:
    stat_cols = get_matching_stat_columns(df, stat_names)

    if not stat_cols:
        return pd.Series([50.0] * len(df), index=df.index)

    lower_is_better = {"Poss Lost/90", "Fls", "Conc", "G. Mis", "Lost"}

    score_parts = []

    for col in stat_cols:
        base = base_column_name(col)
        score_parts.append(
            percentile_score(df[col], higher_is_better=base not in lower_is_better)
        )

    return pd.concat(score_parts, axis=1).mean(axis=1).round(1)


def add_threat_scores(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    df["Attacking Threat"] = df.apply(
        lambda row: weighted_attribute_score(row, ATTACKING_ATTRIBUTES),
        axis=1,
    )

    df["Creative Threat"] = df.apply(
        lambda row: weighted_attribute_score(row, CREATIVE_ATTRIBUTES),
        axis=1,
    )

    df["Wide Threat"] = df.apply(
        lambda row: weighted_attribute_score(row, WIDE_THREAT_ATTRIBUTES),
        axis=1,
    )

    df["Defensive Strength"] = df.apply(
        lambda row: weighted_attribute_score(row, DEFENSIVE_ATTRIBUTES),
        axis=1,
    )

    df["Pressing Intensity"] = df.apply(
        lambda row: weighted_attribute_score(row, PRESSING_ATTRIBUTES),
        axis=1,
    )

    df["Physical Power"] = df.apply(
        lambda row: weighted_attribute_score(row, PHYSICAL_ATTRIBUTES),
        axis=1,
    )

    df["Attacking Stat Score"] = stat_score(df, ATTACKING_STATS)
    df["Creative Stat Score"] = stat_score(df, CREATIVE_STATS)
    df["Wide Stat Score"] = stat_score(df, WIDE_STATS)
    df["Defensive Stat Score"] = stat_score(df, DEFENSIVE_STATS)

    df["Overall Danger Score"] = (
        df["Attacking Threat"] * 0.30
        + df["Creative Threat"] * 0.25
        + df["Wide Threat"] * 0.15
        + df["Attacking Stat Score"] * 0.15
        + df["Creative Stat Score"] * 0.15
    ).round(1)

    df["Weak Link Score"] = (
        100 - (
            df["Defensive Strength"] * 0.50
            + df["Physical Power"] * 0.20
            + df["Defensive Stat Score"] * 0.30
        )
    ).round(1)

    return df


def role_fit_score(row: pd.Series, role_name: str) -> float:
    role = ROLE_PROFILES.get(role_name)

    if not role:
        return 0.0

    return weighted_attribute_score(row, role["attributes"])


# ============================================================
# DISPLAY HELPERS
# ============================================================

IDENTITY_COLS = [
    "Name", "Age", "Nat", "Club", "Division", "League", "Position",
    "Primary Position", "Position Classes", "Transfer Value", "Value", "Wage"
]


def get_identity_cols(df: pd.DataFrame) -> list[str]:
    cols = []

    for wanted in IDENTITY_COLS:
        match = find_column(df, [wanted])
        if match and match not in cols:
            cols.append(match)

    return cols


def build_display_cols(df: pd.DataFrame, score_cols: list[str]) -> list[str]:
    cols = get_identity_cols(df)

    for col in score_cols:
        if col in df.columns and col not in cols:
            cols.append(col)

    return [col for col in cols if col in df.columns]


def club_filter(df: pd.DataFrame, club_name: str) -> pd.DataFrame:
    club_col = find_column(df, ["Club"])

    if not club_col:
        return df.iloc[0:0].copy()

    return df[df[club_col].astype(str) == club_name].copy()


def get_club_options(df: pd.DataFrame) -> list[str]:
    club_col = find_column(df, ["Club"])

    if not club_col:
        return []

    return sorted(df[club_col].dropna().astype(str).unique().tolist())


# ============================================================
# TACTICAL ANALYSIS TEXT
# ============================================================

def generate_opposition_plan(opponent_df: pd.DataFrame) -> list[str]:
    if opponent_df.empty:
        return ["No opponent data available."]

    avg_attack = opponent_df["Attacking Threat"].mean()
    avg_creative = opponent_df["Creative Threat"].mean()
    avg_wide = opponent_df["Wide Threat"].mean()
    avg_press = opponent_df["Pressing Intensity"].mean()
    avg_defense = opponent_df["Defensive Strength"].mean()
    avg_physical = opponent_df["Physical Power"].mean()

    plan = []

    if avg_wide >= 65:
        plan.append(
            "Opponent has strong wide threat. Protect the flanks, stop crosses early, and avoid leaving fullbacks isolated."
        )

    if avg_creative >= 65:
        plan.append(
            "Opponent has strong creators. Screen central zones, press their playmakers, and deny space between the lines."
        )

    if avg_attack >= 65:
        plan.append(
            "Opponent has dangerous finishers. Reduce space behind the defensive line and avoid giving up transition chances."
        )

    if avg_press >= 65:
        plan.append(
            "Opponent can press aggressively. Use calmer buildup, goalkeeper distribution options, and an extra short passing outlet."
        )

    if avg_defense < 55:
        plan.append(
            "Opponent defensive quality looks exploitable. Increase attacking width, create overloads, and target their weakest defender."
        )

    if avg_physical < 55:
        plan.append(
            "Opponent lacks physical power. Increase tempo, attack space, and use aggressive runners to stretch them."
        )

    if not plan:
        plan.append(
            "Opponent profile is balanced. Use your normal tactic, but monitor chance creation zones and transition danger."
        )

    return plan


def generate_exploit_recommendations(opponent_df: pd.DataFrame) -> list[str]:
    recommendations = []

    if opponent_df.empty:
        return ["No opponent data available."]

    weak_links = opponent_df.sort_values("Weak Link Score", ascending=False).head(3)

    for _, row in weak_links.iterrows():
        name = row.get(find_column(opponent_df, ["Name"]) or "Name", "Unknown")
        position = row.get(find_column(opponent_df, ["Position"]) or "Position", "Unknown")
        weakness = row.get("Weak Link Score", 0)

        recommendations.append(
            f"Target {name} ({position}). Weak Link Score: {weakness}. Look to isolate this player with pace, movement, or overloads."
        )

    return recommendations


# ============================================================
# STREAMLIT APP
# ============================================================

st.set_page_config(
    page_title="Opposition Tactical Analyzer",
    page_icon="🧩",
    layout="wide",
)

init_page_memory(__file__)

st.title("Opposition Tactical Analyzer")

st.write(
    """
    Analyze an opponent club, identify threats and weaknesses, then connect the report
    to your saved tactic/philosophy.
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

raw_df = load_page_file(selected_file)
df = add_position_classification(raw_df)
df = add_threat_scores(df)

club_options = get_club_options(df)

if not club_options:
    st.error("No club column found in this database.")
    st.stop()

st.sidebar.header("Match Setup")

your_club = st.sidebar.selectbox("Your Club", club_options)
opponent_club = st.sidebar.selectbox("Opponent Club", club_options)

saved_tactics = list_saved_tactics()

selected_tactic_path = None

if saved_tactics:
    selected_tactic_path = st.sidebar.selectbox(
        "Saved Tactic / Philosophy",
        [None] + saved_tactics,
        format_func=lambda path: "None selected" if path is None else path.name,
    )
else:
    st.sidebar.info("No saved tactic found yet. Use the Tactic Philosophy Builder page first.")

tactic = load_tactic(selected_tactic_path) if selected_tactic_path else {}

your_df = club_filter(df, your_club)
opponent_df = club_filter(df, opponent_club)

st.subheader(f"{your_club} vs {opponent_club}")

if tactic:
    st.info(
        f"Loaded tactic: {tactic.get('tactic_name', 'Unnamed')} | Formation: {tactic.get('formation', 'Unknown')} | Philosophy: {', '.join(tactic.get('philosophy', []))}"
    )

if your_df.empty:
    st.warning("No players found for your selected club.")

if opponent_df.empty:
    st.warning("No players found for the opponent club.")
    st.stop()

# ============================================================
# TEAM PROFILE
# ============================================================

st.subheader("Opponent Team Profile")

profile_cols = st.columns(6)

profile_cols[0].metric("Attack", f"{opponent_df['Attacking Threat'].mean():.1f}")
profile_cols[1].metric("Creativity", f"{opponent_df['Creative Threat'].mean():.1f}")
profile_cols[2].metric("Wide Threat", f"{opponent_df['Wide Threat'].mean():.1f}")
profile_cols[3].metric("Defense", f"{opponent_df['Defensive Strength'].mean():.1f}")
profile_cols[4].metric("Pressing", f"{opponent_df['Pressing Intensity'].mean():.1f}")
profile_cols[5].metric("Physical", f"{opponent_df['Physical Power'].mean():.1f}")

st.divider()

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    [
        "Main Threats",
        "Weak Links",
        "Tactical Plan",
        "Our Best Matchups",
        "Full Opponent Report",
    ]
)

# ============================================================
# MAIN THREATS
# ============================================================

with tab1:
    st.subheader("Opponent Main Threats")

    score_cols = [
        "Overall Danger Score",
        "Attacking Threat",
        "Creative Threat",
        "Wide Threat",
        "Attacking Stat Score",
        "Creative Stat Score",
    ]

    display_cols = build_display_cols(opponent_df, score_cols)

    st.dataframe(
        opponent_df.sort_values("Overall Danger Score", ascending=False)[display_cols].head(10),
        use_container_width=True,
        height=500,
    )

# ============================================================
# WEAK LINKS
# ============================================================

with tab2:
    st.subheader("Opponent Weak Links To Target")

    score_cols = [
        "Weak Link Score",
        "Defensive Strength",
        "Defensive Stat Score",
        "Physical Power",
    ]

    display_cols = build_display_cols(opponent_df, score_cols)

    st.dataframe(
        opponent_df.sort_values("Weak Link Score", ascending=False)[display_cols].head(10),
        use_container_width=True,
        height=500,
    )

    st.markdown("### Exploit Suggestions")

    for item in generate_exploit_recommendations(opponent_df):
        st.write(f"- {item}")

# ============================================================
# TACTICAL PLAN
# ============================================================

with tab3:
    st.subheader("Recommended Tactical Plan")

    for item in generate_opposition_plan(opponent_df):
        st.write(f"- {item}")

    if tactic:
        st.markdown("### Fit With Your Saved Tactic")

        philosophy = tactic.get("philosophy", [])

        if any("Build From The Back" in item or "Positional" in item for item in philosophy):
            st.write(
                "- Your philosophy values control and buildup. Against this opponent, focus on clean progression and avoid rushed turnovers."
            )

        if any("High Press" in item for item in philosophy):
            st.write(
                "- Your philosophy values pressure. Target the opponent's weakest technical defenders and force them into rushed clearances."
            )

        if any("Counter" in item for item in philosophy):
            st.write(
                "- Your philosophy values transitions. Attack quickly into the spaces behind their fullbacks and center backs."
            )

# ============================================================
# OUR BEST MATCHUPS
# ============================================================

with tab4:
    st.subheader("Your Best Players To Exploit The Opponent")

    if your_df.empty:
        st.info("No data for your club.")
    elif not tactic:
        st.info("Load a saved tactic to connect your player roles to the opponent.")
    else:
        roles = tactic.get("roles", {})

        if not roles:
            st.info("Saved tactic has no role assignments.")
        else:
            for slot_name, role_name in roles.items():
                if role_name not in ROLE_PROFILES:
                    continue

                temp_df = your_df.copy()
                temp_df[f"{role_name} Fit"] = temp_df.apply(
                    lambda row: role_fit_score(row, role_name),
                    axis=1,
                )

                display_cols = build_display_cols(
                    temp_df,
                    [f"{role_name} Fit"],
                )

                st.markdown(f"### {slot_name} — {role_name}")

                st.dataframe(
                    temp_df.sort_values(f"{role_name} Fit", ascending=False)[display_cols].head(5),
                    use_container_width=True,
                    height=250,
                )

# ============================================================
# FULL REPORT
# ============================================================

with tab5:
    st.subheader("Full Opponent Report")

    score_cols = [
        "Overall Danger Score",
        "Weak Link Score",
        "Attacking Threat",
        "Creative Threat",
        "Wide Threat",
        "Defensive Strength",
        "Pressing Intensity",
        "Physical Power",
    ]

    display_cols = build_display_cols(opponent_df, score_cols)

    st.dataframe(
        opponent_df.sort_values("Overall Danger Score", ascending=False)[display_cols],
        use_container_width=True,
        height=650,
    )

    st.download_button(
        label="Download Opposition Report CSV",
        data=opponent_df[display_cols].to_csv(index=False).encode("utf-8"),
        file_name=f"{opponent_club.replace(' ', '_')}_opposition_report.csv",
        mime="text/csv",
    )

save_page_memory(__file__)
