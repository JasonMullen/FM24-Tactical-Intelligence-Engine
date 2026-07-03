from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))
from fm_engine.ui_memory import init_page_memory, save_page_memory

from fm_engine.fast_data import (
    clear_file_cache,
    get_file_signature,
    list_saved_files,
    load_fm_file_cached,
)
from fm_engine.persistent_state import (
    collect_session_values,
    get_page_state,
    restore_session_value,
    set_page_state,
)

UPLOAD_DIR = PROJECT_ROOT / "data" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

PAGE_KEY = "dashboard"


# ============================================================
# COLUMN GROUPS
# ============================================================

IDENTITY_COLUMNS = [
    "Name", "Age", "Nat", "Based", "Club", "Division", "League",
    "Height", "Weight", "Position", "Primary Position", "Position Classes",
    "Position Group", "Position Line", "Position Family",
    "Left Foot", "Preferred Foot", "Right Foot",
    "Transfer Value", "Value", "Price", "Wage", "Transfer Status"
]

TECHNICAL_ATTRIBUTES = [
    "Tec", "Tck", "Pen", "Pas", "Mar", "L Th", "Lon", "Hea",
    "Fre", "Fir", "Fin", "Dri", "Cro", "Cor"
]

MENTAL_ATTRIBUTES = [
    "Wor", "Vis", "Tea", "Pos", "OtB", "Ldr", "Fla", "Det",
    "Dec", "Cnt", "Cmp", "Bra", "Ant", "Agg"
]

PHYSICAL_ATTRIBUTES = [
    "Acc", "Str", "Sta", "Pac", "Nat", "Jum", "Bal", "Agi"
]

GOALKEEPING_ATTRIBUTES = [
    "Thr", "TRO", "Ref", "Pun", "1v1", "Kic", "Han", "Ecc",
    "Com", "Cmd", "Aer"
]

STATS_COLUMNS = [
    "Inf", "Apps", "Starts", "Mins", "Gls", "Ast", "xG", "xA",
    "Av Rat", "Shots", "ShT", "Tck", "Tck/90", "Int", "Int/90",
    "Drb", "Drb/90", "Cr C", "Rec", "AT Apps", "Yel", "Saves/90",
    "Tgls/90", "Tcon/90", "Tall", "Tgls", "Shutouts", "Red",
    "Pts/Gm", "PoM", "Pen/R", "Pens S", "Pens Saved Ratio",
    "Pens Saved", "Pens Faced", "Pens", "NP-xG/90", "NP-xG",
    "Last Gl", "Last C", "Mins/Gm", "Int Conc", "Int Av Rat",
    "Int Ast", "Int Apps", "Gls/90", "All/90", "Conc", "Won",
    "G. Mis", "Lost", "D", "Gwin", "Fls", "FA", "xG/90", "xG-OP",
    "xA/90", "Cln/90", "Mins/G", "AT Leg Gls", "AT Leg Apps",
    "AT Gls", "Hdrs A", "Tck C", "Tck A", "Tck R", "Shot/90",
    "Shot %", "ShT/90", "Shots Outside Box/90", "Shts Blckd/90",
    "Shts Blckd", "Svt", "Svp", "Svh", "Sv %", "Pr passes/90",
    "Pr Passes", "Pres C/90", "Pres C", "Pres A/90", "Pres A",
    "Poss Won/90", "Poss Lost/90", "Ps C/90", "Ps C", "Ps A/90",
    "Ps A", "Pas %", "OP-KP/90", "OP-KP", "OP-Crs C/90",
    "OP-Crs C", "OP-Crs A/90", "OP-Crs A", "OP-Cr %", "Off",
    "Gl Mst", "K Tck/90", "K Tck", "K Ps/90", "K Pas",
    "K Hdrs/90", "Itc", "Sprints/90", "Hdr %", "Hdrs W/90",
    "Hdrs", "Hdrs L/90", "Goals Outside Box", "FK Shots",
    "xSV %", "xGP/90", "xGP", "xG/shot", "Dist/90", "Distance",
    "Cr C/90", "Crs A/90", "CrA", "CrC/A", "Conv %", "Clr/90",
    "Clear", "CCC", "Ch C/90", "Blk/90", "Blk", "Asts/90",
    "Aer A/90"
]

