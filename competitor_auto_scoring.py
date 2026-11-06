import json
import os
from datetime import datetime

import pandas as pd
import requests
import streamlit as st
from groq import Groq

from db_storage import load_dataframe, save_dataframe
from competitor_scoring import WEIGHTS


def check_source(url, competitor="", observation=""):
    """Check URL accessibility and basic text relevance, not factual truth."""
    from urllib.parse import urlparse

    if not isinstance(url, str) or urlparse(url).scheme not in ("http", "https"):
        return False, "Invalid URL"

    try:
        response = requests.get(
            url,
            timeout=15,
            headers={"User-Agent": "Mozilla/5.0"},
            allow_redirects=True,
        )

        if response.status_code >= 400:
            return False, f"HTTP {response.status_code}"

        content_type = response.headers.get("Content-Type", "").lower()
        if content_type and not any(
            kind in content_type
            for kind in ("text/html", "text/plain", "application/xhtml")
        ):
            return False, "Not an HTML or text page"

        page = response.content[:1500000].decode(
            response.encoding or "utf-8", errors="replace"
        )

        import html
        import re

        page = re.sub(
            r"<(script|style|noscript)[^>]*>.*?</\1>",
            " ",
            page,
            flags=re.I | re.S,
        )
        page_text = html.unescape(re.sub(r"<[^>]+>", " ", page))
        page_text = re.sub(r"\s+", " ", page_text).lower()

        if len(page_text.strip()) < 80:
            return False, "Page has insufficient readable text"

        stop_words = {
            "the", "and", "for", "with", "from", "that", "this",
            "has", "have", "are", "was", "were", "their", "they",
            "its", "our", "your", "about", "into", "such", "more",
            "than", "not", "verified", "evidence", "appears",
            "indicates", "shows", "using", "related"
        }

        def words(value):
            return {
                word for word in re.findall(r"[a-z0-9]+", str(value).lower())
                if len(word) >= 3 and word not in stop_words
            }

        competitor_words = words(competitor)
        observation_words = words(observation)
        page_words = words(page_text)

        if not competitor_words:
            return False, "Competitor name could not be checked"

        matched_name = competitor_words.intersection(page_words)
        required = 1 if len(competitor_words) == 1 else 2

        if len(matched_name) < required:
            return False, "Competitor name not sufficiently present in page text"

        if observation_words and not observation_words.intersection(page_words):
            return False, "Observation keywords not found in page text"

        return True, (
            f"Content relevance check passed; "
            f"competitor terms matched: {len(matched_name)}"
        )

    except requests.RequestException as exc:
        return False, f"Unavailable: {type(exc).__name__}"
    except (UnicodeError, ValueError) as exc:
        return False, f"Content check failed: {type(exc).__name__}"


