from pathlib import Path
import re

path = Path("app/pages/11_Recommended_Signings.py")
text = path.read_text(encoding="utf-8")

helper = r'''

# ============================================================
# ROBUST TRANSFER COST FALLBACK
# ============================================================

def parse_money_text_to_number(value) -> float:
    try:
        if value is None or pd.isna(value):
            return np.nan
    except Exception:
        pass

    text = str(value).strip()

    if not text:
        return np.nan

    fixed = (
        text.replace("Ã‚Â£", "£")
        .replace("Â£", "£")
        .replace("Â", "")
        .replace("–", "-")
        .replace("—", "-")
        .replace(" to ", "-")
        .replace(" TO ", "-")
    )

    lowered = fixed.lower().strip()

    if "not for sale" in lowered or lowered == "nfs":
        return 1_000_000_000.0

    parts = [part.strip() for part in fixed.split("-") if part.strip()]
    parsed = []

    for part in parts:
        clean = (
            part.upper()
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
        clean = (
            fixed.upper()
            .replace("£", "")
            .replace("$", "")
            .replace("€", "")
            .replace(",", "")
            .replace(" ", "")
        )

        match = re.search(r"([0-9]+(?:\.[0-9]+)?)([KMB]?)", clean)

        if match:
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


def fallback_transfer_cost_from_quality(row) -> float:
    quality_candidates = [
        row.get("Overall Player Quality", np.nan),
        row.get("Candidate Category Rating", np.nan),
        row.get("Quality Score", np.nan),
        row.get("Recommendation Score", np.nan),
    ]

    quality = np.nan

    for value in quality_candidates:
        try:
            value = float(value)
        except Exception:
            continue

        if not pd.isna(value) and value > 0:
            quality = value
            break

    if pd.isna(quality):
        return np.nan

    if quality >= 88:
        return 120_000_000.0
    if quality >= 84:
        return 75_000_000.0
    if quality >= 80:
        return 45_000_000.0
    if quality >= 76:
        return 25_000_000.0
    if quality >= 72:
        return 14_000_000.0
    if quality >= 68:
        return 8_000_000.0
    if quality >= 64:
        return 4_000_000.0

    return 1_500_000.0


def robust_transfer_cost_from_row(row) -> float:
    columns_to_try = [
        "Transfer Cost",
        "Transfer Value Clean",
        "Estimated Value Clean",
        "Transfer Value",
        "Transfer Value Raw",
        "Transfer Value Display",
        "Estimated Value",
        "Estimated Value Raw",
        "Estimated Value Display",
        "Value",
    ]

    for col in columns_to_try:
        if col not in row.index:
            continue

        value = row.get(col)

        try:
            numeric = pd.to_numeric(value, errors="coerce")
            if not pd.isna(numeric) and float(numeric) >= 0:
                return float(numeric)
        except Exception:
            pass

        parsed = parse_money_text_to_number(value)

        if not pd.isna(parsed) and parsed >= 0:
            return float(parsed)

    return fallback_transfer_cost_from_quality(row)


def robust_transfer_cost_source(row) -> str:
    columns_to_try = [
        "Transfer Cost",
        "Transfer Value Clean",
        "Estimated Value Clean",
        "Transfer Value",
        "Transfer Value Raw",
        "Estimated Value",
        "Estimated Value Raw",
        "Value",
    ]

    for col in columns_to_try:
        if col not in row.index:
            continue

        value = row.get(col)

        parsed = parse_money_text_to_number(value)

        try:
            numeric = pd.to_numeric(value, errors="coerce")
        except Exception:
            numeric = np.nan

        if (not pd.isna(parsed) and parsed >= 0) or (not pd.isna(numeric) and float(numeric) >= 0):
            return col

    return "Quality-Based Estimate"


def ensure_transfer_costs(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame() if df is None else df

    out = df.copy()

    out["Transfer Cost"] = out.apply(robust_transfer_cost_from_row, axis=1)
    out["Transfer Cost Display"] = out["Transfer Cost"].apply(format_money)
    out["Price Source"] = out.apply(robust_transfer_cost_source, axis=1)

    return out

'''

if "def robust_transfer_cost_from_row" not in text:
    marker = "def make_safe_df(df: pd.DataFrame) -> pd.DataFrame:"
    if marker not in text:
        marker = "def format_money(value) -> str:"

    text = text.replace(marker, helper + "\n\n" + marker, 1)

text = text.replace(
    "df = add_scores(df, min_minutes)\n    teams = build_team_ratings(df)",
    "df = add_scores(df, min_minutes)\n    df = ensure_transfer_costs(df)\n    teams = build_team_ratings(df)",
)

text = text.replace(
    "cost = r.get(\"Transfer Cost\", np.nan)",
    "cost = robust_transfer_cost_from_row(r)",
)

text = text.replace(
    '"Transfer Cost Display": format_money(cost),',
    '"Transfer Cost Display": format_money(cost),\n                "Price Source": robust_transfer_cost_source(r),',
)

text = text.replace(
    "pool = recs.copy()\n    pool[\"Transfer Cost\"] = pd.to_numeric(pool[\"Transfer Cost\"], errors=\"coerce\")",
    "pool = recs.copy()\n    pool = ensure_transfer_costs(pool)",
)

text = text.replace(
    "recs = recommendations.copy()\n\n    if \"Estimated Value Clean\" not in recs.columns:",
    "recs = recommendations.copy()\n    recs = ensure_transfer_costs(recs)\n\n    if \"Transfer Cost\" not in recs.columns:",
)

text = text.replace(
    "recs = recommendations.copy()\n\n    if \"Transfer Cost\" not in recs.columns:",
    "recs = recommendations.copy()\n    recs = ensure_transfer_costs(recs)\n\n    if \"Transfer Cost\" not in recs.columns:",
)

text = text.replace(
    "pool = recs.copy()\n    pool[\"Transfer Cost\"] = pd.to_numeric(pool[\"Transfer Cost\"], errors=\"coerce\")",
    "pool = recs.copy()\n    pool = ensure_transfer_costs(pool)",
)

text = text.replace(
    '''source_recommendations = (
        budget_recommendations
        if "budget_recommendations" in globals()
        else recommendations
    )''',
    '''source_recommendations = (
        budget_recommendations
        if "budget_recommendations" in globals()
        and isinstance(budget_recommendations, pd.DataFrame)
        and not budget_recommendations.empty
        else recommendations
    )'''
)

text = text.replace(
    '"Transfer Cost Display", "Why Recommended",',
    '"Transfer Cost Display", "Price Source", "Why Recommended",',
)

text = text.replace(
    '"Transfer Cost Display",',
    '"Transfer Cost Display", "Price Source",',
)

text = text.replace(
    '"Transfer Cost Display", "Price Source", "Price Source",',
    '"Transfer Cost Display", "Price Source",',
)

text = text.replace(
    '"Transfer Cost Display", "Price Source", "Budget Share %",',
    '"Transfer Cost Display", "Price Source", "Budget Share %",',
)

path.write_text(text, encoding="utf-8")
print("Fixed transfer budget planner affordability logic.")
