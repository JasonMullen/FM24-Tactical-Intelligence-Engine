from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
import streamlit as st
from sklearn.metrics.pairwise import cosine_similarity

PROJECT_ROOT = Path(__file__).resolve().parents[2]
UPLOAD_DIR = PROJECT_ROOT / "data" / "uploads"


# ============================================================
# FM24 ATTRIBUTE GROUPS
# ============================================================

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

IDENTITY_COLUMNS = [
    "Name", "Age", "Nat", "Club", "Division", "League", "Position",
    "Primary Position", "Position Classes", "Position Group", "Position Line",
    "Position Family", "Transfer Value", "Value", "Wage"
]


# ============================================================
# BASIC HELPERS
# ============================================================

def flatten_column_name(col) -> str:
    if isinstance(col, tuple):
        parts = [str(part).strip() for part in col if str(part).strip()]
        return parts[-1] if parts else "Unknown"

    return str(col).strip()


def make_unique_columns(columns) -> list[str]:
    seen = {}
    fixed = []

    for col in columns:
        base = flatten_column_name(col)

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


def base_column_name(col: str) -> str:
    return re.sub(r"__\d+$", "", str(col))


def duplicate_number(col: str) -> int:
    match = re.search(r"__(\d+)$", str(col))

    if match:
        return int(match.group(1))

    return 1


def readable_column_name(col: str) -> str:
    base = base_column_name(col)

    if col == "Nat":
        return "Nationality"

    if col.startswith("Nat__"):
        return "Nat (Natural Fitness)"

    label = ATTRIBUTE_LABELS.get(base, base)

    if base in ATTRIBUTE_LABELS:
        return f"{base} ({label})"

    if col != base:
        return f"{base} [{col}]"

    return base


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

    files = [
        file for file in UPLOAD_DIR.iterdir()
        if file.is_file() and file.suffix.lower() in allowed
    ]

    return sorted(files, key=lambda file: file.stat().st_mtime, reverse=True)


