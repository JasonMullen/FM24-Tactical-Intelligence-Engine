from __future__ import annotations

import re
from itertools import combinations
from typing import Any

import numpy as np
import pandas as pd


CATEGORY_PROFILES = {
    "Keeper": {
        "accepted_positions": ["GK"],
        "depth": 1,
        "attributes": {"Ref": 1.25, "Han": 1.20, "1v1": 1.15, "Aer": 1.05, "Cmd": 1.05, "Com": 1.00, "Kic": 0.90, "Thr": 0.85, "Dec": 0.90, "Cnt": 0.90},
        "stats": ["Av Rat", "Saves/90", "xSV %", "Shutouts"],
        "weight": 0.10,
    },
    "Defender": {
        "accepted_positions": ["CB", "RB", "LB", "RWB", "LWB"],
        "depth": 4,
        "attributes": {"Tck": 1.20, "Mar": 1.15, "Pos": 1.15, "Ant": 1.10, "Cnt": 1.05, "Hea": 1.00, "Jum": 0.95, "Str": 0.95, "Pac": 0.90, "Pas": 0.75},
        "stats": ["Av Rat", "Tck/90", "Int/90", "Poss Won/90", "Hdr %", "Clear", "Blk/90", "Pas %"],
        "weight": 0.22,
    },
    "Defensive Midfielder": {
        "accepted_positions": ["DM"],
        "depth": 1,
        "attributes": {"Tck": 1.15, "Pos": 1.20, "Ant": 1.10, "Dec": 1.10, "Cnt": 1.05, "Tea": 1.05, "Wor": 1.00, "Pas": 1.00, "Fir": 0.90, "Str": 0.85},
        "stats": ["Av Rat", "Tck/90", "Int/90", "Poss Won/90", "Pas %", "Ps C/90"],
        "weight": 0.10,
    },
    "Central Midfielder": {
        "accepted_positions": ["CM"],
        "depth": 2,
        "attributes": {"Pas": 1.15, "Fir": 1.10, "Dec": 1.15, "Tea": 1.05, "Vis": 1.00, "Tec": 1.00, "Wor": 0.95, "Sta": 0.95, "Tck": 0.85, "Cmp": 1.00},
        "stats": ["Av Rat", "Pas %", "Ps C/90", "OP-KP/90", "Tck/90", "Poss Won/90", "Asts/90"],
        "weight": 0.14,
    },
    "Attacking Midfielder": {
        "accepted_positions": ["AM"],
        "depth": 1,
        "attributes": {"Pas": 1.15, "Vis": 1.25, "Tec": 1.15, "Fir": 1.15, "OtB": 1.10, "Cmp": 1.05, "Dec": 1.05, "Dri": 1.00, "Fla": 1.00, "Fin": 0.85},
        "stats": ["Av Rat", "OP-KP/90", "Ch C/90", "xA/90", "Asts/90", "Drb/90", "Gls/90"],
        "weight": 0.12,
    },
    "Winger": {
        "accepted_positions": ["RW", "LW", "RM", "LM"],
        "depth": 2,
        "attributes": {"Acc": 1.15, "Pac": 1.15, "Dri": 1.20, "Cro": 1.05, "Tec": 1.05, "Fir": 1.00, "OtB": 1.10, "Fin": 0.90, "Dec": 0.90, "Sta": 0.85},
        "stats": ["Av Rat", "Drb/90", "Cr C/90", "OP-KP/90", "xA/90", "Asts/90", "Shot/90", "Gls/90"],
        "weight": 0.15,
    },
    "Striker": {
        "accepted_positions": ["ST"],
        "depth": 1,
        "attributes": {"Fin": 1.30, "OtB": 1.25, "Cmp": 1.10, "Ant": 1.05, "Fir": 1.00, "Acc": 0.95, "Pac": 0.95, "Str": 0.85, "Hea": 0.85, "Tec": 0.80},
        "stats": ["Av Rat", "Gls/90", "xG/90", "Shot/90", "ShT/90", "Conv %", "Asts/90"],
        "weight": 0.17,
    },
}


PLAYSTYLE_PROFILES = {
    "Positional Play / Build From The Back": {
        "attributes": {"Pas": 1.30, "Fir": 1.20, "Tec": 1.15, "Dec": 1.20, "Cmp": 1.15, "Vis": 1.10, "Tea": 1.10, "Pos": 1.00},
        "stats": ["Pas %", "Ps C/90", "OP-KP/90", "Ch C/90"],
    },
    "High Press / Counter-Press": {
        "attributes": {"Wor": 1.30, "Sta": 1.25, "Agg": 1.10, "Ant": 1.10, "Tea": 1.10, "Acc": 1.05, "Pac": 1.00, "Dec": 1.00, "Tck": 0.95},
        "stats": ["Poss Won/90", "Pres C/90", "Sprints/90", "Tck/90", "Int/90"],
    },
    "Vertical Counter Attack": {
        "attributes": {"Pac": 1.25, "Acc": 1.25, "OtB": 1.20, "Dri": 1.10, "Fin": 1.05, "Dec": 1.00, "Pas": 0.95, "Cmp": 0.95},
        "stats": ["Gls/90", "xG/90", "Drb/90", "Sprints/90", "Shot/90", "OP-KP/90"],
    },
    "Defensive Compactness / Control Space": {
        "attributes": {"Pos": 1.30, "Ant": 1.20, "Cnt": 1.15, "Dec": 1.10, "Tck": 1.10, "Mar": 1.05, "Tea": 1.05, "Wor": 1.00, "Str": 0.90},
        "stats": ["Tck/90", "Int/90", "Poss Won/90", "Clear", "Blk/90", "Av Rat"],
    },
    "Wide Overloads / Crossing": {
        "attributes": {"Cro": 1.30, "Dri": 1.10, "Acc": 1.10, "Pac": 1.10, "Sta": 1.05, "Wor": 1.00, "OtB": 1.00, "Tec": 0.95},
        "stats": ["Cr C/90", "OP-Crs C/90", "Crs A/90", "Asts/90", "Sprints/90"],
    },
    "Half-Space Creativity / Cutbacks": {
        "attributes": {"Pas": 1.20, "Vis": 1.25, "Tec": 1.15, "Fir": 1.10, "Dri": 1.05, "OtB": 1.05, "Dec": 1.10, "Cmp": 1.00},
        "stats": ["OP-KP/90", "Ch C/90", "xA/90", "Asts/90", "Drb/90", "Pas %"],
    },
}


