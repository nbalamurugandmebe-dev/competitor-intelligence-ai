import os
from datetime import datetime

import streamlit as st
from dotenv import load_dotenv
from groq import Groq

load_dotenv(override=True)

st.set_page_config(
    page_title="Competitor Intelligence AI",
    page_icon="📊",
    layout="wide",
)

st.markdown("""
<style>
.stApp {background-color: #f5f7fb;}
.block-container {padding-top: 2rem; max-width: 1200px;}
.hero {
    padding: 28px; border-radius: 16px;
    background: linear-gradient(120deg, #10233f, #175b70);
    color: white; margin-bottom: 24px;
}
.hero h1 {color: white; margin-bottom: 8px;}
.hero p {color: #e0edf5; font-size: 17px;}
div.stButton > button {
    background: #087f8c; color: white; border-radius: 9px;
    border: none; min-height: 45px; font-weight: 600;
}
</style>
<div class="hero">
<h1>📊 Competitor Intelligence AI</h1>
<p>AI-powered competitor research, SWOT analysis, market opportunities and strategic recommendations.</p>
</div>
""", unsafe_allow_html=True)

api_key = os.getenv("GROQ_API_KEY", "").strip()
model = "openai/gpt-oss-20b"

with st.sidebar:
    st.header("⚙️ Research Settings")
    st.write("AI Provider: Groq")
    st.write(f"Model: `{model}`")
    st.caption("Reports are AI-generated. Verify important facts before making business decisions.")

st.subheader("Business Information")
st.write("Enter your business details to generate a competitor intelligence report.")

with st.form("competitor_form"):
    c1, c2 = st.columns(2)
    with c1:
        company = st.text_input("Company Name", placeholder="e.g. Sivakasi Fireworks")
        website = st.text_input("Company Website (optional)", placeholder="https://example.com")
        industry = st.text_input("Industry", placeholder="e.g. Fireworks manufacturing and retail")
    with c2:
        market = st.text_input("Target Market", placeholder="e.g. Tamil Nadu, India")
        competitors = st.text_area(
            "Competitors (comma-separated)",
            placeholder="Competitor A, Competitor B, Competitor C",
            height=100,
        )
        goal = st.text_input(
            "Business Goal",
            placeholder="e.g. Increase sales and improve digital marketing",
        )

    depth = st.select_slider(
        "Report Detail",
        options=["Brief", "Standard", "Detailed"],
        value="Standard",
    )
    submitted = st.form_submit_button("🚀 Generate Competitor Analysis", width="stretch")

if submitted:
    if not api_key:
        st.error("GROQ_API_KEY is missing. Please check your .env file.")
    elif not company.strip() or not industry.strip() or not market.strip() or not competitors.strip():
        st.warning("Please fill in Company Name, Industry, Target Market and Competitors.")
    else:
        competitor_list = [x.strip() for x in competitors.split(",") if x.strip()]
        if not competitor_list:
            st.warning("Please enter at least one competitor.")
            st.stop()

        detail_instructions = {
            "Brief": "Keep each section concise.",
            "Standard": "Give useful detail and practical examples.",
            "Detailed": "Provide a thorough, structured analysis with a prioritized action plan.",
        }

        prompt = f"""
You are a careful business strategy analyst.

Prepare a competitor intelligence report using the information below.
Clearly distinguish known information, assumptions, and items requiring research.
You do not have a web-search tool in this request. Do not pretend you browsed websites.
Do not invent exact prices, market shares, revenue, customer counts, citations, or current facts.
If evidence is unavailable, say "Needs verification" and explain how to verify it.
Treat the company website as user-provided context, not proof that its content was checked.

BUSINESS
Company: {company}
Website: {website or "Not provided"}
Industry: {industry}
Target market: {market}
Competitors: {", ".join(competitor_list)}
Business goal: {goal or "Improve competitive position"}
Report detail: {depth}

Write the report in clear professional English using Markdown and these sections:

# Executive Summary
# Business and Market Context
# Competitor Profiles
For each named competitor, explain potential positioning and clearly flag details that need verification.
# Competitor Comparison
Compare likely customer segments, positioning, product/service differentiation, marketing channels,
strengths and weaknesses. Mark unknowns instead of guessing.
# SWOT Analysis
Separate the company's strengths, weaknesses, opportunities and threats.
# Market Opportunities
Give realistic ideas relevant to the specified industry and target market.
# Marketing Recommendations
Include digital marketing, customer retention, branding and seasonal campaigns where relevant.
# 30-Day Action Plan
Create a table with timeframe, action, expected outcome and success metric.
# Risks and Assumptions
# Research Checklist
List specific public sources and information the business owner should check to validate the report.

End with a short note that this is preliminary AI-generated analysis and current competitor facts need verification.
{detail_instructions[depth]}
"""

        try:
            with st.spinner("Generating your competitor intelligence report..."):
                client = Groq(api_key=api_key)
                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a rigorous business analyst. Never fabricate facts or sources.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    max_completion_tokens=6000,
                    temperature=0.2,
                )
                report = response.choices[0].message.content or ""

            if not report.strip():
                st.error("The model returned an empty report. Please try again.")
            else:
                st.session_state["competitor_report"] = report
                st.session_state["report_company"] = company
                st.session_state["report_time"] = datetime.now().strftime("%Y-%m-%d %H:%M")

        except Exception as exc:
            st.error("The analysis could not be completed.")
            st.code(str(exc))
            st.info("Check the Groq API key, model availability and your current Groq usage limits.")

if st.session_state.get("competitor_report"):
    st.divider()
    st.subheader("📑 Competitor Analysis Report")
    st.caption(
        f"Company: {st.session_state.get('report_company', '')} · "
        f"Generated: {st.session_state.get('report_time', '')}"
    )
    st.markdown(st.session_state["competitor_report"])
    safe_name = "".join(
        ch.lower() if ch.isalnum() else "_"
        for ch in st.session_state.get("report_company", "company")
    ).strip("_")
    st.download_button(
        "⬇️ Download Report (Markdown)",
        data=st.session_state["competitor_report"],
        file_name=f"{safe_name or 'company'}_competitor_report.md",
        mime="text/markdown",
        width="stretch",
    )

st.divider()
st.caption("Competitor Intelligence AI · Groq-powered prototype · Verify important business facts independently.")

