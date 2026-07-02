from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from fm_engine.fast_data import (
    get_file_signature,
    list_saved_files,
    load_fm_file_cached,
)

UPLOAD_DIR = PROJECT_ROOT / "data" / "uploads"
TACTICS_DIR = PROJECT_ROOT / "configs" / "saved_tactics"


# ============================================================
# CATEGORY PROFILES
# ============================================================

CATEGORY_PROFILES = {
    "Keeper": {
        "accepted_positions": ["GK"],
        "depth": 1,
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
    "Defender": {
        "accepted_positions": ["CB", "RB", "LB", "RWB", "LWB"],
        "depth": 4,
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
    "Defensive Midfielder": {
        "accepted_positions": ["DM"],
        "depth": 1,
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
    "Central Midfielder": {
        "accepted_positions": ["CM"],
        "depth": 2,
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
    "Attacking Midfielder": {
        "accepted_positions": ["AM"],
        "depth": 1,
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
    "Winger": {
        "accepted_positions": ["RW", "LW", "RM", "LM"],
        "depth": 2,
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
    "Striker": {
        "accepted_positions": ["ST"],
        "depth": 1,
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


CATEGORY_WEIGHTS = {
    "Keeper": 0.10,
    "Defender": 0.22,
    "Defensive Midfielder": 0.10,
    "Central Midfielder": 0.14,
    "Attacking Midfielder": 0.12,
    "Winger": 0.15,
    "Striker": 0.17,
}


PLAYSTYLE_PROFILES = {
    "Positional Play / Build From The Back": {
        "attributes": {
            "Pas": 1.30,
            "Fir": 1.20,
            "Tec": 1.15,
            "Dec": 1.20,
            "Cmp": 1.15,
            "Vis": 1.10,
            "Tea": 1.10,
            "Pos": 1.00,
            "OtB": 0.95,
        },
        "stats": ["Pas %", "Ps C/90", "OP-KP/90", "Ch C/90"],
    },
    "High Press / Counter-Press": {
        "attributes": {
            "Wor": 1.30,
            "Sta": 1.25,
            "Agg": 1.10,
            "Ant": 1.10,
            "Tea": 1.10,
            "Acc": 1.05,
            "Pac": 1.00,
            "Dec": 1.00,
            "Tck": 0.95,
        },
        "stats": ["Poss Won/90", "Pres C/90", "Sprints/90", "Tck/90", "Int/90"],
    },
    "Vertical Counter Attack": {
        "attributes": {
            "Pac": 1.25,
            "Acc": 1.25,
            "OtB": 1.20,
            "Dri": 1.10,
            "Fin": 1.05,
            "Dec": 1.00,
            "Pas": 0.95,
            "Cmp": 0.95,
        },
        "stats": ["Gls/90", "xG/90", "Drb/90", "Sprints/90", "Shot/90", "OP-KP/90"],
    },
    "Defensive Compactness / Control Space": {
        "attributes": {
            "Pos": 1.30,
            "Ant": 1.20,
            "Cnt": 1.15,
            "Dec": 1.10,
            "Tck": 1.10,
            "Mar": 1.05,
            "Tea": 1.05,
            "Wor": 1.00,
            "Str": 0.90,
        },
        "stats": ["Tck/90", "Int/90", "Poss Won/90", "Clear", "Blk/90", "Av Rat"],
    },
    "Wide Overloads / Crossing": {
        "attributes": {
            "Cro": 1.30,
            "Dri": 1.10,
            "Acc": 1.10,
            "Pac": 1.10,
            "Sta": 1.05,
            "Wor": 1.00,
            "OtB": 1.00,
            "Tec": 0.95,
        },
        "stats": ["Cr C/90", "OP-Crs C/90", "Crs A/90", "Asts/90", "Sprints/90"],
    },
    "Half-Space Creativity / Cutbacks": {
        "attributes": {
            "Pas": 1.20,
            "Vis": 1.25,
            "Tec": 1.15,
            "Fir": 1.10,
            "Dri": 1.05,
            "OtB": 1.05,
            "Dec": 1.10,
            "Cmp": 1.00,
        },
        "stats": ["OP-KP/90", "Ch C/90", "xA/90", "Asts/90", "Drb/90", "Pas %"],
    },
}


IDENTITY_COLUMNS = [
    "Name", "Age", "Nat", "Club", "Division", "League", "Position",
    "Primary Position", "Position Classes", "Transfer Value", "Value", "Wage"
]


# ============================================================
# BASIC HELPERS
# ============================================================

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


def get_identity_cols(df: pd.DataFrame) -> list[str]:
    cols = []

    for wanted in IDENTITY_COLUMNS:
        col = find_column(df, [wanted])

        if col and col not in cols:
            cols.append(col)

    return cols


def clean_numeric_series(series: pd.Series) -> pd.Series:
    if series.dtype == "object":
        cleaned = (
            series.astype(str)
            .str.replace("%", "", regex=False)
            .str.replace(",", "", regex=False)
            .str.replace("£", "", regex=False)
            .str.replace("$", "", regex=False)
            .str.replace("€", "", regex=False)
            .str.strip()
        )

        return pd.to_numeric(cleaned, errors="coerce")

    return pd.to_numeric(series, errors="coerce")


def parse_money_to_millions(value) -> float:
    if pd.isna(value):
        return np.nan

    text = str(value).strip()

    if text == "":
        return np.nan

    text = text.replace("£", "").replace("$", "").replace("€", "").replace(",", "")
    text = text.replace("p/w", "").replace("pw", "").strip()

    parts = re.split(r"\s*-\s*", text)
    parsed = []

    for part in parts:
        part = part.strip().upper()

        match = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*([KMB]?)", part)

        if not match:
            continue

        number = float(match.group(1))
        suffix = match.group(2)

        if suffix == "K":
            number = number / 1000
        elif suffix == "M":
            number = number
        elif suffix == "B":
            number = number * 1000

        parsed.append(number)

    if not parsed:
        return np.nan

    return round(sum(parsed) / len(parsed), 2)


def make_streamlit_safe_df(df: pd.DataFrame) -> pd.DataFrame:
    safe_df = df.copy()
    seen = {}
    cols = []

    for col in safe_df.columns:
        base = str(col)

        if base not in seen:
            seen[base] = 1
            cols.append(base)
        else:
            seen[base] += 1
            cols.append(f"{base} [{seen[base]}]")

    safe_df.columns = cols

    return safe_df


def list_saved_tactics() -> list[Path]:
    if not TACTICS_DIR.exists():
        return []

    return sorted(TACTICS_DIR.glob("*.json"))


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


def classify_position_classes(position_text: str) -> list[str]:
    text = normalize_position_text(position_text)
    found = []

    checks = [
        ("GK", ["GK"]),
        ("CB", ["D(C)", "DC", "SW"]),
        ("RB", ["D(R)", "DR"]),
        ("LB", ["D(L)", "DL"]),
        ("RWB", ["WB(R)", "WBR"]),
        ("LWB", ["WB(L)", "WBL"]),
        ("DM", ["DM", "DM(C)"]),
        ("CM", ["M(C)", "MC"]),
        ("RM", ["M(R)", "MR"]),
        ("LM", ["M(L)", "ML"]),
        ("AM", ["AM(C)", "AMC"]),
        ("RW", ["AM(R)", "AMR"]),
        ("LW", ["AM(L)", "AML"]),
        ("ST", ["ST", "ST(C)", "SC", "CF"]),
    ]

    for label, patterns in checks:
        if any(pattern in text for pattern in patterns):
            found.append(label)

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


def add_position_classification(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    position_col = find_column(df, ["Position", "Positions"])

    if not position_col:
        df["Position Classes"] = "Unknown"
        df["Primary Position"] = "Unknown"
        return df

    classes_series = df[position_col].apply(classify_position_classes)

    df["Position Classes"] = classes_series.apply(
        lambda items: ", ".join(items) if items else "Unknown"
    )

    df["Primary Position"] = classes_series.apply(primary_position_from_classes)

    return df


def position_mask(df: pd.DataFrame, accepted_positions: list[str]) -> pd.Series:
    if "Position Classes" not in df.columns:
        return pd.Series(False, index=df.index)

    normalized = "," + df["Position Classes"].astype(str).str.replace(" ", "", regex=False) + ","

    mask = pd.Series(False, index=df.index)

    for pos in accepted_positions:
        mask = mask | normalized.str.contains(f",{pos},", regex=False, na=False)

    return mask


# ============================================================
# FAST SCORING
# ============================================================

def build_attribute_map(df: pd.DataFrame) -> dict[str, str]:
    all_attributes = set()

    for profile in CATEGORY_PROFILES.values():
        all_attributes.update(profile["attributes"].keys())

    for profile in PLAYSTYLE_PROFILES.values():
        all_attributes.update(profile["attributes"].keys())

    attribute_map = {}

    for attr in all_attributes:
        matches = [col for col in df.columns if base_column_name(col) == attr]

        if attr == "Nat":
            natural_fitness = [col for col in matches if col != "Nat"]

            if natural_fitness:
                attribute_map[attr] = natural_fitness[0]
        else:
            first_match = [col for col in matches if duplicate_number(col) == 1]

            if first_match:
                attribute_map[attr] = first_match[0]

    return attribute_map


def vector_attribute_score(df: pd.DataFrame, weights: dict[str, float], attribute_map: dict[str, str]) -> pd.Series:
    cols = []
    weight_values = []

    for attr, weight in weights.items():
        col = attribute_map.get(attr)

        if col and col in df.columns:
            cols.append(col)
            weight_values.append(float(weight))

    if not cols:
        return pd.Series(0.0, index=df.index)

    matrix = pd.DataFrame(index=df.index)

    for col in cols:
        matrix[col] = clean_numeric_series(df[col])

    weights_array = np.array(weight_values, dtype=float)
    weighted_values = matrix.mul(weights_array, axis=1)
    weighted_sum = weighted_values.sum(axis=1, min_count=1)
    valid_weight_sum = matrix.notna().mul(weights_array, axis=1).sum(axis=1)

    score = ((weighted_sum / valid_weight_sum) / 20) * 100
    score = score.where(valid_weight_sum > 0, 0)

    return score.fillna(0).round(1)


def get_matching_stat_columns(df: pd.DataFrame, stat_names: list[str]) -> list[str]:
    cols = []

    for stat in stat_names:
        for col in df.columns:
            if base_column_name(col) == stat and col not in cols:
                cols.append(col)

    return cols


def vector_stat_score(df: pd.DataFrame, stat_names: list[str]) -> pd.Series:
    stat_cols = get_matching_stat_columns(df, stat_names)

    if not stat_cols:
        return pd.Series(50.0, index=df.index)

    lower_is_better = {
        "Poss Lost/90",
        "Fls",
        "Conc",
        "G. Mis",
        "Lost",
    }

    score_parts = []

    for col in stat_cols:
        numeric = clean_numeric_series(df[col])

        if numeric.notna().sum() <= 1:
            score = pd.Series(50.0, index=df.index)
        else:
            score = numeric.rank(pct=True) * 100

            if base_column_name(col) in lower_is_better:
                score = 100 - score

        score_parts.append(score.fillna(50.0))

    return pd.concat(score_parts, axis=1).mean(axis=1).round(1)


def add_player_scores(df: pd.DataFrame, min_minutes: int) -> pd.DataFrame:
    df = df.copy()
    attribute_map = build_attribute_map(df)

    mins_col = find_column(df, ["Mins"])

    if mins_col:
        mins = clean_numeric_series(df[mins_col]).fillna(0)
        df["Stat Eligible"] = mins >= min_minutes
    else:
        df["Stat Eligible"] = True

    for category_name, profile in CATEGORY_PROFILES.items():
        attr_col = f"{category_name} Attribute Rating"
        stat_col = f"{category_name} Statistical Rating"
        combined_col = f"{category_name} Combined Rating"

        df[attr_col] = vector_attribute_score(
            df,
            profile["attributes"],
            attribute_map,
        )

        df[stat_col] = vector_stat_score(
            df,
            profile["stats"],
        )

        df.loc[~df["Stat Eligible"], stat_col] = pd.NA

        df[combined_col] = (
            df[attr_col] * 0.60
            + df[stat_col].fillna(50) * 0.40
        ).round(1)

    for playstyle_name, profile in PLAYSTYLE_PROFILES.items():
        attr_col = f"{playstyle_name} Attribute Fit"
        stat_col = f"{playstyle_name} Statistical Fit"
        combined_col = f"{playstyle_name} Playstyle Fit"

        df[attr_col] = vector_attribute_score(
            df,
            profile["attributes"],
            attribute_map,
        )

        df[stat_col] = vector_stat_score(
            df,
            profile["stats"],
        )

        df[combined_col] = (
            df[attr_col] * 0.65
            + df[stat_col].fillna(50) * 0.35
        ).round(1)

    value_col = find_column(df, ["Transfer Value", "Value"])

    if value_col:
        df["Estimated Value £M"] = df[value_col].apply(parse_money_to_millions)
    else:
        df["Estimated Value £M"] = np.nan

    return df


# ============================================================
# TEAM RATINGS + BENCHMARKS
# ============================================================

def aggregate_category_strength(df: pd.DataFrame, clubs: pd.Index, club_col: str, category_name: str) -> pd.DataFrame:
    profile = CATEGORY_PROFILES[category_name]
    depth = profile["depth"]
    score_col = f"{category_name} Combined Rating"

    mask = position_mask(df, profile["accepted_positions"])
    candidates = df.loc[mask, [club_col, score_col]].copy()
    candidates[score_col] = pd.to_numeric(candidates[score_col], errors="coerce")
    candidates = candidates[candidates[score_col].notna()]

    result = pd.DataFrame(index=clubs)

    if candidates.empty:
        result[f"Combined - {category_name}"] = 0.0
        result[f"Players - {category_name}"] = 0
        return result

    candidates = candidates.sort_values([club_col, score_col], ascending=[True, False])
    candidates["_rank"] = candidates.groupby(club_col).cumcount() + 1
    top_depth = candidates[candidates["_rank"] <= depth]

    grouped = top_depth.groupby(club_col)[score_col].agg(["sum", "count"])

    result[f"Cumulative - {category_name}"] = grouped["sum"].reindex(clubs).fillna(0).round(1)
    result[f"Players - {category_name}"] = grouped["count"].reindex(clubs).fillna(0).astype(int)
    result[f"Combined - {category_name}"] = (
        result[f"Cumulative - {category_name}"] / depth
    ).round(1)

    return result


def get_team_league_map(df: pd.DataFrame, club_col: str) -> pd.Series:
    league_col = find_column(df, ["Division", "League"])

    if not league_col:
        return pd.Series("Unknown", index=sorted(df[club_col].dropna().astype(str).unique()))

    league_map = (
        df[[club_col, league_col]]
        .dropna()
        .astype(str)
        .groupby(club_col)[league_col]
        .agg(lambda values: values.mode().iloc[0] if not values.mode().empty else values.iloc[0])
    )

    return league_map


def build_team_ratings(df: pd.DataFrame) -> pd.DataFrame:
    club_col = find_column(df, ["Club"])

    if not club_col:
        return pd.DataFrame()

    df = df[df[club_col].notna()].copy()
    df[club_col] = df[club_col].astype(str)

    clubs = pd.Index(sorted(df[club_col].dropna().unique()), name=club_col)

    team_ratings = pd.DataFrame(index=clubs)
    team_ratings["Club"] = clubs.astype(str).values
    team_ratings["League"] = get_team_league_map(df, club_col).reindex(clubs).fillna("Unknown").values
    team_ratings["Players In Database"] = df.groupby(club_col).size().reindex(clubs).fillna(0).astype(int).values

    weighted_cols = []

    for category_name in CATEGORY_PROFILES.keys():
        piece = aggregate_category_strength(df, clubs, club_col, category_name)
        team_ratings = pd.concat([team_ratings, piece], axis=1)

        weighted_col = f"Weighted - {category_name}"
        team_ratings[weighted_col] = team_ratings[f"Combined - {category_name}"] * CATEGORY_WEIGHTS[category_name]
        weighted_cols.append(weighted_col)

    team_ratings["Overall Team Rating"] = team_ratings[weighted_cols].sum(axis=1).round(1)
    team_ratings = team_ratings.sort_values("Overall Team Rating", ascending=False).reset_index(drop=True)

    return team_ratings




def detect_south_america_mask(team_ratings: pd.DataFrame) -> pd.Series:
    text = (
        team_ratings["League"].astype(str).str.lower()
        + " "
        + team_ratings["Club"].astype(str).str.lower()
    )

    keywords = [
        "brazil",
        "brasil",
        "argentina",
        "uruguay",
        "chile",
        "colombia",
        "paraguay",
        "peru",
        "ecuador",
        "bolivia",
        "venezuela",
        "brasileiro",
        "brasileirao",
        "serie a brazil",
        "liga profesional",
        "primera division argentina",
        "libertadores",
    ]

    mask = pd.Series(False, index=team_ratings.index)

    for keyword in keywords:
        mask = mask | text.str.contains(keyword, case=False, na=False)

    return mask


def determine_benchmark(
    team_ratings: pd.DataFrame,
    your_club: str,
    target_competition: str,
) -> tuple[dict[str, float], pd.DataFrame, str]:
    your_row = team_ratings[team_ratings["Club"].astype(str) == str(your_club)]

    if your_row.empty:
        pool = team_ratings.head(10).copy()
        explanation = "Could not find your club rating, so the benchmark uses the best teams in the database."
    else:
        your_league = str(your_row.iloc[0]["League"])

        if target_competition == "Win Domestic League":
            same_league = team_ratings[team_ratings["League"].astype(str) == your_league].copy()
            pool = same_league.sort_values("Overall Team Rating", ascending=False).head(3)
            explanation = f"Domestic title benchmark uses the top teams in your league: {your_league}."

        elif target_competition == "Win UEFA Champions League":
            pool = team_ratings.sort_values("Overall Team Rating", ascending=False).head(12)
            explanation = "Champions League benchmark uses the top elite clubs in the full database."

        elif target_competition == "Win UEFA Europa League":
            sorted_teams = team_ratings.sort_values("Overall Team Rating", ascending=False).copy()

            if len(sorted_teams) >= 32:
                pool = sorted_teams.iloc[12:32].copy()
            else:
                pool = sorted_teams.head(20).copy()

            explanation = "Europa League benchmark uses strong continental-level teams below the absolute elite."

        elif target_competition == "Win Copa Libertadores":
            south_america = team_ratings[detect_south_america_mask(team_ratings)].copy()

            if south_america.empty:
                pool = team_ratings.sort_values("Overall Team Rating", ascending=False).head(20)
                explanation = "Could not clearly detect South American leagues, so the Libertadores benchmark uses a strong global fallback."
            else:
                pool = south_america.sort_values("Overall Team Rating", ascending=False).head(10)
                explanation = "Copa Libertadores benchmark uses the strongest detected South American clubs."

        else:
            pool = team_ratings.sort_values("Overall Team Rating", ascending=False).head(10)
            explanation = "Benchmark uses the top teams in the database."

    if pool.empty:
        pool = team_ratings.sort_values("Overall Team Rating", ascending=False).head(10)

    if target_competition == "Win Domestic League":
        cushion = 2.0
    elif target_competition == "Win UEFA Champions League":
        cushion = 4.0
    elif target_competition == "Win UEFA Europa League":
        cushion = 3.0
    elif target_competition == "Win Copa Libertadores":
        cushion = 3.5
    else:
        cushion = 2.0

    benchmark = {}

    for category_name in CATEGORY_PROFILES.keys():
        col = f"Combined - {category_name}"

        if col in pool.columns:
            benchmark[category_name] = round(float(pool[col].mean()) + cushion, 1)
        else:
            benchmark[category_name] = 70.0

    return benchmark, pool, explanation


def build_current_gaps(team_ratings: pd.DataFrame, your_club: str, benchmark: dict[str, float]) -> pd.DataFrame:
    your_row = team_ratings[team_ratings["Club"].astype(str) == str(your_club)]

    if your_row.empty:
        return pd.DataFrame()

    row = your_row.iloc[0]
    records = []

    for category_name in CATEGORY_PROFILES.keys():
        current_score = float(row.get(f"Combined - {category_name}", 0))
        target_score = float(benchmark.get(category_name, 70))
        gap = round(target_score - current_score, 1)

        records.append(
            {
                "Squad Area": category_name,
                "Current Rating": round(current_score, 1),
                "Target Rating": round(target_score, 1),
                "Gap To Target": gap,
                "Priority": "Critical" if gap >= 8 else "Important" if gap >= 4 else "Depth / Optional",
            }
        )

    return pd.DataFrame(records).sort_values("Gap To Target", ascending=False)


# ============================================================
# RECOMMENDATION ENGINE
# ============================================================

def build_signing_recommendations(
    df: pd.DataFrame,
    team_ratings: pd.DataFrame,
    your_club: str,
    target_competition: str,
    playstyle: str,
    benchmark: dict[str, float],
    max_age: int,
    max_value_millions: float | None,
    top_n: int,
    search_pool: str,
) -> pd.DataFrame:
    club_col = find_column(df, ["Club"])
    name_col = find_column(df, ["Name", "Player"])
    age_col = find_column(df, ["Age"])
    position_col = find_column(df, ["Position"])
    league_col = find_column(df, ["Division", "League"])
    value_col = find_column(df, ["Transfer Value", "Value"])

    if not club_col or not name_col:
        return pd.DataFrame()

    current_gaps = build_current_gaps(team_ratings, your_club, benchmark)

    if current_gaps.empty:
        return pd.DataFrame()

    your_team_rating = team_ratings[team_ratings["Club"].astype(str) == str(your_club)]

    if your_team_rating.empty:
        return pd.DataFrame()

    your_row = your_team_rating.iloc[0]
    your_league = str(your_row.get("League", ""))

    priority_categories = current_gaps[current_gaps["Gap To Target"] > 0]["Squad Area"].tolist()

    if not priority_categories:
        priority_categories = current_gaps.head(3)["Squad Area"].tolist()

    candidate_rows = []
    playstyle_col = f"{playstyle} Playstyle Fit"

    base_candidates = df[df[club_col].astype(str) != str(your_club)].copy()

    if search_pool == "Same League Only" and league_col:
        base_candidates = base_candidates[base_candidates[league_col].astype(str) == your_league].copy()

    elif search_pool == "Outside Current League" and league_col:
        base_candidates = base_candidates[base_candidates[league_col].astype(str) != your_league].copy()

    if age_col:
        ages = clean_numeric_series(base_candidates[age_col])
        base_candidates = base_candidates[ages <= max_age].copy()

    if max_value_millions is not None and "Estimated Value £M" in base_candidates.columns:
        values = pd.to_numeric(base_candidates["Estimated Value £M"], errors="coerce")
        base_candidates = base_candidates[
            values.isna() | (values <= max_value_millions)
        ].copy()

    for category_name in priority_categories:
        profile = CATEGORY_PROFILES[category_name]
        category_col = f"{category_name} Combined Rating"
        attr_col = f"{category_name} Attribute Rating"
        stat_col = f"{category_name} Statistical Rating"

        if category_col not in base_candidates.columns:
            continue

        mask = position_mask(base_candidates, profile["accepted_positions"])
        candidates = base_candidates[mask].copy()

        if candidates.empty:
            continue

        current_score = float(your_row.get(f"Combined - {category_name}", 0))
        target_score = float(benchmark.get(category_name, 70))
        gap = max(target_score - current_score, 0)

        candidates["Candidate Category Rating"] = pd.to_numeric(candidates[category_col], errors="coerce")
        candidates["Candidate Attribute Fit"] = pd.to_numeric(candidates[attr_col], errors="coerce")
        candidates["Candidate Statistical Fit"] = pd.to_numeric(candidates[stat_col], errors="coerce")

        if playstyle_col in candidates.columns:
            candidates["Playstyle Fit"] = pd.to_numeric(candidates[playstyle_col], errors="coerce")
        else:
            candidates["Playstyle Fit"] = 50.0

        candidates["Upgrade Over Current Area"] = (
            candidates["Candidate Category Rating"] - current_score
        ).round(1)

        if gap > 0:
            candidates["Gap Covered %"] = (
                candidates["Upgrade Over Current Area"].clip(lower=0) / gap * 100
            ).clip(upper=100).round(1)
        else:
            candidates["Gap Covered %"] = 100.0

        upgrade_score = (candidates["Upgrade Over Current Area"].clip(lower=0, upper=30) / 30 * 100)

        candidates["Recommendation Score"] = (
            candidates["Candidate Category Rating"] * 0.42
            + candidates["Playstyle Fit"] * 0.28
            + upgrade_score * 0.20
            + candidates["Gap Covered %"] * 0.10
        ).round(1)

        for _, row in candidates.iterrows():
            player_name = row.get(name_col, "Unknown")
            player_club = row.get(club_col, "Unknown")
            player_position = row.get(position_col, "Unknown") if position_col else "Unknown"
            player_age = row.get(age_col, "") if age_col else ""
            player_league = row.get(league_col, "") if league_col else ""
            value_display = row.get(value_col, "") if value_col else ""

            reason = (
                f"Targets your {category_name} gap for {target_competition}. "
                f"Current area rating: {current_score:.1f}. "
                f"Target: {target_score:.1f}. "
                f"Candidate rating: {row['Candidate Category Rating']:.1f}. "
                f"Playstyle fit: {row['Playstyle Fit']:.1f}."
            )

            candidate_rows.append(
                {
                    "Player": player_name,
                    "Age": player_age,
                    "Club": player_club,
                    "League": player_league,
                    "Position": player_position,
                    "Recommended For": category_name,
                    "Target Competition": target_competition,
                    "Playstyle": playstyle,
                    "Recommendation Score": row["Recommendation Score"],
                    "Candidate Category Rating": row["Candidate Category Rating"],
                    "Candidate Attribute Fit": row["Candidate Attribute Fit"],
                    "Candidate Statistical Fit": row["Candidate Statistical Fit"],
                    "Playstyle Fit": row["Playstyle Fit"],
                    "Upgrade Over Current Area": row["Upgrade Over Current Area"],
                    "Gap Covered %": row["Gap Covered %"],
                    "Estimated Value": value_display,
                    "Estimated Value £M": row.get("Estimated Value £M", np.nan),
                    "Why Recommended": reason,
                }
            )

    recommendations = pd.DataFrame(candidate_rows)

    if recommendations.empty:
        return recommendations

    gap_priority_order = {
        row["Squad Area"]: index + 1
        for index, row in current_gaps.reset_index(drop=True).iterrows()
    }

    gap_value_map = {
        row["Squad Area"]: row["Gap To Target"]
        for _, row in current_gaps.iterrows()
    }

    priority_map = {
        row["Squad Area"]: row["Priority"]
        for _, row in current_gaps.iterrows()
    }

    recommendations["Gap Priority Order"] = recommendations["Recommended For"].map(gap_priority_order).fillna(99).astype(int)
    recommendations["Squad Gap Value"] = recommendations["Recommended For"].map(gap_value_map).fillna(0)
    recommendations["Squad Gap Priority"] = recommendations["Recommended For"].map(priority_map).fillna("Depth / Optional")

    recommendations = recommendations.sort_values(
        ["Gap Priority Order", "Recommendation Score"],
        ascending=[True, False],
    )

    # Keep unique players inside each specific squad gap.
    recommendations = recommendations.drop_duplicates(
        subset=["Recommended For", "Player", "Club"],
        keep="first",
    )

    # Top N options per squad gap.
    recommendations["Gap Rank"] = (
        recommendations
        .groupby("Recommended For")
        .cumcount()
        + 1
    )

    recommendations = recommendations[
        recommendations["Gap Rank"] <= top_n
    ].copy()

    recommendations = recommendations.sort_values(
        ["Gap Priority Order", "Gap Rank", "Recommendation Score"],
        ascending=[True, True, False],
    ).reset_index(drop=True)

    recommendations.insert(0, "Overall Row", recommendations.index + 1)

    return recommendations


@st.cache_data(show_spinner="Building recommended signing model...")
def prepare_recommended_signings_cached(path_text: str, mtime: float, size: int, min_minutes: int):
    raw_df = load_fm_file_cached(path_text, mtime, size).copy()

    raw_df = raw_df.dropna(axis=0, how="all")
    raw_df = raw_df.dropna(axis=1, how="all")
    raw_df = raw_df.drop_duplicates()

    df = add_position_classification(raw_df)
    df = add_player_scores(df, min_minutes=min_minutes)
    team_ratings = build_team_ratings(df)

    return df, team_ratings


# ============================================================
# STREAMLIT APP
# ============================================================

st.set_page_config(
    page_title="Recommended Signings",
    page_icon="📝",
    layout="wide",
)

st.title("Recommended Signings")

st.write(
    """
    Find targeted signings based on your club, your target competition, your tactic/playstyle,
    and the biggest gaps in your squad.
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

min_minutes = st.sidebar.number_input(
    "Minimum Minutes For Statistical Fit",
    min_value=0,
    value=300,
    step=100,
)

path_text, mtime, size = get_file_signature(selected_file)

df, team_ratings = prepare_recommended_signings_cached(
    path_text,
    mtime,
    size,
    int(min_minutes),
)

if team_ratings.empty:
    st.error("No club/team ratings could be built. Make sure your database has a Club column.")
    st.stop()

club_options = sorted(team_ratings["Club"].dropna().astype(str).unique().tolist())

st.sidebar.header("Signing Mission")

your_club = st.sidebar.selectbox(
    "Your Club",
    club_options,
)

target_competition = st.sidebar.selectbox(
    "Target Goal",
    [
        "Win Domestic League",
        "Win UEFA Champions League",
        "Win UEFA Europa League",
        "Win Copa Libertadores",
    ],
)

saved_tactics = list_saved_tactics()

selected_tactic_path = None

if saved_tactics:
    selected_tactic_path = st.sidebar.selectbox(
        "Saved Tactic Context",
        [None] + saved_tactics,
        format_func=lambda path: "None selected" if path is None else path.name,
    )

tactic = load_tactic(selected_tactic_path) if selected_tactic_path else {}

default_playstyle = "Positional Play / Build From The Back"

if tactic:
    philosophy = tactic.get("philosophy", [])

    if philosophy:
        for item in philosophy:
            if item in PLAYSTYLE_PROFILES:
                default_playstyle = item
                break

playstyle_options = list(PLAYSTYLE_PROFILES.keys())

playstyle = st.sidebar.selectbox(
    "Tactic / Playstyle",
    playstyle_options,
    index=playstyle_options.index(default_playstyle),
)

top_n = st.sidebar.slider(
    "Top Options Per Squad Gap",
    min_value=3,
    max_value=20,
    value=5,
    step=1,
)

search_pool = st.sidebar.selectbox(
    "Candidate Search Pool",
    [
        "Entire Database",
        "Same League Only",
        "Outside Current League",
    ],
)

max_age = st.sidebar.slider(
    "Max Age",
    min_value=16,
    max_value=40,
    value=30,
)

use_value_cap = st.sidebar.checkbox("Use Estimated Value Cap", value=False)

max_value_millions = None

if use_value_cap:
    max_value_millions = st.sidebar.number_input(
        "Max Estimated Value £M",
        min_value=0.0,
        value=50.0,
        step=5.0,
    )

if st.sidebar.button("Clear Signing Recommendation Cache"):
    prepare_recommended_signings_cached.clear()
    st.sidebar.success("Cleared recommended signing cache.")
    st.rerun()

benchmark, benchmark_teams, benchmark_explanation = determine_benchmark(
    team_ratings,
    your_club=your_club,
    target_competition=target_competition,
)

current_gaps = build_current_gaps(
    team_ratings,
    your_club=your_club,
    benchmark=benchmark,
)

recommendations = build_signing_recommendations(
    df=df,
    team_ratings=team_ratings,
    your_club=your_club,
    target_competition=target_competition,
    playstyle=playstyle,
    benchmark=benchmark,
    max_age=int(max_age),
    max_value_millions=max_value_millions,
    top_n=int(top_n),
    search_pool=search_pool,
)

your_team_row = team_ratings[team_ratings["Club"].astype(str) == str(your_club)]

st.subheader(f"Mission: {your_club} — {target_competition}")

if not your_team_row.empty:
    your_rating = float(your_team_row.iloc[0]["Overall Team Rating"])
    your_league = str(your_team_row.iloc[0]["League"])
else:
    your_rating = 0.0
    your_league = "Unknown"

m1, m2, m3, m4 = st.columns(4)

m1.metric("Your Team Rating", f"{your_rating:.1f}")
m2.metric("League", your_league)
m3.metric("Target", target_competition)
m4.metric("Playstyle", playstyle)

st.info(benchmark_explanation)

tab1, tab2, tab3, tab4 = st.tabs(
    [
        "Top Recommended Signings",
        "Squad Gaps",
        "Benchmark Teams",
        "All Candidate Scores",
    ]
)

with tab1:
    st.subheader("Top Recommended Signings By Squad Gap")

    st.write(
        """
        This section now gives you the best signing options for each specific squad gap.
        For example, if your biggest gaps are Striker, Winger, and Defender, you will get
        a separate top 5 list for each one.
        """
    )

    if recommendations.empty:
        st.warning("No recommendations found. Try lowering minimum minutes, increasing max age, or removing the value cap.")
    else:
        gap_summary_cols = [
            "Squad Area",
            "Current Rating",
            "Target Rating",
            "Gap To Target",
            "Priority",
        ]

        gap_summary_cols = [col for col in gap_summary_cols if col in current_gaps.columns]

        st.markdown("### Squad Gap Priority")
        st.dataframe(
            make_streamlit_safe_df(current_gaps[gap_summary_cols]),
            use_container_width=True,
            height=280,
        )

        st.markdown("### Top Options For Each Gap")

        main_cols = [
            "Gap Rank",
            "Player",
            "Age",
            "Club",
            "League",
            "Position",
            "Recommended For",
            "Recommendation Score",
            "Candidate Category Rating",
            "Candidate Attribute Fit",
            "Candidate Statistical Fit",
            "Playstyle Fit",
            "Upgrade Over Current Area",
            "Gap Covered %",
            "Estimated Value",
            "Why Recommended",
        ]

        main_cols = [col for col in main_cols if col in recommendations.columns]

        ordered_gaps = current_gaps["Squad Area"].tolist()

        available_gaps = [
            gap for gap in ordered_gaps
            if gap in recommendations["Recommended For"].astype(str).unique().tolist()
        ]

        if not available_gaps:
            available_gaps = recommendations["Recommended For"].dropna().astype(str).unique().tolist()

        for index, gap in enumerate(available_gaps):
            gap_recs = recommendations[
                recommendations["Recommended For"].astype(str) == str(gap)
            ].copy()

            if gap_recs.empty:
                continue

            gap_row = current_gaps[
                current_gaps["Squad Area"].astype(str) == str(gap)
            ]

            if not gap_row.empty:
                current_rating = gap_row.iloc[0].get("Current Rating", "")
                target_rating = gap_row.iloc[0].get("Target Rating", "")
                gap_value = gap_row.iloc[0].get("Gap To Target", "")
                priority = gap_row.iloc[0].get("Priority", "")
                title = f"{gap} — Gap: {gap_value} | Current: {current_rating} | Target: {target_rating} | {priority}"
            else:
                title = str(gap)

            with st.expander(title, expanded=index < 3):
                st.dataframe(
                    make_streamlit_safe_df(gap_recs[main_cols]),
                    use_container_width=True,
                    height=360,
                )

        st.markdown("### Full Recommended Signing List")

        st.dataframe(
            make_streamlit_safe_df(recommendations[main_cols]),
            use_container_width=True,
            height=500,
        )

        st.download_button(
            label="Download Recommended Signings By Gap CSV",
            data=make_streamlit_safe_df(recommendations).to_csv(index=False).encode("utf-8"),
            file_name=f"{your_club.replace(' ', '_')}_recommended_signings_by_gap.csv",
            mime="text/csv",
        )

with tab2:
    st.subheader("Your Squad Gaps Against Target Level")

    if current_gaps.empty:
        st.warning("Could not calculate squad gaps for this club.")
    else:
        st.dataframe(
            make_streamlit_safe_df(current_gaps),
            use_container_width=True,
            height=450,
        )

        st.markdown(
            """
            ### How To Read This

            - **Current Rating** = your current strength in that squad area.
            - **Target Rating** = the level needed for your selected goal.
            - **Gap To Target** = the area most in need of a signing.
            - **Critical** = this area probably needs a starter-level upgrade.
            """
        )

with tab3:
    st.subheader("Benchmark Teams Used For This Goal")

    display_cols = [
        "Club",
        "League",
        "Overall Team Rating",
    ]

    for category_name in CATEGORY_PROFILES.keys():
        display_cols.append(f"Combined - {category_name}")

    display_cols = [col for col in display_cols if col in benchmark_teams.columns]

    st.dataframe(
        make_streamlit_safe_df(benchmark_teams[display_cols]),
        use_container_width=True,
        height=500,
    )

with tab4:
    st.subheader("Search Candidate Scores")

    club_col = find_column(df, ["Club"])
    league_col = find_column(df, ["Division", "League"])
    name_col = find_column(df, ["Name", "Player"])
    primary_col = find_column(df, ["Primary Position"])

    identity_cols = get_identity_cols(df)

    score_cols = []

    for category_name in CATEGORY_PROFILES.keys():
        score_cols.append(f"{category_name} Combined Rating")
        score_cols.append(f"{category_name} Attribute Rating")
        score_cols.append(f"{category_name} Statistical Rating")

    score_cols.append(f"{playstyle} Playstyle Fit")
    score_cols.append("Estimated Value £M")
    score_cols.append("Stat Eligible")

    display_cols = [col for col in identity_cols + score_cols if col in df.columns]

    candidate_df = df[df[club_col].astype(str) != str(your_club)].copy() if club_col else df.copy()
    candidate_df = candidate_df[display_cols].copy()

    col_a, col_b, col_c = st.columns(3)

    with col_a:
        if league_col and league_col in candidate_df.columns:
            leagues = ["All"] + sorted(candidate_df[league_col].dropna().astype(str).unique().tolist())
            selected_league = st.selectbox("Filter League", leagues)

            if selected_league != "All":
                candidate_df = candidate_df[candidate_df[league_col].astype(str) == selected_league]

    with col_b:
        if primary_col and primary_col in candidate_df.columns:
            positions = ["All"] + sorted(candidate_df[primary_col].dropna().astype(str).unique().tolist())
            selected_position = st.selectbox("Filter Position", positions)

            if selected_position != "All":
                candidate_df = candidate_df[candidate_df[primary_col].astype(str) == selected_position]

    with col_c:
        sort_options = [
            f"{playstyle} Playstyle Fit",
            "Keeper Combined Rating",
            "Defender Combined Rating",
            "Defensive Midfielder Combined Rating",
            "Central Midfielder Combined Rating",
            "Attacking Midfielder Combined Rating",
            "Winger Combined Rating",
            "Striker Combined Rating",
        ]

        sort_options = [col for col in sort_options if col in candidate_df.columns]

        sort_col = st.selectbox("Sort By", sort_options)

    if name_col and name_col in candidate_df.columns:
        search = st.text_input("Search Player")

        if search:
            candidate_df = candidate_df[
                candidate_df[name_col].astype(str).str.contains(search, case=False, na=False)
            ]

    if sort_col:
        candidate_df = candidate_df.sort_values(sort_col, ascending=False)

    rows_to_show = st.slider(
        "Rows To Show",
        min_value=25,
        max_value=1000,
        value=100,
        step=25,
    )

    st.dataframe(
        make_streamlit_safe_df(candidate_df.head(rows_to_show)),
        use_container_width=True,
        height=600,
    )

if tactic:
    st.divider()
    st.subheader("Loaded Tactic Context")
    st.json(tactic)
