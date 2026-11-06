import pandas as pd
import streamlit as st

from db_storage import load_dataframe
from competitor_scoring import WEIGHTS


def render_executive_dashboard(competitor_names):
    st.title("Executive Competitor Intelligence Dashboard")
    st.caption(
        "A consolidated view of competitor scores and saved research evidence."
    )

    scores_raw = load_dataframe("scores")
    evidence = load_dataframe("evidence")

    score_rows = []
    if not scores_raw.empty and "Competitor" in scores_raw.columns:
        for _, row in scores_raw.iterrows():
            available = []
            for metric, weight in WEIGHTS.items():
                value = row.get(metric)
                if pd.notna(value):
                    try:
                        numeric = float(value)
                        if 0 <= numeric <= 100:
                            available.append((numeric, weight))
                    except (TypeError, ValueError):
                        pass

            if available:
                total_weight = sum(weight for _, weight in available)
                score = sum(value * weight for value, weight in available) / total_weight
                score_rows.append({
                    "Competitor": row["Competitor"],
                    "Provisional Score": round(score, 1),
                    "Evidence Coverage (%)": total_weight,
                })

    scored = pd.DataFrame(score_rows)

    total_competitors = len(competitor_names)
    scored_count = len(scored)
    average_score = (
        scored["Provisional Score"].mean() if not scored.empty else None
    )
    average_coverage = (
        scored["Evidence Coverage (%)"].mean() if not scored.empty else None
    )

    evidence_count = len(evidence)
    if evidence.empty:
        verified_count = 0
        not_verified_count = 0
        source_coverage = 0
    else:
        if "Evidence Quality Check" in evidence.columns:
            quality = (
                evidence["Evidence Quality Check"]
                .fillna("")
                .astype(str)
                .str.strip()
                .str.lower()
            )
            verified_count = int(
                quality.str.contains("verified", regex=False)
                .__and__(~quality.str.contains("not verified", regex=False))
                .sum()
            )
            not_verified_count = int(
                quality.str.contains("not verified", regex=False).sum()
            )
        else:
            verified_count = 0
            not_verified_count = evidence_count

        if "Source URL" in evidence.columns:
            source_coverage = int(
                evidence["Source URL"].fillna("").astype(str).str.strip().ne("").sum()
            )
        else:
            source_coverage = 0

    st.markdown("### Key Performance Indicators")
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Competitors", total_competitors)
    c2.metric("Competitors Scored", scored_count)
    c3.metric(
        "Average Provisional Score",
        f"{average_score:.1f}/100" if average_score is not None else "Not calculated",
    )

    c4, c5, c6 = st.columns(3)
    c4.metric(
        "Average Score Coverage",
        f"{average_coverage:.1f}%" if average_coverage is not None else "Not available",
    )
    c5.metric("Saved Evidence Records", evidence_count)
    c6.metric("Evidence with Source URLs", source_coverage)

    st.divider()
    left, right = st.columns(2)

    with left:
        st.subheader("Competitor Score Comparison")
        if not scored.empty:
            chart = scored.set_index("Competitor")["Provisional Score"]
            st.bar_chart(chart)
            st.dataframe(scored, use_container_width=True, hide_index=True)
        else:
            st.info(
                "No competitor scores are available yet. Add ratings in "
                "Competitor Scoring and calculate scores."
            )

    with right:
        st.subheader("Evidence Validation Overview")
        st.metric("Verified Evidence", verified_count)
        st.metric("Not Verified Evidence", not_verified_count)
        if evidence_count:
            st.caption(
                "Validation counts use the saved Evidence Quality Check field. "
                "A responding URL does not by itself prove a claim is true."
            )
        else:
            st.info(
                "No evidence records are saved yet. Collect evidence in "
                "Evidence & Sources."
            )

    st.divider()
    st.subheader("Research Data Summary")
    summary = pd.DataFrame([
        {"Data Category": "Competitor score records", "Saved Records": len(scores_raw)},
        {"Data Category": "Evidence records", "Saved Records": evidence_count},
        {"Data Category": "Evidence records with source URLs", "Saved Records": source_coverage},
    ])
    st.dataframe(summary, use_container_width=True, hide_index=True)

    st.caption(
        "Scores are provisional and depend on manually entered ratings. "
        "Evidence validation is a basic source check, not independent fact verification."
    )