def generate_metric_scores(competitor, evidence, industry='Fireworks Manufacturing and Retail'):
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        raise ValueError("GROQ_API_KEY is missing from your .env file.")

    if evidence.empty:
        raise ValueError("No saved evidence available for this competitor.")

    evidence_text = evidence.to_json(
        orient="records", force_ascii=False, indent=2
    )

    metric_rubrics = {
        "Search visibility": """
        Assess actual search-result visibility using relevant search evidence.
        A single result is limited evidence. Multiple relevant results or
        independently supported visibility indicators are stronger.
        Do not infer traffic, rankings or search volume.
        """,
        "Reputation": """
        Assess customer reputation using review evidence.
        Consider actual ratings, review counts, recency and source relevance
        only when supplied. A review-site listing alone is not proof of
        positive reputation.
        """,
        "Paid activity": """
        Require direct evidence of advertisements or paid campaigns.
        A normal product listing or organic search result is not paid activity.
        If no direct ad evidence exists, return null.
        """,
        "Keyword strategy": """
        Assess evidence of relevant product, service and location keywords.
        A listing containing a few keywords is limited evidence.
        Do not infer keyword rankings, search volume or SEO performance.
        """,
        "Social presence": """
        Assess official social accounts and demonstrated activity.
        Account existence alone is weak evidence. Posting frequency,
        audience engagement and multiple active official channels count
        only when directly supported by supplied evidence.
        """,
        "Website quality": """
        Assess actual website quality indicators such as navigation,
        usable content, mobile experience, functionality and accessibility.
        A website URL or product listing alone does not establish quality.
        Return null when these indicators are not evidenced.
        """,
        "Local presence": """
        Assess physical business presence using relevant address,
        contact details and consistent local listings.
        A directory listing alone is limited evidence.
        Do not infer customer footfall or local market share.
        """
    }


    industry_guidance = {
        "Fireworks Manufacturing and Retail": """
        Consider product range, manufacturing capability, safety information,
        seasonal demand and regional dealer/distribution presence where evidenced.
        """,
        "Restaurant & Food": """
        Consider menu and food categories, customer reviews, ratings,
        ordering or reservation facilities, branch locations and delivery coverage.
        """,
        "Textile & Fashion": """
        Consider clothing categories, collections, fabric information,
        pricing when directly shown, online shopping and store presence.
        """,
        "Mobile & Electronics": """
        Consider product categories, specifications, warranty information,
        service centres, retail locations and online purchase facilities.
        """,
        "Real Estate": """
        Consider property listings, property types, project information,
        location details, contact options and verified project information.
        """,
        "Education & Training": """
        Consider courses, curriculum, faculty information, learning formats,
        campus locations and directly evidenced student feedback.
        """,
        "Beauty & Cosmetics": """
        Consider product categories, ingredients when disclosed,
        product information, customer reviews and retail availability.
        """,
        "Healthcare": """
        Consider listed medical services, specialties, practitioner details,
        facility locations and appointment facilities. Do not infer clinical quality.
        """,
        "Automobile": """
        Consider vehicle models, specifications, service facilities,
        dealership locations, warranty and customer feedback.
        """,
        "E-commerce & Retail": """
        Consider product categories, product information, delivery,
        returns, customer support and online shopping facilities.
        """
    }

    selected_industry_guidance = industry_guidance.get(
        industry,
        "Use only industry-relevant indicators directly supported by the supplied evidence. Do not assume business capabilities."
    )

    prompt = f"""
You are a conservative competitor intelligence analyst.

Industry: {industry}\n\nIndustry-specific context:\n{selected_industry_guidance}\n\nCompetitor: {competitor}

Evaluate each metric independently using ONLY the supplied evidence.

METRIC-SPECIFIC RULES:
{json.dumps(metric_rubrics, ensure_ascii=False, indent=2)}

SCORING SCALE:
0-19: Direct evidence of very weak performance.
20-39: Weak or limited demonstrated presence.
40-49: Some relevant evidence, but important limitations.
50-59: Moderate and directly supported evidence.
60-69: Good evidence with multiple relevant indicators.
70-79: Strong evidence from reliable, specific indicators.
80-89: Very strong evidence from multiple reliable sources.
90-100: Exceptional evidence with extensive direct support.

STRICT RULES:
1. Do not use the same score as a default for different metrics.
2. Never force different scores just to create variation.
3. Each metric must be evaluated using its own rubric.
4. Do not use evidence for one metric to score another metric.
5. A URL being reachable does not prove the claim is true.
6. Do not invent facts, ratings, reviews, rankings, traffic,
   ad spend, search volume, engagement or website features.
7. A website or social account existing does not prove its quality
   or activity.
8. If the evidence does not support a meaningful score, use null.
9. Use only exact source URLs supplied in the evidence.
10. Confidence must be High, Medium, Low, or Not verified.
11. High requires direct, strong and relevant evidence.
12. Medium requires relevant evidence with some limitations.
13. Low means weak but relevant evidence.
14. If score is null, confidence must be Not verified.
15. Give a short factual observation and a specific reason.
16. Return exactly seven metric objects.

Return valid JSON only:
{{
  "scores": [
    {{
      "metric": "Search visibility",
      "score": null,
      "observation": "Not verified",
      "source_url": "",
      "confidence": "Not verified",
      "reason": "Insufficient relevant evidence"
    }}
  ]
}}

SUPPLIED EVIDENCE:
{evidence_text}
"""

    client = Groq(api_key=api_key)
    response = client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=[
            {
                "role": "system",
                "content": (
                    "Return valid JSON only. Apply each metric's own rubric. "
                    "Be conservative and never fabricate evidence."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0,
        max_completion_tokens=3000,
    )

    response_text = (response.choices[0].message.content or "").strip()

    if response_text.startswith("```"):
        response_text = response_text.split("\n", 1)[-1]
        if response_text.endswith("```"):
            response_text = response_text[:-3].strip()

    parsed = json.loads(response_text)
    items = parsed.get("scores", [])
    allowed_urls = set(
        evidence["Source URL"].dropna().astype(str).str.strip()
    )

    by_metric = {}
    for item in items:
        metric = item.get("metric")
        if metric in WEIGHTS and metric not in by_metric:
            by_metric[metric] = item

    output = []

    for metric in WEIGHTS:
        item = by_metric.get(metric, {})
        url = str(item.get("source_url", "")).strip()
        score = item.get("score")
        confidence = str(
            item.get("confidence", "Not verified")
        ).strip()
        observation = str(
            item.get("observation", "Not verified")
        ).strip()
        reason = str(item.get("reason", "")).strip()

        if url not in allowed_urls:
            url = ""
            score = None
            confidence = "Not verified"
            observation = "Not verified: no matching evidence source."

        try:
            score = float(score) if score is not None else None
        except (TypeError, ValueError):
            score = None

        if score is not None and not 0 <= score <= 100:
            score = None

        if confidence not in ("High", "Medium", "Low"):
            confidence = "Not verified"

        if not url or confidence == "Not verified":
            score = None

        output.append({
            "Competitor": competitor,
            "Metric": metric,
            "Score": round(score, 1) if score is not None else None,
            "Observation": observation,
            "Source URL": url,
            "Confidence Level": confidence,
            "Reason": reason,
            "Checked Date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        })

    return pd.DataFrame(output)


def render_automated_scoring(competitor_names):
    st.title("Automated Competitor Scoring")
    st.caption(
        "Generate provisional metric scores from saved public-web evidence. "
        "Webpage text, competitor name and observation relevance are checked. "
        "Content matching does not independently prove a claim is true."
    )

    if not competitor_names:
        competitor_names = st.session_state.get(
            "competitor_names_for_scoring", []
        )

    if not competitor_names:
        saved_competitors = st.session_state.get("research_competitors", "")
        if isinstance(saved_competitors, str):
            competitor_names = [
                name.strip()
                for name in saved_competitors.split(",")
                if name.strip()
            ]
        elif saved_competitors:
            competitor_names = list(saved_competitors)

    names = list(dict.fromkeys(
        str(name).strip() for name in (competitor_names or [])
        if str(name).strip()
    ))
    if not names:
        st.warning("No competitors are available. Run competitor research first.")
        return

    competitor = st.selectbox(
        "Choose competitor",
        names,
        key="auto_score_competitor",
    )

    if st.button(
        "Generate Scores from Saved Evidence",
        type="primary",
        width="stretch",
        key="generate_auto_competitor_scores",
    ):
        records = load_dataframe("evidence")

        if records.empty:
            st.error("No saved evidence found. Run Evidence & Sources research first.")
            return

        records = records[
            records["Competitor"].astype(str) == competitor
        ].copy()

        if records.empty:
            st.error(
                f"No saved evidence found for {competitor}. "
                "Run automated evidence research first."
            )
            return

        if "Source URL" not in records.columns or "Metric" not in records.columns:
            st.error("Evidence data is missing required columns.")
            return

        with st.spinner("Checking source URLs and generating evidence-based scores..."):
            checked_rows = []
            for _, row in records.iterrows():
                accessible, status = check_source(
                    str(row.get("Source URL", "")),
                    competitor,
                    str(row.get("Observation", "")),
                )
                item = row.to_dict()
                item["URL Accessibility"] = status
                item["URL Accessible"] = accessible
                checked_rows.append(item)

            checked = pd.DataFrame(checked_rows)
            usable = checked[
                checked["URL Accessible"].eq(True)
                & checked["Observation"].notna()
                & (checked["Observation"].astype(str).str.strip() != "")
                & (checked["Observation"].astype(str).str.lower() != "not verified")
            ].copy()

            save_dataframe("auto_score_source_checks", checked)

            if usable.empty:
                st.error("No accessible sources with usable observations were found.")
                return

            try:
                industry = st.session_state.get(
                    "research_industry",
                    "Fireworks Manufacturing and Retail"
                )
                result = generate_metric_scores(competitor, usable, industry)
            except Exception as exc:
                st.error(f"AI scoring failed: {exc}")
                return

            old_scores = load_dataframe("scores")
            if old_scores.empty:
                old_scores = pd.DataFrame(columns=["Competitor", *WEIGHTS.keys()])

            if "Competitor" not in old_scores.columns:
                old_scores["Competitor"] = []

            old_scores = old_scores[
                old_scores["Competitor"].astype(str) != competitor
            ].copy()

            new_score_row = {"Competitor": competitor}
            for metric in WEIGHTS:
                values = result.loc[result["Metric"] == metric, "Score"]
                new_score_row[metric] = (
                    values.iloc[0] if not values.empty else None
                )

            updated_scores = pd.concat(
                [old_scores, pd.DataFrame([new_score_row])],
                ignore_index=True,
            )
            save_dataframe("scores", updated_scores)

            all_details = load_dataframe("auto_score_details")
            all_details = all_details[
                all_details["Competitor"].astype(str) != competitor
            ] if not all_details.empty and "Competitor" in all_details.columns else pd.DataFrame()

            all_details = pd.concat([all_details, result], ignore_index=True)
            save_dataframe("auto_score_details", all_details)

            st.session_state.pop("competitor_strength_score_editor", None)
            st.session_state.pop("competitor_strength_score_table", None)

        st.success("Automated scoring completed and saved.")
        st.rerun()


    st.divider()
    st.subheader("Bulk Competitor Scoring")
    st.caption(
        "Generate scores for all listed competitors using their saved evidence. "
        "Competitors without usable evidence will be reported separately."
    )

    if st.button(
        "Generate Scores for All Competitors",
        type="primary",
        width="stretch",
        key="generate_bulk_competitor_scores",
    ):
        records = load_dataframe("evidence")

        if records.empty:
            st.error("No saved evidence found. Run Evidence & Sources research first.")
        elif "Competitor" not in records.columns or "Source URL" not in records.columns:
            st.error("Evidence data is missing required columns.")
        else:
            industry = st.session_state.get("research_industry", "")
            if not industry:
                history = load_dataframe("research_history")
                if not history.empty:
                    industry = str(history.iloc[-1].get("industry", ""))
            if not industry:
                industry = "Fireworks Manufacturing and Retail"

            bulk_results = []
            skipped = []
            progress = st.progress(0, text="Starting bulk scoring...")

            for index, name in enumerate(names):
                competitor_evidence = records[
                    records["Competitor"].astype(str).str.strip() == name
                ].copy()

                if competitor_evidence.empty:
                    missing_rows = []
                    for metric in WEIGHTS:
                        missing_rows.append({
                            "Competitor": name,
                            "Metric": metric,
                            "Score": None,
                            "Observation": "Insufficient Evidence",
                            "Source URL": "",
                            "Confidence Level": "Not verified",
                            "Reason": "No saved evidence is available for this competitor.",
                            "Checked Date": datetime.now().strftime("%Y-%m-%d"),
                        })

                    missing_result = pd.DataFrame(missing_rows)
                    bulk_results.append(missing_result)

                    old_details = load_dataframe("auto_score_details")
                    if not old_details.empty and "Competitor" in old_details.columns:
                        old_details = old_details[
                            old_details["Competitor"].astype(str) != name
                        ]
                    else:
                        old_details = pd.DataFrame()

                    save_dataframe(
                        "auto_score_details",
                        pd.concat([old_details, missing_result], ignore_index=True),
                    )

                    progress.progress(
                        (index + 1) / len(names),
                        text=f"Checking {index + 1} of {len(names)}"
                    )
                    continue

                checked_rows = []
                for _, row in competitor_evidence.iterrows():
                    accessible, status = check_source(
                        str(row.get("Source URL", "")),
                        name,
                        str(row.get("Observation", "")),
                    )
                    item = row.to_dict()
                    item["URL Accessibility"] = status
                    item["URL Accessible"] = accessible
                    checked_rows.append(item)

                checked = pd.DataFrame(checked_rows)
                usable = checked[
                    checked["URL Accessible"].eq(True)
                    & checked["Observation"].notna()
                    & (checked["Observation"].astype(str).str.strip() != "")
                    & (checked["Observation"].astype(str).str.lower() != "not verified")
                ].copy()

                save_dataframe(
                    "auto_score_source_checks",
                    pd.concat(
                        [load_dataframe("auto_score_source_checks"), checked],
                        ignore_index=True,
                    ).drop_duplicates(
                        subset=["Competitor", "Source URL", "Observation"],
                        keep="last",
                    ),
                )

                if usable.empty:
                    skipped.append(f"{name}: no accessible usable evidence")
                else:
                    try:
                        result = generate_metric_scores(name, usable, industry)
                        bulk_results.append(result)

                        old_scores = load_dataframe("scores")
                        if old_scores.empty:
                            old_scores = pd.DataFrame(
                                columns=["Competitor", *WEIGHTS.keys()]
                            )

                        old_scores = old_scores[
                            old_scores["Competitor"].astype(str) != name
                        ].copy()

                        score_row = {"Competitor": name}
                        for metric in WEIGHTS:
                            values = result.loc[
                                result["Metric"] == metric, "Score"
                            ]
                            score_row[metric] = (
                                values.iloc[0] if not values.empty else None
                            )

                        save_dataframe(
                            "scores",
                            pd.concat(
                                [old_scores, pd.DataFrame([score_row])],
                                ignore_index=True,
                            ),
                        )

                        old_details = load_dataframe("auto_score_details")
                        if not old_details.empty and "Competitor" in old_details.columns:
                            old_details = old_details[
                                old_details["Competitor"].astype(str) != name
                            ]
                        else:
                            old_details = pd.DataFrame()

                        save_dataframe(
                            "auto_score_details",
                            pd.concat([old_details, result], ignore_index=True),
                        )

                    except Exception as exc:
                        skipped.append(f"{name}: {type(exc).__name__}: {exc}")

                progress.progress(
                    (index + 1) / len(names),
                    text=f"Processed {index + 1} of {len(names)} competitors"
                )

            progress.empty()

            if bulk_results:
                combined = pd.concat(bulk_results, ignore_index=True)
                st.success(
                    f"Bulk scoring completed for {combined['Competitor'].nunique()} competitor(s)."
                )
                st.subheader("Bulk Scoring Results")
                st.dataframe(combined, width="stretch", hide_index=True)

                st.download_button(
                    "Download Bulk Scores (CSV)",
                    data=combined.to_csv(index=False).encode("utf-8-sig"),
                    file_name="bulk_competitor_scores.csv",
                    mime="text/csv",
                    key="download_bulk_competitor_scores",
                )

            if skipped:
                st.warning("Some competitors could not be scored:")
                for item in skipped:
                    st.write(f"- {item}")

            # Keep bulk results visible; do not immediately rerun here.

    details = load_dataframe("auto_score_details")
    if not details.empty:
        details = details[details["Competitor"].astype(str) == competitor]
        if not details.empty:
            st.subheader("AI Metric Scores & Evidence")
            st.dataframe(details, width="stretch", hide_index=True)

            valid = details.dropna(subset=["Score"])
            st.metric("Metrics with scores", f"{len(valid)} / {len(WEIGHTS)}")

            if not valid.empty:
                st.bar_chart(valid.set_index("Metric")["Score"])

            st.caption(
                "These are provisional AI assessments of supplied observations. "
                "Accessible URLs are not proof that the underlying claims are true. "
                "Review each source before relying on a score."
            )
