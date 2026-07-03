from pathlib import Path
import re

path = Path("app/pages/11_Recommended_Signings.py")
text = path.read_text(encoding="utf-8")

# ============================================================
# 1. ADD SIDEBAR TRANSFER BUDGET INPUTS IF MISSING
# ============================================================

sidebar_budget_block = r'''
st.sidebar.header("Transfer Budget Planner")

transfer_budget = st.sidebar.number_input(
    "Transfer Budget",
    min_value=0,
    value=150_000_000,
    step=5_000_000,
    format="%d",
    key="recommended_signings_transfer_budget",
)

players_to_buy = st.sidebar.slider(
    "Players To Buy",
    min_value=1,
    max_value=10,
    value=4,
    step=1,
    key="recommended_signings_players_to_buy",
)

budget_pool_per_gap = st.sidebar.slider(
    "Budget Options Per Squad Gap",
    min_value=5,
    max_value=50,
    value=20,
    step=5,
    key="recommended_signings_budget_pool_per_gap",
)
'''

if "transfer_budget = st.sidebar.number_input" not in text:
    marker = 'if st.sidebar.button("Clear Signing Recommendation Cache"):'

    if marker not in text:
        raise SystemExit("Could not find sidebar cache button marker.")

    text = text.replace(
        marker,
        sidebar_budget_block + "\n\n" + marker,
        1,
    )

# ============================================================
# 2. ADD BUDGET RECOMMENDATION POOL IF MISSING
# ============================================================

if "budget_recommendations = build_signing_recommendations" not in text:
    pattern = r"recommendations\s*=\s*build_signing_recommendations\([\s\S]*?\n\)"

    match = re.search(pattern, text)

    if not match:
        raise SystemExit("Could not find recommendations build block.")

    budget_recommendation_block = r'''

budget_recommendations = build_signing_recommendations(
    df=df,
    team_ratings=team_ratings,
    your_club=your_club,
    target_competition=target_competition,
    playstyle=playstyle,
    benchmark=benchmark,
    max_age=int(max_age),
    max_value_millions=None,
    top_n=int(budget_pool_per_gap),
    search_pool=search_pool,
)
'''

    insert_pos = match.end()
    text = text[:insert_pos] + budget_recommendation_block + text[insert_pos:]

# ============================================================
# 3. MAKE TAB5 SAFE EVEN IF SOMETHING FAILS LATER
# ============================================================

safe_defaults = r'''
# Safety defaults for Transfer Budget Planner.
if "transfer_budget" not in globals():
    transfer_budget = 150_000_000

if "players_to_buy" not in globals():
    players_to_buy = 4

if "budget_pool_per_gap" not in globals():
    budget_pool_per_gap = 20

if "budget_recommendations" not in globals():
    budget_recommendations = recommendations.copy() if "recommendations" in globals() else pd.DataFrame()
'''

if "# Safety defaults for Transfer Budget Planner." not in text:
    marker = "with tab5:"

    if marker not in text:
        raise SystemExit("Could not find Transfer Budget Plan tab block.")

    text = text.replace(
        marker,
        safe_defaults + "\n" + marker,
        1,
    )

path.write_text(text, encoding="utf-8")
print("Fixed missing transfer budget variables.")
