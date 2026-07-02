from pathlib import Path
import re

path = Path("app/pages/11_Recommended_Signings.py")
text = path.read_text(encoding="utf-8")

fixed_function = r'''
def detect_south_america_mask(team_ratings: pd.DataFrame) -> pd.Series:
    text = (
        team_ratings["League"].astype(str).str.lower()
        + " "
        + team_ratings["Club"].astype(str).str.lower()
    )

    keywords = [
        "brazil",
        "brasil",
        "argentina",
        "uruguay",
        "chile",
        "colombia",
        "paraguay",
        "peru",
        "ecuador",
        "bolivia",
        "venezuela",
        "brasileiro",
        "brasileirao",
        "serie a brazil",
        "liga profesional",
        "primera division argentina",
        "libertadores",
    ]

    mask = pd.Series(False, index=team_ratings.index)

    for keyword in keywords:
        mask = mask | text.str.contains(keyword, case=False, na=False)

    return mask
'''

pattern = r"def detect_south_america_mask\(team_ratings: pd\.DataFrame\) -> pd\.Series:.*?\n\ndef determine_benchmark"

if re.search(pattern, text, flags=re.DOTALL):
    text = re.sub(
        pattern,
        fixed_function + "\n\ndef determine_benchmark",
        text,
        flags=re.DOTALL,
    )
else:
    text = text.replace('par "ecuador",', '"paraguay",\n        "ecuador",')
    text = text.replace('"par "ecuador",', '"paraguay",\n        "ecuador",')

path.write_text(text, encoding="utf-8")
print("Fixed Recommended Signings syntax issue.")
