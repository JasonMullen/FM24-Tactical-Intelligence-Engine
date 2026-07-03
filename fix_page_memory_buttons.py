from pathlib import Path
import json

path = Path("fm_engine/ui_memory.py")
text = path.read_text(encoding="utf-8")

# Add a skip helper if missing.
if "def should_skip_memory_key" not in text:
    marker = "def is_json_simple(value: Any) -> bool:"
    helper = r'''
def should_skip_memory_key(key: str) -> bool:
    key_text = str(key)

    if key_text.startswith("_"):
        return True

    # Streamlit buttons cannot have their values restored through session_state.
    if key_text.startswith("reset_memory_"):
        return True

    if key_text.startswith("FormSubmitter:"):
        return True

    return False


'''
    text = text.replace(marker, helper + marker, 1)

# Patch restore function.
text = text.replace(
'''    for key, value in data.items():
        if key.startswith("_"):
            continue

        if key not in st.session_state:
            st.session_state[key] = value
''',
'''    for key, value in data.items():
        if should_skip_memory_key(key):
            continue

        if key not in st.session_state:
            st.session_state[key] = value
'''
)

# Patch save function.
text = text.replace(
'''    for key, value in st.session_state.items():
        if key.startswith("_"):
            continue

        converted = to_jsonable(value)
''',
'''    for key, value in st.session_state.items():
        if should_skip_memory_key(key):
            continue

        converted = to_jsonable(value)
'''
)

path.write_text(text, encoding="utf-8")

# Clean bad saved button keys from all page memory files.
memory_dir = Path("configs/page_memory")

if memory_dir.exists():
    for json_path in memory_dir.glob("*.json"):
        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))

            if isinstance(data, dict):
                cleaned = {
                    key: value
                    for key, value in data.items()
                    if not (
                        str(key).startswith("_")
                        or str(key).startswith("reset_memory_")
                        or str(key).startswith("FormSubmitter:")
                    )
                }

                json_path.write_text(json.dumps(cleaned, indent=4), encoding="utf-8")
                print(f"Cleaned: {json_path}")

        except Exception as exc:
            print(f"Skipped {json_path}: {exc}")

print("Fixed page memory button restore issue.")
