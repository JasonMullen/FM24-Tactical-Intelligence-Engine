from pathlib import Path
import re

path = Path("app/pages/11_Recommended_Signings.py")
text = path.read_text(encoding="utf-8")

safe_defaults = r'''
# ============================================================
# TRANSFER BUDGET PLAN SAFETY DEFAULTS
# ============================================================

if "your_club" not in globals():
    if "club_options" in globals() and club_options:
        your_club = club_options[0]
    else:
        your_club = "Selected Club"

if "target_competition" not in globals():
    target_competition = "Win Domestic League"

if "playstyle" not in globals():
    playstyle = "Positional Play / Build From The Back"

if "transfer_budget" not in globals():
    transfer_budget = 150_000_000

if "players_to_buy" not in globals():
    players_to_buy = 4

if "budget_pool_per_gap" not in globals():
    budget_pool_per_gap = 20

if "recommendations" not in globals():
    recommendations = pd.DataFrame()

if "budget_recommendations" not in globals():
    budget_recommendations = recommendations.copy()

if "format_money" not in globals():
    def format_money(value) -> str:
        try:
            value = float(value)
        except Exception:
            return "Unknown"

        if pd.isna(value):
            return "Unknown"

        return f"£{value:,.0f}"
'''

# Remove older incomplete safety block if present.
old_safety_pattern = r'''# Safety defaults for Transfer Budget Planner\.[\s\S]*?if "budget_recommendations" not in globals\(\):\s*\n\s*budget_recommendations = recommendations\.copy\(\) if "recommendations" in globals\(\) else pd\.DataFrame\(\)\s*'''

text = re.sub(old_safety_pattern, "", text, flags=re.DOTALL)

# Add the stronger safety defaults right before Transfer Budget Plan tab.
if "# TRANSFER BUDGET PLAN SAFETY DEFAULTS" not in text:
    marker = "with tab5:"

    if marker not in text:
        raise SystemExit("Could not find with tab5 block.")

    text = text.replace(
        marker,
        safe_defaults + "\n\n" + marker,
        1,
    )

path.write_text(text, encoding="utf-8")
print("Fixed missing playstyle variable for Transfer Budget Plan.")