def load_file(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()

    if suffix == ".csv":
        df = pd.read_csv(path)

    elif suffix in [".xlsx", ".xls"]:
        df = pd.read_excel(path)

    elif suffix in [".html", ".htm"]:
        tables = pd.read_html(path)

        if not tables:
            raise ValueError("No table found in this FM HTML file.")

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
# ATTRIBUTE COLUMNS + OVERALL SCORE
# ============================================================

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

        # First Nat is nationality. Duplicate Nat is natural fitness.
        if base == "Nat":
            if col != "Nat":
                matched.append(col)
        else:
            if duplicate_number(col) == 1:
                matched.append(col)

    return matched


def get_attribute_columns(df: pd.DataFrame, groups: list[str]) -> list[str]:
    cols = []

    if "Technical" in groups:
        cols.extend(get_first_attribute_columns(df, TECHNICAL_ATTRIBUTES))

    if "Mental" in groups:
        cols.extend(get_first_attribute_columns(df, MENTAL_ATTRIBUTES))

    if "Physical" in groups:
        cols.extend(get_physical_columns(df))

    if "Goalkeeping" in groups:
        cols.extend(get_first_attribute_columns(df, GOALKEEPING_ATTRIBUTES))

    clean = []

    for col in cols:
        if col in df.columns and col not in clean:
            clean.append(col)

    return clean


def get_all_attribute_columns_for_overall(df: pd.DataFrame) -> list[str]:
    """
    Overall player score uses outfield attributes by default:
    Technical + Mental + Physical.

    Goalkeeping attributes are excluded from general player overall
    because they would unfairly lower outfield players.
    """

    cols = []
    cols.extend(get_first_attribute_columns(df, TECHNICAL_ATTRIBUTES))
    cols.extend(get_first_attribute_columns(df, MENTAL_ATTRIBUTES))
    cols.extend(get_physical_columns(df))

    clean = []

    for col in cols:
        if col in df.columns and col not in clean:
            clean.append(col)

    return clean


def add_overall_attribute_scores(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    overall_cols = get_all_attribute_columns_for_overall(df)

    if not overall_cols:
        df["Overall Attribute Avg"] = 0.0
        df["Overall Attribute Score"] = 0.0
        return df

    numeric_attrs = df[overall_cols].apply(pd.to_numeric, errors="coerce")

    df["Overall Attribute Avg"] = numeric_attrs.mean(axis=1).round(2)
    df["Overall Attribute Score"] = ((df["Overall Attribute Avg"] / 20) * 100).round(1)

    return df


def get_identity_columns(df: pd.DataFrame) -> list[str]:
    cols = []

    for wanted in IDENTITY_COLUMNS:
        match = find_column(df, [wanted])

        if match and match not in cols:
            if base_column_name(match) == "Nat" and match != "Nat":
                continue

            cols.append(match)

    return cols


# ============================================================
# SIMILARITY ENGINE
# ============================================================

def build_similarity_matrix(df: pd.DataFrame, attribute_cols: list[str]) -> pd.DataFrame:
    matrix = df[attribute_cols].apply(pd.to_numeric, errors="coerce")

    matrix = matrix.fillna(matrix.median(numeric_only=True))
    matrix = matrix.fillna(0)

    return matrix


def calculate_overall_level_similarity(
    result: pd.DataFrame,
    target_overall_score: float,
) -> pd.Series:
    """
    Converts overall score difference into a similarity value from 0 to 1.

    Example:
    Same score = 1.00
    10 points apart = 0.90
    30 points apart = 0.70
    """

    overall_diff = (result["Overall Attribute Score"] - target_overall_score).abs()
    level_similarity = 1 - (overall_diff / 100)
    level_similarity = level_similarity.clip(lower=0, upper=1)

    return level_similarity


def find_similar_players(
    df: pd.DataFrame,
    target_index: int,
    attribute_cols: list[str],
    top_n: int,
    use_overall_score: bool = True,
    profile_weight: float = 0.85,
) -> pd.DataFrame:
    if not attribute_cols:
        raise ValueError("No usable attribute columns found.")

    matrix = build_similarity_matrix(df, attribute_cols)

    target_vector = matrix.loc[[target_index]]
    similarities = cosine_similarity(target_vector, matrix)[0]

    result = df.copy()
    result["Attribute Profile Similarity"] = similarities

    if use_overall_score:
        target_overall_score = float(result.loc[target_index, "Overall Attribute Score"])
        overall_level_similarity = calculate_overall_level_similarity(
            result,
            target_overall_score,
        )

        level_weight = 1 - profile_weight

        result["Overall Level Similarity"] = overall_level_similarity
        result["Final Similarity Score"] = (
            result["Attribute Profile Similarity"] * profile_weight
            + result["Overall Level Similarity"] * level_weight
        )
    else:
        result["Overall Level Similarity"] = 0.0
        result["Final Similarity Score"] = result["Attribute Profile Similarity"]

    result["Final Similarity %"] = (result["Final Similarity Score"] * 100).round(1)
    result["Profile Similarity %"] = (result["Attribute Profile Similarity"] * 100).round(1)
    result["Overall Level Similarity %"] = (result["Overall Level Similarity"] * 100).round(1)

    result = result[result.index != target_index]
    result = result.sort_values("Final Similarity Score", ascending=False)

    return result.head(top_n)


def build_attribute_comparison(
    df: pd.DataFrame,
    target_index: int,
    comparison_index: int,
    attribute_cols: list[str],
    name_col: str,
) -> pd.DataFrame:
    target_name = df.loc[target_index, name_col]
    comparison_name = df.loc[comparison_index, name_col]

    rows = []

    for col in attribute_cols:
        target_value = pd.to_numeric(df.loc[target_index, col], errors="coerce")
        comparison_value = pd.to_numeric(df.loc[comparison_index, col], errors="coerce")

        if pd.isna(target_value) and pd.isna(comparison_value):
            continue

        diff = None

        if pd.notna(target_value) and pd.notna(comparison_value):
            diff = comparison_value - target_value

        rows.append(
            {
                "Attribute": readable_column_name(col),
                str(target_name): target_value,
                str(comparison_name): comparison_value,
                "Difference": diff,
            }
        )

    return pd.DataFrame(rows)


def apply_sidebar_filters(df: pd.DataFrame) -> pd.DataFrame:
    filtered = df.copy()

    league_col = find_column(filtered, ["Division", "League"])
    position_col = find_column(filtered, ["Primary Position"])
    position_group_col = find_column(filtered, ["Position Group"])
    club_col = find_column(filtered, ["Club"])
    age_col = find_column(filtered, ["Age"])

    st.sidebar.subheader("Search Pool Filters")

    if league_col:
        leagues = sorted(filtered[league_col].dropna().astype(str).unique().tolist())
        selected_leagues = st.sidebar.multiselect("Leagues / Divisions", leagues)

        if selected_leagues:
            filtered = filtered[filtered[league_col].astype(str).isin(selected_leagues)]

    if position_group_col:
        groups = sorted(filtered[position_group_col].dropna().astype(str).unique().tolist())
        selected_groups = st.sidebar.multiselect("Position Groups", groups)

        if selected_groups:
            filtered = filtered[filtered[position_group_col].astype(str).isin(selected_groups)]

    if position_col:
        positions = sorted(filtered[position_col].dropna().astype(str).unique().tolist())
        selected_positions = st.sidebar.multiselect("Primary Positions", positions)

        if selected_positions:
            filtered = filtered[filtered[position_col].astype(str).isin(selected_positions)]

    if club_col:
        clubs = sorted(filtered[club_col].dropna().astype(str).unique().tolist())
        selected_clubs = st.sidebar.multiselect("Clubs", clubs)

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
                value=(min_age, max_age),
            )

            filtered = filtered[
                numeric_age.between(age_range[0], age_range[1], inclusive="both")
            ]

    return filtered


# ============================================================
# STREAMLIT APP
# ============================================================

st.set_page_config(
    page_title="Player Comparison Search",
    page_icon="🔍",
    layout="wide",
)

st.title("Player Comparison Search")

st.write(
    """
    Search for a player and find the most similar players based on FM24 attributes.
    This version also gives every player an Overall Attribute Score and uses it in the comparison.
    """
)

saved_files = list_saved_files()

if not saved_files:
    st.info("Upload a player database on the main dashboard first.")
    st.stop()

selected_file = st.sidebar.selectbox(
    "Choose Saved Player Database",
    saved_files,
    format_func=lambda path: path.name,
)

raw_df = load_file(selected_file)
df = add_position_classification(raw_df)
df = add_overall_attribute_scores(df)

name_col = find_column(df, ["Name", "Player"])

if not name_col:
    st.error("No player name column found.")
    st.stop()

st.sidebar.subheader("Similarity Settings")

attribute_groups = st.sidebar.multiselect(
    "Attribute Groups Used For Comparison",
    ["Technical", "Mental", "Physical", "Goalkeeping"],
    default=["Technical", "Mental", "Physical"],
)

use_overall_score = st.sidebar.checkbox(
    "Use Overall Attribute Score In Similarity",
    value=True,
)

profile_weight_percent = st.sidebar.slider(
    "Attribute Profile Weight",
    min_value=50,
    max_value=100,
    value=85,
    step=5,
    help="Higher = compare attribute shape more. Lower = overall ability matters more."
)

profile_weight = profile_weight_percent / 100

top_n = st.sidebar.slider(
    "Number of Similar Players",
    min_value=5,
    max_value=100,
    value=25,
    step=5,
)

same_position_only = st.sidebar.checkbox(
    "Limit to same primary position as target",
    value=False,
)

same_position_group_only = st.sidebar.checkbox(
    "Limit to same position group as target",
    value=True,
)

attribute_cols = get_attribute_columns(df, attribute_groups)

if not attribute_cols:
    st.error("No attribute columns found for the selected attribute groups.")
    st.stop()

search_text = st.text_input("Search Player Name")

if not search_text:
    st.info("Type a player name to start comparing.")
    st.stop()

matches = df[
    df[name_col].astype(str).str.contains(search_text, case=False, na=False)
].copy()

if matches.empty:
    st.warning("No players found with that name.")
    st.stop()

club_col = find_column(matches, ["Club"])
position_raw_col = find_column(matches, ["Position"])

label_parts = matches[name_col].astype(str)

if club_col:
    label_parts = label_parts + " | " + matches[club_col].astype(str)

if position_raw_col:
    label_parts = label_parts + " | " + matches[position_raw_col].astype(str)

matches["Search Label"] = label_parts

selected_label = st.selectbox(
    "Choose Player",
    matches["Search Label"].tolist(),
)

target_index = matches[matches["Search Label"] == selected_label].index[0]
target_row = df.loc[target_index]

search_pool = df.copy()

if same_position_only and "Primary Position" in search_pool.columns:
    target_primary = target_row.get("Primary Position", None)
    search_pool = search_pool[search_pool["Primary Position"] == target_primary]

if same_position_group_only and "Position Group" in search_pool.columns:
    target_group = target_row.get("Position Group", None)
    search_pool = search_pool[search_pool["Position Group"] == target_group]

search_pool = apply_sidebar_filters(search_pool)

if target_index not in search_pool.index:
    search_pool = pd.concat([df.loc[[target_index]], search_pool], axis=0)

similar_df = find_similar_players(
    search_pool,
    target_index=target_index,
    attribute_cols=attribute_cols,
    top_n=top_n,
    use_overall_score=use_overall_score,
    profile_weight=profile_weight,
)

identity_cols = get_identity_columns(similar_df)

display_cols = []

for col in identity_cols:
    if col in similar_df.columns and col not in display_cols:
        display_cols.append(col)

for col in [
    "Overall Attribute Avg",
    "Overall Attribute Score",
    "Final Similarity %",
    "Profile Similarity %",
    "Overall Level Similarity %",
]:
    if col in similar_df.columns and col not in display_cols:
        display_cols.append(col)

for col in attribute_cols:
    if col in similar_df.columns and col not in display_cols:
        display_cols.append(col)

st.subheader(f"Most Similar Players to {target_row[name_col]}")

target_info_cols = [col for col in identity_cols if col in df.columns]

target_profile_cols = []

for col in target_info_cols:
    if col not in target_profile_cols:
        target_profile_cols.append(col)

for col in ["Overall Attribute Avg", "Overall Attribute Score"]:
    if col in df.columns and col not in target_profile_cols:
        target_profile_cols.append(col)

for col in attribute_cols:
    if col not in target_profile_cols:
        target_profile_cols.append(col)

with st.expander("Target Player Profile", expanded=True):
    metric1, metric2, metric3 = st.columns(3)

    metric1.metric("Overall Attribute Avg", f"{target_row['Overall Attribute Avg']:.2f}/20")
    metric2.metric("Overall Attribute Score", f"{target_row['Overall Attribute Score']:.1f}/100")
    metric3.metric("Attributes Compared", f"{len(attribute_cols)}")

    st.dataframe(
        df.loc[[target_index], target_profile_cols],
        use_container_width=True,
        height=140,
    )

st.dataframe(
    similar_df[display_cols],
    use_container_width=True,
    height=650,
)

st.download_button(
    label="Download Similar Player Results",
    data=similar_df[display_cols].to_csv(index=False).encode("utf-8"),
    file_name=f"similar_players_to_{str(target_row[name_col]).replace(' ', '_')}.csv",
    mime="text/csv",
)

st.subheader("Attribute-by-Attribute Comparison")

if not similar_df.empty:
    comparison_options = (
        similar_df[name_col].astype(str)
        + " | "
        + similar_df["Final Similarity %"].astype(str)
        + "%"
        + " | Overall "
        + similar_df["Overall Attribute Score"].astype(str)
    ).tolist()

    selected_comparison = st.selectbox(
        "Choose Similar Player To Compare Directly",
        comparison_options,
    )

    selected_comparison_index = similar_df.index[
        comparison_options.index(selected_comparison)
    ]

    comparison_df = build_attribute_comparison(
        df=df,
        target_index=target_index,
        comparison_index=selected_comparison_index,
        attribute_cols=attribute_cols,
        name_col=name_col,
    )

    target_overall = df.loc[target_index, "Overall Attribute Score"]
    comparison_overall = df.loc[selected_comparison_index, "Overall Attribute Score"]

    col1, col2, col3 = st.columns(3)
    col1.metric(str(df.loc[target_index, name_col]), f"{target_overall:.1f}/100")
    col2.metric(str(df.loc[selected_comparison_index, name_col]), f"{comparison_overall:.1f}/100")
    col3.metric("Overall Difference", f"{comparison_overall - target_overall:+.1f}")

    st.dataframe(
        comparison_df,
        use_container_width=True,
        height=650,
    )

else:
    st.info("No similar players found.")
