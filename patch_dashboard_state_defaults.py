from pathlib import Path

path = Path("app/dashboard.py")
text = path.read_text(encoding="utf-8")

old = """for key in PERSIST_KEYS:
    restore_session_value(st.session_state, page_state, key)
"""

new = """DEFAULT_SESSION_VALUES = {
    "dashboard_selected_leagues": [],
    "dashboard_selected_lines": [],
    "dashboard_selected_groups": [],
    "dashboard_selected_positions": [],
    "dashboard_selected_raw_positions": [],
    "dashboard_selected_clubs": [],
    "dashboard_pick_attributes": [],
    "dashboard_name_search": "",
    "dashboard_attribute_condition": "Is At Least",
    "dashboard_attribute_value": 12,
    "dashboard_attribute_match_mode": "Match ALL selected attributes",
    "dashboard_active_view": "Full Organized View",
}

for key in PERSIST_KEYS:
    restore_session_value(
        st.session_state,
        page_state,
        key,
        DEFAULT_SESSION_VALUES.get(key, "__NO_DEFAULT__"),
    )

for key, value in DEFAULT_SESSION_VALUES.items():
    if st.session_state.get(key) is None:
        st.session_state[key] = value
"""

if old not in text:
    print("Could not find old restore block. No patch made.")
else:
    text = text.replace(old, new)
    path.write_text(text, encoding="utf-8")
    print("Dashboard state defaults patched.")
