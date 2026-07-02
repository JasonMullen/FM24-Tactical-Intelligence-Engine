from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from fm_engine.fast_data import (
    get_file_signature,
    list_saved_files as fast_list_saved_files,
    load_fm_file_cached,
)

sys.path.append(str(PROJECT_ROOT))

try:
    from fm_engine.role_profiles import ROLE_PROFILES
except Exception:
    ROLE_PROFILES = {}

from fm_engine.screenshot_reader import (
    build_ocr_tactical_advice,
    detect_formation,
    extract_text_from_image,
    split_strengths_weaknesses,
)

UPLOAD_DIR = PROJECT_ROOT / "data" / "uploads"


def load_page_file(path: Path) -> pd.DataFrame:
    path_text, mtime, size = get_file_signature(path)
    return load_fm_file_cached(path_text, mtime, size).copy()
SCREENSHOT_DIR = PROJECT_ROOT / "data" / "screenshots"
TACTICS_DIR = PROJECT_ROOT / "configs" / "saved_tactics"

SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)


def flatten_column_name(col) -> str:
    if isinstance(col, tuple):
        parts = [str(part).strip() for part in col if str(part).strip()]
        return parts[-1] if parts else "Unknown"
    return str(col).strip()


def make_unique_columns(columns) -> list[str]:
    seen = {}
    fixed = []

    for col in columns:
        base = flatten_column_name(col)

        if base == "" or base.lower().startswith("unnamed"):
            base = "Unknown"

        key = base.lower()

        if key not in seen:
            seen[key] = 1
            fixed.append(base)
        else:
            seen[key] += 1
            fixed.append(f"{base}__{seen[key]}")

    return fixed


def base_column_name(col: str) -> str:
    return re.sub(r"__\d+$", "", str(col))


def find_column(df: pd.DataFrame, possible_names: list[str]) -> str | None:
    wanted = {name.lower() for name in possible_names}

    for col in df.columns:
        if base_column_name(col).lower() in wanted:
            return col

    return None


def list_saved_files() -> list[Path]:
    allowed = {".csv", ".xlsx", ".xls", ".html", ".htm"}

    if not UPLOAD_DIR.exists():
        return []

    return sorted(
        [file for file in UPLOAD_DIR.iterdir() if file.is_file() and file.suffix.lower() in allowed],
        key=lambda file: file.stat().st_mtime,
        reverse=True,
    )


def list_saved_tactics() -> list[Path]:
    if not TACTICS_DIR.exists():
        return []
    return sorted(TACTICS_DIR.glob("*.json"))


