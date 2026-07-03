from pathlib import Path
import re

path = Path("app/pages/11_Recommended_Signings.py")
text = path.read_text(encoding="utf-8")

fixed_tabs = '''tab1, tab2, tab3, tab4, tab5 = st.tabs(
    [
        "Top Recommended Signings",
        "Squad Gaps",
        "Benchmark Teams",
        "All Candidate Scores",
        "Transfer Budget Plan",
    ]
)
'''

# Replace old 4-tab assignment with new 5-tab assignment.
pattern = r"tab1\s*,\s*tab2\s*,\s*tab3\s*,\s*tab4\s*=\s*st\.tabs\(\s*\[.*?\]\s*\)"

if re.search(pattern, text, flags=re.DOTALL):
    text = re.sub(pattern, fixed_tabs.strip(), text, count=1, flags=re.DOTALL)
elif "tab1, tab2, tab3, tab4, tab5 = st.tabs" not in text:
    # Emergency fallback: insert fixed tab assignment right before the first tab usage.
    marker = "with tab1:"
    if marker not in text:
        raise SystemExit("Could not find tab section to patch.")

    text = text.replace(marker, fixed_tabs + "\n" + marker, 1)

path.write_text(text, encoding="utf-8")
print("Fixed Recommended Signings tab5 issue.")
