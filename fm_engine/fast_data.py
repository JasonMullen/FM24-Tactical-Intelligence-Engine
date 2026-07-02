from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CACHE_DIR = PROJECT_ROOT / "data" / "cache"
UPLOAD_DIR = PROJECT_ROOT / "data" / "uploads"

CACHE_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


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


def list_saved_files() -> list[Path]:
    allowed = {".csv", ".xlsx", ".xls", ".html", ".htm"}

    if not UPLOAD_DIR.exists():
        return []

    files = [
        file for file in UPLOAD_DIR.iterdir()
        if file.is_file() and file.suffix.lower() in allowed
    ]

    return sorted(files, key=lambda file: file.stat().st_mtime, reverse=True)


def get_file_signature(path: str | Path) -> tuple[str, float, int]:
    path = Path(path)
    stat = path.stat()
    return str(path), stat.st_mtime, stat.st_size


def cache_path_for_file(path: str | Path, mtime: float, size: int) -> Path:
    path = Path(path)
    raw_key = f"{path.resolve()}::{mtime}::{size}"
    key = hashlib.md5(raw_key.encode("utf-8")).hexdigest()
    return CACHE_DIR / f"{path.stem}_{key}.pkl"


def load_raw_file(path: str | Path) -> pd.DataFrame:
    path = Path(path)
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
    return df


@st.cache_data(show_spinner="Loading FM database from fast cache...")
def load_fm_file_cached(path_text: str, mtime: float, size: int) -> pd.DataFrame:
    path = Path(path_text)
    cache_path = cache_path_for_file(path, mtime, size)

    if cache_path.exists():
        return pd.read_pickle(cache_path)

    df = load_raw_file(path)

    df.to_pickle(cache_path)

    return df


def clear_file_cache() -> int:
    deleted = 0

    for file in CACHE_DIR.glob("*.pkl"):
        file.unlink(missing_ok=True)
        deleted += 1

    load_fm_file_cached.clear()

    return deleted