def base_column_name(col: str) -> str:
    return re.sub(r"__\d+$", "", str(col))


def find_column(df: pd.DataFrame, names: list[str]) -> str | None:
    wanted = {name.lower() for name in names}

    for col in df.columns:
        if base_column_name(str(col)).lower() in wanted:
            return col

    return None


def clean_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(
        series.astype(str)
        .str.replace("%", "", regex=False)
        .str.replace(",", "", regex=False)
        .str.replace("£", "", regex=False)
        .str.replace("Â", "", regex=False)
        .str.strip(),
        errors="coerce",
    )


def make_safe_df(df: pd.DataFrame) -> pd.DataFrame:
    safe = df.copy()
    seen = {}
    cols = []

    for col in safe.columns:
        base = str(col)

        if base not in seen:
            seen[base] = 1
            cols.append(base)
        else:
            seen[base] += 1
            cols.append(f"{base} [{seen[base]}]")

    safe.columns = cols

    return safe


def format_money(value: Any) -> str:
    try:
        if value is None or pd.isna(value):
            return "Unknown"

        return f"£{float(value):,.0f}"
    except Exception:
        return "Unknown"


def parse_money_text(value: Any) -> float:
    try:
        if value is None or pd.isna(value):
            return np.nan
    except Exception:
        pass

    text = str(value).strip()

    if not text:
        return np.nan

    text = (
        text.replace("Ã‚Â£", "£")
        .replace("Â£", "£")
        .replace("Â", "")
        .replace("–", "-")
        .replace("—", "-")
        .replace(" to ", "-")
        .replace(" TO ", "-")
    )

    lowered = text.lower().strip()

    if "not for sale" in lowered or lowered == "nfs":
        return 1_000_000_000.0

    pieces = [piece.strip() for piece in text.split("-") if piece.strip()]
    parsed = []

    for piece in pieces:
        clean = (
            piece.upper()
            .replace("£", "")
            .replace("$", "")
            .replace("€", "")
            .replace(",", "")
            .replace(" ", "")
        )

        match = re.search(r"([0-9]+(?:\.[0-9]+)?)([KMB]?)", clean)

        if not match:
            continue

        number = float(match.group(1))
        suffix = match.group(2)

        if suffix == "K":
            number *= 1_000
        elif suffix == "M":
            number *= 1_000_000
        elif suffix == "B":
            number *= 1_000_000_000

        parsed.append(number)

    if not parsed:
        return np.nan

    return float(sum(parsed) / len(parsed))


def parse_budget_input(value: Any) -> float:
    text = str(value or "").strip().lower()
    text = text.replace("£", "").replace("$", "").replace("€", "")
    text = text.replace(",", "").replace("_", "").replace(" ", "")
    text = text.replace("millions", "m").replace("million", "m")
    text = text.replace("billions", "b").replace("billion", "b")
    text = text.replace("thousands", "k").replace("thousand", "k")

    match = re.search(r"([0-9]+(?:\.[0-9]+)?)([kmb]?)", text)

    if not match:
        return 0.0

    number = float(match.group(1))
    suffix = match.group(2)

    if suffix == "k":
        number *= 1_000
    elif suffix == "m":
        number *= 1_000_000
    elif suffix == "b":
        number *= 1_000_000_000

    return float(number)


def fallback_cost_from_quality(row: pd.Series) -> float:
    quality = row.get("Overall Player Quality", row.get("Candidate Category Rating", np.nan))

    try:
        quality = float(quality)
    except Exception:
        return np.nan

    if pd.isna(quality):
        return np.nan

    if quality >= 90:
        return 150_000_000.0
    if quality >= 86:
        return 95_000_000.0
    if quality >= 82:
        return 60_000_000.0
    if quality >= 78:
        return 35_000_000.0
    if quality >= 74:
        return 20_000_000.0
    if quality >= 70:
        return 12_000_000.0
    if quality >= 66:
        return 6_000_000.0

    return 2_000_000.0


def transfer_cost_from_row(row: pd.Series) -> float:
    million_cols = [
        "Transfer Value Clean £M",
        "Estimated Value Clean £M",
        "Estimated Value £M",
    ]

    normal_cols = [
        "Transfer Cost",
        "Transfer Value Clean",
        "Estimated Value Clean",
    ]

    text_cols = [
        "Transfer Value",
        "Transfer Value Raw",
        "Transfer Value Display",
        "Estimated Value",
        "Estimated Value Raw",
        "Estimated Value Display",
        "Value",
    ]

    for col in normal_cols:
        if col in row.index:
            value = pd.to_numeric(row.get(col), errors="coerce")

            if not pd.isna(value) and float(value) >= 0:
                return float(value)

    for col in million_cols:
        if col in row.index:
            value = pd.to_numeric(row.get(col), errors="coerce")

            if not pd.isna(value) and float(value) >= 0:
                return float(value) * 1_000_000

    for col in text_cols:
        if col in row.index:
            value = parse_money_text(row.get(col))

            if not pd.isna(value) and float(value) >= 0:
                return float(value)

    return fallback_cost_from_quality(row)


