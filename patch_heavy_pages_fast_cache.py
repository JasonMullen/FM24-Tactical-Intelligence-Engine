from pathlib import Path
import re

PROJECT_ROOT = Path(__file__).resolve().parent

PAGES_TO_PATCH = [
    "app/pages/2_Role_Fit_Scouting.py",
    "app/pages/3_Player_Comparison_Search.py",
    "app/pages/4_Statistical_Comparison_Search.py",
    "app/pages/5_Top_10_Role_Performers.py",
    "app/pages/6_Tactic_Philosophy_Builder.py",
    "app/pages/7_Opposition_Tactical_Analyzer.py",
    "app/pages/8_Tactic_Screenshot_Tweak_Board.py",
    "app/pages/10_Squad_And_League_Strength_Ratings.py",
]

FAST_IMPORT_BLOCK = """
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from fm_engine.fast_data import (
    get_file_signature,
    list_saved_files as fast_list_saved_files,
    load_fm_file_cached,
)
"""

LOAD_HELPER_BLOCK = """

def load_page_file(path: Path) -> pd.DataFrame:
    path_text, mtime, size = get_file_signature(path)
    return load_fm_file_cached(path_text, mtime, size).copy()
"""


def ensure_sys_import(text: str) -> str:
    if "import sys" in text:
        return text

    if "import re\n" in text:
        return text.replace("import re\n", "import re\nimport sys\n", 1)

    if "from pathlib import Path\n" in text:
        return text.replace("from pathlib import Path\n", "import sys\nfrom pathlib import Path\n", 1)

    return "import sys\n" + text


def insert_fast_import(text: str) -> str:
    if "from fm_engine.fast_data import" in text:
        return text

    pattern = "PROJECT_ROOT = Path(__file__).resolve().parents[2]\n"

    if pattern not in text:
        return text

    replacement = pattern + FAST_IMPORT_BLOCK + "\n"

    return text.replace(pattern, replacement, 1)


def insert_load_helper(text: str) -> str:
    if "def load_page_file(" in text:
        return text

    pattern = 'UPLOAD_DIR = PROJECT_ROOT / "data" / "uploads"\n'

    if pattern not in text:
        return text

    replacement = pattern + LOAD_HELPER_BLOCK

    return text.replace(pattern, replacement, 1)


def replace_loader_calls(text: str) -> str:
    text = text.replace("saved_files = list_saved_files()", "saved_files = fast_list_saved_files()")

    text = re.sub(
        r"(\w+)\s*=\s*load_file\(selected_file\)",
        r"\1 = load_page_file(selected_file)",
        text,
    )

    return text


def patch_file(path: Path) -> None:
    text = path.read_text(encoding="utf-8")

    original = text

    text = ensure_sys_import(text)
    text = insert_fast_import(text)
    text = insert_load_helper(text)
    text = replace_loader_calls(text)

    if text != original:
        path.write_text(text, encoding="utf-8")
        print(f"Patched: {path}")
    else:
        print(f"No changes needed: {path}")


def main() -> None:
    for relative_path in PAGES_TO_PATCH:
        path = PROJECT_ROOT / relative_path

        if not path.exists():
            print(f"Missing, skipped: {path}")
            continue

        patch_file(path)


if __name__ == "__main__":
    main()
