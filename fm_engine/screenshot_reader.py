from __future__ import annotations

import re
from pathlib import Path

from PIL import Image, ImageFilter, ImageOps

try:
    import cv2
    import numpy as np
except ImportError:
    cv2 = None
    np = None

try:
    import pytesseract
except ImportError:
    pytesseract = None


TESSERACT_WINDOWS_PATHS = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
]


def setup_tesseract() -> None:
    if pytesseract is None:
        return

    for path_text in TESSERACT_WINDOWS_PATHS:
        path = Path(path_text)
        if path.exists():
            pytesseract.pytesseract.tesseract_cmd = str(path)
            return


def clean_ocr_text(text: str) -> str:
    text = text.replace("\x0c", " ")
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


def preprocess_image_for_ocr(image_path: str | Path) -> Path:
    image_path = Path(image_path)
    output_dir = image_path.parent / "ocr_processed"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / f"{image_path.stem}_ocr.png"

    if cv2 is not None and np is not None:
        image = cv2.imread(str(image_path))

        if image is not None:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            gray = cv2.resize(gray, None, fx=2.5, fy=2.5, interpolation=cv2.INTER_CUBIC)
            gray = cv2.medianBlur(gray, 3)

            thresh = cv2.adaptiveThreshold(
                gray,
                255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY,
                31,
                11,
            )

            cv2.imwrite(str(output_path), thresh)
            return output_path

    image = Image.open(image_path).convert("RGB")
    image = ImageOps.grayscale(image)
    image = image.resize((image.width * 2, image.height * 2))
    image = ImageOps.autocontrast(image)
    image = image.filter(ImageFilter.SHARPEN)
    image.save(output_path)

    return output_path


def extract_text_from_image(image_path: str | Path) -> str:
    if pytesseract is None:
        return "OCR package not installed. Run: python -m pip install pytesseract pillow opencv-python"

    setup_tesseract()

    processed_path = preprocess_image_for_ocr(image_path)
    image = Image.open(processed_path)

    config_primary = "--oem 3 --psm 6"
    text = pytesseract.image_to_string(image, config=config_primary)

    if len(text.strip()) < 20:
        config_backup = "--oem 3 --psm 11"
        text = pytesseract.image_to_string(image, config=config_backup)

    return clean_ocr_text(text)


def detect_formation(text: str) -> str:
    lower = text.lower()

    patterns = [
        ("4-2-3-1", [r"4[- ]?2[- ]?3[- ]?1"]),
        ("4-3-3 DM Wide", [r"4[- ]?3[- ]?3", r"dm wide"]),
        ("4-4-2", [r"4[- ]?4[- ]?2"]),
        ("4-4-1-1", [r"4[- ]?4[- ]?1[- ]?1"]),
        ("4-1-4-1", [r"4[- ]?1[- ]?4[- ]?1"]),
        ("3-5-2", [r"3[- ]?5[- ]?2", r"5[- ]?3[- ]?2"]),
        ("3-4-2-1", [r"3[- ]?4[- ]?2[- ]?1"]),
        ("3-4-3", [r"3[- ]?4[- ]?3", r"5[- ]?2[- ]?3"]),
    ]

    for formation, regexes in patterns:
        for pattern in regexes:
            if re.search(pattern, lower):
                return formation

    return "Unknown / Not Sure"


def split_strengths_weaknesses(text: str) -> dict[str, str]:
    clean = text.strip()
    lower = clean.lower()

    strength_markers = ["strengths", "strength", "strong at", "good at", "pros"]
    weakness_markers = ["weaknesses", "weakness", "weak at", "bad at", "vulnerable", "cons"]

    strength_index = -1
    weakness_index = -1

    for marker in strength_markers:
        idx = lower.find(marker)
        if idx != -1:
            strength_index = idx
            break

    for marker in weakness_markers:
        idx = lower.find(marker)
        if idx != -1:
            weakness_index = idx
            break

    strengths = ""
    weaknesses = ""

    if strength_index != -1 and weakness_index != -1:
        if strength_index < weakness_index:
            strengths = clean[strength_index:weakness_index].strip()
            weaknesses = clean[weakness_index:].strip()
        else:
            weaknesses = clean[weakness_index:strength_index].strip()
            strengths = clean[strength_index:].strip()
    elif strength_index != -1:
        strengths = clean[strength_index:].strip()
    elif weakness_index != -1:
        weaknesses = clean[weakness_index:].strip()

    return {
        "strengths": strengths,
        "weaknesses": weaknesses,
        "full_text": clean,
    }


