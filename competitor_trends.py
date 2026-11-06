from datetime import datetime
import pandas as pd
import streamlit as st

from db_storage import load_dataframe, save_dataframe
from competitor_scoring import WEIGHTS


def render_competitor_trends(competitor_names):
    st.title("Competitor Trend Tracking")
    st.caption("Track how competitor strength scores change across saved snapshots.")

    scores = load_dataframe("scores")
    history = load_dataframe("score_history")

    if scores.empty:
        st.info("No competitor scores found. Enter scores in Competitor Scoring first.")
        return

    total_weight = sum(WEIGHTS.values())
    current_rows = []

    for _, row in scores.iterrows():
        competitor = str(row.get("Competitor", "")).strip()
        if not competitor:
            continue

        weighted_total = 0.0
        available_weight = 0

        for metric, weight in WEIGHTS.items():
            value = pd.to_numeric(
                pd.Series([row.get(metric)]), errors="coerce"
            ).iloc[0]

            if pd.notna(value):
                weighted_total += float(value) * weight
                available_weight += weight

        if available_weight > 0:
            current_rows.append({
                "Competitor": competitor,
                "Score": round(weighted_total / available_weight, 2),
                "Coverage": round(available_weight / total_weight * 100, 1),
            })

    current = pd.DataFrame(current_rows)

    if current.empty:
        st.warning(
            "No numeric scores are available yet. Open Competitor Scoring, "
            "enter ratings from 0 to 100, and save them first."
        )
        return

    st.subheader("Current Competitor Scores")
    st.dataframe(current, use_container_width=True, hide_index=True)

    if st.button("Capture Current Scores", type="primary"):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        new_rows = current.copy()
        new_rows["Timestamp"] = timestamp

        if history.empty:
            history = new_rows[["Timestamp", "Competitor", "Score", "Coverage"]]
        else:
            history = pd.concat(
                [history, new_rows[["Timestamp", "Competitor", "Score", "Coverage"]]],
                ignore_index=True
            )

        save_dataframe("score_history", history)
        st.success("Current scores saved to trend history.")
        st.rerun()

    history = load_dataframe("score_history")

    st.divider()
    st.subheader("Score Trend History")

    if history.empty:
        st.info("No snapshots captured yet. Click 'Capture Current Scores' to begin.")
        return

    history["Score"] = pd.to_numeric(history["Score"], errors="coerce")
    history["Timestamp"] = pd.to_datetime(history["Timestamp"], errors="coerce")
    history = history.dropna(subset=["Timestamp", "Score"])

    available_competitors = sorted(history["Competitor"].dropna().unique().tolist())
    selected = st.multiselect(
        "Choose competitors to compare",
        available_competitors,
        default=available_competitors
    )

    filtered = history[history["Competitor"].isin(selected)].copy()

    if filtered.empty:
        st.info("Select at least one competitor with saved history.")
        return

    chart_data = filtered.pivot_table(
        index="Timestamp",
        columns="Competitor",
        values="Score",
        aggfunc="last"
    ).sort_index()

    st.line_chart(chart_data)
    st.dataframe(
        filtered.sort_values("Timestamp", ascending=False),
        use_container_width=True,
        hide_index=True
    )

    st.caption(
        "Scores are provisional weighted ratings based on manually entered values. "
        "A trend becomes meaningful after multiple snapshots."
    )