def load_file(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()

    if suffix == ".csv":
        df = pd.read_csv(path)
    elif suffix in [".xlsx", ".xls"]:
        df = pd.read_excel(path)
    elif suffix in [".html", ".htm"]:
        tables = pd.read_html(path)
        if not tables:
            raise ValueError("No table found in this FM HTML file.")
        df = max(tables, key=lambda table: table.shape[0] * table.shape[1])
    else:
        raise ValueError("Unsupported file type.")

    df.columns = make_unique_columns(df.columns)
    df = df.dropna(axis=0, how="all")
    df = df.dropna(axis=1, how="all")
    df = df.drop_duplicates()

    return df


def load_tactic(path: Path | None) -> dict:
    if path is None:
        return {}

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_screenshot(uploaded_file, label: str) -> Path:
    safe_name = uploaded_file.name.strip().replace(" ", "_")
    safe_name = re.sub(r"[^A-Za-z0-9_.-]", "", safe_name)
    path = SCREENSHOT_DIR / f"{label}_{safe_name}"

    with open(path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    return path


def save_and_read_screenshot(uploaded_file, label: str) -> tuple[Path | None, str]:
    if uploaded_file is None:
        return None, ""

    path = save_screenshot(uploaded_file, label)

    with st.spinner(f"Reading text from {label.replace('_', ' ')} screenshot..."):
        text = extract_text_from_image(path)

    return path, text


POSITION_ORDER = [
    "GK", "CB", "RB", "LB", "RWB", "LWB",
    "DM", "CM", "RM", "LM", "AM", "RW", "LW", "ST"
]


def normalize_position_text(position_text: str) -> str:
    text = str(position_text).upper()
    text = text.replace(" ", "")
    text = text.replace("-", "")
    return text


def has_position(text: str, patterns: list[str]) -> bool:
    return any(pattern in text for pattern in patterns)


def classify_position_classes(position_text: str) -> list[str]:
    text = normalize_position_text(position_text)
    found = []

    if has_position(text, ["GK"]):
        found.append("GK")
    if has_position(text, ["D(C)", "DC", "SW"]):
        found.append("CB")
    if has_position(text, ["D(R)", "DR"]):
        found.append("RB")
    if has_position(text, ["D(L)", "DL"]):
        found.append("LB")
    if has_position(text, ["WB(R)", "WBR"]):
        found.append("RWB")
    if has_position(text, ["WB(L)", "WBL"]):
        found.append("LWB")
    if has_position(text, ["DM", "DM(C)"]):
        found.append("DM")
    if has_position(text, ["M(C)", "MC"]):
        found.append("CM")
    if has_position(text, ["M(R)", "MR"]):
        found.append("RM")
    if has_position(text, ["M(L)", "ML"]):
        found.append("LM")
    if has_position(text, ["AM(C)", "AMC"]):
        found.append("AM")
    if has_position(text, ["AM(R)", "AMR"]):
        found.append("RW")
    if has_position(text, ["AM(L)", "AML"]):
        found.append("LW")
    if has_position(text, ["ST", "ST(C)", "SC", "CF"]):
        found.append("ST")

    clean = []
    for pos in POSITION_ORDER:
        if pos in found and pos not in clean:
            clean.append(pos)

    return clean


def primary_position_from_classes(position_classes: list[str]) -> str:
    if not position_classes:
        return "Unknown"

    priority = [
        "GK", "ST", "AM", "RW", "LW", "CM", "DM",
        "CB", "RB", "LB", "RWB", "LWB", "RM", "LM"
    ]

    for pos in priority:
        if pos in position_classes:
            return pos

    return position_classes[0]


def add_position_classification(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    position_col = find_column(df, ["Position", "Positions"])

    if not position_col:
        df["Position Classes"] = "Unknown"
        df["Primary Position"] = "Unknown"
        return df

    classes_series = df[position_col].apply(classify_position_classes)

    df["Position Classes"] = classes_series.apply(
        lambda classes: ", ".join(classes) if classes else "Unknown"
    )
    df["Primary Position"] = classes_series.apply(primary_position_from_classes)

    return df


ATTACKING_ATTRIBUTES = {
    "Fin": 1.25, "OtB": 1.20, "Cmp": 1.10,
    "Acc": 1.00, "Pac": 1.00, "Fir": 0.95, "Tec": 0.95,
}

CREATIVE_ATTRIBUTES = {
    "Pas": 1.25, "Vis": 1.30, "Tec": 1.10,
    "Fir": 1.05, "Dec": 1.15, "Cmp": 1.00, "Fla": 0.95,
}

WIDE_THREAT_ATTRIBUTES = {
    "Pac": 1.15, "Acc": 1.15, "Dri": 1.20,
    "Cro": 1.20, "OtB": 1.00, "Tec": 0.95,
}

DEFENSIVE_ATTRIBUTES = {
    "Tck": 1.20, "Mar": 1.10, "Pos": 1.20,
    "Ant": 1.10, "Cnt": 1.05, "Str": 0.90, "Pac": 0.85,
}

PHYSICAL_ATTRIBUTES = {
    "Pac": 1.20, "Acc": 1.20, "Sta": 1.00,
    "Str": 0.90, "Agi": 0.95, "Bal": 0.90,
}

PRESS_RESISTANCE_ATTRIBUTES = {
    "Pas": 1.15, "Fir": 1.20, "Tec": 1.10,
    "Cmp": 1.15, "Dec": 1.10, "Agi": 0.95, "Bal": 0.95,
}


def find_attr_column(row: pd.Series, attr: str) -> str | None:
    for col in row.index:
        if base_column_name(col) == attr:
            return col
    return None


def weighted_attribute_score(row: pd.Series, weights: dict[str, float]) -> float:
    total = 0.0
    weight_total = 0.0

    for attr, weight in weights.items():
        col = find_attr_column(row, attr)

        if col is None:
            continue

        value = pd.to_numeric(row[col], errors="coerce")

        if pd.isna(value):
            continue

        total += float(value) * weight
        weight_total += weight

    if weight_total == 0:
        return 0.0

    return round(((total / weight_total) / 20) * 100, 1)


def add_team_scores(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    df["Attacking Threat"] = df.apply(lambda row: weighted_attribute_score(row, ATTACKING_ATTRIBUTES), axis=1)
    df["Creative Threat"] = df.apply(lambda row: weighted_attribute_score(row, CREATIVE_ATTRIBUTES), axis=1)
    df["Wide Threat"] = df.apply(lambda row: weighted_attribute_score(row, WIDE_THREAT_ATTRIBUTES), axis=1)
    df["Defensive Strength"] = df.apply(lambda row: weighted_attribute_score(row, DEFENSIVE_ATTRIBUTES), axis=1)
    df["Physical Power"] = df.apply(lambda row: weighted_attribute_score(row, PHYSICAL_ATTRIBUTES), axis=1)
    df["Press Resistance"] = df.apply(lambda row: weighted_attribute_score(row, PRESS_RESISTANCE_ATTRIBUTES), axis=1)

    df["Overall Danger Score"] = (
        df["Attacking Threat"] * 0.35
        + df["Creative Threat"] * 0.30
        + df["Wide Threat"] * 0.20
        + df["Physical Power"] * 0.15
    ).round(1)

    df["Weak Link Score"] = (
        100 - (
            df["Defensive Strength"] * 0.45
            + df["Physical Power"] * 0.25
            + df["Press Resistance"] * 0.30
        )
    ).round(1)

    df["Pressing Target Score"] = (
        100 - (
            df["Press Resistance"] * 0.70
            + df["Physical Power"] * 0.30
        )
    ).round(1)

    return df


def weapon_score(row: pd.Series, weapon: str) -> float:
    if weapon == "Runners In Behind":
        weights = {"Pac": 1.25, "Acc": 1.25, "OtB": 1.20, "Fin": 1.05, "Ant": 1.00}
    elif weapon == "Creative Passers":
        weights = {"Pas": 1.25, "Vis": 1.30, "Tec": 1.10, "Fir": 1.05, "Dec": 1.15, "Cmp": 1.00}
    elif weapon == "Wide 1v1 Threats":
        weights = {"Dri": 1.25, "Acc": 1.20, "Pac": 1.20, "Tec": 1.05, "Cro": 0.95}
    elif weapon == "Crossers":
        weights = {"Cro": 1.35, "Tec": 1.00, "Pas": 0.95, "Acc": 0.95, "Sta": 0.90}
    elif weapon == "Pressing Monsters":
        weights = {"Wor": 1.30, "Sta": 1.25, "Agg": 1.10, "Ant": 1.05, "Acc": 0.95, "Tea": 1.00}
    else:
        weights = {"Fin": 1.10, "OtB": 1.10, "Pas": 1.00, "Tec": 1.00}

    return weighted_attribute_score(row, weights)


def get_identity_cols(df: pd.DataFrame) -> list[str]:
    wanted = [
        "Name", "Age", "Nat", "Club", "Division", "League",
        "Position", "Primary Position", "Position Classes",
        "Transfer Value", "Value", "Wage"
    ]

    cols = []

    for item in wanted:
        match = find_column(df, [item])
        if match and match not in cols:
            cols.append(match)

    return cols


def build_display_cols(df: pd.DataFrame, score_cols: list[str]) -> list[str]:
    cols = get_identity_cols(df)

    for col in score_cols:
        if col in df.columns and col not in cols:
            cols.append(col)

    return [col for col in cols if col in df.columns]


def get_club_options(df: pd.DataFrame) -> list[str]:
    club_col = find_column(df, ["Club"])

    if not club_col:
        return []

    return sorted(df[club_col].dropna().astype(str).unique().tolist())


def club_filter(df: pd.DataFrame, club_name: str) -> pd.DataFrame:
    club_col = find_column(df, ["Club"])

    if not club_col:
        return df.iloc[0:0].copy()

    return df[df[club_col].astype(str) == club_name].copy()


def formation_advice(formation: str) -> list[str]:
    advice = []

    if formation in ["4-2-3-1", "4-3-3 DM Wide"]:
        advice.append("Their central structure is likely protected by a DM or double pivot. Do not force central passes. Move them side-to-side and attack the fullback/center-back channel.")
        advice.append("Create winger + fullback + near CM overloads. Pull their fullback out, then attack the half-space behind him.")

    elif formation in ["4-4-2", "4-4-1-1"]:
        advice.append("A 4-4-2 can leave space between midfield and defense. Use an AM, false nine, or roaming midfielder to receive between the lines.")
        advice.append("Switch play quickly. Their wide midfielders can get dragged narrow, opening the far-side winger.")

    elif formation in ["3-5-2", "3-4-2-1", "3-4-3"]:
        advice.append("Back-three systems can be attacked outside the wide center backs. Pin their wingback, then attack the channel beside the outside CB.")
        advice.append("Avoid blind crosses into three center backs. Prefer cutbacks, low crosses, and half-space combinations.")

    else:
        advice.append("Formation was not confidently detected. Use the manual formation selector and the OCR text to guide the plan.")

    return advice


def generate_final_plan(
    ocr_text: str,
    detected_or_selected_formation: str,
    opponent_df: pd.DataFrame,
    weak_zone: str,
    match_goal: str,
) -> dict[str, list[str]]:
    plan = {
        "Main Tactical Idea": [],
        "In Possession": [],
        "Out Of Possession": [],
        "Transition Plan": [],
        "Pressing Plan": [],
        "Players To Target": [],
    }

    plan["Main Tactical Idea"].extend(formation_advice(detected_or_selected_formation))

    ocr_advice = build_ocr_tactical_advice(ocr_text)

    for item in ocr_advice["How To Exploit Their Weaknesses"]:
        plan["In Possession"].append(item)

    for item in ocr_advice["How To Protect Against Their Strengths"]:
        plan["Out Of Possession"].append(item)

    for item in ocr_advice["Pressing Triggers"]:
        plan["Pressing Plan"].append(item)

    for item in ocr_advice["Chance Creation Plan"]:
        plan["In Possession"].append(item)

    for item in ocr_advice["Specific Tactical Tweaks"]:
        plan["Main Tactical Idea"].append(item)

    if weak_zone == "Left Side":
        plan["In Possession"].append("Attack their left side with your right-sided triangle: RB/RWB + RW/RM + RCM. Create 2v1s and cutbacks.")
    elif weak_zone == "Right Side":
        plan["In Possession"].append("Attack their right side with your left-sided triangle: LB/LWB + LW/LM + LCM. Create 2v1s and cutbacks.")
    elif weak_zone == "Central":
        plan["In Possession"].append("Attack centrally by using an AM/false nine between lines and runners beyond him.")
    elif weak_zone == "Behind Defensive Line":
        plan["Transition Plan"].append("Attack space behind with Pass Into Space, faster tempo, and runners with Pace, Acceleration, and Off The Ball.")

    if match_goal == "Control The Game":
        plan["Main Tactical Idea"].append("Control the game with patient possession, safe rest-defense, and repeated overloads rather than forcing low-quality shots.")
    elif match_goal == "Attack Aggressively":
        plan["Main Tactical Idea"].append("Attack aggressively by raising tempo and committing one extra runner, but keep a DM or conservative fullback for rest-defense.")
    elif match_goal == "Protect A Lead":
        plan["Transition Plan"].append("Protect the lead: reduce risky passes, keep one fullback on Defend, and stay compact after losing the ball.")
    elif match_goal == "Chase A Goal":
        plan["In Possession"].append("Chase the goal: increase width, add one attacking duty, and repeatedly target the weakest defender.")

    weak_links = opponent_df.sort_values("Weak Link Score", ascending=False).head(3)
    name_col = find_column(opponent_df, ["Name", "Player"])
    pos_col = find_column(opponent_df, ["Position"])

    for _, row in weak_links.iterrows():
        name = row.get(name_col, "Unknown") if name_col else "Unknown"
        position = row.get(pos_col, "Unknown") if pos_col else "Unknown"
        score = row.get("Weak Link Score", 0)
        plan["Players To Target"].append(
            f"Target {name} ({position}). Weak Link Score: {score}. Isolate him with your best runner, dribbler, or overlapping fullback."
        )

    for section, items in plan.items():
        if not items:
            plan[section].append("No specific note generated for this section.")

    return plan


st.set_page_config(
    page_title="Tactic Screenshot Tweak Board",
    page_icon="🧠",
    layout="wide",
)

st.title("Tactic Screenshot Tweak Board")

st.write(
    """
    Upload your tactic screenshot, the opposition tactic screenshot, and their strengths/weaknesses report.
    This version reads screenshot text with OCR and turns it into tactical advice.
    """
)

saved_files = fast_list_saved_files()

if not saved_files:
    st.info("Upload your FM24 database on the main dashboard first.")
    st.stop()

selected_file = st.sidebar.selectbox(
    "Choose Saved Database",
    saved_files,
    format_func=lambda path: path.name,
)

df = load_page_file(selected_file)
df = add_position_classification(df)
df = add_team_scores(df)

club_options = get_club_options(df)

if not club_options:
    st.error("No Club column found.")
    st.stop()

st.sidebar.header("Match Setup")

your_club = st.sidebar.selectbox("Your Club", club_options)
opponent_club = st.sidebar.selectbox("Opponent Club", club_options)

saved_tactics = list_saved_tactics()
selected_tactic_path = None

if saved_tactics:
    selected_tactic_path = st.sidebar.selectbox(
        "Saved Tactic",
        [None] + saved_tactics,
        format_func=lambda path: "None selected" if path is None else path.name,
    )

tactic = load_tactic(selected_tactic_path) if selected_tactic_path else {}

manual_formation = st.sidebar.selectbox(
    "Manual Opposition Formation Override",
    [
        "Use OCR Detection",
        "4-2-3-1",
        "4-3-3 DM Wide",
        "4-4-2",
        "4-4-1-1",
        "4-1-4-1",
        "3-5-2",
        "3-4-2-1",
        "3-4-3",
        "Unknown / Not Sure",
    ],
)

weak_zone = st.sidebar.selectbox(
    "Primary Weak Zone To Attack",
    [
        "Auto / Use Weak Link",
        "Left Side",
        "Right Side",
        "Central",
        "Behind Defensive Line",
    ],
)

match_goal = st.sidebar.selectbox(
    "Match Goal",
    [
        "Control The Game",
        "Attack Aggressively",
        "Protect A Lead",
        "Chase A Goal",
    ],
)

st.subheader("Screenshot OCR Uploads")

col1, col2 = st.columns(2)

with col1:
    your_tactic_upload = st.file_uploader(
        "Upload YOUR Tactic Screenshot",
        type=["png", "jpg", "jpeg"],
        key="your_tactic_upload",
    )

    your_path, your_tactic_text = save_and_read_screenshot(your_tactic_upload, "your_tactic")

    if your_path:
        st.image(str(your_path), caption="Your Tactic Screenshot", use_container_width=True)

with col2:
    opponent_tactic_upload = st.file_uploader(
        "Upload OPPOSITION Tactic Screenshot",
        type=["png", "jpg", "jpeg"],
        key="opponent_tactic_upload",
    )

    opponent_path, opponent_tactic_text = save_and_read_screenshot(opponent_tactic_upload, "opponent_tactic")

    if opponent_path:
        st.image(str(opponent_path), caption="Opposition Tactic Screenshot", use_container_width=True)

strength_upload = st.file_uploader(
    "Upload Opposition Strengths / Weaknesses Screenshot",
    type=["png", "jpg", "jpeg"],
    key="strength_upload",
)

strength_path, strength_text = save_and_read_screenshot(strength_upload, "opposition_strengths_weaknesses")

if strength_path:
    st.image(str(strength_path), caption="Opposition Strengths / Weaknesses Screenshot", use_container_width=True)

combined_ocr_text = "\n\n".join(
    [
        "YOUR TACTIC OCR:",
        your_tactic_text,
        "OPPOSITION TACTIC OCR:",
        opponent_tactic_text,
        "OPPOSITION STRENGTHS / WEAKNESSES OCR:",
        strength_text,
    ]
)

detected_formation = detect_formation(opponent_tactic_text + "\n" + strength_text)

if manual_formation == "Use OCR Detection":
    final_formation = detected_formation
else:
    final_formation = manual_formation

st.divider()

st.subheader("OCR Text Reader")

tab_ocr1, tab_ocr2, tab_ocr3 = st.tabs(
    ["Extracted Text", "Correct / Add Notes", "Strengths & Weaknesses Split"]
)

with tab_ocr1:
    st.markdown("### Detected Opposition Formation")
    st.write(final_formation)

    st.markdown("### Raw OCR Text")
    st.text_area(
        "OCR Output",
        value=combined_ocr_text,
        height=350,
        disabled=True,
    )

with tab_ocr2:
    corrected_text = st.text_area(
        "Correct OCR Text Or Add Manual Tactical Notes",
        value=combined_ocr_text,
        height=350,
        help="OCR is not perfect. Fix names, strengths, weaknesses, formations, and notes here.",
    )

with tab_ocr3:
    split_report = split_strengths_weaknesses(corrected_text)

    st.markdown("### Strengths")
    st.write(split_report["strengths"] or "No clear strengths section detected.")

    st.markdown("### Weaknesses")
    st.write(split_report["weaknesses"] or "No clear weaknesses section detected.")

your_df = club_filter(df, your_club)
opponent_df = club_filter(df, opponent_club)

if opponent_df.empty:
    st.warning("No opponent players found.")
    st.stop()

if weak_zone == "Auto / Use Weak Link":
    weakest = opponent_df.sort_values("Weak Link Score", ascending=False).head(1)

    if not weakest.empty:
        weakest_position_col = find_column(opponent_df, ["Position"])
        weakest_position = str(weakest.iloc[0].get(weakest_position_col, "")) if weakest_position_col else ""

        if "D (L)" in weakest_position or "WB (L)" in weakest_position:
            weak_zone = "Left Side"
        elif "D (R)" in weakest_position or "WB (R)" in weakest_position:
            weak_zone = "Right Side"
        elif "D (C)" in weakest_position or "DM" in weakest_position:
            weak_zone = "Central"
        else:
            weak_zone = "Behind Defensive Line"

st.divider()

st.subheader(f"Exploit Plan: {your_club} vs {opponent_club}")

m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Opponent Attack", f"{opponent_df['Attacking Threat'].mean():.1f}")
m2.metric("Creativity", f"{opponent_df['Creative Threat'].mean():.1f}")
m3.metric("Wide Threat", f"{opponent_df['Wide Threat'].mean():.1f}")
m4.metric("Defensive Strength", f"{opponent_df['Defensive Strength'].mean():.1f}")
m5.metric("Press Resistance", f"{opponent_df['Press Resistance'].mean():.1f}")

plan = generate_final_plan(
    ocr_text=corrected_text,
    detected_or_selected_formation=final_formation,
    opponent_df=opponent_df,
    weak_zone=weak_zone,
    match_goal=match_goal,
)

tab1, tab2, tab3, tab4 = st.tabs(
    [
        "Deep Tactical Advice",
        "Opponent Weak Links",
        "Opponent Main Threats",
        "Your Weapons",
    ]
)

with tab1:
    for section, items in plan.items():
        st.markdown(f"### {section}")
        for item in items:
            st.write(f"- {item}")

with tab2:
    display_cols = build_display_cols(
        opponent_df,
        ["Weak Link Score", "Defensive Strength", "Physical Power", "Press Resistance", "Pressing Target Score"],
    )

    st.dataframe(
        opponent_df.sort_values("Weak Link Score", ascending=False)[display_cols].head(10),
        use_container_width=True,
        height=500,
    )

with tab3:
    display_cols = build_display_cols(
        opponent_df,
        ["Overall Danger Score", "Attacking Threat", "Creative Threat", "Wide Threat"],
    )

    st.dataframe(
        opponent_df.sort_values("Overall Danger Score", ascending=False)[display_cols].head(10),
        use_container_width=True,
        height=500,
    )

with tab4:
    if your_df.empty:
        st.info("No players found for your club.")
    else:
        weapon = st.selectbox(
            "Choose Weapon To Exploit Them",
            [
                "Runners In Behind",
                "Creative Passers",
                "Wide 1v1 Threats",
                "Crossers",
                "Pressing Monsters",
            ],
        )

        temp = your_df.copy()
        temp[f"{weapon} Score"] = temp.apply(lambda row: weapon_score(row, weapon), axis=1)

        display_cols = build_display_cols(temp, [f"{weapon} Score"])

        st.dataframe(
            temp.sort_values(f"{weapon} Score", ascending=False)[display_cols].head(10),
            use_container_width=True,
            height=500,
        )

if tactic:
    st.divider()
    st.subheader("Loaded Saved Tactic Context")
    st.json(tactic)