def keyword_hits(text: str) -> dict[str, list[str]]:
    lower = text.lower()

    keyword_map = {
        "wide_attack": ["wide", "wings", "flanks", "cross", "crosses", "wingers", "overlap"],
        "central_attack": ["through the middle", "central", "playmaker", "number 10", "amc", "zone 14"],
        "pace_in_behind": ["pace", "speed", "runs in behind", "space behind", "through balls", "counter attack"],
        "aerial": ["aerial", "heading", "headers", "crosses", "set pieces", "corners"],
        "high_press": ["high press", "pressing", "counter-press", "aggressive press", "wins possession"],
        "low_block": ["low block", "deep", "compact", "sits back", "defensive"],
        "poor_press_resistance": ["mistakes under pressure", "poor press resistance", "loses possession", "turnovers"],
        "weak_wide_defense": ["weak on the flanks", "vulnerable wide", "crosses conceded", "weak fullbacks"],
        "weak_central_defense": ["space between lines", "poor marking", "central weakness", "vulnerable through middle"],
        "weak_physical": ["weak physical", "lacks strength", "poor aerial", "weak in air", "low strength"],
        "weak_transition": ["vulnerable to counters", "slow recovery", "countered", "space in transition"],
        "poor_finishing": ["poor finishing", "struggles to score", "low xg", "few shots"],
    }

    hits = {}

    for category, keywords in keyword_map.items():
        found = [keyword for keyword in keywords if keyword in lower]
        if found:
            hits[category] = found

    return hits


def build_ocr_tactical_advice(text: str) -> dict[str, list[str]]:
    hits = keyword_hits(text)

    advice = {
        "What The Screenshot Says": [],
        "How To Protect Against Their Strengths": [],
        "How To Exploit Their Weaknesses": [],
        "Specific Tactical Tweaks": [],
        "Pressing Triggers": [],
        "Chance Creation Plan": [],
    }

    if not text.strip():
        advice["What The Screenshot Says"].append("No readable OCR text was detected. Try a clearer screenshot or paste the report manually.")
        return advice

    advice["What The Screenshot Says"].append("The app read the screenshot text and converted the key phrases into tactical recommendations.")

    if "wide_attack" in hits:
        advice["How To Protect Against Their Strengths"].append(
            "They may create danger wide. Stop crosses early, protect fullbacks with winger support, and avoid leaving your wide defenders 1v2."
        )

    if "central_attack" in hits:
        advice["How To Protect Against Their Strengths"].append(
            "They may create through the middle. Use a DM screen, defend narrower, and deny their playmaker free touches in Zone 14."
        )

    if "pace_in_behind" in hits:
        advice["How To Protect Against Their Strengths"].append(
            "They threaten space behind. Avoid an extreme high line unless your press is strong. Keep rest-defense secure."
        )

    if "aerial" in hits:
        advice["How To Protect Against Their Strengths"].append(
            "They may be dangerous aerially or from set pieces. Stop wide service, assign strong aerial markers, and protect the far post."
        )

    if "high_press" in hits:
        advice["How To Protect Against Their Strengths"].append(
            "They press aggressively. Use your goalkeeper, center backs, and DM as a buildup triangle, then release quickly into the open side."
        )

    if "low_block" in hits:
        advice["Specific Tactical Tweaks"].append(
            "If they defend deep, do not force central passes. Use width, switches of play, overlaps, cutbacks, and patient circulation."
        )

    if "poor_press_resistance" in hits:
        advice["Pressing Triggers"].append(
            "They struggle under pressure. Press backward passes, poor first touches, and passes into fullbacks or weaker center backs."
        )

    if "weak_wide_defense" in hits:
        advice["How To Exploit Their Weaknesses"].append(
            "Attack their wide defensive weakness. Build 2v1 or 3v2 overloads with winger, fullback, and near-side midfielder."
        )
        advice["Chance Creation Plan"].append(
            "Best pattern: overload wide → pull their fullback out → attack half-space → cutback or low cross."
        )

    if "weak_central_defense" in hits:
        advice["How To Exploit Their Weaknesses"].append(
            "Attack the space between their midfield and defensive line. Use an AM, false nine, or advanced playmaker to receive between lines."
        )

    if "weak_physical" in hits:
        advice["How To Exploit Their Weaknesses"].append(
            "They may lack physical power. Raise tempo, attack duels, use runners, and test them with crosses or direct balls depending on your squad."
        )

    if "weak_transition" in hits:
        advice["How To Exploit Their Weaknesses"].append(
            "They are vulnerable in transition. Win the ball and attack quickly before their shape resets."
        )
        advice["Chance Creation Plan"].append(
            "Best pattern: regain possession → first forward pass → runner behind fullback/center back channel."
        )

    if "poor_finishing" in hits:
        advice["Specific Tactical Tweaks"].append(
            "If they struggle to finish, you can be more patient and force them into low-quality shots, but do not give up central transitions."
        )

    if not any(items for section, items in advice.items() if section != "What The Screenshot Says"):
        advice["Specific Tactical Tweaks"].append(
            "The OCR text was readable, but no strong tactical keywords were detected. Paste the strengths and weaknesses into the manual notes box for deeper advice."
        )

    return advice
