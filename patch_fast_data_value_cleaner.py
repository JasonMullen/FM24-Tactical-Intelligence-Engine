from pathlib import Path

path = Path("fm_engine/fast_data.py")
text = path.read_text(encoding="utf-8")

if "from fm_engine.value_cleaner import add_clean_estimated_value_columns" not in text:
    text = text.replace(
        "import streamlit as st\n",
        "import streamlit as st\nfrom fm_engine.value_cleaner import add_clean_estimated_value_columns\n",
        1,
    )

if "df = add_clean_estimated_value_columns(df)" not in text:
    text = text.replace(
        "df = load_raw_file(path)\n",
        "df = load_raw_file(path)\n    df = add_clean_estimated_value_columns(df)\n",
        1,
    )

path.write_text(text, encoding="utf-8")
print("Patched fast_data.py to clean estimated values during cached loading.")
