import pandas as pd
import streamlit as st
from db_storage import load_dataframe, save_dataframe

WEIGHTS = {
    "Search visibility": 25,
    "Reputation": 20,
    "Paid activity": 15,
    "Keyword strategy": 15,
    "Social presence": 10,
    "Website quality": 10,
    "Local presence": 5,
}


INDUSTRY_GUIDANCE = {
    "Fireworks Manufacturing and Retail": {
        "Reputation": "Product safety reputation, customer feedback and brand trust.",
        "Website quality": "Product catalogue, safety information, contact details and usability.",
        "Local presence": "Manufacturing facilities, authorised dealers and local distribution."
    },
    "Restaurant & Food": {
        "Reputation": "Customer reviews, food quality feedback, ratings and service reputation.",
        "Website quality": "Menu, ordering options, location details and mobile usability.",
        "Local presence": "Restaurant locations, delivery coverage and local listings."
    },
    "Textile & Fashion": {
        "Reputation": "Product quality feedback, brand trust and customer reviews.",
        "Website quality": "Product catalogue, images, size information and shopping experience.",
        "Local presence": "Retail outlets, showrooms and distribution availability."
    },
    "Mobile & Electronics": {
        "Reputation": "Product reviews, after-sales feedback and warranty reputation.",
        "Website quality": "Product specifications, comparison information and support details.",
        "Local presence": "Retail stores, service centres and authorised dealers."
    },
    "Real Estate": {
        "Reputation": "Buyer feedback, project credibility and customer service.",
        "Website quality": "Property listings, project details, images and enquiry facilities.",
        "Local presence": "Project locations, office presence and local property coverage."
    },
    "Education & Training": {
        "Reputation": "Learner reviews, course feedback and educational credibility.",
        "Website quality": "Course details, faculty information, learning options and admissions.",
        "Local presence": "Campus locations, training centres and regional accessibility."
    },
    "Beauty & Cosmetics": {
        "Reputation": "Customer product feedback, brand trust and service reviews.",
        "Website quality": "Product details, ingredients, usage information and shopping experience.",
        "Local presence": "Retail availability, salons and authorised sellers."
    },
    "Healthcare": {
        "Reputation": "Patient feedback, verified credentials and service reputation.",
        "Website quality": "Service information, appointment access and provider credentials.",
        "Local presence": "Clinic locations, facilities and service availability."
    },
    "Automobile": {
        "Reputation": "Owner feedback, vehicle reliability reviews and after-sales service.",
        "Website quality": "Vehicle specifications, model information and booking facilities.",
        "Local presence": "Showrooms, service centres and authorised dealers."
    },
    "E-commerce & Retail": {
        "Reputation": "Customer reviews, product feedback and service reliability.",
        "Website quality": "Product discovery, checkout experience, delivery and return information.",
        "Local presence": "Stores, delivery coverage and fulfilment locations."
    }
}

def get_industry_guidance(industry):
    return INDUSTRY_GUIDANCE.get(industry, {
        "Reputation": "Customer feedback, reviews and brand trust.",
        "Website quality": "Relevant content, usability, functionality and accessibility.",
        "Local presence": "Business locations, contact details and regional availability."
    })


