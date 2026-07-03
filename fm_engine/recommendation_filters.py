
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
