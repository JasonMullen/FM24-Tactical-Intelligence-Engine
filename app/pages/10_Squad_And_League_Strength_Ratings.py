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


# ============================================================
# FM ATTRIBUTE GROUPS
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


# ============================================================
# CATEGORY PROFILES
# ============================================================

CATEGORY_PROFILES = {
    "Keepers": {
        "accepted_positions": ["GK"],
        "depth": 2,
        "attributes": {
            "Ref": 1.25,
            "Han": 1.20,
            "1v1": 1.15,
            "Aer": 1.05,
            "Cmd": 1.05,
            "Com": 1.00,
            "Kic": 0.90,
            "Thr": 0.85,
            "Dec": 0.90,
            "Cnt": 0.90,
        },
        "stats": ["Av Rat", "Saves/90", "xSV %", "Shutouts", "Pens Saved Ratio"],
    },
    "Defenders": {
        "accepted_positions": ["CB", "RB", "LB", "RWB", "LWB"],
        "depth": 8,
        "attributes": {
            "Tck": 1.20,
            "Mar": 1.15,
            "Pos": 1.15,
            "Ant": 1.10,
            "Cnt": 1.05,
            "Hea": 1.00,
            "Jum": 0.95,
            "Str": 0.95,
            "Pac": 0.90,
            "Pas": 0.75,
        },
        "stats": ["Av Rat", "Tck/90", "Int/90", "Poss Won/90", "Hdr %", "Clear", "Blk/90", "Pas %"],
    },
    "Defensive Midfielders": {
        "accepted_positions": ["DM"],
        "depth": 3,
        "attributes": {
            "Tck": 1.15,
            "Pos": 1.20,
            "Ant": 1.10,
            "Dec": 1.10,
            "Cnt": 1.05,
            "Tea": 1.05,
            "Wor": 1.00,
            "Pas": 1.00,
            "Fir": 0.90,
            "Str": 0.85,
        },
        "stats": ["Av Rat", "Tck/90", "Int/90", "Poss Won/90", "Pas %", "Ps C/90"],
    },
    "Central Midfielders": {
        "accepted_positions": ["CM"],
        "depth": 5,
        "attributes": {
            "Pas": 1.15,
            "Fir": 1.10,
            "Dec": 1.15,
            "Tea": 1.05,
            "Vis": 1.00,
            "Tec": 1.00,
            "Wor": 0.95,
            "Sta": 0.95,
            "Tck": 0.85,
            "Cmp": 1.00,
        },
        "stats": ["Av Rat", "Pas %", "Ps C/90", "OP-KP/90", "Tck/90", "Poss Won/90", "Asts/90"],
    },
    "Attacking Midfielders": {
        "accepted_positions": ["AM"],
        "depth": 3,
        "attributes": {
            "Pas": 1.15,
            "Vis": 1.25,
            "Tec": 1.15,
            "Fir": 1.15,
            "OtB": 1.10,
            "Cmp": 1.05,
            "Dec": 1.05,
            "Dri": 1.00,
            "Fla": 1.00,
            "Fin": 0.85,
        },
        "stats": ["Av Rat", "OP-KP/90", "Ch C/90", "xA/90", "Asts/90", "Drb/90", "Gls/90"],
    },
    "Wingers": {
        "accepted_positions": ["RW", "LW", "RM", "LM"],
        "depth": 5,
        "attributes": {
            "Acc": 1.15,
            "Pac": 1.15,
            "Dri": 1.20,
            "Cro": 1.05,
            "Tec": 1.05,
            "Fir": 1.00,
            "OtB": 1.10,
            "Fin": 0.90,
            "Dec": 0.90,
            "Sta": 0.85,
        },
        "stats": ["Av Rat", "Drb/90", "Cr C/90", "OP-KP/90", "xA/90", "Asts/90", "Shot/90", "Gls/90"],
    },
    "Strikers": {
        "accepted_positions": ["ST"],
        "depth": 3,
        "attributes": {
            "Fin": 1.30,
            "OtB": 1.25,
            "Cmp": 1.10,
            "Ant": 1.05,
            "Fir": 1.00,
            "Acc": 0.95,
            "Pac": 0.95,
            "Str": 0.85,
            "Hea": 0.85,
            "Tec": 0.80,
        },
        "stats": ["Av Rat", "Gls/90", "xG/90", "Shot/90", "ShT/90", "Conv %", "Asts/90"],
    },
}


