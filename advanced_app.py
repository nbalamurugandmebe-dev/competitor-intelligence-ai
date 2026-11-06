import os
import re
from datetime import datetime
from urllib.parse import urlparse

import streamlit as st
import pandas as pd
from db_storage import load_dataframe, save_dataframe
from dotenv import load_dotenv
from ddgs import DDGS
from groq import Groq
from competitor_discovery import render_competitor_discovery
from competitor_scoring import render_competitor_scoring
from competitor_evidence import render_competitor_evidence
from dashboard import render_executive_dashboard
from competitor_trends import render_competitor_trends
from competitor_auto_scoring import render_automated_scoring
from pdf_report import build_pdf_report

load_dotenv()

MODEL = "openai/gpt-oss-20b"

st.set_page_config(
    page_title="Advanced Marketing Intelligence",
    page_icon="ðŸŽ¯",
    layout="wide"
)

st.markdown("""
<style>
.stApp {
    background: linear-gradient(135deg,#07111f,#101c32,#17132d);
    color: #edf5ff;
}
[data-testid="stHeader"] { background: rgba(7,17,31,.85); }
[data-testid="stSidebar"] {
    background: linear-gradient(180deg,#0d1b2e,#171b35);
}
.hero {
    padding: 52px 34px;
    border-radius: 24px;
    background-image:
      linear-gradient(100deg,rgba(5,15,30,.96),rgba(6,44,65,.76),rgba(31,22,70,.55)),
      url("https://images.unsplash.com/photo-1451187580459-43490279c0fa?auto=format&fit=crop&w=1800&q=85");
    background-size: cover;
    background-position: center;
    border: 1px solid rgba(100,220,255,.35);
    box-shadow: 0 18px 55px rgba(0,0,0,.32);
    margin-bottom: 24px;
}
.hero h1 { color: white; font-size: clamp(30px,4vw,48px); font-weight: 800; }
.hero p { color: #d7f5ff; font-size: 17px; }
.visual-grid {
    display: grid;
    grid-template-columns: repeat(3,minmax(0,1fr));
    gap: 16px;
    margin: 18px 0 28px;
}
.visual-card {
    min-height: 180px;
    display: flex;
    flex-direction: column;
    justify-content: flex-end;
    padding: 22px;
    border-radius: 18px;
    background-size: cover;
    background-position: center;
    border: 1px solid rgba(148,190,255,.25);
    box-shadow: 0 12px 28px rgba(0,0,0,.22);
    transition: transform .25s ease;
}
.visual-card:hover { transform: translateY(-5px); }
.visual-card h3 { color: white; margin: 0 0 7px; }
.visual-card p { color: #e5f4ff; margin: 0; font-size: 14px; }
.card-one {
    background-image: linear-gradient(0deg,rgba(4,13,27,.96),rgba(4,13,27,.08)),
    url("https://images.unsplash.com/photo-1460925895917-afdab827c52f?auto=format&fit=crop&w=900&q=80");
}
.card-two {
    background-image: linear-gradient(0deg,rgba(4,13,27,.96),rgba(4,13,27,.08)),
    url("https://images.unsplash.com/photo-1551288049-bebda4e38f71?auto=format&fit=crop&w=900&q=80");
}
.card-three {
    background-image: linear-gradient(0deg,rgba(4,13,27,.96),rgba(4,13,27,.08)),
    url("https://images.unsplash.com/photo-1553877522-43269d4ea984?auto=format&fit=crop&w=900&q=80");
}
[data-testid="stMetric"] {
    background: linear-gradient(135deg,rgba(24,44,68,.94),rgba(20,31,56,.94));
    padding: 17px;
    border: 1px solid rgba(105,190,220,.22);
    border-radius: 16px;
}
div.stButton > button, div.stDownloadButton > button {
    border-radius: 12px;
    border: 1px solid #39cfc0;
    background: linear-gradient(100deg,#087f8c,#3156a8);
    color: white;
    font-weight: 700;
}
h1, h2, h3 { color: #eaf5ff; }
.small-note { color: #a6bbd2; font-size: 13px; }
@media(max-width:760px) {
    .visual-grid { grid-template-columns: 1fr; }
    .hero { padding: 32px 20px; }
}

/* ===== UI READABILITY AND ACCESSIBILITY FIX ===== */

.stApp, [data-testid="stAppViewContainer"] {
    color: #F8FAFC !important;
}

.stApp p, .stApp label, .stApp li,
.stApp .stMarkdown, .stApp [data-testid="stCaptionContainer"] {
    color: #E2EAF5;
}

.stApp h1, .stApp h2, .stApp h3,
.stApp h4, .stApp h5 {
    color: #FFFFFF !important;
    font-weight: 700;
}

[data-testid="stSidebar"] * {
    color: #F1F5F9;
}

[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea,
[data-testid="stNumberInput"] input,
[data-testid="stDateInput"] input,
[data-testid="stTimeInput"] input {
    background-color: #F8FAFC !important;
    color: #172B4D !important;
    border: 1px solid #94A3B8 !important;
    border-radius: 9px !important;
    -webkit-text-fill-color: #172B4D !important;
}

[data-testid="stTextInput"] input::placeholder,
[data-testid="stTextArea"] textarea::placeholder {
    color: #64748B !important;
    opacity: 1 !important;
}

/* Selectbox: visible background, text and arrow */
[data-testid="stSelectbox"] [data-baseweb="select"] > div,
[data-testid="stMultiSelect"] [data-baseweb="select"] > div {
    background-color: #F8FAFC !important;
    border: 1px solid #94A3B8 !important;
    color: #172B4D !important;
}

[data-testid="stSelectbox"] [data-baseweb="select"] *,
[data-testid="stMultiSelect"] [data-baseweb="select"] * {
    color: #172B4D !important;
    -webkit-text-fill-color: #172B4D !important;
}

[data-testid="stSelectbox"] [data-baseweb="select"] svg,
[data-testid="stMultiSelect"] [data-baseweb="select"] svg {
    fill: #172B4D !important;
    color: #172B4D !important;
    opacity: 1 !important;
    visibility: visible !important;
}

/* Dropdown menu */
[data-baseweb="popover"] [role="listbox"],
[data-baseweb="menu"] {
    background-color: #FFFFFF !important;
}

[data-baseweb="popover"] [role="option"],
[data-baseweb="menu"] * {
    color: #172B4D !important;
}

/* Radio buttons and checkboxes */
[data-testid="stRadio"] label,
[data-testid="stCheckbox"] label {
    color: #F1F5F9 !important;
}

/* Buttons */
.stButton > button, .stDownloadButton > button {
    color: #FFFFFF !important;
    font-weight: 700 !important;
    border: 1px solid #5EEAD4 !important;
}

.stButton > button:hover, .stDownloadButton > button:hover {
    background: #0F766E !important;
    color: #FFFFFF !important;
    border-color: #99F6E4 !important;
}

/* Metrics and data tables */
[data-testid="stMetric"] {
    color: #FFFFFF !important;
}

[data-testid="stMetric"] label,
[data-testid="stMetricValue"],
[data-testid="stMetricDelta"] {
    color: #FFFFFF !important;
}

[data-testid="stDataFrame"],
[data-testid="stTable"] {
    color: #172B4D !important;
}

/* Links and focus visibility */
.stApp a {
    color: #67E8F9 !important;
}

*:focus-visible {
    outline: 2px solid #5EEAD4 !important;
    outline-offset: 2px !important;
}

</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero">
<h1>ðŸŽ¯ Advanced Marketing Intelligence</h1>
<p>Discover competitors. Uncover keyword opportunities. Build a smarter marketing strategy.</p>
<p>âœ¦ Live Research &nbsp; âœ¦ Competitor Insights &nbsp; âœ¦ SEO Intelligence</p>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="visual-grid">
  <div class="visual-card card-one">
    <h3>ðŸ”Ž SEO Intelligence</h3>
    <p>Keywords, search intent and organic visibility opportunities.</p>
  </div>
  <div class="visual-card card-two">
    <h3>ðŸ“Š Competitor Analytics</h3>
    <p>Research market signals and compare competitor positioning.</p>
  </div>
  <div class="visual-card card-three">
    <h3>ðŸš€ Marketing Strategy</h3>
    <p>Social content, campaign ideas and a practical action plan.</p>
  </div>
</div>
""", unsafe_allow_html=True)


