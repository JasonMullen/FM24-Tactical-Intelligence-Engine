from pathlib import Path
import re

path = Path("app/pages/11_Recommended_Signings.py")
text = path.read_text(encoding="utf-8")

# ============================================================
# 1. ADD MANUAL PLANNED SPEND LIMIT INPUT
# ============================================================

planned_spend_block = r'''
planned_spend_text = st.sidebar.text_input(
    "Planned Spend Limit",
    value=budget_text,
    placeholder="Example: 75M or 75,000,000",
    key="rec_planned_spend_limit_text",
)

planned_spend_limit = parse_budget_input(planned_spend_text)

if planned_spend_limit <= 0:
    planned_spend_limit = transfer_budget

planned_spend_limit = min(float(planned_spend_limit), float(transfer_budget))

st.sidebar.caption(f"Planned spend limit: {format_money(planned_spend_limit)}")
'''

if "planned_spend_limit = parse_budget_input(planned_spend_text)" not in text:
    marker = 'st.sidebar.caption(f"Budget read as: {format_money(transfer_budget)}")'

    if marker not in text:
        raise SystemExit("Could not find transfer budget caption marker.")

    text = text.replace(
        marker,
        marker + "\n\n" + planned_spend_block,
        1,
    )


# ============================================================
# 2. MAKE REALISM AND RECOMMENDATIONS USE PLANNED SPEND LIMIT
# ============================================================

text = text.replace(
    "context = club_realism_context(team_ratings, your_club, target_goal, transfer_budget)",
    "context = club_realism_context(team_ratings, your_club, target_goal, planned_spend_limit)",
)

text = text.replace(
    "transfer_budget=transfer_budget,",
    "transfer_budget=planned_spend_limit,",
)


# ============================================================
# 3. FIX TOP METRIC TO SHOW SPEND LIMIT
# ============================================================

text = text.replace(
    'm4.metric("Budget", format_money(transfer_budget))',
    'm4.metric("Spend Limit", format_money(planned_spend_limit))',
)


# ============================================================
# 4. MAKE DYNAMIC BUDGET PLAN USE PLANNED SPEND LIMIT
# ============================================================

text = text.replace(
    '''    st.write(
        f"Build a realistic spending plan for **{your_club}** with **{format_money(transfer_budget)}** "
        f"to buy **{players_to_buy} player(s)** for **{target_goal}** using **{playstyle}**."
    )''',
    '''    st.write(
        f"Build a realistic spending plan for **{your_club}** with **{format_money(transfer_budget)} total budget** "
        f"and a manual spend limit of **{format_money(planned_spend_limit)}** "
        f"to buy **{players_to_buy} player(s)** for **{target_goal}** using **{playstyle}**."
    )''',
)

text = text.replace(
    '''    plan, alternatives, summary = build_dynamic_budget_plan(
        budget_recommendations,
        transfer_budget,
        players_to_buy,
    )''',
    '''    plan, alternatives, summary = build_dynamic_budget_plan(
        budget_recommendations,
        planned_spend_limit,
        players_to_buy,
    )''',
)


# ============================================================
# 5. REPLACE METRICS WITH TOTAL BUDGET + SPEND LIMIT CONTROL
# ============================================================

old_metrics = '''    b1, b2, b3, b4 = st.columns(4)
    b1.metric("Transfer Budget", format_money(transfer_budget))
    b2.metric("Planned Spend", format_money(summary["spend"]))
    b3.metric("Budget Left", format_money(summary["left"]))
    b4.metric("Players Selected", len(plan))
'''

new_metrics = '''    total_budget_left = max(float(transfer_budget) - float(summary["spend"]), 0)
    spend_limit_left = max(float(planned_spend_limit) - float(summary["spend"]), 0)

    b1, b2, b3, b4, b5 = st.columns(5)
    b1.metric("Transfer Budget", format_money(transfer_budget))
    b2.metric("Spend Limit", format_money(planned_spend_limit))
    b3.metric("Planned Spend", format_money(summary["spend"]))
    b4.metric("Total Budget Left", format_money(total_budget_left))
    b5.metric("Players Selected", len(plan))

    st.caption(f"Spend limit left: {format_money(spend_limit_left)}")
'''

if old_metrics in text:
    text = text.replace(old_metrics, new_metrics, 1)
else:
    print("Metric block not found. Skipping metric replacement.")


# ============================================================
# 6. UPDATE SUCCESS MESSAGE TO SHOW MANUAL SPEND CONTROL
# ============================================================

text = text.replace(
    '''            st.success(
                f"Recommended {len(plan)}-player plan: spend **{format_money(summary['spend'])}** "
                f"and keep **{format_money(summary['left'])}**."
            )''',
    '''            st.success(
                f"Recommended {len(plan)}-player plan: spend **{format_money(summary['spend'])}** "
                f"out of your manual spend limit of **{format_money(planned_spend_limit)}**. "
                f"Total budget left: **{format_money(total_budget_left)}**."
            )''',
)

path.write_text(text, encoding="utf-8")
print("Added manual planned spend limit control.")