STARTING_XI_SLOTS = [
    {"slot": "GK", "accepted_positions": ["GK"], "category": "Keepers"},
    {"slot": "RB", "accepted_positions": ["RB", "RWB"], "category": "Defenders"},
    {"slot": "RCB", "accepted_positions": ["CB"], "category": "Defenders"},
    {"slot": "LCB", "accepted_positions": ["CB"], "category": "Defenders"},
    {"slot": "LB", "accepted_positions": ["LB", "LWB"], "category": "Defenders"},
    {"slot": "DM", "accepted_positions": ["DM"], "category": "Defensive Midfielders"},
    {"slot": "CM", "accepted_positions": ["CM"], "category": "Central Midfielders"},
    {"slot": "AM", "accepted_positions": ["AM", "CM"], "category": "Attacking Midfielders"},
    {"slot": "RW", "accepted_positions": ["RW", "RM"], "category": "Wingers"},
    {"slot": "LW", "accepted_positions": ["LW", "LM"], "category": "Wingers"},
    {"slot": "ST", "accepted_positions": ["ST"], "category": "Strikers"},
]


IDENTITY_COLUMNS = [
    "Name", "Age", "Nat", "Club", "Division", "League", "Position",
    "Primary Position", "Position Classes", "Transfer Value", "Value", "Wage"
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
        [
            file for file in UPLOAD_DIR.iterdir()
            if file.is_file() and file.suffix.lower() in allowed
        ],
        key=lambda file: file.stat().st_mtime,
        reverse=True,
    )


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
        return "Keeper"

    if any(pos in position_classes for pos in ["CB", "RB", "LB", "RWB", "LWB"]):
        return "Defender"

    if any(pos in position_classes for pos in ["DM", "CM"]):
        return "Midfielder"

    if any(pos in position_classes for pos in ["AM", "RM", "LM", "RW", "LW", "ST"]):
        return "Attacker"

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


def player_matches_positions(row: pd.Series, accepted_positions: list[str]) -> bool:
    classes = str(row.get("Position Classes", ""))

    player_positions = [
        item.strip()
        for item in classes.split(",")
        if item.strip()
    ]

    return any(pos in accepted_positions for pos in player_positions)


# ============================================================
# ATTRIBUTE + STAT SCORING
# ============================================================

def find_attribute_column(row: pd.Series, attr: str) -> str | None:
    for col in row.index:
        base = base_column_name(col)

        if base != attr:
            continue

        # First Nat is nationality. Duplicate Nat is Natural Fitness.
        if attr == "Nat":
            if col != "Nat":
                return col
        else:
            if duplicate_number(col) == 1:
                return col

    return None


def weighted_attribute_score(row: pd.Series, weights: dict[str, float]) -> float:
    total = 0.0
    weight_total = 0.0

    for attr, weight in weights.items():
        col = find_attribute_column(row, attr)

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

    return ranks.fillna(50).round(1)


def get_matching_stat_columns(df: pd.DataFrame, stat_names: list[str]) -> list[str]:
    cols = []

    for stat in stat_names:
        for col in df.columns:
            if base_column_name(col) == stat and col not in cols:
                cols.append(col)

    return cols


def category_stat_score(df: pd.DataFrame, stat_names: list[str]) -> pd.Series:
    stat_cols = get_matching_stat_columns(df, stat_names)

    if not stat_cols:
        return pd.Series([50.0] * len(df), index=df.index)

    lower_is_better = {
        "Poss Lost/90",
        "Fls",
        "Conc",
        "G. Mis",
        "Lost",
    }

    score_parts = []

    for col in stat_cols:
        base = base_column_name(col)
        score_parts.append(
            percentile_score(df[col], higher_is_better=base not in lower_is_better)
        )

    return pd.concat(score_parts, axis=1).mean(axis=1).round(1)


