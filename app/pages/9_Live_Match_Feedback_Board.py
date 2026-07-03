from __future__ import annotations

import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st
from fm_engine.ui_memory import init_page_memory, save_page_memory
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[2]
LIVE_DIR = PROJECT_ROOT / "outputs" / "live_match_frames"
LIVE_DIR.mkdir(parents=True, exist_ok=True)

try:
    import mss
except ImportError:
    mss = None


# ============================================================
# SCREEN CAPTURE
# ============================================================

def capture_screen_frame() -> Path:
    if mss is None:
        raise RuntimeError("mss is not installed. Run: python -m pip install mss pillow")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    frame_path = LIVE_DIR / f"frame_{timestamp}.png"

    with mss.mss() as sct:
        monitor = sct.monitors[1]
        screenshot = sct.grab(monitor)
        image = Image.frombytes("RGB", screenshot.size, screenshot.rgb)
        image.save(frame_path)

    return frame_path


def capture_frame_sequence(duration_seconds: int, interval_seconds: int) -> list[Path]:
    frames = []
    end_time = time.time() + duration_seconds

    while time.time() < end_time:
        frame = capture_screen_frame()
        frames.append(frame)
        time.sleep(interval_seconds)

    return frames


# ============================================================
# LIVE TACTICAL FEEDBACK
# ============================================================

def generate_live_feedback(
    minute: int,
    score_state: str,
    xg_for: float,
    xg_against: float,
    shots_for: int,
    shots_against: int,
    current_issue: list[str],
    danger_zone: str,
    risk_level: str,
) -> list[str]:
    feedback = []

    if xg_against > xg_for + 0.5:
        feedback.append("Opponent is creating better chances. Reduce risk, protect central space, and stop transition attacks.")

    if shots_against >= shots_for + 5:
        feedback.append("Opponent shot volume is too high. Press the ball carrier earlier or drop into a more compact block.")

    if "Opponent overloading wide areas" in current_issue:
        feedback.append("Wide overload detected. Defend wider, make your winger support the fullback, and stop crosses.")

    if "Opponent playing through the middle" in current_issue:
        feedback.append("Central progression issue. Add a DM screen, defend narrower, and press their playmaker.")

    if "We cannot progress the ball" in current_issue:
        feedback.append("Buildup issue. Add a deeper playmaker, lower tempo, and create a safe passing triangle near the ball.")

    if "Striker isolated" in current_issue:
        feedback.append("Striker is isolated. Move an attacking midfielder closer or change the striker to a support role.")

    if "We are getting countered" in current_issue:
        feedback.append("Counterattack danger. Keep one fullback on defend, use a holding midfielder, and reduce risky passes.")

    if "Opponent pressing high" in current_issue:
        feedback.append("Opponent press is high. Use goalkeeper distribution to wide defenders or pass into space behind the press.")

    if danger_zone == "Left Side":
        feedback.append("Danger is coming from your left side. Give your LB help, shift midfield left, and reduce attacking duty on that side.")

    if danger_zone == "Right Side":
        feedback.append("Danger is coming from your right side. Give your RB help, shift midfield right, and reduce attacking duty on that side.")

    if danger_zone == "Central":
        feedback.append("Danger is central. Protect Zone 14, use a DM, and deny through balls.")

    if score_state == "Winning" and minute >= 70:
        feedback.append("You are winning late. Lower tempo, protect rest-defense, and avoid unnecessary fullback risk.")

    if score_state == "Losing" and minute >= 65:
        feedback.append("You are losing late. Increase tempo, add a runner, and target the opponent's weakest side.")

    if risk_level == "Aggressive":
        feedback.append("Aggressive risk selected. Push for chances, but monitor counters and keep at least 2 players back.")

    if risk_level == "Conservative":
        feedback.append("Conservative risk selected. Prioritize structure, shorter passing, and defensive balance.")

    if not feedback:
        feedback.append("No major issue detected from the current inputs. Keep monitoring shot quality, overloads, and transition danger.")

    return feedback


# ============================================================
# STREAMLIT APP
# ============================================================

st.set_page_config(
    page_title="Live Match Feedback Board",
    page_icon="🎥",
    layout="wide",
)

init_page_memory(__file__)

st.title("Live Match Feedback Board")

st.write(
    """
    This is the first local live-analysis board. It can capture your screen locally and give tactical feedback
    based on live match-state inputs. Full computer-vision reading of FM will come later.
    """
)

if mss is None:
    st.warning("mss is not installed. Run: python -m pip install mss pillow")

st.sidebar.header("Screen Capture")

if st.sidebar.button("Capture Current Screen"):
    try:
        frame_path = capture_screen_frame()
        st.sidebar.success(f"Captured: {frame_path.name}")
        st.image(str(frame_path), caption="Latest Captured Frame", use_container_width=True)
    except Exception as error:
        st.sidebar.error(str(error))

duration = st.sidebar.slider("Recording Duration Seconds", 10, 120, 30, step=10)
interval = st.sidebar.slider("Capture Every X Seconds", 2, 15, 5, step=1)

if st.sidebar.button("Record Frame Sequence"):
    try:
        progress = st.progress(0)
        frames = []
        steps = max(1, duration // interval)

        for i in range(steps):
            frame = capture_screen_frame()
            frames.append(frame)
            progress.progress((i + 1) / steps)
            time.sleep(interval)

        st.sidebar.success(f"Captured {len(frames)} frames.")

        if frames:
            st.image(str(frames[-1]), caption="Latest Captured Frame", use_container_width=True)

    except Exception as error:
        st.sidebar.error(str(error))

st.sidebar.divider()
st.sidebar.header("Live Match State")

minute = st.sidebar.slider("Minute", 1, 120, 45)
score_state = st.sidebar.selectbox("Score State", ["Drawing", "Winning", "Losing"])
risk_level = st.sidebar.selectbox("Risk Level", ["Balanced", "Conservative", "Aggressive"])

xg_for = st.sidebar.number_input("xG For", min_value=0.0, value=0.5, step=0.1)
xg_against = st.sidebar.number_input("xG Against", min_value=0.0, value=0.5, step=0.1)

shots_for = st.sidebar.number_input("Shots For", min_value=0, value=5, step=1)
shots_against = st.sidebar.number_input("Shots Against", min_value=0, value=5, step=1)

danger_zone = st.sidebar.selectbox(
    "Main Danger Zone",
    ["None", "Left Side", "Right Side", "Central", "Behind Defensive Line"],
)

current_issue = st.sidebar.multiselect(
    "What is happening right now?",
    [
        "Opponent overloading wide areas",
        "Opponent playing through the middle",
        "We cannot progress the ball",
        "Striker isolated",
        "We are getting countered",
        "Opponent pressing high",
        "We are taking low-quality shots",
        "We are losing midfield",
    ],
)

st.subheader("Live Tactical Feedback")

feedback = generate_live_feedback(
    minute=minute,
    score_state=score_state,
    xg_for=xg_for,
    xg_against=xg_against,
    shots_for=shots_for,
    shots_against=shots_against,
    current_issue=current_issue,
    danger_zone=danger_zone,
    risk_level=risk_level,
)

for item in feedback:
    st.write(f"- {item}")

st.divider()

st.subheader("Captured Frames Folder")

st.code(str(LIVE_DIR))

recent_frames = sorted(LIVE_DIR.glob("*.png"), key=lambda path: path.stat().st_mtime, reverse=True)[:5]

if recent_frames:
    st.write("Recent captured frames:")
    for frame in recent_frames:
        st.image(str(frame), caption=frame.name, use_container_width=True)
else:
    st.info("No frames captured yet.")

save_page_memory(__file__)
