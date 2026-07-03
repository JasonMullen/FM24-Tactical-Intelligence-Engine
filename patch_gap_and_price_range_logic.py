from pathlib import Path
import re

# ============================================================
# 1. CREATE GAP + PRICE FILTER MODULE
# ============================================================

filter_path = Path("fm_engine/recommendation_filters.py")

filter_path.write_text(r'''
from __future__ import annotations

import pandas as pd

from fm_engine.signing_engine import ensure_transfer_costs


def choose_focused_gaps(
    gaps: pd.DataFrame,
    mode: str,
    minimum_gap: float,
    top_n: int,
    manual_gaps: list[str] | None = None,
) -> list[str]:
    if gaps is None or gaps.empty or "Squad Area" not in gaps.columns:
        return []

    gap_table = gaps.copy()

    if "Gap To Target" in gap_table.columns:
        gap_table["Gap To Target"] = pd.to_numeric(
            gap_table["Gap To Target"],
            errors="coerce",
        ).fillna(0)
    else:
        gap_table["Gap To Target"] = 0

    all_gaps = gap_table["Squad Area"].dropna().astype(str).tolist()

    if mode == "Manual: choose squad areas":
        selected = [gap for gap in (manual_gaps or []) if gap in all_gaps]
        return selected if selected else all_gaps[: max(top_n, 1)]

    if mode == "Auto: Critical/Important gaps only":
        selected = (
            gap_table[gap_table["Gap To Target"] >= float(minimum_gap)]
            .sort_values("Gap To Target", ascending=False)
            ["Squad Area"]
            .dropna()
            .astype(str)
            .tolist()
        )

        if selected:
            return selected

        return (
            gap_table.sort_values("Gap To Target", ascending=False)
            .head(max(top_n, 1))
            ["Squad Area"]
            .dropna()
            .astype(str)
            .tolist()
        )

    return (
        gap_table.sort_values("Gap To Target", ascending=False)
        .head(max(top_n, 1))
        ["Squad Area"]
        .dropna()
        .astype(str)
        .tolist()
    )


def apply_recommendation_filters(
    recs: pd.DataFrame,
    focused_gaps: list[str],
    min_price: float,
    max_price: float,
) -> pd.DataFrame:
    if recs is None or recs.empty:
        return pd.DataFrame()

    out = ensure_transfer_costs(recs.copy())

    if focused_gaps and "Recommended For" in out.columns:
        out = out[out["Recommended For"].astype(str).isin([str(gap) for gap in focused_gaps])].copy()

    if "Transfer Cost" in out.columns:
        out["Transfer Cost"] = pd.to_numeric(out["Transfer Cost"], errors="coerce")

        out = out[
            out["Transfer Cost"].notna()
            & (out["Transfer Cost"] >= float(min_price))
            & (out["Transfer Cost"] <= float(max_price))
        ].copy()

    if out.empty:
        return out

    sort_cols = [
        col for col in [
            "Gap Priority Order",
            "Gap Rank",
            "Recommendation Score",
            "Quality Score",
            "Realism Fit",
        ]
        if col in out.columns
    ]

    if sort_cols:
        ascending = [True if col in ["Gap Priority Order", "Gap Rank"] else False for col in sort_cols]
        out = out.sort_values(sort_cols, ascending=ascending)

    return out.reset_index(drop=True)
''', encoding="utf-8")


# ============================================================
# 2. PATCH RECOMMENDED SIGNINGS PAGE
# ============================================================

page_path = Path("app/pages/11_Recommended_Signings.py")
text = page_path.read_text(encoding="utf-8")

# Add import.
if "from fm_engine.recommendation_filters import apply_recommendation_filters, choose_focused_gaps" not in text:
    if "from fm_engine.manual_spend_planner import build_manual_spend_budget_plan\n" in text:
        text = text.replace(
            "from fm_engine.manual_spend_planner import build_manual_spend_budget_plan\n",
            "from fm_engine.manual_spend_planner import build_manual_spend_budget_plan\n"
            "from fm_engine.recommendation_filters import apply_recommendation_filters, choose_focused_gaps\n",
            1,
        )
    else:
        pattern = r"from fm_engine\.signing_engine import \([\s\S]*?\)\n"
        match = re.search(pattern, text)

        if not match:
            raise SystemExit("Could not find signing_engine import block.")

        text = (
            text[:match.end()]
            + "from fm_engine.recommendation_filters import apply_recommendation_filters, choose_focused_gaps\n"
            + text[match.end():]
        )