ATTRIBUTE_LABELS = {
    "Tec": "Technique", "Tck": "Tackling", "Pen": "Penalty Taking",
    "Pas": "Passing", "Mar": "Marking", "L Th": "Long Throws",
    "Lon": "Long Shots", "Hea": "Heading", "Fre": "Free Kicks",
    "Fir": "First Touch", "Fin": "Finishing", "Dri": "Dribbling",
    "Cro": "Crossing", "Cor": "Corners",
    "Wor": "Work Rate", "Vis": "Vision", "Tea": "Teamwork",
    "Pos": "Positioning", "OtB": "Off The Ball", "Ldr": "Leadership",
    "Fla": "Flair", "Det": "Determination", "Dec": "Decisions",
    "Cnt": "Concentration", "Cmp": "Composure", "Bra": "Bravery",
    "Ant": "Anticipation", "Agg": "Aggression",
    "Acc": "Acceleration", "Str": "Strength", "Sta": "Stamina",
    "Pac": "Pace", "Nat": "Natural Fitness", "Jum": "Jumping Reach",
    "Bal": "Balance", "Agi": "Agility",
    "Thr": "Throwing", "TRO": "Rushing Out", "Ref": "Reflexes",
    "Pun": "Punching", "1v1": "One on Ones", "Kic": "Kicking",
    "Han": "Handling", "Ecc": "Eccentricity", "Com": "Communication",
    "Cmd": "Command of Area", "Aer": "Aerial Reach",
}

DISPLAY_NAMES = {
    "Name": "Name",
    "Age": "Age",
    "Nat": "Nationality",
    "Based": "Based",
    "Club": "Club",
    "Division": "League / Division",
    "League": "League",
    "Height": "Height",
    "Weight": "Weight",
    "Position": "FM Position",
    "Primary Position": "Primary Position",
    "Position Classes": "Position Classes",
    "Position Group": "Position Group",
    "Position Line": "Position Line",
    "Position Family": "Position Family",
    "Transfer Value": "Transfer Value",
    "Transfer Status": "Transfer Status",
    "Apps": "Apps",
    "Starts": "Starts",
    "Mins": "Minutes",
    "Gls": "Goals",
    "Ast": "Assists",
    "xG": "Expected Goals",
    "xA": "Expected Assists",
    "Av Rat": "Average Rating",
    "Tck/90": "Tackles per 90",
    "Int/90": "Interceptions per 90",
    "Drb/90": "Dribbles per 90",
    "Pas %": "Pass Completion %",
    "Poss Won/90": "Possession Won per 90",
    "Poss Lost/90": "Possession Lost per 90",
    "Sprints/90": "Sprints per 90",
    "Hdr %": "Header Win %",
    "Conv %": "Conversion %",
}

for short_name, long_name in ATTRIBUTE_LABELS.items():
    DISPLAY_NAMES[short_name] = f"{short_name} ({long_name})"


# ============================================================
# BASIC HELPERS
# ============================================================

def safe_filename(filename: str) -> str:
    filename = filename.strip().replace(" ", "_")
    filename = re.sub(r"[^A-Za-z0-9_.-]", "", filename)
    return filename or "fm24_upload.html"