def search_web(query, limit=5):
    """Fetch live search results; search may fail temporarily."""
    try:
        with DDGS() as ddgs:
            rows = list(ddgs.text(query, max_results=limit))
        cleaned = []
        for r in rows:
            url = r.get("href") or r.get("url") or ""
            title = r.get("title", "")
            body = r.get("body", "")
            if url and title:
                cleaned.append({
                    "title": title,
                    "url": url,
                    "snippet": body,
                    "domain": urlparse(url).netloc
                })
        return cleaned
    except Exception as exc:
        return [{"title": "Search unavailable",
                 "url": "",
                 "snippet": str(exc),
                 "domain": ""}]


def unique_results(results):
    seen, output = set(), []
    for item in results:
        url = item.get("url", "")
        if url and url not in seen:
            seen.add(url)
            output.append(item)
    return output


def validate_keywords(keywords, results):
    """Evidence presence only; does not measure search volume."""
    evidence_text = " ".join(
        (r.get("title", "") + " " + r.get("snippet", "")).lower()
        for r in results
    )
    rows = []
    for keyword in keywords:
        k = keyword.strip()
        if not k:
            continue
        found = k.lower() in evidence_text
        rows.append({
            "Keyword": k,
            "Evidence in search results": "Found" if found else "Not found",
            "Meaning": (
                "Phrase appears in returned titles/snippets"
                if found else
                "No exact phrase found; review manually"
            )
        })
    return pd.DataFrame(rows)


