import pandas as pd
import streamlit as st


def render_competitor_discovery(results):
    st.subheader("Competitor Discovery & Evidence")
    st.caption(
        "Search results are potential leads, not proof that a business "
        "is a direct competitor. Verify each result before relying on it."
    )

    if not results:
        st.info("Run the main research first to collect search results.")
        return

    rows = []
    for item in results:
        title = item.get("title", "")
        url = item.get("url", "")
        snippet = item.get("snippet", "")
        domain = item.get("domain", "")

        if not title or not url:
            continue

        rows.append({
            "Include": True,
            "Business / Result": title,
            "Website / Source": url,
            "Domain": domain,
            "Search Evidence": snippet,
            "Classification": "Needs review",
            "Verification Status": "Unverified"
        })

    if not rows:
        st.warning("No usable business results were found.")
        return

    df = pd.DataFrame(rows).drop_duplicates(
        subset=["Website / Source"]
    ).reset_index(drop=True)

    edited = st.data_editor(
        df,
        width="stretch",
        hide_index=True,
        num_rows="fixed",
        column_config={
            "Include": st.column_config.CheckboxColumn(
                "Include in analysis",
                help="Select the results you want to review."
            ),
            "Website / Source": st.column_config.LinkColumn(
                "Open source",
                help="Open the original search result."
            ),
            "Classification": st.column_config.SelectboxColumn(
                "Competitor type",
                options=[
                    "Needs review",
                    "Direct competitor",
                    "Indirect competitor",
                    "Irrelevant"
                ],
                required=True
            ),
            "Verification Status": st.column_config.SelectboxColumn(
                "Verification",
                options=[
                    "Unverified",
                    "Website checked",
                    "Business identity confirmed"
                ],
                required=True
            )
        },
        disabled=[
            "Business / Result",
            "Website / Source",
            "Domain",
            "Search Evidence"
        ],
        key="competitor_discovery_editor"
    )

    selected = edited[
        edited["Include"]
        & (edited["Classification"] != "Irrelevant")
    ].copy()

    st.metric("Potential competitors selected", len(selected))
    st.dataframe(
        selected,
        width="stretch",
        hide_index=True
    )

    st.download_button(
        "Download competitor review CSV",
        data=selected.to_csv(index=False).encode("utf-8-sig"),
        file_name="competitor_discovery_review.csv",
        mime="text/csv",
        width="stretch"
    )