def render_competitor_scoring(competitor_names, industry='Fireworks Manufacturing and Retail'):
    st.divider()
    st.subheader("Competitor Strength Score")
    st.caption(
        f"Industry: {industry}. Enter evidence-based ratings from 0 to 100. "
        "Leave unknown metrics blank. Scores are provisional."
    )

    guidance = get_industry_guidance(industry)
    with st.expander("Industry-specific scoring guidance", expanded=True):
        for metric, description in guidance.items():
            st.markdown(f"**{metric}:** {description}")

    st.markdown(
        "**Scoring weights:** Search visibility 25%, Reputation 20%, "
        "Paid activity 15%, Keyword strategy 15%, Social presence 10%, "
        "Website quality 10%, Local presence 5%."
    )

    names = list(dict.fromkeys(
        str(name).strip() for name in competitor_names if str(name).strip()
    ))

    if not names:
        st.info("Select competitor results above to begin scoring.")
        return

    state_key = "competitor_strength_score_editor"
    if state_key not in st.session_state:
        saved_scores = load_dataframe("scores")
        if not saved_scores.empty and "Competitor" in saved_scores.columns:
            old = saved_scores[saved_scores["Competitor"].isin(names)].copy()
            existing = set(old["Competitor"])
            missing = [name for name in names if name not in existing]
            if missing:
                additions = {"Competitor": missing}
                for metric in WEIGHTS:
                    additions[metric] = [None] * len(missing)
                old = pd.concat([old, pd.DataFrame(additions)], ignore_index=True)
            st.session_state[state_key] = old
        else:
            data = {"Competitor": names}
            for metric in WEIGHTS:
                data[metric] = [None] * len(names)
            st.session_state[state_key] = pd.DataFrame(data)
    else:
        old = st.session_state[state_key].copy()
        old = old[old["Competitor"].isin(names)]
        existing = set(old["Competitor"])
        missing = [n for n in names if n not in existing]
        if missing:
            add = {"Competitor": missing}
            for metric in WEIGHTS:
                add[metric] = [None] * len(missing)
            old = pd.concat([old, pd.DataFrame(add)], ignore_index=True)
        st.session_state[state_key] = old

    edited = st.data_editor(
        st.session_state[state_key],
        width="stretch",
        hide_index=True,
        num_rows="fixed",
        disabled=["Competitor"],
        column_config={
            "Competitor": st.column_config.TextColumn("Competitor"),
            **{
                metric: st.column_config.NumberColumn(
                    metric,
                    min_value=0,
                    max_value=100,
                    step=1,
                    help=f"Evidence-based rating. Weight: {weight}%. Leave blank if unknown."
                )
                for metric, weight in WEIGHTS.items()
            }
        },
        key="competitor_strength_score_table",
    )
    st.session_state[state_key] = edited
    save_dataframe("scores", edited)

    if not st.button("Calculate Score", key="calculate_competitor_scores", type="primary", width="stretch"):
        st.info("Enter evidence-based ratings, then click Calculate Score.")
        return

    scored_rows = []
    for _, row in edited.iterrows():
        available = [
            (metric, weight, row[metric])
            for metric, weight in WEIGHTS.items()
            if pd.notna(row[metric])
        ]
        if not available:
            continue

        total_weight = sum(weight for _, weight, _ in available)
        score = sum(
            float(value) * weight for _, weight, value in available
        ) / total_weight
        coverage = total_weight

        scored_rows.append({
            "Competitor": row["Competitor"],
            "Provisional Score (0-100)": round(score, 1),
            "Evidence Coverage (%)": coverage,
            "Metrics Rated": len(available),
            "Metrics Missing": len(WEIGHTS) - len(available),
        })

    if scored_rows:
        scores = pd.DataFrame(scored_rows).sort_values(
            "Provisional Score (0-100)", ascending=False
        )
        st.markdown("#### Comparison Dashboard")
        c1, c2 = st.columns(2)
        c1.metric("Competitors scored", len(scores))
        c2.metric(
            "Average provisional score",
            f"{scores['Provisional Score (0-100)'].mean():.1f}/100"
        )
        st.dataframe(scores, width="stretch", hide_index=True)
        chart_data = scores.set_index("Competitor")[
            "Provisional Score (0-100)"
        ]
        st.bar_chart(chart_data)
        st.download_button(
            "Download competitor strength scores CSV",
            scores.to_csv(index=False).encode("utf-8-sig"),
            file_name="competitor_strength_scores.csv",
            mime="text/csv",
            width="stretch",
        )
        st.caption(
            "Scores are provisional, not independently verified rankings. "
            "Missing metrics are excluded and the remaining weights are "
            "renormalized. Evidence coverage shows how much of the original "
            "weight was rated."
        )
    else:
        st.info(
            "Enter at least one evidence-based rating for a competitor "
            "to calculate a provisional score."
        )