def call_ai(company, website, industry, market, competitors, goal,
            results, detail):
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY .env file-à®²à¯ à®‡à®²à¯à®²à¯ˆ. à®‰à®™à¯à®•à®³à¯ key-à® à®…à®™à¯à®•à¯‡ à®®à®Ÿà¯à®Ÿà¯à®®à¯ à®šà¯‡à®°à¯à®•à¯à®•à®µà¯à®®à¯."
        )

    source_text = "\n\n".join(
        f"Title: {r['title']}\nURL: {r['url']}\nSnippet: {r['snippet']}"
        for r in results if r.get("url")
    )
    if not source_text:
        source_text = "No usable live search results were returned."

    system_prompt = """
You are a professional competitor intelligence analyst.
Write a concise, decision-focused business report.
Use only supplied search evidence for factual claims.
Never invent prices, sales, market share, rankings, search volumes,
keyword difficulty, advertising activity, or company facts.
Clearly distinguish observed evidence, inference, and recommendations.
Include source URLs for factual competitor claims where available.
Use professional, concise Markdown with short paragraphs and bullet points.
Avoid repetition, generic filler, exaggerated claims, and lengthy explanations.
Keep the report approximately 700-1000 words when evidence permits.
If evidence is limited, make the report shorter rather than inventing details.
Explain data limitations clearly and briefly.
"""

    user_prompt = f"""
Create a concise, professional Competitor Intelligence Executive Report.

Business: {company}
Website: {website or "Not provided"}
Industry: {industry}
Target market: {market}
Competitors: {competitors or "Discover from supplied search results"}
Business goal: {goal}

LIVE SEARCH RESULTS:
{source_text}

Use exactly these sections:

1. Executive Summary
   - 3-4 concise bullet points covering the main findings.

2. Competitor Comparison
   - NEVER list the target company itself as a competitor.
   - Exclude the target company name and its alternate spellings.
   - Prefer direct competitors serving the same customer segment and target location.
   - For an A2B vegetarian restaurant analysis, prioritize Chennai vegetarian and South Indian restaurant competitors.
   - Do not treat unrelated fast-food brands as direct competitors without evidence.
   - Use a competitor only when the supplied search results support its relevance.
   - Prefer official competitor websites and reliable local sources over Wikipedia.
   - If evidence is insufficient, clearly state that instead of guessing.
   - Summarize up to 5 relevant competitors.
   - For each, state positioning and evidence-supported strengths or gaps.
   - Include source URLs where available.

3. SEO & Keyword Insights
   - List up to 5 useful keywords or phrases.
   - State intent and suggested page/content for each.
   - Never imply search volume or ranking data was measured unless supplied.

4. Digital Marketing Findings
   - Summarize relevant website, search, social, or advertising evidence.
   - Clearly label unavailable or unverified information.

5. Key Opportunities
   - Give 3 prioritized, practical opportunities for this business.

6. 30-Day Action Plan
   - Give up to 5 actions with priority and a measurable KPI where appropriate.

7. Data Limitations & Sources
   - Briefly list important evidence gaps and the source URLs used.

Keep each section focused. Avoid repeating the same finding in multiple sections.
Do not claim that a competitor profile, website, social page, advertisement,
keyword volume, or business fact is verified unless the supplied evidence supports it.
Do not create numerical competitor scores from missing data.
"""

    client = Groq(api_key=api_key)
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.2,
        max_completion_tokens=6000
    )
    return response.choices[0].message.content


