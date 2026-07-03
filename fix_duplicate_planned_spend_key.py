from pathlib import Path
import re

page_path = Path("app/pages/11_Recommended_Signings.py")
text = page_path.read_text(encoding="utf-8")

clean_transfer_budget_section = r'''st.sidebar.header("Transfer Budget Planner")

budget_text = st.sidebar.text_input(
    "Transfer Budget",
    value="150,000,000",
    placeholder="Example: 150M or 150,000,000",
    key="rec_transfer_budget_text",
)

transfer_budget = parse_budget_input(budget_text)

st.sidebar.caption(f"Budget read as: {format_money(transfer_budget)}")

planned_spend_text = st.sidebar.text_input(
    "Planned Spend Target",
    value="100,000,000",
    placeholder="Example: 100M or 100,000,000",
    key="rec_planned_spend_target_text",
)

planned_spend_target = parse_budget_input(planned_spend_text)

if planned_spend_target <= 0:
    planned_spend_target = transfer_budget

planned_spend_target = min(float(planned_spend_target), float(transfer_budget))

st.sidebar.caption(f"Planned spend target: {format_money(planned_spend_target)}")

spend_strategy = st.sidebar.selectbox(
    "Spending Strategy",
    ["Conservative", "Balanced", "Aggressive"],
    index=1,
    key="rec_spending_strategy",
)

st.sidebar.caption(
    "Conservative saves money. Balanced uses the budget intelligently. Aggressive pushes closer to the planned spend target."
)

players_to_buy = st.sidebar.slider(
    "Players To Buy",
    min_value=1,
    max_value=10,
    value=3,
    step=1,
    key="rec_players_to_buy",
)

budget_pool_per_gap = st.sidebar.slider(
    "Budget Options Per Gap",
    min_value=5,
    max_value=50,
    value=25,
    step=5,
    key="rec_budget_pool_per_gap",
)

'''

pattern = r'st\.sidebar\.header\("Transfer Budget Planner"\)[\s\S]*?(?=if st\.sidebar\.button\("Clear Signing Recommendation Cache")'

if not re.search(pattern, text):
    raise SystemExit("Could not find Transfer Budget Planner sidebar section.")

text = re.sub(
    pattern,
    clean_transfer_budget_section,
    text,
    count=1,
)

# Remove any extra duplicated planned spend input blocks outside the rebuilt section.
matches = list(re.finditer(r'planned_spend_text\s*=\s*st\.sidebar\.text_input\([\s\S]*?key="rec_planned_spend_target_text",\s*\)\s*', text))

if len(matches) > 1:
    keep_start, keep_end = matches[0].span()
    rebuilt = []
    last = 0

    for index, match in enumerate(matches):
        start, end = match.span()

        if index == 0:
            continue

        rebuilt.append(text[last:start])
        last = end

    rebuilt.append(text[last:])
    text = "".join(rebuilt)

# Remove any extra duplicated spending strategy blocks outside the rebuilt section.
matches = list(re.finditer(r'spend_strategy\s*=\s*st\.sidebar\.selectbox\([\s\S]*?key="rec_spending_strategy",\s*\)\s*', text))

if len(matches) > 1:
    rebuilt = []
    last = 0

    for index, match in enumerate(matches):
        start, end = match.span()

        if index == 0:
            continue

        rebuilt.append(text[last:start])
        last = end

    rebuilt.append(text[last:])
    text = "".join(rebuilt)

page_path.write_text(text, encoding="utf-8")

print("Fixed duplicate planned spend target key.")
