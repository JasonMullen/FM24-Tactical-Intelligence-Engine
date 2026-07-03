from pathlib import Path

PROJECT_ROOT = Path.cwd()

files = [PROJECT_ROOT / "app" / "dashboard.py"]
files.extend(sorted((PROJECT_ROOT / "app" / "pages").glob("*.py")))


def insert_import(text: str) -> str:
    if "from fm_engine.ui_memory import init_page_memory, save_page_memory" in text:
        return text

    import_line = "from fm_engine.ui_memory import init_page_memory, save_page_memory\n"

    if "sys.path.append(str(PROJECT_ROOT))\n" in text:
        return text.replace(
            "sys.path.append(str(PROJECT_ROOT))\n",
            "sys.path.append(str(PROJECT_ROOT))\n" + import_line,
            1,
        )

    if "import streamlit as st\n" in text:
        return text.replace(
            "import streamlit as st\n",
            "import streamlit as st\n" + import_line,
            1,
        )

    return import_line + text


def insert_after_set_page_config(text: str) -> str:
    if "init_page_memory(__file__)" in text:
        return text

    target = "st.set_page_config("

    start = text.find(target)

    if start == -1:
        return text

    i = start
    parens = 0
    found_open = False

    while i < len(text):
        char = text[i]

        if char == "(":
            parens += 1
            found_open = True

        elif char == ")":
            parens -= 1

            if found_open and parens == 0:
                line_end = text.find("\n", i)

                if line_end == -1:
                    line_end = len(text) - 1

                return (
                    text[:line_end + 1]
                    + "\ninit_page_memory(__file__)\n"
                    + text[line_end + 1:]
                )

        i += 1

    return text


def append_save(text: str) -> str:
    if "save_page_memory(__file__)" in text:
        return text

    return text.rstrip() + "\n\nsave_page_memory(__file__)\n"


for path in files:
    if not path.exists():
        continue

    text = path.read_text(encoding="utf-8")
    original = text

    text = insert_import(text)
    text = insert_after_set_page_config(text)
    text = append_save(text)

    if text != original:
        path.write_text(text, encoding="utf-8")
        print(f"Patched memory: {path}")
    else:
        print(f"Already patched: {path}")
