from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(PROJECT_ROOT))

from fm_engine.role_profiles import ROLE_PROFILES

UPLOAD_DIR = PROJECT_ROOT / "data" / "uploads"
TACTICS_DIR = PROJECT_ROOT / "configs" / "saved_tactics"
TACTICS_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# FORMATIONS
# ============================================================

FORMATIONS = {
    "4-3-3 DM Wide": [
        {"slot": "GK", "accepted": ["GK"], "default_role": "Sweeper Keeper"},
        {"slot": "RB", "accepted": ["RB", "RWB"], "default_role": "Inverted Wing Back"},
        {"slot": "RCB", "accepted": ["CB"], "default_role": "Ball Playing Defender"},
        {"slot": "LCB", "accepted": ["CB"], "default_role": "Ball Playing Defender"},
        {"slot": "LB", "accepted": ["LB", "LWB"], "default_role": "Wing Back"},
        {"slot": "DM", "accepted": ["DM", "CM"], "default_role": "Deep Lying Playmaker"},
        {"slot": "RCM", "accepted": ["CM", "DM", "AM"], "default_role": "Mezzala"},
        {"slot": "LCM", "accepted": ["CM", "DM", "AM"], "default_role": "Box To Box Midfielder"},
        {"slot": "RW", "accepted": ["RW", "RM"], "default_role": "Inverted Winger"},
        {"slot": "LW", "accepted": ["LW", "LM"], "default_role": "Inside Forward"},
        {"slot": "ST", "accepted": ["ST"], "default_role": "Pressing Forward"},
    ],
    "4-2-3-1": [
        {"slot": "GK", "accepted": ["GK"], "default_role": "Sweeper Keeper"},
        {"slot": "RB", "accepted": ["RB", "RWB"], "default_role": "Full Back"},
        {"slot": "RCB", "accepted": ["CB"], "default_role": "Ball Playing Defender"},
        {"slot": "LCB", "accepted": ["CB"], "default_role": "Central Defender"},
        {"slot": "LB", "accepted": ["LB", "LWB"], "default_role": "Wing Back"},
        {"slot": "RDM", "accepted": ["DM", "CM"], "default_role": "Defensive Midfielder"},
        {"slot": "LDM", "accepted": ["DM", "CM"], "default_role": "Deep Lying Playmaker"},
        {"slot": "AM", "accepted": ["AM", "CM"], "default_role": "Advanced Playmaker"},
        {"slot": "RW", "accepted": ["RW", "RM"], "default_role": "Inverted Winger"},
        {"slot": "LW", "accepted": ["LW", "LM"], "default_role": "Inside Forward"},
        {"slot": "ST", "accepted": ["ST"], "default_role": "Complete Forward"},
    ],
    "4-1-4-1": [
        {"slot": "GK", "accepted": ["GK"], "default_role": "Goalkeeper"},
        {"slot": "RB", "accepted": ["RB", "RWB"], "default_role": "Full Back"},
        {"slot": "RCB", "accepted": ["CB"], "default_role": "Central Defender"},
        {"slot": "LCB", "accepted": ["CB"], "default_role": "Ball Playing Defender"},
        {"slot": "LB", "accepted": ["LB", "LWB"], "default_role": "Full Back"},
        {"slot": "DM", "accepted": ["DM"], "default_role": "Anchor"},
        {"slot": "RCM", "accepted": ["CM", "DM"], "default_role": "Carrilero"},
        {"slot": "LCM", "accepted": ["CM", "DM"], "default_role": "Box To Box Midfielder"},
        {"slot": "RM", "accepted": ["RM", "RW"], "default_role": "Wide Midfielder"},
        {"slot": "LM", "accepted": ["LM", "LW"], "default_role": "Wide Midfielder"},
        {"slot": "ST", "accepted": ["ST"], "default_role": "Advanced Forward"},
    ],
    "4-4-2": [
        {"slot": "GK", "accepted": ["GK"], "default_role": "Goalkeeper"},
        {"slot": "RB", "accepted": ["RB", "RWB"], "default_role": "Full Back"},
        {"slot": "RCB", "accepted": ["CB"], "default_role": "Central Defender"},
        {"slot": "LCB", "accepted": ["CB"], "default_role": "Central Defender"},
        {"slot": "LB", "accepted": ["LB", "LWB"], "default_role": "Full Back"},
        {"slot": "RM", "accepted": ["RM", "RW"], "default_role": "Winger"},
        {"slot": "RCM", "accepted": ["CM", "DM"], "default_role": "Ball Winning Midfielder"},
        {"slot": "LCM", "accepted": ["CM", "DM"], "default_role": "Deep Lying Playmaker"},
        {"slot": "LM", "accepted": ["LM", "LW"], "default_role": "Winger"},
        {"slot": "RST", "accepted": ["ST"], "default_role": "Advanced Forward"},
        {"slot": "LST", "accepted": ["ST"], "default_role": "Deep Lying Forward"},
    ],
    "3-4-2-1": [
        {"slot": "GK", "accepted": ["GK"], "default_role": "Sweeper Keeper"},
        {"slot": "RCB", "accepted": ["CB"], "default_role": "Wide Centre-Back"},
        {"slot": "CB", "accepted": ["CB"], "default_role": "Ball Playing Defender"},
        {"slot": "LCB", "accepted": ["CB"], "default_role": "Wide Centre-Back"},
        {"slot": "RWB", "accepted": ["RWB", "RB", "RM"], "default_role": "Wing Back"},
        {"slot": "RCM", "accepted": ["CM", "DM"], "default_role": "Box To Box Midfielder"},
        {"slot": "LCM", "accepted": ["CM", "DM"], "default_role": "Deep Lying Playmaker"},
        {"slot": "LWB", "accepted": ["LWB", "LB", "LM"], "default_role": "Complete Wing Back"},
        {"slot": "RAM", "accepted": ["AM", "RW", "RM"], "default_role": "Advanced Playmaker"},
        {"slot": "LAM", "accepted": ["AM", "LW", "LM"], "default_role": "Inside Forward"},
        {"slot": "ST", "accepted": ["ST"], "default_role": "Complete Forward"},
    ],
    "3-5-2": [
        {"slot": "GK", "accepted": ["GK"], "default_role": "Sweeper Keeper"},
        {"slot": "RCB", "accepted": ["CB"], "default_role": "Wide Centre-Back"},
        {"slot": "CB", "accepted": ["CB"], "default_role": "Central Defender"},
        {"slot": "LCB", "accepted": ["CB"], "default_role": "Wide Centre-Back"},
        {"slot": "RWB", "accepted": ["RWB", "RB", "RM"], "default_role": "Wing Back"},
        {"slot": "DM", "accepted": ["DM", "CM"], "default_role": "Anchor"},
        {"slot": "RCM", "accepted": ["CM", "DM"], "default_role": "Mezzala"},
        {"slot": "LCM", "accepted": ["CM", "DM"], "default_role": "Box To Box Midfielder"},
        {"slot": "LWB", "accepted": ["LWB", "LB", "LM"], "default_role": "Wing Back"},
        {"slot": "RST", "accepted": ["ST"], "default_role": "Advanced Forward"},
        {"slot": "LST", "accepted": ["ST"], "default_role": "Deep Lying Forward"},
    ],
}