with st.sidebar:
    # ===== PROFESSIONAL SIDEBAR NAVIGATION =====
    st.markdown("## MARKETING INTELLIGENCE")
    page = st.radio(
        "NAVIGATION",
        [
            "Research History",
            "Executive Dashboard",
            "Competitor Research",
            "Competitor Scoring",
            "Automated Competitor Scoring",
            "Competitor Trend Tracking",
            "Evidence & Sources",
            "Competitor Discovery",
            "Keyword Evidence",
            "Marketing Report",
        ],
        key="main_navigation"
    )
    st.header("âš™ï¸ Research Settings")
    result_count = st.slider("Results per search", 3, 8, 5)
    detail = st.selectbox("Report detail", ["Brief", "Standard", "Detailed"],
                          index=2)
    st.caption("Search depends on third-party providers and internet access.")
    st.caption("API usage may have provider-specific limits.")

if page == "Competitor Research":
    with st.form("research_form"):
        st.subheader("Business Profile")
        c1, c2 = st.columns(2)
        industry_options = [
            "Fireworks Manufacturing and Retail",
            "Restaurant & Food",
            "Textile & Fashion",
            "Mobile & Electronics",
            "Real Estate",
            "Education & Training",
            "Beauty & Cosmetics",
            "Healthcare",
            "Automobile",
            "E-commerce & Retail",
            "Other"
        ]

        with c1:
            company = st.text_input("Company / Brand", "")
            website = st.text_input("Website (optional)", "")
            selected_industry = st.selectbox(
                "Select Industry",
                industry_options,
                index=0,
                key="selected_business_industry"
            )
            if selected_industry == "Other":
                custom_industry = st.text_input(
                    "Enter Your Industry",
                    placeholder="Example: Logistics, Agriculture, Travel & Tourism"
                )
                industry = custom_industry.strip() or "Other"
            else:
                industry = selected_industry

        industry_competitors = {
            "Fireworks Manufacturing and Retail":
                "Standard Fireworks, Ayyan Fireworks, Sri Kaliswari Fireworks, Sony Fireworks"
        }

        with c2:
            market = st.text_input(
                "Target Market / Location",
                "Tamil Nadu, India"
            )
            competitors = st.text_input(
                "Competitors (comma-separated)",
                industry_competitors.get(industry, ""),
                help="Enter competitor names, separated by commas. Leave blank to discover competitors from research."
            )
            goal = st.text_area(
                "Business Goal",
                "Find marketing opportunities, improve SEO, attract customers, "
                "compare competitors and create a practical marketing plan."
            )
        submitted = st.form_submit_button(
            "ðŸ”Ž Research & Generate Intelligence Report",
            type="primary",
            width="stretch"
        )

    if submitted:
        if not company.strip() or not industry.strip() or not market.strip():
            st.error("Company, industry à®®à®±à¯à®±à¯à®®à¯ target market à®µà®¿à®µà®°à®™à¯à®•à®³à¯ˆ à®¨à®¿à®°à®ªà¯à®ªà®µà¯à®®à¯.")
            st.stop()

        terms = [
            f'"{company}" {industry} official website',
            f'vegetarian restaurant chains Chennai competitors',
            f'best vegetarian restaurants Chennai official websites',
            f'popular South Indian restaurant chains Chennai',
            f'{industry} {market} competitors official websites',
            f'{industry} SEO marketing keywords {market}',
        ]
        for name in [x.strip() for x in competitors.split(",") if x.strip()][:4]:
            terms.append(f'"{name}" {market} official website products')

        all_results = []
        progress = st.progress(0, text="Live search à®¤à¯Šà®Ÿà®™à¯à®•à¯à®•à®¿à®±à®¤à¯...")
        for i, query in enumerate(terms):
            all_results.extend(search_web(query, result_count))
            progress.progress(
                (i + 1) / len(terms),
                text=f"Searching {i + 1} of {len(terms)}..."
            )
        results = unique_results(all_results)
        progress.empty()

        st.session_state["research_company"] = company
        st.session_state["research_industry"] = industry
        st.session_state["research_market"] = market
        st.session_state["research_competitors"] = competitors
        st.session_state["competitor_names_for_scoring"] = [
            name.strip()
            for name in competitors.split(",")
            if name.strip()
        ]

        st.session_state["research_results"] = results
        st.session_state["research_keywords"] = []
        st.session_state["research_report"] = ""

        if results:
            st.success(f"{len(results)} unique search result(s) à®•à®¿à®Ÿà¯ˆà®¤à¯à®¤à®©.")
            try:
                with st.spinner("AI report à®‰à®°à¯à®µà®¾à®•à¯à®•à¯à®•à®¿à®±à®¤à¯..."):
                    report = call_ai(
                        company, website, industry, market, competitors, goal,
                        results, detail
                    )
                st.session_state["research_report"] = report
            except Exception as exc:
                st.error(f"AI report à®‰à®°à¯à®µà®¾à®•à¯à®• à®®à¯à®Ÿà®¿à®¯à®µà®¿à®²à¯à®²à¯ˆ: {exc}")
                st.info(
                    "GROQ_API_KEY, internet connection, model availability "
                    "à®®à®±à¯à®±à¯à®®à¯ API limits à®šà®°à®¿à®ªà®¾à®°à¯à®•à¯à®•à®µà¯à®®à¯."
                )
        else:
            st.warning(
                "Live search results à®•à®¿à®Ÿà¯ˆà®•à¯à®•à®µà®¿à®²à¯à®²à¯ˆ. Internet connection à®…à®²à¯à®²à®¤à¯ "
                "search provider-à® à®šà®°à®¿à®ªà®¾à®°à¯à®¤à¯à®¤à¯ à®®à¯€à®£à¯à®Ÿà¯à®®à¯ à®®à¯à®¯à®±à¯à®šà®¿à®•à¯à®•à®µà¯à®®à¯."
            )

        # Save this research run permanently in SQLite.
        history_record = {
            "timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
            "company": company,
            "website": website,
            "industry": industry,
            "market": market,
            "competitors": competitors,
            "goal": goal,
            "result_count": len(results),
            "search_results": __import__("json").dumps(results, ensure_ascii=False),
            "report": st.session_state.get("research_report", ""),
        }
        old_history = load_dataframe("research_history")
        updated_history = pd.concat(
            [old_history, pd.DataFrame([history_record])],
            ignore_index=True
        )
        updated_history = updated_history.tail(200).reset_index(drop=True)
        save_dataframe("research_history", updated_history)
        st.success("Research History saved to database.")

