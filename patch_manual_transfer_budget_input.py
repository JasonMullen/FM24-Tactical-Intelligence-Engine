from pathlib import Path
import re

path = Path("app/pages/11_Recommended_Signings.py")
text = path.read_text(encoding="utf-8")

# ============================================================
# 1. ADD MANUAL BUDGET PARSER
# ============================================================

manual_budget_helper = r'''

def parse_manual_budget_input(value) -> float:
    if value is None:
        return 0.0

    text = str(value).strip()

    if not text:
        return 0.0

    text = text.replace("£", "")
    text = text.replace("$", "")
    text = text.replace("€", "")
    text = text.replace(",", "")
    text = text.replace("_", "")
    text = text.strip().lower()

    text = text.replace("million", "m")
    text = text.replace("millions", "m")
    text = text.replace("billion", "b")
    text = text.replace("billions", "b")
    text = text.replace("thousand", "k")
    text = text.replace("thousands", "k")
    text = text.replace(" ", "")

    match = re.search(r"([0-9]+(?:\.[0-9]+)?)([kmb]?)", text)

    if not match:
        return 0.0

    number = float(match.group(1))
    suffix = match.group(2)

    if suffix == "k":
        number *= 1_000
    elif suffix == "m":
        number *= 1_000_000
    elif suffix == "b":
        number *= 1_000_000_000

    return float(number)
'''

if "def parse_manual_budget_input" not in text:
    if "def format_money(value)" in text:
        text = text.replace(
            "def format_money(value) -> str:",
            manual_budget_helper + "\n\ndef format_money(value) -> str:",
            1,
        )
    else:
        marker = "# ============================================================\n# TRANSFER BUDGET PLANNER"
        text = text.replace(marker, marker + manual_budget_helper, 1)

# ============================================================
# 2. REPLACE NUMBER INPUT WITH MANUAL TEXT INPUT
# ============================================================

old_pattern = r'''transfer_budget\s*=\s*st\.sidebar\.number_input\(
\s*"Transfer Budget",
\s*min_value=0,
\s*value=150_000_000,
\s*step=5_000_000,
\s*format="%d",
\s*key="recommended_signings_transfer_budget",
\s*\)'''

new_block = r'''transfer_budget_text = st.sidebar.text_input(
    "Transfer Budget",
    value="150,000,000",
    placeholder="Example: 150,000,000 or 150M",
    key="recommended_signings_transfer_budget_text",
)

transfer_budget = parse_manual_budget_input(transfer_budget_text)

st.sidebar.caption(f"Budget read as: {format_money(transfer_budget)}")'''

if re.search(old_pattern, text, flags=re.DOTALL):
    text = re.sub(old_pattern, new_block, text, count=1, flags=re.DOTALL)
elif "transfer_budget_text = st.sidebar.text_input" not in text:
    marker = "players_to_buy = st.sidebar.slider("

    if marker not in text:
        raise SystemExit("Could not find players_to_buy marker.")

    text = text.replace(
        marker,
        new_block + "\n\n" + marker,
        1,
    )

path.write_text(text, encoding="utf-8")
print("Transfer budget is now a manual text input.")