def add_player_strength_scores(df: pd.DataFrame, min_minutes: int) -> pd.DataFrame:
    df = df.copy()

    mins_col = find_column(df, ["Mins"])

    if mins_col:
        mins = pd.to_numeric(df[mins_col], errors="coerce").fillna(0)
        df["Stat Eligible"] = mins >= min_minutes
    else:
        df["Stat Eligible"] = True

    for category_name, profile in CATEGORY_PROFILES.items():
        attr_col = f"{category_name} Attribute Rating"
        stat_col = f"{category_name} Statistical Rating"

        df[attr_col] = df.apply(
            lambda row: weighted_attribute_score(row, profile["attributes"]),
            axis=1,
        )

        df[stat_col] = category_stat_score(df, profile["stats"])

        # If a player does not meet minimum minutes, keep attribute score but lower stat confidence.
        df.loc[~df["Stat Eligible"], stat_col] = pd.NA

    attr_cols = [
        f"{category_name} Attribute Rating"
        for category_name in CATEGORY_PROFILES.keys()
    ]

    stat_cols = [
        f"{category_name} Statistical Rating"
        for category_name in CATEGORY_PROFILES.keys()
    ]

    df["Best Attribute Category Score"] = df[attr_cols].max(axis=1).round(1)
    df["Best Statistical Category Score"] = df[stat_cols].max(axis=1).round(1)

    return df


# ============================================================
# TEAM AGGREGATION
# ============================================================

def get_identity_cols(df: pd.DataFrame) -> list[str]:
    cols = []

    for wanted in IDENTITY_COLUMNS:
        match = find_column(df, [wanted])

        if match and match not in cols:
            cols.append(match)

    return cols


def get_category_candidates(
    team_df: pd.DataFrame,
    category_name: str,
    mode: str,
    require_stat_eligible: bool = False,
) -> pd.DataFrame:
    profile = CATEGORY_PROFILES[category_name]
    score_col = f"{category_name} {mode} Rating"

    candidates = team_df[
        team_df.apply(
            lambda row: player_matches_positions(row, profile["accepted_positions"]),
            axis=1,
        )
    ].copy()

    if require_stat_eligible and "Stat Eligible" in candidates.columns:
        candidates = candidates[candidates["Stat Eligible"]].copy()

    if score_col not in candidates.columns:
        return candidates.iloc[0:0].copy()

    candidates[score_col] = pd.to_numeric(candidates[score_col], errors="coerce")
    candidates = candidates[candidates[score_col].notna()].copy()

    return candidates.sort_values(score_col, ascending=False)


def category_team_strength(
    team_df: pd.DataFrame,
    category_name: str,
    mode: str,
    require_stat_eligible: bool = False,
) -> dict:
    profile = CATEGORY_PROFILES[category_name]
    depth = profile["depth"]
    score_col = f"{category_name} {mode} Rating"

    candidates = get_category_candidates(
        team_df,
        category_name=category_name,
        mode=mode,
        require_stat_eligible=require_stat_eligible,
    )

    top_players = candidates.head(depth)

    raw_sum = pd.to_numeric(top_players.get(score_col, pd.Series(dtype=float)), errors="coerce").sum()
    filled_avg = round(raw_sum / depth, 1) if depth > 0 else 0.0
    available_avg = round(pd.to_numeric(top_players.get(score_col, pd.Series(dtype=float)), errors="coerce").mean(), 1)

    if pd.isna(available_avg):
        available_avg = 0.0

    return {
        "category": category_name,
        "depth": depth,
        "players_found": len(top_players),
        "cumulative": round(raw_sum, 1),
        "filled_avg": filled_avg,
        "available_avg": available_avg,
    }


