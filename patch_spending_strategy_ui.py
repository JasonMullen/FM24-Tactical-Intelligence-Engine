from pathlib import Path
import re

page_path = Path("app/pages/11_Recommended_Signings.py")
page_text = page_path.read_text(encoding="utf-8")

# Remove broken import from signing_engine import block.
page_text = page_text.replace("    build_manual_spend_budget_plan,\n", "")

# Add correct separate import.
if "from fm_engine.manual_spend_planner import build_manual_spend_budget_plan" not in page_text:
    pattern = r"from fm_engine\.signing_engine import \([\s\S]*?\)\n"
    match = re.search(pattern, page_text)

    if not match:
        raise SystemExit("Could not find signing_engine import block.")

    insert_at = match.end()
    page_text = (
        page_text[:insert_at]
        + "from fm_engine.manual_spend_planner import build_manual_spend_budget_plan\n"
        + page_text[insert_at:]
    )

# Normalize old variable names from previous patches.
page_text = page_text.replace("planned_spend_limit", "planned_spend_target")
page_text = page_text.replace("Planned Spend Limit", "Planned Spend Target")
page_text = page_text.replace("Spend Limit", "Spend Target")
page_text = page_text.replace("manual spend limit", "manual planned spend target")
page_text = page_text.replace("manual spend target", "manual planned spend target")

# Ensure planned spend target input exists.
planned_spend_block = r'''
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
'''

if "planned_spend_target = parse_budget_input(planned_spend_text)" not in page_text:
    marker = 'st.sidebar.caption(f"Budget read as: {format_money(transfer_budget)}")'

    if marker not in page_text:
        raise SystemExit("Could not find budget caption marker.")

    page_text = page_text.replace(marker, marker + "\n\n" + planned_spend_block, 1)

# Add spending strategy selector.
spend_strategy_block = r'''
spend_strategy = st.sidebar.selectbox(
    "Spending Strategy",
    ["Conservative", "Balanced", "Aggressive"],
    index=1,
    key="rec_spending_strategy",
)

st.sidebar.caption(
    "Conservative saves money. Balanced uses the budget intelligently. Aggressive pushes closer to the planned spend target."
)
'''

if "rec_spending_strategy" not in page_text:
    marker = 'st.sidebar.caption(f"Planned spend target: {format_money(planned_spend_target)}")'

    if marker not in page_text:
        raise SystemExit("Could not find planned spend target caption marker.")

    page_text = page_text.replace(marker, marker + "\n\n" + spend_strategy_block, 1)

# Make context and recommendations use planned spend target.
page_text = page_text.replace(
    "context = club_realism_context(team_ratings, your_club, target_goal, transfer_budget)",
    "context = club_realism_context(team_ratings, your_club, target_goal, planned_spend_target)",
)

page_text = page_text.replace(
    "transfer_budget=transfer_budget,",
    "transfer_budget=planned_spend_target,",
)

# Make top metric show spend target.
page_text = page_text.replace(
    'm4.metric("Budget", format_money(transfer_budget))',
    'm4.metric("Spend Target", format_money(planned_spend_target))',
)

# Replace old dynamic planner call with manual spend planner call.
page_text = re.sub(
    r'''plan,\s*alternatives,\s*summary\s*=\s*build_dynamic_budget_plan\(\s*
\s*budget_recommendations,\s*
\s*transfer_budget,\s*
\s*players_to_buy,\s*
\s*\)''',
    '''plan, alternatives, summary = build_manual_spend_budget_plan(
        budget_recommendations,
        total_budget=transfer_budget,
        planned_spend_target=planned_spend_target,
        players_to_buy=players_to_buy,
        spend_strategy=spend_strategy,
    )''',
    page_text,
    flags=re.DOTALL,
)

# If already using manual planner, make sure spend_strategy is passed.
if "build_manual_spend_budget_plan(" in page_text and "spend_strategy=spend_strategy" not in page_text:
    page_text = re.sub(
        r"(build_manual_spend_budget_plan\([\s\S]*?players_to_buy=players_to_buy,\s*)\)",
        r"\1        spend_strategy=spend_strategy,\n    )",
        page_text,
        count=1,
    )

# Update the write-up text.
page_text = re.sub(
    r'''st\.write\(
\s*f"Build a realistic spending plan for \*\*\{your_club\}\*\* with \*\*\{format_money\(transfer_budget\)\}\*\* "\s*
\s*f"to buy \*\*\{players_to_buy\} player\(s\)\*\* for \*\*\{target_goal\}\*\* using \*\*\{playstyle\}\*\*\."
\s*\)''',
    '''st.write(
        f"Build a realistic spending plan for **{your_club}** with **{format_money(transfer_budget)} total budget** "
        f"and a manual planned spend target of **{format_money(planned_spend_target)}** "
        f"using **{spend_strategy}** spending to buy **{players_to_buy} player(s)** "
        f"for **{target_goal}** using **{playstyle}**."
    )''',
    page_text,
    flags=re.DOTALL,
)

# Replace budget metrics block.
old_metric_block = '''    b1, b2, b3, b4 = st.columns(4)
    b1.metric("Transfer Budget", format_money(transfer_budget))
    b2.metric("Planned Spend", format_money(summary["spend"]))
    b3.metric("Budget Left", format_money(summary["left"]))
    b4.metric("Players Selected", len(plan))
'''

new_metric_block = '''    b1, b2, b3, b4, b5 = st.columns(5)
    b1.metric("Transfer Budget", format_money(transfer_budget))
    b2.metric("Spend Target", format_money(planned_spend_target))
    b3.metric("Planned Spend", format_money(summary["spend"]))
    b4.metric("Target Left", format_money(summary["target_left"]))
    b5.metric("Players Selected", len(plan))
'''

if old_metric_block in page_text:
    page_text = page_text.replace(old_metric_block, new_metric_block, 1)

# Update success message.
page_text = page_text.replace(
    '''            st.success(
                f"Recommended {len(plan)}-player plan: spend **{format_money(summary['spend'])}** "
                f"and keep **{format_money(summary['left'])}**."
            )''',
    '''            st.success(
                f"Recommended {len(plan)}-player plan: spend **{format_money(summary['spend'])}** "
                f"out of your manual planned spend target of **{format_money(planned_spend_target)}** "
                f"using **{spend_strategy}** spending. Total budget left: **{format_money(summary['left'])}**."
            )''',
)

# Update display columns.
page_text = page_text.replace(
    '"Budget Remaining Display",',
    '"Total Budget Remaining Display",\n            "Planned Spend Remaining Display",',
)

page_path.write_text(page_text, encoding="utf-8")

print("Patched UI to use true planned spend target and spending strategy.")
