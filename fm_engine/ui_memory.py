from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import streamlit as st

try:
    import numpy as np
except Exception:
    np = None

try:
    from streamlit.delta_generator import DeltaGenerator
except Exception:
    DeltaGenerator = None


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MEMORY_DIR = PROJECT_ROOT / "configs" / "page_memory"
MEMORY_DIR.mkdir(parents=True, exist_ok=True)

_PATCHED = False
_AUTO_COUNTERS: dict[str, dict[str, int]] = {}

WIDGETS_TO_REMEMBER = [
    "checkbox",
    "toggle",
    "selectbox",
    "multiselect",
    "radio",
    "text_input",
    "text_area",
    "number_input",
    "slider",
    "select_slider",
    "date_input",
    "time_input",
]


def page_key_from_file(file_path: str | Path) -> str:
    path = Path(file_path)
    stem = path.stem
    stem = re.sub(r"^\d+_", "", stem)
    stem = re.sub(r"[^A-Za-z0-9_-]", "_", stem)
    return stem.lower()


def memory_path(page_key: str) -> Path:
    return MEMORY_DIR / f"{page_key}.json"


def load_page_memory(page_key: str) -> dict[str, Any]:
    path = memory_path(page_key)

    if not path.exists():
        return {}

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, dict):
            return data

        return {}

    except Exception:
        return {}


def save_page_memory_dict(page_key: str, data: dict[str, Any]) -> None:
    path = memory_path(page_key)
    temp_path = path.with_suffix(".tmp")

    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

    temp_path.replace(path)


def clear_page_memory(page_key: str) -> None:
    path = memory_path(page_key)
    path.unlink(missing_ok=True)


def slug_text(text: Any) -> str:
    text = str(text)
    text = text.strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = text.strip("_")

    if not text:
        return "widget"

    return text[:80]


def make_auto_key(widget_name: str, label: Any) -> str:
    page_key = st.session_state.get("_ui_memory_page_key", "global")
    base = f"mem__{page_key}__{widget_name}__{slug_text(label)}"

    if page_key not in _AUTO_COUNTERS:
        _AUTO_COUNTERS[page_key] = {}

    _AUTO_COUNTERS[page_key][base] = _AUTO_COUNTERS[page_key].get(base, 0) + 1

    count = _AUTO_COUNTERS[page_key][base]

    if count == 1:
        return base

    return f"{base}__{count}"


def get_widget_label(args, kwargs, fallback: str) -> Any:
    if args:
        return args[0]

    return kwargs.get("label", fallback)


def patch_streamlit_widgets() -> None:
    global _PATCHED

    if _PATCHED:
        return

    if DeltaGenerator is None:
        return

    for widget_name in WIDGETS_TO_REMEMBER:
        if not hasattr(DeltaGenerator, widget_name):
            continue

        original = getattr(DeltaGenerator, widget_name)

        if getattr(original, "_ui_memory_patched", False):
            continue

        def make_wrapper(original_func, current_widget_name):
            def wrapper(self, *args, **kwargs):
                if kwargs.get("key") is None:
                    label = get_widget_label(args, kwargs, current_widget_name)
                    kwargs["key"] = make_auto_key(current_widget_name, label)

                return original_func(self, *args, **kwargs)

            wrapper._ui_memory_patched = True
            return wrapper

        setattr(
            DeltaGenerator,
            widget_name,
            make_wrapper(original, widget_name),
        )

    _PATCHED = True




def should_skip_memory_key(key: str) -> bool:
    key_text = str(key)

    if key_text.startswith("_"):
        return True

    # Streamlit buttons cannot have values restored through st.session_state.
    button_patterns = [
        "reset_memory_",
        "clear_cache",
        "rec_clear_cache",
        "clear_signing",
        "button",
        "submit",
    ]

    lowered = key_text.lower()

    if key_text.startswith("FormSubmitter:"):
        return True

    for pattern in button_patterns:
        if pattern in lowered:
            return True

    return False



def is_json_simple(value: Any) -> bool:
    return value is None or isinstance(value, (str, int, float, bool))


def to_jsonable(value: Any):
    if is_json_simple(value):
        return value

    if np is not None:
        if isinstance(value, np.integer):
            return int(value)

        if isinstance(value, np.floating):
            return float(value)

        if isinstance(value, np.bool_):
            return bool(value)

    if isinstance(value, Path):
        return "__SKIP__"

    if isinstance(value, tuple):
        value = list(value)

    if isinstance(value, list):
        clean = []

        for item in value:
            converted = to_jsonable(item)

            if converted == "__SKIP__":
                return "__SKIP__"

            clean.append(converted)

        return clean

    if isinstance(value, dict):
        clean = {}

        for key, item in value.items():
            converted = to_jsonable(item)

            if converted == "__SKIP__":
                return "__SKIP__"

            clean[str(key)] = converted

        return clean

    return "__SKIP__"


def restore_page_memory_values(page_key: str) -> None:
    data = load_page_memory(page_key)

    for key, value in data.items():
        if should_skip_memory_key(key):
            continue

        if key not in st.session_state:
            st.session_state[key] = value


def save_page_memory(file_path: str | Path) -> None:
    page_key = page_key_from_file(file_path)
    data = {}

    for key, value in st.session_state.items():
        if should_skip_memory_key(key):
            continue

        converted = to_jsonable(value)

        if converted == "__SKIP__":
            continue

        data[key] = converted

    save_page_memory_dict(page_key, data)


def init_page_memory(file_path: str | Path) -> None:
    page_key = page_key_from_file(file_path)

    st.session_state["_ui_memory_page_key"] = page_key
    _AUTO_COUNTERS[page_key] = {}

    patch_streamlit_widgets()
    restore_page_memory_values(page_key)

    with st.sidebar.expander("Page Memory", expanded=False):
        st.caption("This page remembers your searches, filters, and selected options.")

        if st.button(
            "Reset This Page Progress",
            key=f"reset_memory_{page_key}",
        ):
            saved_keys = list(load_page_memory(page_key).keys())
            clear_page_memory(page_key)

            for key in saved_keys:
                if key in st.session_state:
                    del st.session_state[key]

            st.success("Page progress reset.")
            st.rerun()
