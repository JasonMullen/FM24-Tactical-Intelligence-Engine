
from __future__ import annotations

import re
from typing import Any

import numpy as np
import pandas as pd


NOT_FOR_SALE_VALUE = 1_000_000_000


def base_column_name(col: str) -> str:
    return re.sub(r"__\d+$", "", str(col))


def find_column(df: pd.DataFrame, possible_names: list[str]) -> str | None:
    wanted = {name.lower() for name in possible_names}

    for col in df.columns:
        if base_column_name(str(col)).lower() in wanted:
            return col

    return None


def normalize_money_text(value: Any) -> str:
    if value is None or pd.isna(value):
        return ""

    text = str(value).strip()

    # Fix broken FM export encoding: Â£45K / Ã‚Â£45K
    text = text.replace("Ã‚Â£", "£")
    text = text.replace("Â£", "£")
    text = text.replace("Â", "")

    text = text.replace("–", "-")
    text = text.replace("—", "-")
    text = text.replace(" to ", "-")
    text = text.replace(" TO ", "-")

    return text.strip()


def parse_single_money_piece(piece: Any) -> float | None:
    text = normalize_money_text(piece)

    if not text:
        return None

    text = text.upper()
    text = text.replace("£", "")
    text = text.replace("$", "")
    text = text.replace("€", "")
    text = text.replace(",", "")
    text = text.replace(" ", "")

    match = re.search(r"([0-9]+(?:\.[0-9]+)?)([KMB]?)", text)

    if not match:
        return None

    number = float(match.group(1))
    suffix = match.group(2)

    if suffix == "K":
        number *= 1_000
    elif suffix == "M":
        number *= 1_000_000
    elif suffix == "B":
        number *= 1_000_000_000

    return float(number)


def parse_money_value(value: Any) -> float:
    text = normalize_money_text(value)

    if not text:
        return np.nan

    lowered = text.lower().strip()

    if "not for sale" in lowered or lowered == "nfs":
        return float(NOT_FOR_SALE_VALUE)

    pieces = [piece.strip() for piece in text.split("-") if piece.strip()]
    parsed_numbers = []

    for piece in pieces:
        parsed = parse_single_money_piece(piece)

        if parsed is not None:
            parsed_numbers.append(parsed)

    if not parsed_numbers:
        parsed = parse_single_money_piece(text)

        if parsed is not None:
            parsed_numbers.append(parsed)

    if not parsed_numbers:
        return np.nan

    # Example: £45K - £425K = 235,000
    return float(sum(parsed_numbers) / len(parsed_numbers))


def money_value_status(value: Any) -> str:
    text = normalize_money_text(value)

    if not text:
        return "Missing"

    lowered = text.lower().strip()

    if "not for sale" in lowered or lowered == "nfs":
        return "Not For Sale"

    if "-" in text:
        return "Range Averaged"

    return "Single Value"


def format_clean_money(value: Any) -> str:
    try:
        if value is None or pd.isna(value):
            return ""
        return f"£{float(value):,.0f}"
    except Exception:
        return ""


def add_clean_money_columns(
    df: pd.DataFrame,
    source_names: list[str],
    output_prefix: str,
    overwrite_source: bool = False,
) -> pd.DataFrame:
    df = df.copy()

    source_col = find_column(df, source_names)

    if not source_col:
        df[f"{output_prefix} Raw"] = ""
        df[f"{output_prefix} Clean"] = pd.Series([pd.NA] * len(df), dtype="Int64")
        df[f"{output_prefix} Clean £M"] = np.nan
        df[f"{output_prefix} Display"] = ""
        df[f"{output_prefix} Status"] = "Missing"
        return df

    raw_values = df[source_col].copy()
    clean_values = raw_values.apply(parse_money_value)

    df[f"{output_prefix} Raw"] = raw_values
    df[f"{output_prefix} Clean"] = clean_values.round(0).astype("Int64")
    df[f"{output_prefix} Clean £M"] = (clean_values / 1_000_000).round(2)
    df[f"{output_prefix} Display"] = clean_values.apply(format_clean_money)
    df[f"{output_prefix} Status"] = raw_values.apply(money_value_status)

    if overwrite_source:
        df[source_col] = df[f"{output_prefix} Display"]

    return df


def add_clean_estimated_value_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # Clean Transfer Value first.
    df = add_clean_money_columns(
        df,
        source_names=["Transfer Value", "Transfer Value Range", "Tr Value"],
        output_prefix="Transfer Value",
        overwrite_source=True,
    )

    # Make the visible Transfer Status useful instead of just "Not set".
    transfer_status_col = find_column(df, ["Transfer Status"])

    if "Transfer Value Status" in df.columns:
        if transfer_status_col:
            df[transfer_status_col] = df["Transfer Value Status"]
        else:
            df["Transfer Status"] = df["Transfer Value Status"]

    # Clean Estimated Value / Value too.
    df = add_clean_money_columns(
        df,
        source_names=["Estimated Value", "Value", "Transfer Value"],
        output_prefix="Estimated Value",
        overwrite_source=False,
    )

    return df


# Backward-compatible names used by older app code.
parse_estimated_value = parse_money_value
estimated_value_status = money_value_status