results = st.session_state.get("research_results", [])

# Restore competitor names from the latest saved research if session data is missing.
competitor_names = st.session_state.get("competitor_names_for_scoring", [])

if not competitor_names:
    saved_competitors = st.session_state.get("research_competitors", "")
    if isinstance(saved_competitors, str):
        competitor_names = [
            name.strip() for name in saved_competitors.split(",") if name.strip()
        ]

if not competitor_names:
    history = load_dataframe("research_history")
    if not history.empty and "competitors" in history.columns:
        saved_value = history.iloc[-1].get("competitors", "")
        if isinstance(saved_value, str):
            competitor_names = [
                name.strip() for name in saved_value.split(",") if name.strip()
            ]

# Quick fallback for the previously researched A2B restaurant project.
saved_history_for_fallback = load_dataframe("research_history")
latest_company = ""
latest_industry = ""

if not saved_history_for_fallback.empty:
    latest_record = saved_history_for_fallback.iloc[-1]
    latest_company = str(latest_record.get("company", "")).strip().upper()
    latest_industry = str(latest_record.get("industry", "")).strip()

if (
    not competitor_names
    and (
        (
            st.session_state.get("research_company", "").strip().upper() == "A2B"
            and st.session_state.get("research_industry") == "Restaurant & Food"
        )
        or (
            latest_company == "A2B"
            and latest_industry == "Restaurant & Food"
        )
    )
):
    competitor_names = [
        "Saravana Bhavan",
        "Sangeetha Veg Restaurant",
        "Murugan Idli Shop",
        "Hotel Junior Kuppanna",
        "Anjappar Chettinad Restaurant",
        "Geetham Veg Restaurant",
    ]

