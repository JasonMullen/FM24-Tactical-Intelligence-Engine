from __future__ import annotations

import json
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = PROJECT_ROOT / "configs"
STATE_PATH = CONFIG_DIR / "ui_state.json"

CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def load_state() -> dict[str, Any]:
    if not STATE_PATH.exists():
        return {}

    try:
        with open(STATE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, dict):
            return data

        return {}

    except Exception:
        return {}


def save_state(state: dict[str, Any]) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    temp_path = STATE_PATH.with_suffix(".tmp")

    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=4)

    temp_path.replace(STATE_PATH)


def get_page_state(page_key: str) -> dict[str, Any]:
    state = load_state()
    page_state = state.get(page_key, {})

    if isinstance(page_state, dict):
        return page_state

    return {}


def set_page_state(page_key: str, values: dict[str, Any]) -> None:
    state = load_state()
    page_state = state.get(page_key, {})

    if not isinstance(page_state, dict):
        page_state = {}

    clean_values = {}

    for key, value in values.items():
        if value is None:
            continue

        clean_values[key] = value

    page_state.update(clean_values)
    state[page_key] = page_state

    save_state(state)


def restore_session_value(session_state, page_state: dict[str, Any], key: str, default: Any = "__NO_DEFAULT__") -> None:
    if key in session_state:
        return

    if key in page_state and page_state[key] is not None:
        session_state[key] = page_state[key]
        return

    if default != "__NO_DEFAULT__":
        session_state[key] = default


def serializable_value(value: Any) -> Any:
    if value is None:
        return None

    if isinstance(value, tuple):
        return list(value)

    return value


def collect_session_values(session_state, keys: list[str]) -> dict[str, Any]:
    values = {}

    for key in keys:
        if key in session_state:
            value = serializable_value(session_state[key])

            if value is not None:
                values[key] = value

    return values
