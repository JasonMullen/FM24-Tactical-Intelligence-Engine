from pathlib import Path
import json
import re

memory_path = Path("fm_engine/ui_memory.py")
text = memory_path.read_text(encoding="utf-8")

# ============================================================
# 1. PATCH BUTTON/FORMS KEYS SO PAGE MEMORY NEVER RESTORES THEM
# ============================================================

new_skip_function = r'''
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
'''

if "def should_skip_memory_key" in text:
    text = re.sub(
        r"def should_skip_memory_key\(key: str\) -> bool:[\s\S]*?\n\n\ndef is_json_simple",
        new_skip_function + "\n\n\ndef is_json_simple",
        text,
        count=1,
    )
else:
    marker = "def is_json_simple(value: Any) -> bool:"
    if marker not in text:
        raise SystemExit("Could not find is_json_simple marker in ui_memory.py")

    text = text.replace(marker, new_skip_function + "\n\n" + marker, 1)

memory_path.write_text(text, encoding="utf-8")
print("Patched ui_memory.py to skip button/cache keys.")


# ============================================================
# 2. CLEAN BAD BUTTON KEYS FROM SAVED PAGE MEMORY JSON FILES
# ============================================================

memory_dir = Path("configs/page_memory")

bad_key_patterns = [
    "reset_memory_",
    "clear_cache",
    "rec_clear_cache",
    "clear_signing",
    "button",
    "submit",
    "FormSubmitter:",
]

if memory_dir.exists():
    for json_file in memory_dir.glob("*.json"):
        try:
            data = json.loads(json_file.read_text(encoding="utf-8"))

            if not isinstance(data, dict):
                continue

            cleaned = {}

            for key, value in data.items():
                key_text = str(key)
                lowered = key_text.lower()

                should_remove = False

                if key_text.startswith("_"):
                    should_remove = True

                for pattern in bad_key_patterns:
                    if pattern.lower() in lowered or key_text.startswith(pattern):
                        should_remove = True

                if not should_remove:
                    cleaned[key] = value

            json_file.write_text(json.dumps(cleaned, indent=4), encoding="utf-8")
            print(f"Cleaned memory file: {json_file}")

        except Exception as exc:
            print(f"Skipped {json_file}: {exc}")

print("Finished cleaning page memory button keys.")