competitor_names = list(dict.fromkeys(
    str(name).strip() for name in (competitor_names or [])
    if str(name).strip()
))

if competitor_names:
    st.session_state["competitor_names_for_scoring"] = competitor_names

if page == "Research History":
    st.header("Research History")
    st.caption("Previously saved competitor research reports.")

    history = load_dataframe("research_history")

    if history.empty:
        st.info("No saved research history yet. Run Competitor Research first.")
    else:
        history = history.sort_values(
            "timestamp", ascending=False
        ).reset_index(drop=True)

        display_columns = [
            column for column in [
                "timestamp", "company", "industry", "market", "result_count"
            ] if column in history.columns
        ]
        st.subheader("Saved Research Runs")
        st.dataframe(
            history[display_columns],
            use_container_width=True,
            hide_index=True
        )

        choices = [
            f"{row.get('company', 'Unknown')} | {row.get('timestamp', '')}"
            for _, row in history.iterrows()
        ]
        selected = st.selectbox("Select a saved report", choices)
        selected_index = choices.index(selected)
        saved = history.iloc[selected_index]

        st.divider()
        st.subheader(str(saved.get("company", "Saved Research Report")))
        st.caption(f"Date: {saved.get('timestamp', '')}")
        saved_report = str(saved.get("report", "") or "")

        if saved_report.strip():
            st.markdown(saved_report)

            pdf_bytes = build_pdf_report(saved.to_dict())
            safe_company = re.sub(
                r"[^A-Za-z0-9_-]+", "_",
                str(saved.get("company", "company"))
            ).strip("_") or "company"

            st.download_button(
                "Download Professional PDF Report",
                data=pdf_bytes,
                file_name=f"{safe_company}_marketing_intelligence_report.pdf",
                mime="application/pdf",
                key="download_saved_research_pdf"
            )
            st.download_button(
                "Download Saved Report (.md)",
                data=saved_report.encode("utf-8"),
                file_name="saved_competitor_research_report.md",
                mime="text/markdown",
                key="download_saved_research_report"
            )
        else:
            st.warning("This research run has no AI report saved.")

        saved_results = str(saved.get("search_results", "[]") or "[]")
        st.download_button(
            "Download Saved Search Results (.json)",
            data=saved_results.encode("utf-8"),
            file_name="saved_search_results.json",
            mime="application/json",
            key="download_saved_search_results"
        )

if page == "Executive Dashboard":
    render_executive_dashboard(competitor_names)

if page == "Automated Competitor Scoring":
    render_automated_scoring(competitor_names)

if page == "Competitor Trend Tracking":
    render_competitor_trends(competitor_names)

if page == "Competitor Scoring":
    with st.expander("Competitor Strength Score & Comparison Dashboard", expanded=False):
        render_competitor_scoring(competitor_names, st.session_state.get("research_industry", "Fireworks Manufacturing and Retail"))

if page == "Evidence & Sources":
    with st.expander("Evidence Collection & Research Links", expanded=False):
        render_competitor_evidence(
            competitor_names,
            search_web,
            st.session_state.get("research_company", "Default"),
        )

report = st.session_state.get("research_report", "")

st.divider()
if page == "Competitor Discovery":
    with st.expander("Competitor Discovery & Evidence", expanded=True):
        render_competitor_discovery(results)