# Insert gap targeting and price range controls after gaps are calculated.
controls_block = r'''
# ============================================================
# SQUAD GAP + PRICE RANGE TARGETING
# ============================================================

st.sidebar.header("Squad Gap Targeting")

gap_focus_mode = st.sidebar.selectbox(
    "Squad Gap Focus",
    [
        "Auto: Critical/Important gaps only",
        "Auto: Top N biggest gaps",
        "Manual: choose squad areas",
    ],
    index=0,
    key="rec_gap_focus_mode",
)

minimum_gap_to_target = st.sidebar.number_input(
    "Minimum Gap To Target",
    min_value=0.0,
    max_value=50.0,
    value=4.0,
    step=0.5,
    key="rec_minimum_gap_to_target",
)

top_gap_count = st.sidebar.slider(
    "Number Of Squad Gaps To Target",
    min_value=1,
    max_value=len(CATEGORY_PROFILES),
    value=3,
    step=1,
    key="rec_top_gap_count",
)

all_gap_options = gaps["Squad Area"].dropna().astype(str).tolist() if not gaps.empty else list(CATEGORY_PROFILES.keys())

default_focused_gaps = choose_focused_gaps(
    gaps=gaps,
    mode="Auto: Critical/Important gaps only",
    minimum_gap=minimum_gap_to_target,
    top_n=top_gap_count,
    manual_gaps=[],
)

manual_gap_choices = st.sidebar.multiselect(
    "Manual Squad Areas",
    all_gap_options,
    default=[gap for gap in default_focused_gaps if gap in all_gap_options],
    key="rec_manual_gap_choices",
)

focused_gaps = choose_focused_gaps(
    gaps=gaps,
    mode=gap_focus_mode,
    minimum_gap=minimum_gap_to_target,
    top_n=top_gap_count,
    manual_gaps=manual_gap_choices,
)

st.sidebar.caption("Targeting: " + (", ".join(focused_gaps) if focused_gaps else "No squad gaps selected"))

st.sidebar.header("Player Price Range")

price_range_mode = st.sidebar.selectbox(
    "Price Range Mode",
    [
        "Auto from planned spend",
        "Manual",
    ],
    index=0,
    key="rec_price_range_mode",
)

per_player_spend_target = float(planned_spend_target) / max(int(players_to_buy), 1)

if spend_strategy == "Aggressive":
    auto_min_price = per_player_spend_target * 0.65
    auto_max_price = per_player_spend_target * 2.00
elif spend_strategy == "Conservative":
    auto_min_price = per_player_spend_target * 0.35
    auto_max_price = per_player_spend_target * 1.25
else:
    auto_min_price = per_player_spend_target * 0.50
    auto_max_price = per_player_spend_target * 1.60

auto_min_price = max(auto_min_price, 0)
auto_max_price = min(auto_max_price, float(planned_spend_target))

if price_range_mode == "Auto from planned spend":
    player_min_price = float(auto_min_price)
    player_max_price = float(auto_max_price)

    st.sidebar.caption(
        f"Auto range: {format_money(player_min_price)} to {format_money(player_max_price)} per player"
    )
else:
    min_price_text = st.sidebar.text_input(
        "Minimum Player Price",
        value=f"{int(auto_min_price):,}",
        placeholder="Example: 10M or 10,000,000",
        key="rec_min_player_price_text",
    )

    max_price_text = st.sidebar.text_input(
        "Maximum Player Price",
        value=f"{int(auto_max_price):,}",
        placeholder="Example: 80M or 80,000,000",
        key="rec_max_player_price_text",
    )

    player_min_price = parse_budget_input(min_price_text)
    player_max_price = parse_budget_input(max_price_text)

    if player_max_price <= 0:
        player_max_price = float(planned_spend_target)

    if player_min_price > player_max_price:
        player_min_price, player_max_price = player_max_price, player_min_price

    st.sidebar.caption(
        f"Manual range: {format_money(player_min_price)} to {format_money(player_max_price)} per player"
    )
'''

if "# SQUAD GAP + PRICE RANGE TARGETING" not in text:
    marker = "gaps = squad_gaps(team_ratings, your_club, benchmark)"

    if marker not in text:
        raise SystemExit("Could not find gaps calculation marker.")

    text = text.replace(
        marker,
        marker + "\n\n" + controls_block,
        1,
    )


# Filter recommendations after both recommendation pools are built.
filter_block = r'''
# Enforce selected squad gaps and player price range.
recommendations = apply_recommendation_filters(
    recs=recommendations,
    focused_gaps=focused_gaps,
    min_price=player_min_price,
    max_price=player_max_price,
)

budget_recommendations = apply_recommendation_filters(
    recs=budget_recommendations,
    focused_gaps=focused_gaps,
    min_price=player_min_price,
    max_price=player_max_price,
)
'''

if "# Enforce selected squad gaps and player price range." not in text:
    marker = "sell_df, replacement_df = build_sell_upgrade_table("

    if marker not in text:
        raise SystemExit("Could not find sell_df marker.")

    text = text.replace(
        marker,
        filter_block + "\n" + marker,
        1,
    )


# Add visible summary to main page after realism warning.
summary_line = r'''
st.caption(
    f"Active filters → Squad gaps: {', '.join(focused_gaps)} | "
    f"Player price range: {format_money(player_min_price)} to {format_money(player_max_price)}"
)
'''

if "Active filters → Squad gaps:" not in text:
    marker = 'st.warning(context["Realistic Goal"])'

    if marker in text:
        text = text.replace(
            marker,
            marker + "\n" + summary_line,
            1,
        )


# Improve empty-plan warning.
text = text.replace(
    'st.warning(summary["message"])',
    '''st.warning(summary["message"])
        st.info(
            "If no plan appears, your selected squad gaps or player price range may be too restrictive. "
            "Try widening the price range, lowering Minimum Gap To Target, or switching Squad Gap Focus to Manual."
        )''',
)

page_path.write_text(text, encoding="utf-8")

print("Added squad-gap-only recommendations and player price range cutoffs.")