# ============================================================
# PHILOSOPHY PROFILES
# ============================================================

PHILOSOPHY_PRESETS = {
    "Positional Play / Build From The Back": {
        "attributes": {
            "Pas": 1.30, "Fir": 1.20, "Tec": 1.15, "Dec": 1.20,
            "Cmp": 1.15, "Vis": 1.10, "Tea": 1.10, "Pos": 1.00,
            "OtB": 0.95,
        },
        "stats": ["Pas %", "Ps C/90", "OP-KP/90", "Ch C/90", "Poss Lost/90"],
        "description": "Values technical security, decision-making, structured possession, and controlled chance creation."
    },
    "High Press / Counter-Press": {
        "attributes": {
            "Wor": 1.30, "Sta": 1.25, "Agg": 1.10, "Ant": 1.10,
            "Tea": 1.10, "Acc": 1.05, "Pac": 1.00, "Dec": 1.00,
            "Tck": 0.95,
        },
        "stats": ["Poss Won/90", "Pres C/90", "Sprints/90", "Tck/90", "Int/90"],
        "description": "Values work rate, stamina, pressing, speed, aggression, and winning the ball back quickly."
    },
    "Vertical Counter Attack": {
        "attributes": {
            "Pac": 1.25, "Acc": 1.25, "OtB": 1.20, "Dri": 1.10,
            "Fin": 1.05, "Dec": 1.00, "Pas": 0.95, "Cmp": 0.95,
        },
        "stats": ["Gls/90", "xG/90", "Drb/90", "Sprints/90", "Shot/90", "OP-KP/90"],
        "description": "Values speed, directness, off-ball movement, transition threat, and quick chance creation."
    },
    "Defensive Compactness / Control Space": {
        "attributes": {
            "Pos": 1.30, "Ant": 1.20, "Cnt": 1.15, "Dec": 1.10,
            "Tck": 1.10, "Mar": 1.05, "Tea": 1.05, "Wor": 1.00,
            "Str": 0.90,
        },
        "stats": ["Tck/90", "Int/90", "Poss Won/90", "Clear", "Blk/90", "Av Rat"],
        "description": "Values defensive intelligence, compactness, dueling, concentration, and protecting central zones."
    },
    "Wide Overloads / Crossing": {
        "attributes": {
            "Cro": 1.30, "Dri": 1.10, "Acc": 1.10, "Pac": 1.10,
            "Sta": 1.05, "Wor": 1.00, "OtB": 1.00, "Tec": 0.95,
        },
        "stats": ["Cr C/90", "OP-Crs C/90", "Crs A/90", "Asts/90", "Sprints/90"],
        "description": "Values width, crossing volume, wide running, stamina, and chance creation from wide zones."
    },
    "Half-Space Creativity / Cutbacks": {
        "attributes": {
            "Pas": 1.20, "Vis": 1.25, "Tec": 1.15, "Fir": 1.10,
            "Dri": 1.05, "OtB": 1.05, "Dec": 1.10, "Cmp": 1.00,
        },
        "stats": ["OP-KP/90", "Ch C/90", "xA/90", "Asts/90", "Drb/90", "Pas %"],
        "description": "Values creators who combine between the lines and create high-quality chances."
    },
}


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

    clean_found = []

    for pos in POSITION_ORDER:
        if pos in found and pos not in clean_found:
            clean_found.append(pos)

    return clean_found


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