if page == "Keyword Evidence":
    if results:
        st.divider()
        st.subheader("ðŸŒ Live Research Sources")
        st.caption("Search results are leads for research, not guaranteed verified facts.")
        for i, item in enumerate(results, 1):
            st.markdown(f"**{i}. [{item['title']}]({item['url']})**")
            if item.get("snippet"):
                st.write(item["snippet"])
            st.caption(item.get("domain", ""))

        st.divider()
        st.subheader("ðŸ”‘ Keyword Evidence Check")
        st.write(
            "Report-à®²à¯ à®ªà®°à®¿à®¨à¯à®¤à¯à®°à¯ˆà®•à¯à®•à®ªà¯à®ªà®Ÿà¯à®®à¯ keyword-à®•à®³à¯ˆ à®•à¯€à®´à¯‡ paste à®šà¯†à®¯à¯à®¤à¯, "
            "à®•à®¿à®Ÿà¯ˆà®¤à¯à®¤ search-result titles/snippets-à®²à¯ à®…à®µà¯ˆ à®‰à®³à¯à®³à®©à®µà®¾ à®Žà®©à¯à®±à¯ à®ªà®¾à®°à¯à®•à¯à®•à®²à®¾à®®à¯. "
            "à®‡à®¤à¯ search volume validation à®…à®²à¯à®²."
        )
        keyword_company = st.session_state.get("research_company", "Your Business")
        keyword_industry = st.session_state.get("research_industry", "Your Industry")
        keyword_market = st.session_state.get("research_market", "Your Market")

        keyword_defaults = [
            f"{keyword_company} {keyword_industry}",
            f"{keyword_industry} products {keyword_market}",
            f"{keyword_industry} services {keyword_market}",
            f"{keyword_industry} competitors {keyword_market}",
            f"{keyword_company} SEO keywords"
        ]

        keyword_text = st.text_area(
            "One keyword per line",
            value="\\n".join(keyword_defaults),
            key="keyword_input"
        )
        if st.button("Validate against search evidence"):
            keywords = [
                x.strip() for x in keyword_text.splitlines() if x.strip()
            ]
            st.session_state["keyword_validation"] = validate_keywords(
                keywords, results
            )

        validation = st.session_state.get("keyword_validation")
        if validation is not None:
            st.dataframe(validation, width="stretch", hide_index=True)
            st.download_button(
                "Download keyword evidence CSV",
                validation.to_csv(index=False).encode("utf-8-sig"),
                file_name="keyword_evidence_check.csv",
                mime="text/csv"
            )

if page == "Marketing Report":
    st.divider()
    st.subheader("Advanced Marketing Intelligence Report")

    report_to_show = str(report or "")
    saved_record = None

    if not report_to_show.strip():
        saved_reports = load_dataframe("research_history")

        if (
            not saved_reports.empty
            and "report" in saved_reports.columns
        ):
            valid_reports = saved_reports[
                saved_reports["report"].fillna("").astype(str).str.strip() != ""
            ]

            if not valid_reports.empty:
                saved_record = valid_reports.iloc[-1]
                report_to_show = str(saved_record.get("report", ""))

    if report_to_show.strip():
        if saved_record is not None:
            st.caption(
                "Showing the latest saved research report: "
                + str(saved_record.get("company", "Company"))
            )

        st.markdown(report_to_show)

        st.download_button(
            "Download Full Report (.md)",
            data=report_to_show.encode("utf-8"),
            file_name="advanced_marketing_intelligence_report.md",
            mime="text/markdown",
            width="stretch",
            key="download_marketing_report_md"
        )

        if saved_record is not None:
            try:
                pdf_bytes = build_pdf_report(saved_record.to_dict())
                st.download_button(
                    "Download Report (.pdf)",
                    data=pdf_bytes,
                    file_name="advanced_marketing_intelligence_report.pdf",
                    mime="application/pdf",
                    width="stretch",
                    key="download_marketing_report_pdf"
                )
            except Exception as exc:
                st.warning(f"PDF generation issue: {exc}")
    else:
        st.info(
            "No marketing report is available yet. "
            "Go to Competitor Research, run a research analysis, "
            "and generate an AI report. It will appear here."
        )

st.divider()
st.markdown(
    "<p class='small-note'>Advanced Marketing Intelligence Â· "
    "Live search availability and API limits may vary. "
    "Verify important claims using the original sources.</p>",
    unsafe_allow_html=True
)