def build_best_xi(team_df: pd.DataFrame, mode: str) -> pd.DataFrame:
    available = team_df.copy()
    selected_rows = []

    name_col = find_column(team_df, ["Name", "Player"])
    club_col = find_column(team_df, ["Club"])
    position_col = find_column(team_df, ["Position"])
    age_col = find_column(team_df, ["Age"])

    for slot in STARTING_XI_SLOTS:
        slot_name = slot["slot"]
        category_name = slot["category"]
        accepted_positions = slot["accepted_positions"]
        score_col = f"{category_name} {mode} Rating"

        candidates = available[
            available.apply(
                lambda row: player_matches_positions(row, accepted_positions),
                axis=1,
            )
        ].copy()

        if mode == "Statistical" and "Stat Eligible" in candidates.columns:
            candidates = candidates[candidates["Stat Eligible"]].copy()

        if score_col in candidates.columns:
            candidates[score_col] = pd.to_numeric(candidates[score_col], errors="coerce")
            candidates = candidates[candidates[score_col].notna()].copy()
            candidates = candidates.sort_values(score_col, ascending=False)

        if candidates.empty:
            selected_rows.append(
                {
                    "Slot": slot_name,
                    "Category": category_name,
                    "Player": "No player found",
                    "Age": "",
                    "Club": "",
                    "FM Position": "",
                    "Score": 0.0,
                    "Selection Type": mode,
                }
            )
            continue

        best_index = candidates.index[0]
        best = available.loc[best_index]

        selected_rows.append(
            {
                "Slot": slot_name,
                "Category": category_name,
                "Player": best.get(name_col, "Unknown") if name_col else "Unknown",
                "Age": best.get(age_col, "") if age_col else "",
                "Club": best.get(club_col, "") if club_col else "",
                "FM Position": best.get(position_col, "") if position_col else "",
                "Score": round(float(best.get(score_col, 0)), 1),
                "Selection Type": mode,
            }
        )

        available = available.drop(index=best_index, errors="ignore")

    return pd.DataFrame(selected_rows)


def get_team_league(team_df: pd.DataFrame) -> str:
    league_col = find_column(team_df, ["Division", "League"])

    if not league_col:
        return "Unknown"

    values = team_df[league_col].dropna().astype(str)

    if values.empty:
        return "Unknown"

    mode = values.mode()

    if mode.empty:
        return values.iloc[0]

    return mode.iloc[0]