def add_position_classification(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    position_col = find_column(df, ["Position", "Positions"])

    if not position_col:
        df["Position Classes"] = "Unknown"
        df["Primary Position"] = "Unknown"
        return df

    classes_series = df[position_col].apply(classify_position_classes)

    df["Position Classes"] = classes_series.apply(
        lambda classes: ", ".join(classes) if classes else "Unknown"
    )

    df["Primary Position"] = classes_series.apply(primary_position_from_classes)

    return df


def player_matches_slot(row: pd.Series, accepted_positions: list[str]) -> bool:
    classes = str(row.get("Position Classes", ""))
    player_positions = [pos.strip() for pos in classes.split(",")]

    return any(pos in accepted_positions for pos in player_positions)


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


def role_attribute_fit(row: pd.Series, role_name: str) -> float:
    role_weights = ROLE_PROFILES[role_name]["attributes"]
    return weighted_attribute_score(row, role_weights)


def philosophy_attribute_fit(row: pd.Series, philosophy_names: list[str]) -> float:
    combined_weights = {}

    for name in philosophy_names:
        preset = PHILOSOPHY_PRESETS[name]
        for attr, weight in preset["attributes"].items():
            combined_weights[attr] = combined_weights.get(attr, 0) + weight

    return weighted_attribute_score(row, combined_weights)


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


def stat_performance_score(df: pd.DataFrame, stat_cols: list[str]) -> pd.Series:
    if not stat_cols:
        return pd.Series([50.0] * len(df), index=df.index)

    lower_is_better = {"Poss Lost/90", "Fls", "Conc", "G. Mis", "Lost"}

    scores = []

    for col in stat_cols:
        base = base_column_name(col)
        scores.append(
            percentile_score(df[col], higher_is_better=base not in lower_is_better)
        )

    matrix = pd.concat(scores, axis=1)

    return matrix.mean(axis=1).round(1)


def recommend_for_slot(
    df: pd.DataFrame,
    slot_name: str,
    accepted_positions: list[str],
    role_name: str,
    philosophy_names: list[str],
    min_minutes: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    candidates = df[df.apply(lambda row: player_matches_slot(row, accepted_positions), axis=1)].copy()

    mins_col = find_column(candidates, ["Mins"])

    if mins_col:
        mins = pd.to_numeric(candidates[mins_col], errors="coerce").fillna(0)
        candidates = candidates[mins >= min_minutes].copy()

    if candidates.empty:
        return candidates, candidates

    candidates["Role Attribute Fit"] = candidates.apply(
        lambda row: role_attribute_fit(row, role_name),
        axis=1,
    )

    candidates["Philosophy Attribute Fit"] = candidates.apply(
        lambda row: philosophy_attribute_fit(row, philosophy_names),
        axis=1,
    )

    candidates["Tactic Attribute Recommendation"] = (
        candidates["Role Attribute Fit"] * 0.60
        + candidates["Philosophy Attribute Fit"] * 0.40
    ).round(1)

    role_stats = ROLE_PROFILES[role_name].get("stats", [])

    philosophy_stats = []
    for philosophy_name in philosophy_names:
        philosophy_stats.extend(PHILOSOPHY_PRESETS[philosophy_name].get("stats", []))

    combined_stats = []
    for stat in role_stats + philosophy_stats:
        if stat not in combined_stats:
            combined_stats.append(stat)

    stat_cols = get_matching_stat_columns(candidates, combined_stats)

    candidates["Role + Philosophy Stat Performance"] = stat_performance_score(
        candidates,
        stat_cols,
    )

    candidates["Tactic Statistical Recommendation"] = (
        candidates["Role + Philosophy Stat Performance"] * 0.60
        + candidates["Role Attribute Fit"] * 0.25
        + candidates["Philosophy Attribute Fit"] * 0.15
    ).round(1)

    attribute_ranked = candidates.sort_values(
        "Tactic Attribute Recommendation",
        ascending=False,
    ).head(10)

    stat_ranked = candidates.sort_values(
        "Tactic Statistical Recommendation",
        ascending=False,
    ).head(10)

    return attribute_ranked, stat_ranked


# ============================================================
# DISPLAY
# ============================================================

IDENTITY_COLUMNS = [
    "Name", "Age", "Nat", "Club", "Division", "League", "Position",
    "Primary Position", "Position Classes", "Transfer Value", "Value", "Wage",
]


def get_identity_cols(df: pd.DataFrame) -> list[str]:
    cols = []

    for wanted in IDENTITY_COLUMNS:
        match = find_column(df, [wanted])
        if match and match not in cols:
            cols.append(match)

    return cols


def get_role_attribute_cols(df: pd.DataFrame, role_name: str) -> list[str]:
    cols = []

    for attr in ROLE_PROFILES[role_name]["attributes"].keys():
        match = find_attr_column(df, attr)
        if match and match not in cols:
            cols.append(match)

    return cols


def get_philosophy_attribute_cols(df: pd.DataFrame, philosophy_names: list[str]) -> list[str]:
    cols = []

    for philosophy_name in philosophy_names:
        for attr in PHILOSOPHY_PRESETS[philosophy_name]["attributes"].keys():
            match = find_attr_column(df, attr)
            if match and match not in cols:
                cols.append(match)

    return cols


def build_display_cols(df: pd.DataFrame, role_name: str, mode: str, philosophy_names: list[str]) -> list[str]:
    cols = get_identity_cols(df)

    score_cols = [
        "Tactic Attribute Recommendation",
        "Tactic Statistical Recommendation",
        "Role Attribute Fit",
        "Philosophy Attribute Fit",
        "Role + Philosophy Stat Performance",
    ]

    for col in score_cols:
        if col in df.columns and col not in cols:
            cols.append(col)

    if mode == "attribute":
        extra_cols = get_role_attribute_cols(df, role_name) + get_philosophy_attribute_cols(df, philosophy_names)
    else:
        role_stats = ROLE_PROFILES[role_name].get("stats", [])
        philosophy_stats = []
        for philosophy_name in philosophy_names:
            philosophy_stats.extend(PHILOSOPHY_PRESETS[philosophy_name].get("stats", []))
        extra_cols = get_matching_stat_columns(df, role_stats + philosophy_stats)

    for col in extra_cols:
        if col in df.columns and col not in cols:
            cols.append(col)

    return cols


# ============================================================
# STREAMLIT APP
# ============================================================

st.set_page_config(
    page_title="Tactic Philosophy Builder",
    page_icon="🧠",
    layout="wide",
)

st.title("Tactic Philosophy Builder")

st.write(
    """
    Build a tactic, choose your footballing philosophy, assign roles, and get
    top 10 player recommendations for every position in the formation.
    """
)

saved_files = list_saved_files()

if not saved_files:
    st.info("Upload a player database on the main dashboard first.")
    st.stop()

selected_file = st.sidebar.selectbox(
    "Choose Saved Database",
    saved_files,
    format_func=lambda path: path.name,
)

raw_df = load_file(selected_file)
df = add_position_classification(raw_df)

st.sidebar.header("Build Your Tactic")

tactic_name = st.sidebar.text_input("Tactic Name", value="My Tactical Philosophy")

formation_name = st.sidebar.selectbox(
    "Formation",
    list(FORMATIONS.keys()),
)

philosophy_names = st.sidebar.multiselect(
    "Footballing Philosophy",
    list(PHILOSOPHY_PRESETS.keys()),
    default=["Positional Play / Build From The Back"],
)

if not philosophy_names:
    st.warning("Choose at least one footballing philosophy.")
    st.stop()

min_minutes = st.sidebar.number_input(
    "Minimum Minutes For Statistical Recommendations",
    min_value=0,
    value=300,
    step=100,
)

st.subheader("Tactic Identity")

for philosophy_name in philosophy_names:
    st.markdown(f"**{philosophy_name}:** {PHILOSOPHY_PRESETS[philosophy_name]['description']}")

formation_slots = FORMATIONS[formation_name]

st.subheader(f"Formation: {formation_name}")

role_options = list(ROLE_PROFILES.keys())
selected_roles = {}

with st.expander("Assign Roles To Formation", expanded=True):
    for slot in formation_slots:
        slot_name = slot["slot"]
        default_role = slot["default_role"]

        if default_role not in role_options:
            default_role = role_options[0]

        selected_role = st.selectbox(
            f"{slot_name} Role",
            role_options,
            index=role_options.index(default_role),
            key=f"role_{slot_name}",
        )

        selected_roles[slot_name] = selected_role

tactic_config = {
    "tactic_name": tactic_name,
    "formation": formation_name,
    "philosophy": philosophy_names,
    "roles": selected_roles,
}

col_a, col_b = st.columns(2)

with col_a:
    if st.button("Save Tactic"):
        safe_name = re.sub(r"[^A-Za-z0-9_-]", "_", tactic_name)
        save_path = TACTICS_DIR / f"{safe_name}.json"

        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(tactic_config, f, indent=4)

        st.success(f"Saved tactic to {save_path.name}")

with col_b:
    st.download_button(
        label="Download Tactic JSON",
        data=json.dumps(tactic_config, indent=4).encode("utf-8"),
        file_name=f"{tactic_name.replace(' ', '_')}.json",
        mime="application/json",
    )

st.divider()

st.subheader("Top 10 Player Recommendations By Formation Slot")

for slot in formation_slots:
    slot_name = slot["slot"]
    accepted_positions = slot["accepted"]
    role_name = selected_roles[slot_name]

    attribute_ranked, stat_ranked = recommend_for_slot(
        df=df,
        slot_name=slot_name,
        accepted_positions=accepted_positions,
        role_name=role_name,
        philosophy_names=philosophy_names,
        min_minutes=min_minutes,
    )

    with st.expander(f"{slot_name} — {role_name}", expanded=False):
        st.caption(
            f"Accepted positions: {', '.join(accepted_positions)} | Role: {role_name}"
        )

        if attribute_ranked.empty and stat_ranked.empty:
            st.warning("No matching players found for this slot.")
            continue

        tab1, tab2 = st.tabs(
            ["Attribute-Based Recommendation", "Statistical Recommendation"]
        )

        with tab1:
            st.write(
                "Ranks players by role attributes + philosophy attributes."
            )

            display_cols = build_display_cols(
                attribute_ranked,
                role_name=role_name,
                mode="attribute",
                philosophy_names=philosophy_names,
            )

            st.dataframe(
                attribute_ranked[display_cols],
                use_container_width=True,
                height=400,
            )

        with tab2:
            st.write(
                "Ranks players by role-relevant stats + philosophy stats, with attribute fit included."
            )

            display_cols = build_display_cols(
                stat_ranked,
                role_name=role_name,
                mode="stats",
                philosophy_names=philosophy_names,
            )

            st.dataframe(
                stat_ranked[display_cols],
                use_container_width=True,
                height=400,
            )
