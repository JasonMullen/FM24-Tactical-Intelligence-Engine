from pathlib import Path
import re

path = Path("app/pages/11_Recommended_Signings.py")
text = path.read_text(encoding="utf-8")

old_return_block = '''    recommendations = pd.DataFrame(candidate_rows)

    if recommendations.empty:
        return recommendations

    recommendations = recommendations.sort_values("Recommendation Score", ascending=False)
    recommendations = recommendations.drop_duplicates(subset=["Player", "Club"], keep="first")
    recommendations = recommendations.head(top_n).reset_index(drop=True)
    recommendations.insert(0, "Rank", recommendations.index + 1)

    return recommendations
'''

new_return_block = '''    recommendations = pd.DataFrame(candidate_rows)

    if recommendations.empty:
        return recommendations

    gap_priority_order = {
        row["Squad Area"]: index + 1
        for index, row in current_gaps.reset_index(drop=True).iterrows()
    }

    gap_value_map = {
        row["Squad Area"]: row["Gap To Target"]
        for _, row in current_gaps.iterrows()
    }

    priority_map = {
        row["Squad Area"]: row["Priority"]
        for _, row in current_gaps.iterrows()
    }

    recommendations["Gap Priority Order"] = recommendations["Recommended For"].map(gap_priority_order).fillna(99).astype(int)
    recommendations["Squad Gap Value"] = recommendations["Recommended For"].map(gap_value_map).fillna(0)
    recommendations["Squad Gap Priority"] = recommendations["Recommended For"].map(priority_map).fillna("Depth / Optional")

    recommendations = recommendations.sort_values(
        ["Gap Priority Order", "Recommendation Score"],
        ascending=[True, False],
    )

    # Keep unique players inside each specific squad gap.
    recommendations = recommendations.drop_duplicates(
        subset=["Recommended For", "Player", "Club"],
        keep="first",
    )

    # Top N options per squad gap.
    recommendations["Gap Rank"] = (
        recommendations
        .groupby("Recommended For")
        .cumcount()
        + 1
    )

    recommendations = recommendations[
        recommendations["Gap Rank"] <= top_n
    ].copy()

    recommendations = recommendations.sort_values(
        ["Gap Priority Order", "Gap Rank", "Recommendation Score"],
        ascending=[True, True, False],
    ).reset_index(drop=True)

    recommendations.insert(0, "Overall Row", recommendations.index + 1)

    return recommendations
'''

if old_return_block not in text:
    raise SystemExit("Could not find the recommendation return block. No patch made.")

text = text.replace(old_return_block, new_return_block)

text = text.replace(
'''top_n = st.sidebar.slider(
    "Number Of Recommended Signings",
    min_value=5,
    max_value=50,
    value=5,
    step=5,
)
''',
'''top_n = st.sidebar.slider(
    "Top Options Per Squad Gap",
    min_value=3,
    max_value=20,
    value=5,
    step=1,
)
'''
)

start = text.find("with tab1:")
end = text.find("with tab2:")

if start == -1 or end == -1 or end <= start:
    raise SystemExit("Could not find tab1/tab2 block. No patch made.")

new_tab1 = r'''with tab1:
    st.subheader("Top Recommended Signings By Squad Gap")

    st.write(
        """
        This section now gives you the best signing options for each specific squad gap.
        For example, if your biggest gaps are Striker, Winger, and Defender, you will get
        a separate top 5 list for each one.
        """
    )

    if recommendations.empty:
        st.warning("No recommendations found. Try lowering minimum minutes, increasing max age, or removing the value cap.")
    else:
        gap_summary_cols = [
            "Squad Area",
            "Current Rating",
            "Target Rating",
            "Gap To Target",
            "Priority",
        ]

        gap_summary_cols = [col for col in gap_summary_cols if col in current_gaps.columns]

        st.markdown("### Squad Gap Priority")
        st.dataframe(
            make_streamlit_safe_df(current_gaps[gap_summary_cols]),
            use_container_width=True,
            height=280,
        )

        st.markdown("### Top Options For Each Gap")

        main_cols = [
            "Gap Rank",
            "Player",
            "Age",
            "Club",
            "League",
            "Position",
            "Recommended For",
            "Recommendation Score",
            "Candidate Category Rating",
            "Candidate Attribute Fit",
            "Candidate Statistical Fit",
            "Playstyle Fit",
            "Upgrade Over Current Area",
            "Gap Covered %",
            "Estimated Value",
            "Why Recommended",
        ]

        main_cols = [col for col in main_cols if col in recommendations.columns]

        ordered_gaps = current_gaps["Squad Area"].tolist()

        available_gaps = [
            gap for gap in ordered_gaps
            if gap in recommendations["Recommended For"].astype(str).unique().tolist()
        ]

        if not available_gaps:
            available_gaps = recommendations["Recommended For"].dropna().astype(str).unique().tolist()

        for index, gap in enumerate(available_gaps):
            gap_recs = recommendations[
                recommendations["Recommended For"].astype(str) == str(gap)
            ].copy()

            if gap_recs.empty:
                continue

            gap_row = current_gaps[
                current_gaps["Squad Area"].astype(str) == str(gap)
            ]

            if not gap_row.empty:
                current_rating = gap_row.iloc[0].get("Current Rating", "")
                target_rating = gap_row.iloc[0].get("Target Rating", "")
                gap_value = gap_row.iloc[0].get("Gap To Target", "")
                priority = gap_row.iloc[0].get("Priority", "")
                title = f"{gap} — Gap: {gap_value} | Current: {current_rating} | Target: {target_rating} | {priority}"
            else:
                title = str(gap)

            with st.expander(title, expanded=index < 3):
                st.dataframe(
                    make_streamlit_safe_df(gap_recs[main_cols]),
                    use_container_width=True,
                    height=360,
                )

        st.markdown("### Full Recommended Signing List")

        st.dataframe(
            make_streamlit_safe_df(recommendations[main_cols]),
            use_container_width=True,
            height=500,
        )

        st.download_button(
            label="Download Recommended Signings By Gap CSV",
            data=make_streamlit_safe_df(recommendations).to_csv(index=False).encode("utf-8"),
            file_name=f"{your_club.replace(' ', '_')}_recommended_signings_by_gap.csv",
            mime="text/csv",
        )

'''

text = text[:start] + new_tab1 + text[end:]

path.write_text(text, encoding="utf-8")
print("Recommended Signings now gives top options for each squad gap.")