def ensure_transfer_costs(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    out["Transfer Cost"] = out.apply(transfer_cost_from_row, axis=1)
    out["Transfer Cost Display"] = out["Transfer Cost"].apply(format_money)

    return out


def position_classes(text: str) -> list[str]:
    t = str(text).upper().replace(" ", "").replace("-", "")

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

    found = []

    for label, patterns in checks:
        if any(pattern in t for pattern in patterns):
            found.append(label)

    return found or ["Unknown"]


def add_positions(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    pos_col = find_column(df, ["Position", "Positions"])

    if not pos_col:
        df["Position Classes"] = "Unknown"
        df["Primary Position"] = "Unknown"
        return df

    classes = df[pos_col].apply(position_classes)
    df["Position Classes"] = classes.apply(lambda x: ", ".join(x))
    df["Primary Position"] = classes.apply(lambda x: x[0] if x else "Unknown")

    return df


def pos_mask(df: pd.DataFrame, accepted: list[str]) -> pd.Series:
    if "Position Classes" not in df.columns:
        return pd.Series(False, index=df.index)

    text = "," + df["Position Classes"].astype(str).str.replace(" ", "", regex=False) + ","
    mask = pd.Series(False, index=df.index)

    for pos in accepted:
        mask = mask | text.str.contains(f",{pos},", regex=False, na=False)

    return mask


def attr_map(df: pd.DataFrame) -> dict[str, str]:
    attrs = set()

    for profile in CATEGORY_PROFILES.values():
        attrs.update(profile["attributes"])

    for profile in PLAYSTYLE_PROFILES.values():
        attrs.update(profile["attributes"])

    result = {}

    for attr in attrs:
        matches = [col for col in df.columns if base_column_name(str(col)) == attr]

        if matches:
            result[attr] = matches[0]

    return result


def weighted_attr_score(df: pd.DataFrame, weights: dict[str, float], amap: dict[str, str]) -> pd.Series:
    cols = []
    vals = []

    for attr, weight in weights.items():
        col = amap.get(attr)

        if col in df.columns:
            cols.append(col)
            vals.append(float(weight))

    if not cols:
        return pd.Series(0.0, index=df.index)

    matrix = pd.DataFrame(index=df.index)

    for col in cols:
        matrix[col] = clean_numeric(df[col])

    weights_array = np.array(vals)
    total = matrix.mul(weights_array, axis=1).sum(axis=1, min_count=1)
    possible = matrix.notna().mul(weights_array, axis=1).sum(axis=1)
    score = ((total / possible) / 20) * 100

    return score.where(possible > 0, 0).fillna(0).round(1)


def stat_score(df: pd.DataFrame, stats: list[str]) -> pd.Series:
    cols = []

    for stat in stats:
        for col in df.columns:
            if base_column_name(str(col)) == stat and col not in cols:
                cols.append(col)

    if not cols:
        return pd.Series(50.0, index=df.index)

    parts = []

    for col in cols:
        numeric = clean_numeric(df[col])

        if numeric.notna().sum() <= 1:
            parts.append(pd.Series(50.0, index=df.index))
        else:
            parts.append((numeric.rank(pct=True) * 100).fillna(50))

    return pd.concat(parts, axis=1).mean(axis=1).round(1)


def add_scores(df: pd.DataFrame, min_minutes: int) -> pd.DataFrame:
    df = df.copy()
    amap = attr_map(df)

    mins_col = find_column(df, ["Mins"])

    if mins_col:
        df["Stat Eligible"] = clean_numeric(df[mins_col]).fillna(0) >= min_minutes
    else:
        df["Stat Eligible"] = True

    combined_cols = []

    for category, profile in CATEGORY_PROFILES.items():
        attr_col = f"{category} Attribute Rating"
        stat_col = f"{category} Statistical Rating"
        combined_col = f"{category} Combined Rating"

        df[attr_col] = weighted_attr_score(df, profile["attributes"], amap)
        df[stat_col] = stat_score(df, profile["stats"])
        df.loc[~df["Stat Eligible"], stat_col] = pd.NA
        df[combined_col] = (df[attr_col] * 0.60 + df[stat_col].fillna(50) * 0.40).round(1)
        combined_cols.append(combined_col)

    for playstyle, profile in PLAYSTYLE_PROFILES.items():
        attr_col = f"{playstyle} Attribute Fit"
        stat_col = f"{playstyle} Statistical Fit"
        fit_col = f"{playstyle} Playstyle Fit"

        df[attr_col] = weighted_attr_score(df, profile["attributes"], amap)
        df[stat_col] = stat_score(df, profile["stats"])
        df[fit_col] = (df[attr_col] * 0.65 + df[stat_col].fillna(50) * 0.35).round(1)

    df["Overall Player Quality"] = df[combined_cols].max(axis=1).round(1)
    df["Global Player Quality Rank"] = df["Overall Player Quality"].rank(
        ascending=False,
        method="dense",
    ).astype("Int64")

    df = ensure_transfer_costs(df)

    return df


def build_team_ratings(df: pd.DataFrame) -> pd.DataFrame:
    club_col = find_column(df, ["Club"])
    league_col = find_column(df, ["Division", "League"])

    if not club_col:
        return pd.DataFrame()

    records = []

    for club in sorted(df[club_col].dropna().astype(str).unique()):
        team = df[df[club_col].astype(str) == club]
        record = {"Club": club}

        if league_col:
            mode = team[league_col].dropna().astype(str).mode()
            record["League"] = mode.iloc[0] if not mode.empty else "Unknown"
        else:
            record["League"] = "Unknown"

        overall = 0.0

        for category, profile in CATEGORY_PROFILES.items():
            score_col = f"{category} Combined Rating"
            candidates = team[pos_mask(team, profile["accepted_positions"])].copy()

            if candidates.empty:
                category_score = 0.0
            else:
                category_score = float(
                    candidates.sort_values(score_col, ascending=False)
                    .head(profile["depth"])[score_col]
                    .mean()
                )

            record[f"Combined - {category}"] = round(category_score, 1)
            overall += category_score * profile["weight"]

        record["Overall Team Rating"] = round(overall, 1)
        records.append(record)

    return pd.DataFrame(records).sort_values("Overall Team Rating", ascending=False).reset_index(drop=True)


def club_realism_context(team_ratings: pd.DataFrame, your_club: str, target_goal: str, budget: float) -> dict:
    ranked = team_ratings.sort_values("Overall Team Rating", ascending=False).reset_index(drop=True)
    ranked["Club Rank"] = ranked.index + 1

    row = ranked[ranked["Club"].astype(str) == str(your_club)]

    if row.empty:
        rating = 60.0
        rank = len(ranked)
        league = "Unknown"
    else:
        rating = float(row.iloc[0]["Overall Team Rating"])
        rank = int(row.iloc[0]["Club Rank"])
        league = str(row.iloc[0]["League"])

    if rating >= 78 or rank <= 8:
        band = "World Elite"
        excluded_top_ranks = 0
        max_fee = 300_000_000
        max_quality = 99
        min_quality = 70
    elif rating >= 72 or rank <= 20:
        band = "UCL Contender"
        excluded_top_ranks = 3
        max_fee = 200_000_000
        max_quality = 94
        min_quality = 66
    elif rating >= 65 or rank <= 50:
        band = "Continental / Top 50 Club"
        excluded_top_ranks = 8
        max_fee = 150_000_000
        max_quality = 90
        min_quality = 60
    elif rating >= 58 or rank <= 100:
        band = "Upper Mid-table / Europa Builder"
        excluded_top_ranks = 20
        max_fee = 85_000_000
        max_quality = 84
        min_quality = 54
    else:
        band = "Lower Table / Development Club"
        excluded_top_ranks = 50
        max_fee = 45_000_000
        max_quality = 78
        min_quality = 48

    if target_goal == "Win UEFA Champions League":
        max_fee *= 1.20
        max_quality += 2
    elif target_goal in ["Win UEFA Europa League", "Win Copa Libertadores"]:
        max_fee *= 1.10
        max_quality += 1

    if budget > 0:
        max_fee = min(max_fee, budget)

    if target_goal == "Win UEFA Champions League" and rating < 70:
        realistic_goal = "Build toward UCL qualification/knockout level first. Avoid top-5-world targets."
    elif target_goal == "Win UEFA Champions League" and rating < 74:
        realistic_goal = "Buy UCL-level starters, but avoid unrealistic elite-world targets."
    elif target_goal == "Win Domestic League":
        realistic_goal = "Close domestic title gaps first."
    else:
        realistic_goal = "Improve the squad within the club's current pull and budget."

    return {
        "Club Rank": rank,
        "Club Rating": round(rating, 1),
        "League": league,
        "Club Band": band,
        "Excluded Top Global Ranks": excluded_top_ranks,
        "Max Realistic Fee": float(max_fee),
        "Max Realistic Quality": float(min(max_quality, 99)),
        "Realistic Min Quality": float(min_quality),
        "Realistic Goal": realistic_goal,
    }


def benchmark_for_goal(team_ratings: pd.DataFrame, your_club: str, target: str):
    your = team_ratings[team_ratings["Club"].astype(str) == str(your_club)]

    if target == "Win Domestic League" and not your.empty:
        league = str(your.iloc[0]["League"])
        pool = team_ratings[team_ratings["League"].astype(str) == league].head(3)
        explanation = f"Domestic title benchmark uses the top teams in your league: {league}."
        cushion = 2.0
    elif target == "Win UEFA Champions League":
        pool = team_ratings.head(12)
        explanation = "Champions League benchmark uses the top elite clubs in the database."
        cushion = 4.0
    elif target == "Win UEFA Europa League":
        pool = team_ratings.iloc[12:32] if len(team_ratings) > 32 else team_ratings.head(20)
        explanation = "Europa League benchmark uses strong continental clubs below the absolute elite."
        cushion = 3.0
    elif target == "Win Copa Libertadores":
        text = team_ratings["League"].astype(str).str.lower() + " " + team_ratings["Club"].astype(str).str.lower()
        mask = text.str.contains("brazil|brasil|argentina|uruguay|chile|colombia|paraguay|peru|ecuador|libertadores", regex=True, na=False)
        pool = team_ratings[mask].head(10)

        if pool.empty:
            pool = team_ratings.head(20)

        explanation = "Copa Libertadores benchmark uses the strongest detected South American clubs."
        cushion = 3.5
    else:
        pool = team_ratings.head(10)
        explanation = "Benchmark uses the strongest clubs in the database."
        cushion = 2.0

    benchmark = {}

    for category in CATEGORY_PROFILES:
        col = f"Combined - {category}"
        benchmark[category] = round(float(pool[col].mean()) + cushion, 1) if col in pool else 70.0

    return benchmark, pool, explanation


def squad_gaps(team_ratings: pd.DataFrame, your_club: str, benchmark: dict[str, float]) -> pd.DataFrame:
    your = team_ratings[team_ratings["Club"].astype(str) == str(your_club)]

    if your.empty:
        return pd.DataFrame()

    row = your.iloc[0]
    records = []

    for category in CATEGORY_PROFILES:
        current = float(row.get(f"Combined - {category}", 0))
        target = float(benchmark.get(category, 70))
        gap = round(target - current, 1)

        records.append(
            {
                "Squad Area": category,
                "Current Rating": round(current, 1),
                "Target Rating": round(target, 1),
                "Gap To Target": gap,
                "Priority": "Critical" if gap >= 8 else "Important" if gap >= 4 else "Depth / Optional",
            }
        )

    return pd.DataFrame(records).sort_values("Gap To Target", ascending=False).reset_index(drop=True)


def add_realism_scores(df: pd.DataFrame, context: dict, budget: float, players_to_buy: int, mode: str) -> pd.DataFrame:
    out = df.copy()
    out = ensure_transfer_costs(out)

    out["Overall Player Quality"] = pd.to_numeric(out.get("Overall Player Quality", 0), errors="coerce").fillna(0)
    out["Global Player Quality Rank"] = pd.to_numeric(out.get("Global Player Quality Rank", 9999), errors="coerce").fillna(9999)
    out["Transfer Cost"] = pd.to_numeric(out["Transfer Cost"], errors="coerce")

    excluded = int(context["Excluded Top Global Ranks"])
    max_fee = float(context["Max Realistic Fee"])
    max_quality = float(context["Max Realistic Quality"])
    min_quality = float(context["Realistic Min Quality"])

    target_fee = budget if players_to_buy <= 1 else budget / max(players_to_buy, 1)

    if target_fee <= 0:
        target_fee = max_fee

    out["Hard Elite Block"] = out["Global Player Quality Rank"] <= excluded
    out["Hard Fee Block"] = out["Transfer Cost"] > max_fee * 1.50
    out["Hard Quality Block"] = out["Overall Player Quality"] > max_quality + 4

    out["Rank Realism"] = np.where(out["Hard Elite Block"], 0, 100)
    out["Fee Realism"] = np.where(
        out["Transfer Cost"].isna(),
        60,
        np.where(out["Transfer Cost"] <= max_fee, 100, 100 - ((out["Transfer Cost"] - max_fee) / max(max_fee, 1)) * 90),
    )
    out["Fee Realism"] = out["Fee Realism"].clip(0, 100)

    out["Quality Realism"] = (
        100
        - (out["Overall Player Quality"] - max_quality).clip(lower=0) * 10
        - (min_quality - out["Overall Player Quality"]).clip(lower=0) * 2
    ).clip(0, 100)

    out["Price Range Fit"] = np.where(
        out["Transfer Cost"].isna(),
        55,
        (100 - ((out["Transfer Cost"] - target_fee).abs() / max(target_fee, 1)) * 35).clip(0, 100),
    )

    out["Realism Fit"] = (
        out["Rank Realism"] * 0.28
        + out["Fee Realism"] * 0.27
        + out["Quality Realism"] * 0.27
        + out["Price Range Fit"] * 0.18
    ).round(1)

    minimum = {"Strict": 62, "Balanced": 44, "Aggressive": 28}.get(mode, 44)

    if mode == "Aggressive":
        out["Realistic Target"] = (
            (out["Realism Fit"] >= minimum)
            & ~out["HardFeeBlock"] if "HardFeeBlock" in out.columns else (out["Realism Fit"] >= minimum)
        )
    else:
        out["Realistic Target"] = (
            (out["Realism Fit"] >= minimum)
            & ~out["Hard Elite Block"]
            & ~out["Hard Fee Block"]
            & ~out["Hard Quality Block"]
        )

    return out


def build_recommendations_by_gap(
    df: pd.DataFrame,
    team_ratings: pd.DataFrame,
    your_club: str,
    target_goal: str,
    playstyle: str,
    benchmark: dict[str, float],
    context: dict,
    transfer_budget: float,
    players_to_buy: int,
    max_age: int,
    max_value: float | None,
    top_per_gap: int,
    search_pool: str,
    realism_mode: str,
) -> pd.DataFrame:
    club_col = find_column(df, ["Club"])
    name_col = find_column(df, ["Name", "Player"])
    age_col = find_column(df, ["Age"])
    league_col = find_column(df, ["Division", "League"])
    pos_col = find_column(df, ["Position"])

    if not club_col or not name_col:
        return pd.DataFrame()

    gaps = squad_gaps(team_ratings, your_club, benchmark)
    your = team_ratings[team_ratings["Club"].astype(str) == str(your_club)]

    if gaps.empty or your.empty:
        return pd.DataFrame()

    your_row = your.iloc[0]
    your_league = str(your_row.get("League", ""))

    candidates = df[df[club_col].astype(str) != str(your_club)].copy()

    if search_pool == "Same League Only" and league_col:
        candidates = candidates[candidates[league_col].astype(str) == your_league]
    elif search_pool == "Outside Current League" and league_col:
        candidates = candidates[candidates[league_col].astype(str) != your_league]

    if age_col:
        candidates = candidates[clean_numeric(candidates[age_col]).fillna(99) <= max_age]

    candidates = ensure_transfer_costs(candidates)

    if max_value is not None:
        candidates = candidates[candidates["Transfer Cost"].isna() | (candidates["Transfer Cost"] <= max_value)]

    candidates = add_realism_scores(candidates, context, transfer_budget, players_to_buy, realism_mode)

    realistic = candidates[candidates["Realistic Target"]].copy()

    if realistic.empty and realism_mode != "Strict":
        realistic = candidates[candidates["Realism Fit"] >= 25].copy()

    candidates = realistic

    if candidates.empty:
        return pd.DataFrame()

    play_col = f"{playstyle} Playstyle Fit"
    rows = []

    for order, gap_row in gaps.iterrows():
        category = gap_row["Squad Area"]
        profile = CATEGORY_PROFILES[category]
        current = float(your_row.get(f"Combined - {category}", 0))
        target_rating = float(benchmark.get(category, 70))
        gap_value = max(target_rating - current, 0.1)

        pool = candidates[pos_mask(candidates, profile["accepted_positions"])].copy()

        if pool.empty:
            continue

        cat_col = f"{category} Combined Rating"
        attr_col = f"{category} Attribute Rating"
        stat_col = f"{category} Statistical Rating"

        pool["Candidate Category Rating"] = pd.to_numeric(pool[cat_col], errors="coerce").fillna(0)
        pool["Candidate Attribute Fit"] = pd.to_numeric(pool[attr_col], errors="coerce").fillna(0)
        pool["Candidate Statistical Fit"] = pd.to_numeric(pool[stat_col], errors="coerce").fillna(50)
        pool["Playstyle Fit"] = pd.to_numeric(pool.get(play_col, 50), errors="coerce").fillna(50)
        pool["Upgrade Over Current Area"] = (pool["Candidate Category Rating"] - current).round(1)
        pool["Gap Covered %"] = (pool["Upgrade Over Current Area"].clip(lower=0) / gap_value * 100).clip(upper=100).round(1)

        upgrade_score = pool["Upgrade Over Current Area"].clip(lower=0, upper=30) / 30 * 100

        pool["Recommendation Score"] = (
            pool["Candidate Category Rating"] * 0.32
            + pool["Playstyle Fit"] * 0.22
            + pool["Realism Fit"] * 0.24
            + upgrade_score * 0.12
            + pool["Gap Covered %"] * 0.10
        ).round(1)

        pool["Quality Score"] = (
            pool["Recommendation Score"] * 0.45
            + pool["Candidate Category Rating"] * 0.25
            + pool["Realism Fit"] * 0.20
            + pool["Playstyle Fit"] * 0.10
        ).round(1)

        pool = pool.sort_values(["Recommendation Score", "Quality Score"], ascending=False)
        pool = pool.drop_duplicates(subset=[name_col, club_col]).head(top_per_gap)

        for rank, (_, r) in enumerate(pool.iterrows(), start=1):
            rows.append(
                {
                    "Gap Rank": rank,
                    "Player": r.get(name_col, "Unknown"),
                    "Age": r.get(age_col, ""),
                    "Club": r.get(club_col, ""),
                    "League": r.get(league_col, ""),
                    "Position": r.get(pos_col, ""),
                    "Recommended For": category,
                    "Gap Priority Order": order + 1,
                    "Squad Gap Value": round(gap_value, 1),
                    "Recommendation Score": r["Recommendation Score"],
                    "Quality Score": r["Quality Score"],
                    "Realism Fit": r["Realism Fit"],
                    "Candidate Category Rating": r["Candidate Category Rating"],
                    "Candidate Attribute Fit": r["Candidate Attribute Fit"],
                    "Candidate Statistical Fit": r["Candidate Statistical Fit"],
                    "Playstyle Fit": r["Playstyle Fit"],
                    "Upgrade Over Current Area": r["Upgrade Over Current Area"],
                    "Gap Covered %": r["Gap Covered %"],
                    "Global Player Quality Rank": int(r.get("Global Player Quality Rank", 9999)),
                    "Transfer Cost": r.get("Transfer Cost", np.nan),
                    "Transfer Cost Display": r.get("Transfer Cost Display", format_money(r.get("Transfer Cost", np.nan))),
                    "Why Recommended": (
                        f"Realistic {category} upgrade. Current area: {current:.1f}. "
                        f"Target: {target_rating:.1f}. Candidate: {r['Candidate Category Rating']:.1f}. "
                        f"Realism fit: {r['Realism Fit']:.1f}."
                    ),
                }
            )

    result = pd.DataFrame(rows)

    if result.empty:
        return result

    return result.sort_values(["Gap Priority Order", "Gap Rank"]).reset_index(drop=True)


def build_dynamic_budget_plan(recs: pd.DataFrame, budget: float, players_to_buy: int) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    if recs.empty:
        return pd.DataFrame(), pd.DataFrame(), {"spend": 0, "left": budget, "message": "No realistic recommendations available."}

    pool = ensure_transfer_costs(recs)
    pool["Transfer Cost"] = pd.to_numeric(pool["Transfer Cost"], errors="coerce")
    pool = pool[pool["Transfer Cost"].notna() & (pool["Transfer Cost"] >= 0) & (pool["Transfer Cost"] <= budget)].copy()

    if budget < 1_000_000_000:
        pool = pool[pool["Transfer Cost"] < 1_000_000_000].copy()

    if pool.empty:
        return pd.DataFrame(), pd.DataFrame(), {"spend": 0, "left": budget, "message": "No affordable realistic players found inside this budget."}

    pool = pool.drop_duplicates(subset=["Player", "Club"]).copy()
    target_price = budget / max(players_to_buy, 1)

    pool["Value Efficiency"] = (pool["Quality Score"] / ((pool["Transfer Cost"] / 1_000_000) + 1)).round(3)
    pool["Budget Share %"] = (pool["Transfer Cost"] / budget * 100).round(1)
    pool["Price Range Fit"] = (100 - ((pool["Transfer Cost"] - target_price).abs() / max(target_price, 1) * 35)).clip(lower=0, upper=100).round(1)

    if players_to_buy <= 1:
        pool["Budget Plan Score"] = (
            pool["Quality Score"] * 0.55
            + pool["Recommendation Score"] * 0.22
            + pool["Realism Fit"] * 0.14
            + pool["Squad Gap Value"].clip(lower=0) * 1.20
        ).round(2)

        plan = pool.sort_values(["Budget Plan Score", "Quality Score"], ascending=False).head(1).copy()
        plan.insert(0, "Buy Order", 1)

    elif players_to_buy <= 4:
        pool["Budget Plan Score"] = (
            pool["Quality Score"] * 0.46
            + pool["Recommendation Score"] * 0.18
            + pool["Realism Fit"] * 0.16
            + pool["ValueEfficiency"] * 3.00 if "ValueEfficiency" in pool.columns else pool["Value Efficiency"] * 3.00
            + pool["Price Range Fit"] * 0.06
            + pool["Squad Gap Value"].clip(lower=0) * 1.60
            - pool["Gap Priority Order"] * 0.20
        ).round(2)

        pool = pool.sort_values(["Budget Plan Score", "Quality Score"], ascending=False).head(35).reset_index(drop=True)

        best_combo = None
        best_score = -999999

        for indexes in combinations(range(len(pool)), players_to_buy):
            combo = pool.iloc[list(indexes)].copy()
            total_cost = float(combo["Transfer Cost"].sum())

            if total_cost > budget:
                continue

            unique_gaps = combo["Recommended For"].astype(str).nunique()
            avg_quality = float(combo["Quality Score"].mean())
            avg_realism = float(combo["Realism Fit"].mean())
            avg_value = float(combo["Value Efficiency"].mean())
            spend_ratio = total_cost / budget

            score = (
                avg_quality * 1.00
                + avg_realism * 0.35
                + avg_value * 3.00
                + unique_gaps * 4.50
                + spend_ratio * 3.00
            )

            if score > best_score:
                best_score = score
                best_combo = combo.copy()

        if best_combo is None:
            selected = []
            remaining = budget
            used = set()

            for _, row in pool.iterrows():
                key = (str(row["Player"]), str(row["Club"]))

                if key in used:
                    continue

                if float(row["Transfer Cost"]) <= remaining:
                    selected.append(row)
                    used.add(key)
                    remaining -= float(row["Transfer Cost"])

                if len(selected) >= players_to_buy:
                    break

            plan = pd.DataFrame(selected)
        else:
            plan = best_combo

        plan = plan.sort_values(["Gap Priority Order", "Budget Plan Score"], ascending=[True, False]).reset_index(drop=True)
        plan.insert(0, "Buy Order", plan.index + 1)

    else:
        pool["Budget Plan Score"] = (
            pool["Quality Score"] * 0.45
            + pool["Recommendation Score"] * 0.18
            + pool["Realism Fit"] * 0.16
            + pool["Value Efficiency"] * 3.50
            + pool["Squad Gap Value"].clip(lower=0) * 1.50
        ).round(2)

        selected = []
        remaining = budget
        used = set()

        for _, row in pool.sort_values("Budget Plan Score", ascending=False).iterrows():
            key = (str(row["Player"]), str(row["Club"]))

            if key in used:
                continue

            if float(row["Transfer Cost"]) <= remaining:
                selected.append(row)
                used.add(key)
                remaining -= float(row["Transfer Cost"])

            if len(selected) >= players_to_buy:
                break

        plan = pd.DataFrame(selected).reset_index(drop=True)

        if not plan.empty:
            plan.insert(0, "Buy Order", plan.index + 1)

    if plan.empty:
        return pd.DataFrame(), pool, {"spend": 0, "left": budget, "message": "Could not build a realistic plan under this budget."}

    plan["Cumulative Spend"] = plan["Transfer Cost"].cumsum()
    plan["Cumulative Spend Display"] = plan["Cumulative Spend"].apply(format_money)
    plan["Budget Remaining After Deal"] = budget - plan["Cumulative Spend"]
    plan["Budget Remaining Display"] = plan["Budget Remaining After Deal"].apply(format_money)

    spend = float(plan["Transfer Cost"].sum())

    summary = {
        "spend": spend,
        "left": budget - spend,
        "message": "Dynamic realistic budget plan created.",
    }

    alternatives = pool.sort_values(["Quality Score", "Recommendation Score", "Realism Fit"], ascending=False).head(75)

    return plan, alternatives, summary


def best_category_for_player(row: pd.Series) -> str:
    classes = str(row.get("Position Classes", ""))

    possible = []

    for category, profile in CATEGORY_PROFILES.items():
        if any(pos in classes for pos in profile["accepted_positions"]):
            possible.append(category)

    if not possible:
        possible = list(CATEGORY_PROFILES.keys())

    best_category = possible[0]
    best_score = -1.0

    for category in possible:
        score = pd.to_numeric(pd.Series([row.get(f"{category} Combined Rating", 0)]), errors="coerce").iloc[0]

        if pd.isna(score):
            score = 0

        if float(score) > best_score:
            best_score = float(score)
            best_category = category

    return best_category


def build_sell_upgrade_table(df: pd.DataFrame, your_club: str, playstyle: str, recs: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    club_col = find_column(df, ["Club"])
    name_col = find_column(df, ["Name", "Player"])
    age_col = find_column(df, ["Age"])
    pos_col = find_column(df, ["Position"])

    if not club_col or not name_col:
        return pd.DataFrame(), pd.DataFrame()

    team = df[df[club_col].astype(str) == str(your_club)].copy()

    if team.empty:
        return pd.DataFrame(), pd.DataFrame()

    play_col = f"{playstyle} Playstyle Fit"
    sell_rows = []
    upgrade_rows = []

    for _, row in team.iterrows():
        category = best_category_for_player(row)

        attr = pd.to_numeric(pd.Series([row.get(f"{category} Attribute Rating", np.nan)]), errors="coerce").iloc[0]
        stat = pd.to_numeric(pd.Series([row.get(f"{category} Statistical Rating", np.nan)]), errors="coerce").iloc[0]
        combined = pd.to_numeric(pd.Series([row.get(f"{category} Combined Rating", np.nan)]), errors="coerce").iloc[0]
        play_fit = pd.to_numeric(pd.Series([row.get(play_col, np.nan)]), errors="coerce").iloc[0]

        attr = 0 if pd.isna(attr) else float(attr)
        stat = 50 if pd.isna(stat) else float(stat)
        combined = 0 if pd.isna(combined) else float(combined)
        play_fit = 50 if pd.isna(play_fit) else float(play_fit)

        underperformance_gap = round(attr - stat, 1)

        age = np.nan

        if age_col:
            age = pd.to_numeric(pd.Series([row.get(age_col, np.nan)]), errors="coerce").iloc[0]

        age_penalty = 8 if not pd.isna(age) and age >= 31 else 4 if not pd.isna(age) and age >= 29 else 0

        sell_score = (
            max(underperformance_gap, 0) * 2.00
            + max(60 - stat, 0) * 0.85
            + max(58 - play_fit, 0) * 0.55
            + age_penalty
        )

        if sell_score < 20 and underperformance_gap < 9:
            continue

        player = row.get(name_col, "Unknown")
        value = row.get("Transfer Cost", np.nan)

        sell_rows.append(
            {
                "Player": player,
                "Age": row.get(age_col, ""),
                "Position": row.get(pos_col, ""),
                "Best Role Area": category,
                "Attribute Strength": round(attr, 1),
                "Statistical Performance": round(stat, 1),
                "Underperformance Gap": underperformance_gap,
                "Combined Rating": round(combined, 1),
                "Playstyle Fit": round(play_fit, 1),
                "Estimated Value": format_money(value),
                "Sell / Upgrade Score": round(sell_score, 1),
                "Reason": f"Attributes suggest {attr:.1f}, but statistical output is {stat:.1f}.",
            }
        )

        options = recs[recs["Recommended For"].astype(str) == str(category)].copy() if not recs.empty else pd.DataFrame()

        if not options.empty:
            options["Replacement Upgrade"] = pd.to_numeric(options["Candidate Category Rating"], errors="coerce") - combined
            options = options.sort_values(["Replacement Upgrade", "Recommendation Score", "Realism Fit"], ascending=False).head(3)

            for rank, (_, option) in enumerate(options.iterrows(), start=1):
                upgrade_rows.append(
                    {
                        "Replace": player,
                        "Replacement Rank": rank,
                        "Replacement": option.get("Player", ""),
                        "Replacement Club": option.get("Club", ""),
                        "Replacement Age": option.get("Age", ""),
                        "Squad Area": category,
                        "Current Player Rating": round(combined, 1),
                        "Replacement Rating": option.get("Candidate Category Rating", np.nan),
                        "Upgrade Gain": round(float(option.get("Replacement Upgrade", 0)), 1),
                        "Replacement Cost": option.get("Transfer Cost Display", ""),
                        "Realism Fit": option.get("Realism Fit", ""),
                        "Recommendation Score": option.get("Recommendation Score", ""),
                    }
                )

    sell_df = pd.DataFrame(sell_rows)

    if not sell_df.empty:
        sell_df = sell_df.sort_values("Sell / Upgrade Score", ascending=False).reset_index(drop=True)
        sell_df.insert(0, "Sell Rank", sell_df.index + 1)

    return sell_df, pd.DataFrame(upgrade_rows)



def build_manual_spend_budget_plan(
    recs: pd.DataFrame,
    total_budget: float,
    planned_spend_target: float,
    players_to_buy: int,
) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """
    Builds a plan that tries to spend close to the user's manually entered planned spend target.

    Example:
    - Total budget: 150M
    - Planned spend target: 50M
    - Players to buy: 3

    The engine tries to find the best 3-player combination near 50M,
    not merely the cheapest 3 players under 50M.
    """

    if recs.empty:
        return pd.DataFrame(), pd.DataFrame(), {
            "spend": 0,
            "left": total_budget,
            "target_left": planned_spend_target,
            "message": "No realistic recommendations available.",
        }

    total_budget = float(total_budget)
    planned_spend_target = float(planned_spend_target)
    players_to_buy = int(players_to_buy)

    if planned_spend_target <= 0:
        planned_spend_target = total_budget

    planned_spend_target = min(planned_spend_target, total_budget)

    pool = ensure_transfer_costs(recs)
    pool["Transfer Cost"] = pd.to_numeric(pool["Transfer Cost"], errors="coerce")

    pool = pool[
        pool["Transfer Cost"].notna()
        & (pool["Transfer Cost"] >= 0)
        & (pool["Transfer Cost"] <= planned_spend_target)
    ].copy()

    if planned_spend_target < 1_000_000_000:
        pool = pool[pool["Transfer Cost"] < 1_000_000_000].copy()

    if pool.empty:
        return pd.DataFrame(), pd.DataFrame(), {
            "spend": 0,
            "left": total_budget,
            "target_left": planned_spend_target,
            "message": "No affordable realistic players found inside your planned spend target.",
        }

    pool = pool.drop_duplicates(subset=["Player", "Club"]).copy()

    for col in [
        "Quality Score",
        "Recommendation Score",
        "Realism Fit",
        "Squad Gap Value",
        "Gap Priority Order",
        "Playstyle Fit",
        "Upgrade Over Current Area",
    ]:
        if col not in pool.columns:
            pool[col] = 0

        pool[col] = pd.to_numeric(pool[col], errors="coerce").fillna(0)

    target_price_per_player = planned_spend_target / max(players_to_buy, 1)

    pool["Value Efficiency"] = (
        pool["Quality Score"] / ((pool["Transfer Cost"] / 1_000_000) + 1)
    ).round(3)

    pool["Budget Share %"] = (
        pool["Transfer Cost"] / max(total_budget, 1) * 100
    ).round(1)

    pool["Planned Spend Share %"] = (
        pool["Transfer Cost"] / max(planned_spend_target, 1) * 100
    ).round(1)

    pool["Target Price Fit"] = (
        100
        - (
            (pool["Transfer Cost"] - target_price_per_player).abs()
            / max(target_price_per_player, 1)
            * 45
        )
    ).clip(lower=0, upper=100).round(1)

    # Single player mode: best player under planned target, while preferring players
    # who actually use a meaningful part of the target.
    if players_to_buy <= 1:
        pool["Spend Target Fit"] = (
            100
            - (
                (pool["Transfer Cost"] - planned_spend_target).abs()
                / max(planned_spend_target, 1)
                * 35
            )
        ).clip(lower=0, upper=100).round(1)

        pool["Manual Spend Plan Score"] = (
            pool["Quality Score"] * 0.48
            + pool["Recommendation Score"] * 0.20
            + pool["Realism Fit"] * 0.14
            + pool["Spend Target Fit"] * 0.14
            + pool["Squad Gap Value"].clip(lower=0) * 1.35
        ).round(2)

        plan = (
            pool.sort_values(
                ["Manual Spend Plan Score", "Quality Score", "Recommendation Score"],
                ascending=False,
            )
            .head(1)
            .copy()
        )

        plan.insert(0, "Buy Order", 1)

    # 2-4 players: search combinations and reward being close to manual planned spend.
    elif players_to_buy <= 4:
        pool["Manual Spend Plan Score"] = (
            pool["Quality Score"] * 0.44
            + pool["Recommendation Score"] * 0.18
            + pool["Realism Fit"] * 0.15
            + pool["Target Price Fit"] * 0.12
            + pool["Value Efficiency"] * 2.00
            + pool["Squad Gap Value"].clip(lower=0) * 1.50
            - pool["Gap Priority Order"] * 0.15
        ).round(2)

        pool = (
            pool.sort_values(
                ["Manual Spend Plan Score", "Quality Score", "Recommendation Score"],
                ascending=False,
            )
            .head(60)
            .reset_index(drop=True)
        )

        best_combo = None
        best_score = -999999999

        for indexes in combinations(range(len(pool)), players_to_buy):
            combo = pool.iloc[list(indexes)].copy()
            total_cost = float(combo["Transfer Cost"].sum())

            if total_cost > planned_spend_target:
                continue

            spend_ratio = total_cost / max(planned_spend_target, 1)
            spend_closeness = 100 - abs(1 - spend_ratio) * 100
            spend_closeness = max(spend_closeness, 0)

            unique_gaps = combo["Recommended For"].astype(str).nunique()
            avg_quality = float(combo["Quality Score"].mean())
            avg_realism = float(combo["Realism Fit"].mean())
            avg_recommendation = float(combo["Recommendation Score"].mean())
            avg_playstyle = float(combo["Playstyle Fit"].mean())

            combo_score = (
                avg_quality * 1.00
                + avg_recommendation * 0.35
                + avg_realism * 0.30
                + avg_playstyle * 0.20
                + spend_closeness * 0.65
                + unique_gaps * 5.00
            )

            if combo_score > best_score:
                best_score = combo_score
                best_combo = combo.copy()

        if best_combo is None:
            selected = []
            remaining = planned_spend_target
            used_players = set()

            for _, row in pool.iterrows():
                key = (str(row["Player"]), str(row["Club"]))

                if key in used_players:
                    continue

                cost = float(row["Transfer Cost"])

                if cost <= remaining:
                    selected.append(row)
                    used_players.add(key)
                    remaining -= cost

                if len(selected) >= players_to_buy:
                    break

            plan = pd.DataFrame(selected)
        else:
            plan = best_combo

        if not plan.empty:
            plan = plan.sort_values(
                ["Gap Priority Order", "Manual Spend Plan Score"],
                ascending=[True, False],
            ).reset_index(drop=True)

            plan.insert(0, "Buy Order", plan.index + 1)

    # 5+ players: greedy, but still tries to spend near the target.
    else:
        pool["Manual Spend Plan Score"] = (
            pool["Quality Score"] * 0.42
            + pool["Recommendation Score"] * 0.18
            + pool["Realism Fit"] * 0.15
            + pool["Target Price Fit"] * 0.12
            + pool["Value Efficiency"] * 2.75
            + pool["Squad Gap Value"].clip(lower=0) * 1.35
        ).round(2)

        selected = []
        remaining = planned_spend_target
        used_players = set()

        for _, row in pool.sort_values("Manual Spend Plan Score", ascending=False).iterrows():
            key = (str(row["Player"]), str(row["Club"]))

            if key in used_players:
                continue

            cost = float(row["Transfer Cost"])

            if cost <= remaining:
                selected.append(row)
                used_players.add(key)
                remaining -= cost

            if len(selected) >= players_to_buy:
                break

        plan = pd.DataFrame(selected).reset_index(drop=True)

        if not plan.empty:
            plan.insert(0, "Buy Order", plan.index + 1)

    if plan.empty:
        return pd.DataFrame(), pool, {
            "spend": 0,
            "left": total_budget,
            "target_left": planned_spend_target,
            "message": "Could not build a plan under your manual planned spend target.",
        }

    plan["Cumulative Spend"] = plan["Transfer Cost"].cumsum()
    plan["Cumulative Spend Display"] = plan["Cumulative Spend"].apply(format_money)
    plan["Total Budget Remaining After Deal"] = total_budget - plan["Cumulative Spend"]
    plan["Total Budget Remaining Display"] = plan["Total Budget Remaining After Deal"].apply(format_money)
    plan["Planned Spend Remaining After Deal"] = planned_spend_target - plan["Cumulative Spend"]
    plan["Planned Spend Remaining Display"] = plan["Planned Spend Remaining After Deal"].apply(format_money)

    total_spend = float(plan["Transfer Cost"].sum())

    summary = {
        "spend": total_spend,
        "left": total_budget - total_spend,
        "target_left": planned_spend_target - total_spend,
        "message": "Manual planned spend plan created.",
    }

    alternatives = (
        pool.sort_values(
            ["Quality Score", "Recommendation Score", "Realism Fit"],
            ascending=False,
        )
        .head(75)
        .copy()
    )

    return plan, alternatives, summary

