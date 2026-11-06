import json
import os
from datetime import date
from urllib.parse import quote_plus

import pandas as pd
import requests
from urllib.parse import urlparse
import streamlit as st
from groq import Groq
from db_storage import load_dataframe, save_dataframe


METRICS = [
    "Search visibility",
    "Reputation",
    "Paid activity",
    "Keyword strategy",
    "Social presence",
    "Website quality",
    "Local presence",
]


def run_automated_evidence(competitor, search_func):
    queries = {
        "Search visibility": f'"{competitor}" website search results',
        "Reputation": f'"{competitor}" customer reviews ratings',
        "Paid activity": f'"{competitor}" advertisements ads',
        "Keyword strategy": f'"{competitor}" products services keywords',
        "Social presence": f'"{competitor}" Instagram Facebook social media',
        "Website quality": f'"{competitor}" official website',
        "Local presence": f'"{competitor}" business address Google Maps',
    }

    collected = {}
    all_results = []

    progress = st.progress(0, text="Researching competitor evidence...")
    for index, (metric, query) in enumerate(queries.items()):
        results = search_func(query, limit=4)
        valid = [
            item for item in results
            if item.get("url")
            and item.get("title")
            and item.get("title") != "Search unavailable"
        ]
        collected[metric] = valid
        all_results.extend(valid)
        progress.progress(
            (index + 1) / len(queries),
            text=f"Researching {metric} ({index + 1}/7)...",
        )
    progress.empty()

    unique = {}
    for item in all_results:
        unique[item["url"]] = item
    all_results = list(unique.values())

    if not all_results:
        raise RuntimeError(
            "Live search returned no usable sources. Please try again later."
        )

    source_text = "\n\n".join(
        f"Metric searches: {', '.join(metric for metric, rows in collected.items() if item in rows)}\n"
        f"Title: {item['title']}\n"
        f"URL: {item['url']}\n"
        f"Snippet: {item.get('snippet', '')}"
        for item in all_results
    )

    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        raise ValueError("GROQ_API_KEY is missing from your .env file.")

    prompt = f"""
Analyze the public search evidence for this competitor: {competitor}

Return ONLY a valid JSON object in this exact structure:
{{
  "evidence": [
    {{
      "metric": "Search visibility",
      "observation": "A concise factual statement based only on supplied evidence.",
      "source_url": "An exact URL copied from the supplied sources, or an empty string.",
      "confidence": "High, Medium, or Low"
    }}
  ]
}}

Create exactly one item for each of these metrics:
{json.dumps(METRICS)}

Rules:
- Use only the supplied search titles and snippets.
- Never invent facts, ratings, review counts, ad activity, rankings, or website features.
- A search result snippet is preliminary evidence, not independent verification.
- Use a source_url only when that exact URL supports the observation.
- If evidence is absent or insufficient, use observation "Not verified",
  source_url "", and confidence "Not verified".
- High: direct and clear evidence from an official or primary source.
- Medium: relevant evidence, but indirect or incomplete.
- Low: weak or ambiguous evidence.
- Do not use High merely because a search result exists.
- Do not claim to have opened or independently verified a page.
- Return all seven metrics, even when evidence is unavailable.

SUPPLIED SEARCH RESULTS:
{source_text}
"""

    client = Groq(api_key=api_key)
    response = client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=[
            {
                "role": "system",
                "content": "You are a careful competitor research analyst. Never fabricate evidence. Return valid JSON only.",
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.1,
        max_completion_tokens=3000,
    )

    content = response.choices[0].message.content or ""
    content = content.strip()
    if content.startswith("```"):
        content = content.split("\n", 1)[-1]
        if content.endswith("```"):
            content = content[:-3].strip()

    parsed = json.loads(content)
    items = parsed.get("evidence", [])
    allowed_urls = {item["url"] for item in all_results}

    by_metric = {}
    for item in items:
        metric = item.get("metric")
        if metric in METRICS and metric not in by_metric:
            by_metric[metric] = item

    rows = []
    for metric in METRICS:
        item = by_metric.get(metric, {})
        observation = str(item.get("observation", "Not verified")).strip()
        url = str(item.get("source_url", "")).strip()
        confidence = str(item.get("confidence", "Not verified")).strip()

        if url not in allowed_urls:
            url = ""
            observation = "Not verified: no matching source URL was supplied."
            confidence = "Not verified"

        if not observation:
            observation = "Not verified"

        if confidence not in ["High", "Medium", "Low"]:
            confidence = "Not verified"

        if not url:
            observation = "Not verified" if observation == "Not verified" else observation
            confidence = "Not verified"

        rows.append({
            "Competitor": competitor,
            "Metric": metric,
            "Observation": observation,
            "Source URL": url,
            "Confidence Level": confidence,
            "Checked Date": date.today().isoformat(),
        })

    return pd.DataFrame(rows)



def validate_evidence_sources(records):
    """Check whether evidence URLs respond and contain competitor references."""
    checked = records.copy()
    statuses = []
    matches = []
    quality = []

    for _, row in checked.iterrows():
        url = str(row.get("Source URL", "")).strip()
        competitor = str(row.get("Competitor", "")).strip()

        if not url.startswith(("http://", "https://")):
            statuses.append("Invalid URL")
            matches.append("Not checked")
            quality.append("Needs review")
            continue

        try:
            parsed = urlparse(url)
            if not parsed.hostname:
                raise ValueError("Missing hostname")

            response = requests.get(
                url,
                timeout=10,
                headers={"User-Agent": "Mozilla/5.0"},
                allow_redirects=True,
            )
            status = f"HTTP {response.status_code}"
            is_accessible = response.status_code < 400
        except requests.RequestException:
            status = "Unavailable"
            is_accessible = False
        except ValueError:
            status = "Invalid URL"
            is_accessible = False

        statuses.append(status)

        searchable = " ".join([
            str(row.get("Competitor", "")),
            str(row.get("Observation", "")),
            str(row.get("Source URL", "")),
        ]).lower()

        words = [
            word.lower()
            for word in competitor.split()
            if len(word) > 2
        ]
        matched = bool(words) and any(word in searchable for word in words)

        matches.append("Possible match" if matched else "No clear match")

        if is_accessible and matched:
            quality.append("Review source content")
        elif is_accessible:
            quality.append("Name match needed")
        else:
            quality.append("Source unavailable")

    checked["URL Status"] = statuses
    checked["Competitor Match"] = matches
    checked["Evidence Quality Check"] = quality
    return checked


def render_competitor_evidence(competitor_names, search_func=None, company_name='Default'):
    st.divider()
    st.subheader("Competitor Evidence Collection")
    st.caption(
        "Research public information and save evidence with source links. "
        "AI findings are limited to the supplied search evidence."
    )

    names = list(dict.fromkeys(
        str(name).strip()
        for name in competitor_names
        if str(name).strip()
    ))

    if not names:
        st.info("Select competitor results above to collect evidence.")
        return

    selected = st.selectbox(
        "Choose a competitor",
        names,
        key="evidence_competitor_select",
    )

    query = quote_plus(selected)
    search_links = {
        "Website / web results": f"https://www.google.com/search?q={query}",
        "Google Maps / reviews": f"https://www.google.com/maps/search/{query}",
        "Google Ads Transparency Center": f"https://adstransparency.google.com/?region=IN&query={query}",
        "Meta Ads Library": f"https://www.facebook.com/ads/library/?active_status=all&ad_type=ALL&country=IN&q={query}",
        "Facebook search": f"https://www.facebook.com/search/top?q={query}",
        "Instagram search": f"https://www.google.com/search?q={quote_plus(selected + ' Instagram')}",
        "SEO / keyword evidence": f"https://www.google.com/search?q={quote_plus(selected + ' products keywords')}",
    }

    st.markdown("#### Research links")
    for label, url in search_links.items():
        st.markdown(f"- [{label}]({url})")

    company_slug = "".join(
        ch.lower() if ch.isalnum() else "_"
        for ch in str(company_name)
    ).strip("_") or "default"

    evidence_key = f"competitor_evidence_records_{company_slug}"
    evidence_db_key = f"evidence_{company_slug}"
    if evidence_key not in st.session_state:
        saved_evidence = load_dataframe(evidence_db_key)
        if saved_evidence.empty:
            saved_evidence = pd.DataFrame(
                columns=[
                    "Competitor", "Metric", "Observation", "Source URL",
                    "Confidence Level", "Checked Date",
                ]
            )
        st.session_state[evidence_key] = saved_evidence

    records = st.session_state[evidence_key]
    if "Confidence Level" not in records.columns:
        records["Confidence Level"] = "Not rated"
    if "Checked Date" not in records.columns:
        records["Checked Date"] = ""
    st.session_state[evidence_key] = records
    save_dataframe(evidence_db_key, records)

    st.markdown("#### Automated Evidence Research")
    st.caption(
        "Searches public web results for all seven metrics and asks AI "
        "to summarize only the evidence supplied by those results."
    )

    if search_func is None:
        st.warning("Live search function is not connected.")
    else:
        if st.button(
            "Research Evidence Automatically",
            type="primary",
            width="stretch",
            key="automated_evidence_research",
        ):
            try:
                with st.spinner("Searching and analyzing public evidence..."):
                    new_records = run_automated_evidence(selected, search_func)

                existing = st.session_state[evidence_key]
                existing = existing[
                    existing["Competitor"] != selected
                ]
                combined = pd.concat(
                    [existing, new_records],
                    ignore_index=True,
                )
                st.session_state[evidence_key] = combined
                save_dataframe(evidence_db_key, combined)
                st.success(
                    f"Research completed. {len(new_records)} metric records saved."
                )
                st.rerun()
            except Exception as exc:
                st.error(f"Automated research could not be completed: {exc}")
                st.info(
                    "Check internet access, Groq API availability, and "
                    "GROQ_API_KEY in your .env file."
                )


    st.markdown("#### Bulk Competitor Evidence Research")
    st.caption(
        "Run automated evidence research for every competitor in the list."
    )

    if search_func is not None and len(names) > 1:
        if st.button(
            "Research All Competitors Automatically",
            type="primary",
            width="stretch",
            key="automated_all_competitors_research",
        ):
            try:
                all_new_records = []

                for competitor in names:
                    with st.spinner(
                        f"Researching {competitor}..."
                    ):
                        competitor_records = run_automated_evidence(
                            competitor,
                            search_func,
                        )
                        all_new_records.append(competitor_records)

                if all_new_records:
                    combined_new = pd.concat(
                        all_new_records,
                        ignore_index=True,
                    )

                    existing = st.session_state[evidence_key]
                    existing = existing[
                        ~existing["Competitor"].isin(names)
                    ]

                    st.session_state[evidence_key] = pd.concat(
                        [existing, combined_new],
                        ignore_index=True,
                    )
                    save_dataframe(evidence_db_key, st.session_state[evidence_key])

                    st.success(
                        f"Research completed for {len(names)} competitors. "
                        f"{len(combined_new)} metric records saved."
                    )
                    st.rerun()

            except Exception as exc:
                st.error(f"Bulk research could not be completed: {exc}")
                st.info(
                    "Check internet access, Groq API availability, "
                    "and GROQ_API_KEY in your .env file."
                )

    st.markdown("#### Manual Evidence Entry")
    with st.form("add_competitor_evidence_form", clear_on_submit=True):
        evidence_competitor = st.selectbox(
            "Competitor",
            names,
            index=names.index(selected),
            key="evidence_form_competitor",
        )
        metric = st.selectbox("Metric", METRICS)
        observation = st.text_area(
            "What did you observe?",
            placeholder="Write only what you verified from the source.",
        )
        source_url = st.text_input(
            "Source URL",
            placeholder="https://...",
        )
        checked_date = st.date_input("Date checked")
        confidence = st.selectbox(
            "Evidence Confidence Level",
            ["High", "Medium", "Low"],
        )

        submitted = st.form_submit_button(
            "Save Evidence",
            width="stretch",
        )

        if submitted:
            if not observation.strip() or not source_url.strip():
                st.error("Enter both an observation and its source URL.")
            elif not (
                source_url.strip().startswith("https://")
                or source_url.strip().startswith("http://")
            ):
                st.error("Source URL must start with http:// or https://.")
            else:
                new_row = pd.DataFrame([{
                    "Competitor": evidence_competitor,
                    "Metric": metric,
                    "Observation": observation.strip(),
                    "Source URL": source_url.strip(),
                    "Confidence Level": confidence,
                    "Checked Date": checked_date.isoformat(),
                }])
                st.session_state[evidence_key] = pd.concat(
                    [st.session_state[evidence_key], new_row],
                    ignore_index=True,
                )
                save_dataframe(evidence_db_key, st.session_state[evidence_key])
                st.success("Evidence saved for this session.")
                st.rerun()

    records = st.session_state[evidence_key]

    st.markdown("#### Source URL Validation")
    st.caption(
        "Checks whether source links respond and whether competitor "
        "names appear in the saved evidence. This is an initial check, "
        "not proof that a claim is true."
    )

    if not records.empty:
        if st.button(
            "Validate All Evidence Sources",
            width="stretch",
            key="validate_all_evidence_sources",
        ):
            with st.spinner("Checking evidence source URLs..."):
                validated = validate_evidence_sources(records)
                st.session_state[evidence_key] = validated
                save_dataframe(evidence_db_key, validated)
            st.success("Source validation completed.")
            st.rerun()

    st.markdown("#### Saved evidence")
    if records.empty:
        st.info("No evidence saved yet.")
    else:
        st.dataframe(records, width="stretch", hide_index=True)
        st.download_button(
            "Download Evidence CSV",
            records.to_csv(index=False).encode("utf-8-sig"),
            file_name="competitor_evidence.csv",
            mime="text/csv",
            width="stretch",
        )