def save_uploaded_file(uploaded_file) -> Path:
    filename = safe_filename(uploaded_file.name)
    path = UPLOAD_DIR / filename

    with open(path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    return path


def base_column_name(col: str) -> str:
    return re.sub(r"__\d+$", "", str(col))


def duplicate_number(col: str) -> int:
    match = re.search(r"__(\d+)$", str(col))

    if match:
        return int(match.group(1))

    return 1


def find_column(df: pd.DataFrame, possible_names: list[str]) -> str | None:
    wanted = {name.lower() for name in possible_names}

    for col in df.columns:
        if base_column_name(col).lower() in wanted:
            return col

    return None


def clean_database(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df = df.dropna(axis=0, how="all")
    df = df.dropna(axis=1, how="all")
    df = df.drop_duplicates()

    unnamed = [
        col for col in df.columns
        if base_column_name(col).lower().startswith("unnamed")
    ]

    df = df.drop(columns=unnamed, errors="ignore")

    return df


# ============================================================
# POSITION CLASSIFICATION
# ============================================================

POSITION_ORDER = [
    "GK", "CB", "RB", "LB", "RWB", "LWB",
    "DM", "CM", "RM", "LM",
    "AM", "RW", "LW", "ST"
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


def position_group_from_classes(position_classes: list[str]) -> str:
    if not position_classes:
        return "Unknown"

    if "GK" in position_classes:
        return "Goalkeeper"

    if "CB" in position_classes:
        return "Center Back"

    if any(pos in position_classes for pos in ["RB", "LB", "RWB", "LWB"]):
        return "Fullback / Wingback"

    if "DM" in position_classes:
        return "Defensive Midfielder"

    if any(pos in position_classes for pos in ["CM", "RM", "LM"]):
        return "Midfielder"

    if "AM" in position_classes:
        return "Attacking Midfielder"

    if any(pos in position_classes for pos in ["RW", "LW"]):
        return "Wide Attacker"

    if "ST" in position_classes:
        return "Striker"

    return "Unknown"


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


def position_family_from_classes(position_classes: list[str]) -> str:
    if not position_classes:
        return "Unknown"

    if "GK" in position_classes:
        return "Goalkeeper"

    if "CB" in position_classes:
        return "Central Defender"

    if any(pos in position_classes for pos in ["RB", "LB", "RWB", "LWB"]):
        return "Wide Defender"

    if "DM" in position_classes:
        return "Pivot / Number 6"

    if "CM" in position_classes:
        return "Central Midfielder / Number 8"

    if "AM" in position_classes:
        return "Creator / Number 10"

    if any(pos in position_classes for pos in ["RW", "LW", "RM", "LM"]):
        return "Wide Player"

    if "ST" in position_classes:
        return "Forward / Number 9"

    return "Unknown"


def add_position_classification(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    position_col = find_column(df, ["Position", "Positions"])

    if not position_col:
        df["Position Classes"] = "Unknown"
        df["Primary Position"] = "Unknown"
        df["Position Group"] = "Unknown"
        df["Position Line"] = "Unknown"
        df["Position Family"] = "Unknown"
        return df

    classes_series = df[position_col].apply(classify_position_classes)

    df["Position Classes"] = classes_series.apply(
        lambda classes: ", ".join(classes) if classes else "Unknown"
    )

    df["Primary Position"] = classes_series.apply(primary_position_from_classes)
    df["Position Group"] = classes_series.apply(position_group_from_classes)
    df["Position Line"] = classes_series.apply(position_line_from_classes)
    df["Position Family"] = classes_series.apply(position_family_from_classes)

    return df


# ============================================================
# COLUMN ORGANIZATION
# ============================================================

def get_identity_columns(df: pd.DataFrame) -> list[str]:
    matched = []
    wanted = {col.lower() for col in IDENTITY_COLUMNS}

    for col in df.columns:
        base = base_column_name(col).lower()

        if base in wanted:
            if base == "nat" and col != "Nat":
                continue

            if col not in matched:
                matched.append(col)

    return matched


def get_first_attribute_columns(df: pd.DataFrame, wanted_columns: list[str]) -> list[str]:
    matched = []
    wanted = {col.lower() for col in wanted_columns}

    for col in df.columns:
        base = base_column_name(col)

        if base.lower() in wanted and duplicate_number(col) == 1:
            matched.append(col)

    return matched


def get_physical_columns(df: pd.DataFrame) -> list[str]:
    matched = []

    for col in df.columns:
        base = base_column_name(col)

        if base not in PHYSICAL_ATTRIBUTES:
            continue

        if base == "Nat":
            if col != "Nat":
                matched.append(col)
        else:
            if duplicate_number(col) == 1:
                matched.append(col)

    return matched


def get_stat_columns(df: pd.DataFrame, used_columns: set[str]) -> list[str]:
    matched = []
    wanted = {col.lower() for col in STATS_COLUMNS}

    for col in df.columns:
        base = base_column_name(col).lower()

        if base in wanted and col not in used_columns:
            matched.append(col)

    return matched


def organize_columns(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, list[str]]]:
    identity_cols = get_identity_columns(df)
    technical_cols = get_first_attribute_columns(df, TECHNICAL_ATTRIBUTES)
    mental_cols = get_first_attribute_columns(df, MENTAL_ATTRIBUTES)
    physical_cols = get_physical_columns(df)
    gk_cols = get_first_attribute_columns(df, GOALKEEPING_ATTRIBUTES)

    used_before_stats = set(
        identity_cols + technical_cols + mental_cols + physical_cols + gk_cols
    )

    stats_cols = get_stat_columns(df, used_before_stats)
    attribute_cols = technical_cols + mental_cols + physical_cols + gk_cols

    ordered = []
    used = set()

    for group in [identity_cols, attribute_cols, stats_cols]:
        for col in group:
            if col not in used:
                ordered.append(col)
                used.add(col)

    other_cols = [col for col in df.columns if col not in used]
    ordered.extend(other_cols)

    grouped = {
        "Identity": identity_cols,
        "All Attributes": attribute_cols,
        "Technical Attributes": technical_cols,
        "Mental Attributes": mental_cols,
        "Physical Attributes": physical_cols,
        "Goalkeeping Attributes": gk_cols,
        "Stats": stats_cols,
        "Other Columns": other_cols,
    }

    return df[ordered].copy(), grouped


@st.cache_data(show_spinner="Preparing organized dashboard database...")
def prepare_database_cached(path_text: str, mtime: float, size: int):
    raw_df = load_fm_file_cached(path_text, mtime, size)
    clean_df = clean_database(raw_df)
    classified_df = add_position_classification(clean_df)
    organized_df, grouped = organize_columns(classified_df)

    return organized_df, grouped


# ============================================================
# DISPLAY HELPERS
# ============================================================

def readable_column_name(col: str) -> str:
    base = base_column_name(col)

    if col == "Nat":
        return "Nationality"

    if col.startswith("Nat__"):
        return "Nat (Natural Fitness)"

    label = DISPLAY_NAMES.get(base, base)

    if col != base:
        return f"{label} [{col}]"

    return label


def make_unique_display_columns(columns) -> list[str]:
    seen = {}
    fixed = []

    for col in columns:
        base = str(col).strip()

        if base == "":
            base = "Unknown"

        key = base.lower()

        if key not in seen:
            seen[key] = 1
            fixed.append(base)
        else:
            seen[key] += 1
            fixed.append(f"{base} [{seen[key]}]")

    return fixed


def make_display_df(df: pd.DataFrame) -> pd.DataFrame:
    display_df = df.copy()
    display_df.columns = make_unique_display_columns(
        [readable_column_name(col) for col in display_df.columns]
    )

    return display_df


def get_attribute_short_label(col: str) -> str:
    base = base_column_name(col)

    if col.startswith("Nat__"):
        return "Nat"

    return base


def add_all_attributes_summary_column(df: pd.DataFrame, attribute_cols: list[str]) -> pd.DataFrame:
    df = df.copy()
    actual_cols = [col for col in attribute_cols if col in df.columns]

    def build_summary(row: pd.Series) -> str:
        values = []

        for col in actual_cols:
            value = row.get(col)

            if pd.isna(value):
                continue

            numeric = pd.to_numeric(value, errors="coerce")

            if pd.isna(numeric):
                continue

            values.append(f"{get_attribute_short_label(col)} {int(numeric)}")

        return " | ".join(values)

    df["All Attributes"] = df.apply(build_summary, axis=1)

    identity_cols = [col for col in get_identity_columns(df) if col in df.columns]
    remaining_cols = [
        col for col in df.columns
        if col not in identity_cols and col != "All Attributes"
    ]

    return df[identity_cols + ["All Attributes"] + remaining_cols]


def safe_multiselect_default(key: str, options: list[str]) -> list[str]:
    current = st.session_state.get(key, [])

    if not isinstance(current, list):
        return []

    return [item for item in current if item in options]


def safe_slider_range(key: str, min_value: int, max_value: int) -> tuple[int, int]:
    current = st.session_state.get(key, [min_value, max_value])

    if isinstance(current, tuple):
        low, high = current
    elif isinstance(current, list) and len(current) == 2:
        low, high = current
    else:
        low, high = min_value, max_value

    low = max(min_value, min(int(low), max_value))
    high = max(min_value, min(int(high), max_value))

    if low > high:
        low, high = min_value, max_value

    return low, high


# ============================================================
# FILTERS
# ============================================================

def apply_general_filters(df: pd.DataFrame) -> pd.DataFrame:
    filtered = df.copy()

    st.sidebar.divider()
    st.sidebar.header("Search Filters")

    name_col = find_column(filtered, ["Name", "Player"])
    club_col = find_column(filtered, ["Club"])
    league_col = find_column(filtered, ["Division", "League"])
    position_col = find_column(filtered, ["Position"])
    primary_position_col = find_column(filtered, ["Primary Position"])
    position_group_col = find_column(filtered, ["Position Group"])
    position_line_col = find_column(filtered, ["Position Line"])
    age_col = find_column(filtered, ["Age"])

    if name_col:
        search = st.sidebar.text_input(
            "Search Player Name",
            key="dashboard_name_search",
        )

        if search:
            filtered = filtered[
                filtered[name_col].astype(str).str.contains(search, case=False, na=False)
            ]

    if league_col:
        leagues = sorted(filtered[league_col].dropna().astype(str).unique().tolist())

        selected_leagues = st.sidebar.multiselect(
            "Select Multiple Leagues / Divisions",
            leagues,
            default=safe_multiselect_default("dashboard_selected_leagues", leagues),
            key="dashboard_selected_leagues",
        )

        if selected_leagues:
            filtered = filtered[filtered[league_col].astype(str).isin(selected_leagues)]

    if position_line_col:
        lines = sorted(filtered[position_line_col].dropna().astype(str).unique().tolist())

        selected_lines = st.sidebar.multiselect(
            "Select Position Lines",
            lines,
            default=safe_multiselect_default("dashboard_selected_lines", lines),
            key="dashboard_selected_lines",
        )

        if selected_lines:
            filtered = filtered[filtered[position_line_col].astype(str).isin(selected_lines)]

    if position_group_col:
        groups = sorted(filtered[position_group_col].dropna().astype(str).unique().tolist())

        selected_groups = st.sidebar.multiselect(
            "Select Position Groups",
            groups,
            default=safe_multiselect_default("dashboard_selected_groups", groups),
            key="dashboard_selected_groups",
        )

        if selected_groups:
            filtered = filtered[filtered[position_group_col].astype(str).isin(selected_groups)]

    if primary_position_col:
        positions = sorted(filtered[primary_position_col].dropna().astype(str).unique().tolist())

        selected_positions = st.sidebar.multiselect(
            "Select Multiple Positions",
            positions,
            default=safe_multiselect_default("dashboard_selected_positions", positions),
            key="dashboard_selected_positions",
        )

        if selected_positions:
            filtered = filtered[filtered[primary_position_col].astype(str).isin(selected_positions)]

    if position_col:
        raw_positions = sorted(filtered[position_col].dropna().astype(str).unique().tolist())

        selected_raw_positions = st.sidebar.multiselect(
            "Select Raw FM Positions",
            raw_positions,
            default=safe_multiselect_default("dashboard_selected_raw_positions", raw_positions),
            key="dashboard_selected_raw_positions",
        )

        if selected_raw_positions:
            filtered = filtered[filtered[position_col].astype(str).isin(selected_raw_positions)]

    if club_col:
        clubs = sorted(filtered[club_col].dropna().astype(str).unique().tolist())

        selected_clubs = st.sidebar.multiselect(
            "Select Multiple Clubs",
            clubs,
            default=safe_multiselect_default("dashboard_selected_clubs", clubs),
            key="dashboard_selected_clubs",
        )

        if selected_clubs:
            filtered = filtered[filtered[club_col].astype(str).isin(selected_clubs)]

    if age_col:
        numeric_age = pd.to_numeric(filtered[age_col], errors="coerce")

        if numeric_age.notna().any():
            min_age = int(numeric_age.min())
            max_age = int(numeric_age.max())

            age_range = st.sidebar.slider(
                "Age Range",
                min_value=min_age,
                max_value=max_age,
                value=safe_slider_range("dashboard_age_range", min_age, max_age),
                key="dashboard_age_range",
            )

            filtered = filtered[
                numeric_age.between(age_range[0], age_range[1], inclusive="both")
            ]

    return filtered


def apply_attribute_search_filter(df: pd.DataFrame, attribute_cols: list[str]) -> pd.DataFrame:
    filtered = df.copy()
    actual_attribute_cols = [col for col in attribute_cols if col in filtered.columns]

    st.sidebar.divider()
    st.sidebar.header("Pick Attributes Filter")

    if not actual_attribute_cols:
        st.sidebar.info("No attribute columns were found.")
        return filtered

    label_to_col = {
        readable_column_name(col): col
        for col in actual_attribute_cols
    }

    label_options = list(label_to_col.keys())

    selected_labels = st.sidebar.multiselect(
        "Pick Attributes",
        options=label_options,
        default=safe_multiselect_default("dashboard_pick_attributes", label_options),
        key="dashboard_pick_attributes",
    )

    if not selected_labels:
        return filtered

    condition = st.sidebar.selectbox(
        "Condition",
        ["Is At Least", "Is At Most", "Is Exactly"],
        key="dashboard_attribute_condition",
    )

    value = st.sidebar.slider(
        "Attribute Value",
        min_value=1,
        max_value=20,
        value=int(st.session_state.get("dashboard_attribute_value", 12)),
        step=1,
        key="dashboard_attribute_value",
    )

    match_mode = st.sidebar.radio(
        "Match Type",
        ["Match ALL selected attributes", "Match ANY selected attribute"],
        key="dashboard_attribute_match_mode",
    )

    masks = []

    for label in selected_labels:
        col = label_to_col[label]
        numeric_col = pd.to_numeric(filtered[col], errors="coerce")

        if condition == "Is At Least":
            masks.append(numeric_col >= value)
        elif condition == "Is At Most":
            masks.append(numeric_col <= value)
        else:
            masks.append(numeric_col == value)

    if not masks:
        return filtered

    if match_mode == "Match ALL selected attributes":
        final_mask = masks[0]

        for mask in masks[1:]:
            final_mask = final_mask & mask
    else:
        final_mask = masks[0]

        for mask in masks[1:]:
            final_mask = final_mask | mask

    filtered = filtered[final_mask.fillna(False)].copy()

    matched_cols = [label_to_col[label] for label in selected_labels]
    numeric_selected = filtered[matched_cols].apply(pd.to_numeric, errors="coerce")

    if condition == "Is At Least":
        filtered["Attribute Matches"] = (numeric_selected >= value).sum(axis=1)
    elif condition == "Is At Most":
        filtered["Attribute Matches"] = (numeric_selected <= value).sum(axis=1)
    else:
        filtered["Attribute Matches"] = (numeric_selected == value).sum(axis=1)

    filtered["Attribute Filter"] = f"{match_mode.replace('Match ', '')}: {condition} {value}"

    return filtered


# ============================================================
# STREAMLIT APP
# ============================================================

st.set_page_config(
    page_title="FM24 Tactical Intelligence Engine",
    page_icon="⚽",
    layout="wide",
)

init_page_memory(__file__)

page_state = get_page_state(PAGE_KEY)

PERSIST_KEYS = [
    "dashboard_active_file",
    "dashboard_active_view",
    "dashboard_name_search",
    "dashboard_selected_leagues",
    "dashboard_selected_lines",
    "dashboard_selected_groups",
    "dashboard_selected_positions",
    "dashboard_selected_raw_positions",
    "dashboard_selected_clubs",
    "dashboard_age_range",
    "dashboard_pick_attributes",
    "dashboard_attribute_condition",
    "dashboard_attribute_value",
    "dashboard_attribute_match_mode",
]

DEFAULT_SESSION_VALUES = {
    "dashboard_selected_leagues": [],
    "dashboard_selected_lines": [],
    "dashboard_selected_groups": [],
    "dashboard_selected_positions": [],
    "dashboard_selected_raw_positions": [],
    "dashboard_selected_clubs": [],
    "dashboard_pick_attributes": [],
    "dashboard_name_search": "",
    "dashboard_attribute_condition": "Is At Least",
    "dashboard_attribute_value": 12,
    "dashboard_attribute_match_mode": "Match ALL selected attributes",
    "dashboard_active_view": "Full Organized View",
}

for key in PERSIST_KEYS:
    restore_session_value(
        st.session_state,
        page_state,
        key,
        DEFAULT_SESSION_VALUES.get(key, "__NO_DEFAULT__"),
    )

for key, value in DEFAULT_SESSION_VALUES.items():
    if st.session_state.get(key) is None:
        st.session_state[key] = value

st.title("FM24 Tactical Intelligence Engine")

st.write(
    """
    Faster dashboard with persistent state. It remembers your selected file, filters,
    attribute search, and active view after switching pages or reopening the browser tab.
    """
)

st.sidebar.header("Saved Files")

uploaded_file = st.sidebar.file_uploader(
    "Upload FM24 File",
    type=["csv", "xlsx", "xls", "html", "htm"],
)

if uploaded_file is not None:
    saved_path = save_uploaded_file(uploaded_file)
    st.session_state["dashboard_active_file"] = saved_path.name
    st.sidebar.success(f"Saved and selected: {saved_path.name}")

saved_files = list_saved_files()

if not saved_files:
    st.info("Upload a CSV, Excel, or FM24 HTML file to begin.")
    st.stop()

saved_file_names = [file.name for file in saved_files]

if st.session_state.get("dashboard_active_file") not in saved_file_names:
    st.session_state["dashboard_active_file"] = saved_file_names[0]

selected_file_name = st.sidebar.selectbox(
    "Choose Saved File",
    saved_file_names,
    index=saved_file_names.index(st.session_state["dashboard_active_file"]),
    key="dashboard_active_file",
)

selected_file = UPLOAD_DIR / selected_file_name

if st.sidebar.button("Delete Selected File"):
    selected_file.unlink(missing_ok=True)
    st.session_state["dashboard_active_file"] = None
    st.sidebar.warning(f"Deleted: {selected_file_name}")
    st.rerun()

if st.sidebar.button("Clear Speed Cache"):
    deleted_count = clear_file_cache()
    prepare_database_cached.clear()
    st.sidebar.success(f"Cleared {deleted_count} cached files.")
    st.rerun()

st.sidebar.caption(f"Current file: {selected_file_name}")

try:
    path_text, mtime, size = get_file_signature(selected_file)

    organized_df, grouped = prepare_database_cached(path_text, mtime, size)

    filtered_df = apply_general_filters(organized_df)
    filtered_df = apply_attribute_search_filter(filtered_df, grouped["All Attributes"])

    view_df = add_all_attributes_summary_column(filtered_df, grouped["All Attributes"])
    display_df = make_display_df(view_df)

    total_attributes = (
        len(grouped["Technical Attributes"])
        + len(grouped["Mental Attributes"])
        + len(grouped["Physical Attributes"])
        + len(grouped["Goalkeeping Attributes"])
    )

    st.success(
        f"Loaded {len(display_df):,} players and {len(display_df.columns):,} columns from {selected_file_name}."
    )

    metric1, metric2, metric3, metric4 = st.columns(4)
    metric1.metric("Players", f"{len(display_df):,}")
    metric2.metric("Total Columns", f"{len(display_df.columns):,}")
    metric3.metric("Attribute Columns", f"{total_attributes:,}")
    metric4.metric("Stat Columns", f"{len(grouped['Stats']):,}")

    view_options = [
        "Full Organized View",
        "All Attributes",
        "Position Classification",
        "Identity",
        "Technical",
        "Mental + Physical",
        "Stats",
        "Column Groups",
    ]

    if st.session_state.get("dashboard_active_view") not in view_options:
        st.session_state["dashboard_active_view"] = view_options[0]

    active_view = st.radio(
        "Dashboard View",
        view_options,
        horizontal=True,
        key="dashboard_active_view",
    )

    st.caption(
        "This replaces normal tabs with a persistent view selector so the dashboard reopens where you left off."
    )

    if active_view == "Full Organized View":
        st.subheader("Full Organized View")
        st.dataframe(display_df, use_container_width=True, height=650)

    elif active_view == "All Attributes":
        st.subheader("All Attributes")

        cols = grouped["Identity"] + grouped["All Attributes"]

        if "Attribute Matches" in filtered_df.columns:
            cols = ["Attribute Matches"] + cols

        if "Attribute Filter" in filtered_df.columns:
            cols = ["Attribute Filter"] + cols

        cols = [col for col in cols if col in filtered_df.columns]

        st.dataframe(
            make_display_df(filtered_df[cols]),
            use_container_width=True,
            height=650,
        )

    elif active_view == "Position Classification":
        st.subheader("Position Classification")

        position_cols = [
            col for col in grouped["Identity"]
            if base_column_name(col) in [
                "Name", "Age", "Club", "Division", "League", "Position",
                "Primary Position", "Position Classes", "Position Group",
                "Position Line", "Position Family"
            ]
        ]

        position_cols = [col for col in position_cols if col in filtered_df.columns]

        st.dataframe(
            make_display_df(filtered_df[position_cols]),
            use_container_width=True,
            height=650,
        )

        st.markdown(
            """
            ### Position Classification Logic

            - **GK** = Goalkeeper
            - **CB** = Center Back
            - **RB/LB** = Fullback
            - **RWB/LWB** = Wingback
            - **DM** = Defensive Midfielder / Pivot
            - **CM** = Central Midfielder
            - **AM** = Attacking Midfielder
            - **RW/LW** = Wide Attacker
            - **ST** = Striker
            """
        )

    elif active_view == "Identity":
        st.subheader("Identity")

        cols = [col for col in grouped["Identity"] if col in filtered_df.columns]

        st.dataframe(
            make_display_df(filtered_df[cols]),
            use_container_width=True,
            height=650,
        )

    elif active_view == "Technical":
        st.subheader("Technical Attributes")

        cols = grouped["Identity"] + grouped["Technical Attributes"]
        cols = [col for col in cols if col in filtered_df.columns]

        st.dataframe(
            make_display_df(filtered_df[cols]),
            use_container_width=True,
            height=650,
        )

    elif active_view == "Mental + Physical":
        st.subheader("Mental + Physical + Goalkeeping")

        cols = (
            grouped["Identity"]
            + grouped["Mental Attributes"]
            + grouped["Physical Attributes"]
            + grouped["Goalkeeping Attributes"]
        )

        cols = [col for col in cols if col in filtered_df.columns]

        st.dataframe(
            make_display_df(filtered_df[cols]),
            use_container_width=True,
            height=650,
        )

    elif active_view == "Stats":
        st.subheader("Stats")

        cols = grouped["Identity"] + grouped["Stats"]
        cols = [col for col in cols if col in filtered_df.columns]

        if cols:
            st.dataframe(
                make_display_df(filtered_df[cols]),
                use_container_width=True,
                height=650,
            )
        else:
            st.info("No stat columns detected.")

    elif active_view == "Column Groups":
        st.subheader("Column Groups")

        for group_name, columns in grouped.items():
            st.write(f"### {group_name}")

            if columns:
                st.write([readable_column_name(col) for col in columns])
            else:
                st.write("None found")

    st.download_button(
        label="Download Organized CSV",
        data=display_df.to_csv(index=False).encode("utf-8"),
        file_name="fm24_organized_player_database.csv",
        mime="text/csv",
    )

    set_page_state(
        PAGE_KEY,
        collect_session_values(st.session_state, PERSIST_KEYS),
    )

except Exception as error:
    set_page_state(
        PAGE_KEY,
        collect_session_values(st.session_state, PERSIST_KEYS),
    )

    st.error(f"Could not load selected file: {error}")

save_page_memory(__file__)