def build_team_ratings(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, dict[str, pd.DataFrame]]]:
    club_col = find_column(df, ["Club"])

    if not club_col:
        return pd.DataFrame(), {}

    rows = []
    xi_store = {}

    for club, team_df in df.groupby(club_col, dropna=True):
        team_df = team_df.copy()

        if str(club).strip() == "":
            continue

        attribute_xi = build_best_xi(team_df, mode="Attribute")
        statistical_xi = build_best_xi(team_df, mode="Statistical")

        xi_store[str(club)] = {
            "Attribute XI": attribute_xi,
            "Statistical XI": statistical_xi,
        }

        attribute_xi_cumulative = round(attribute_xi["Score"].sum(), 1)
        statistical_xi_cumulative = round(statistical_xi["Score"].sum(), 1)

        attribute_xi_avg = round(attribute_xi_cumulative / 11, 1)
        statistical_xi_avg = round(statistical_xi_cumulative / 11, 1)

        attribute_filled_slots = int((attribute_xi["Score"] > 0).sum())
        statistical_filled_slots = int((statistical_xi["Score"] > 0).sum())

        row = {
            "Club": str(club),
            "League": get_team_league(team_df),
            "Players In Database": len(team_df),
            "Stat Eligible Players": int(team_df["Stat Eligible"].sum()) if "Stat Eligible" in team_df.columns else len(team_df),

            "Starting XI Attribute Avg": attribute_xi_avg,
            "Starting XI Attribute Cumulative": attribute_xi_cumulative,
            "Filled Attribute XI Slots": attribute_filled_slots,

            "Starting XI Statistical Avg": statistical_xi_avg,
            "Starting XI Statistical Cumulative": statistical_xi_cumulative,
            "Filled Statistical XI Slots": statistical_filled_slots,
        }

        attribute_squad_cumulative = 0.0
        attribute_expected_depth = 0

        statistical_squad_cumulative = 0.0
        statistical_expected_depth = 0

        for category_name, profile in CATEGORY_PROFILES.items():
            attr_strength = category_team_strength(
                team_df,
                category_name=category_name,
                mode="Attribute",
                require_stat_eligible=False,
            )

            stat_strength = category_team_strength(
                team_df,
                category_name=category_name,
                mode="Statistical",
                require_stat_eligible=True,
            )

            row[f"Attribute - {category_name}"] = attr_strength["filled_avg"]
            row[f"Statistical - {category_name}"] = stat_strength["filled_avg"]

            row[f"Attribute Players - {category_name}"] = attr_strength["players_found"]
            row[f"Statistical Players - {category_name}"] = stat_strength["players_found"]

            attribute_squad_cumulative += attr_strength["cumulative"]
            attribute_expected_depth += attr_strength["depth"]

            statistical_squad_cumulative += stat_strength["cumulative"]
            statistical_expected_depth += stat_strength["depth"]

        row["Squad Attribute Cumulative"] = round(attribute_squad_cumulative, 1)
        row["Squad Attribute Avg"] = round(attribute_squad_cumulative / attribute_expected_depth, 1)

        row["Squad Statistical Cumulative"] = round(statistical_squad_cumulative, 1)
        row["Squad Statistical Avg"] = round(statistical_squad_cumulative / statistical_expected_depth, 1)

        row["Overall Attribute Team Rating"] = round(
            row["Starting XI Attribute Avg"] * 0.65
            + row["Squad Attribute Avg"] * 0.35,
            1,
        )

        row["Overall Statistical Team Rating"] = round(
            row["Starting XI Statistical Avg"] * 0.65
            + row["Squad Statistical Avg"] * 0.35,
            1,
        )

        row["Combined Team Rating"] = round(
            row["Overall Attribute Team Rating"] * 0.50
            + row["Overall Statistical Team Rating"] * 0.50,
            1,
        )

        rows.append(row)

    ratings_df = pd.DataFrame(rows)

    if not ratings_df.empty:
        ratings_df = ratings_df.sort_values("Combined Team Rating", ascending=False)

    return ratings_df, xi_store


def rank_best_teams_by_league(team_ratings: pd.DataFrame, metric: str, top_n: int) -> pd.DataFrame:
    if team_ratings.empty:
        return team_ratings

    ranked = team_ratings.copy()
    ranked["League Rank"] = ranked.groupby("League")[metric].rank(
        ascending=False,
        method="dense",
    ).astype(int)

    ranked = ranked[ranked["League Rank"] <= top_n].copy()
    ranked = ranked.sort_values(["League", "League Rank", metric], ascending=[True, True, False])

    return ranked




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


# ============================================================
# STREAMLIT APP
# ============================================================

st.set_page_config(
    page_title="Squad & League Strength Ratings",
    page_icon="🏟️",
    layout="wide",
)

init_page_memory(__file__)

st.title("Squad & League Strength Ratings")

st.write(
    """
    Rate every squad and best XI in the database using both attributes and statistics.
    Teams are broken down by keepers, defenders, midfielders, wingers, attacking midfielders, and strikers.
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

min_minutes = st.sidebar.number_input(
    "Minimum Minutes For Statistical Ratings",
    min_value=0,
    value=300,
    step=100,
)

top_n_per_league = st.sidebar.slider(
    "Top Teams Per League",
    min_value=3,
    max_value=20,
    value=10,
    step=1,
)

raw_df = load_page_file(selected_file)
df = add_position_classification(raw_df)
df = add_player_strength_scores(df, min_minutes=min_minutes)

team_ratings, xi_store = build_team_ratings(df)

if team_ratings.empty:
    st.error("No team ratings could be built. Make sure your database has a Club column.")
    st.stop()

metric_options = [
    "Combined Team Rating",
    "Overall Attribute Team Rating",
    "Overall Statistical Team Rating",
    "Starting XI Attribute Avg",
    "Starting XI Statistical Avg",
    "Squad Attribute Avg",
    "Squad Statistical Avg",
]

selected_metric = st.sidebar.selectbox(
    "Ranking Metric",
    metric_options,
)

league_options = ["All"] + sorted(team_ratings["League"].dropna().astype(str).unique().tolist())

selected_league = st.sidebar.selectbox(
    "League Filter",
    league_options,
)

filtered_team_ratings = team_ratings.copy()

if selected_league != "All":
    filtered_team_ratings = filtered_team_ratings[
        filtered_team_ratings["League"].astype(str) == selected_league
    ].copy()

filtered_team_ratings = filtered_team_ratings.sort_values(selected_metric, ascending=False)

metric1, metric2, metric3, metric4 = st.columns(4)

metric1.metric("Teams Rated", f"{len(team_ratings):,}")
metric2.metric("Players Rated", f"{len(df):,}")
metric3.metric("Best Team", str(team_ratings.iloc[0]["Club"]))
metric4.metric("Best Rating", f"{team_ratings.iloc[0][selected_metric]:.1f}")

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    [
        "Team Strength Ratings",
        "Best Teams By League",
        "Starting XI Ratings",
        "Category Breakdowns",
        "Player Category Scores",
    ]
)

with tab1:
    st.subheader("Every Squad Rated")

    main_cols = [
        "Club",
        "League",
        "Players In Database",
        "Stat Eligible Players",
        "Combined Team Rating",
        "Overall Attribute Team Rating",
        "Overall Statistical Team Rating",
        "Starting XI Attribute Avg",
        "Squad Attribute Avg",
        "Starting XI Statistical Avg",
        "Squad Statistical Avg",
        "Starting XI Attribute Cumulative",
        "Squad Attribute Cumulative",
        "Starting XI Statistical Cumulative",
        "Squad Statistical Cumulative",
        "Filled Attribute XI Slots",
        "Filled Statistical XI Slots",
    ]

    st.dataframe(
        make_streamlit_safe_df(filtered_team_ratings[main_cols]),
        use_container_width=True,
        height=650,
    )

    st.download_button(
        label="Download Team Strength Ratings CSV",
        data=filtered_team_ratings.to_csv(index=False).encode("utf-8"),
        file_name="fm24_team_strength_ratings.csv",
        mime="text/csv",
    )

with tab2:
    st.subheader("Best Overall Teams In Each League")

    best_by_league = rank_best_teams_by_league(
        team_ratings,
        metric=selected_metric,
        top_n=top_n_per_league,
    )

    display_cols = [
        "League",
        "League Rank",
        "Club",
        selected_metric,
        "Combined Team Rating",
        "Overall Attribute Team Rating",
        "Overall Statistical Team Rating",
        "Starting XI Attribute Avg",
        "Starting XI Statistical Avg",
        "Squad Attribute Avg",
        "Squad Statistical Avg",
    ]

    display_cols = unique_column_list([col for col in display_cols if col in best_by_league.columns])

    st.dataframe(
        make_streamlit_safe_df(best_by_league[display_cols]),
        use_container_width=True,
        height=650,
    )

    st.download_button(
        label="Download Best Teams By League CSV",
        data=make_streamlit_safe_df(best_by_league[display_cols]).to_csv(index=False).encode("utf-8"),
        file_name="fm24_best_teams_by_league.csv",
        mime="text/csv",
    )

with tab3:
    st.subheader("Best XI Builder")

    selected_club = st.selectbox(
        "Choose Club",
        sorted(xi_store.keys()),
    )

    xi_tabs = st.tabs(["Attribute Best XI", "Statistical Best XI"])

    with xi_tabs[0]:
        st.write("Best available player for each starting XI slot using attribute category ratings.")
        st.dataframe(
            xi_store[selected_club]["Attribute XI"],
            use_container_width=True,
            height=500,
        )

    with xi_tabs[1]:
        st.write("Best available player for each starting XI slot using statistical category ratings.")
        st.dataframe(
            xi_store[selected_club]["Statistical XI"],
            use_container_width=True,
            height=500,
        )

with tab4:
    st.subheader("Squad Category Breakdowns")

    category_cols = ["Club", "League"]

    for category_name in CATEGORY_PROFILES.keys():
        category_cols.append(f"Attribute - {category_name}")
        category_cols.append(f"Statistical - {category_name}")
        category_cols.append(f"Attribute Players - {category_name}")
        category_cols.append(f"Statistical Players - {category_name}")

    category_cols = unique_column_list([col for col in category_cols if col in filtered_team_ratings.columns])

    st.dataframe(
        make_streamlit_safe_df(filtered_team_ratings[category_cols]),
        use_container_width=True,
        height=650,
    )

    st.markdown(
        """
        ### Category Logic

        - **Keepers** = GK
        - **Defenders** = CB, RB, LB, RWB, LWB
        - **Defensive Midfielders** = DM
        - **Central Midfielders** = CM
        - **Attacking Midfielders** = AM
        - **Wingers** = RW, LW, RM, LM
        - **Strikers** = ST

        Squad scores use top-depth strength, so a team needs both elite starters and depth.
        """
    )

with tab5:
    st.subheader("Player Category Scores")

    identity_cols = get_identity_cols(df)

    score_cols = []

    for category_name in CATEGORY_PROFILES.keys():
        score_cols.append(f"{category_name} Attribute Rating")
        score_cols.append(f"{category_name} Statistical Rating")

    score_cols.extend(
        [
            "Best Attribute Category Score",
            "Best Statistical Category Score",
            "Stat Eligible",
        ]
    )

    player_display_cols = unique_column_list([
        col for col in identity_cols + score_cols
        if col in df.columns
    ])

    player_df = df[player_display_cols].copy()

    name_col = find_column(make_streamlit_safe_df(player_df), ["Name", "Player"])
    club_col = find_column(make_streamlit_safe_df(player_df), ["Club"])
    league_col = find_column(make_streamlit_safe_df(player_df), ["Division", "League"])
    primary_col = find_column(make_streamlit_safe_df(player_df), ["Primary Position"])

    if league_col:
        leagues = ["All"] + sorted(player_df[league_col].dropna().astype(str).unique().tolist())
        selected_player_league = st.selectbox("Filter Player League", leagues, key="player_league_filter")

        if selected_player_league != "All":
            player_df = player_df[player_df[league_col].astype(str) == selected_player_league]

    if primary_col:
        positions = ["All"] + sorted(player_df[primary_col].dropna().astype(str).unique().tolist())
        selected_position = st.selectbox("Filter Primary Position", positions)

        if selected_position != "All":
            player_df = player_df[player_df[primary_col].astype(str) == selected_position]

    if club_col:
        clubs = ["All"] + sorted(player_df[club_col].dropna().astype(str).unique().tolist())
        selected_player_club = st.selectbox("Filter Player Club", clubs)

        if selected_player_club != "All":
            player_df = player_df[player_df[club_col].astype(str) == selected_player_club]

    if name_col:
        search_name = st.text_input("Search Player Name")

        if search_name:
            player_df = player_df[
                player_df[name_col].astype(str).str.contains(search_name, case=False, na=False)
            ]

    player_df = player_df.sort_values("Best Attribute Category Score", ascending=False)

    st.dataframe(
        make_streamlit_safe_df(player_df),
        use_container_width=True,
        height=650,
    )

    st.download_button(
        label="Download Player Category Scores CSV",
        data=make_streamlit_safe_df(player_df).to_csv(index=False).encode("utf-8"),
        file_name="fm24_player_category_scores.csv",
        mime="text/csv",
    )

save_page_memory(__file__)
