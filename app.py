import streamlit as st
import pandas as pd
import json
import os
import altair as alt
import subprocess
import sys

st.set_page_config(
    page_title="Singapore Court Case Analytics",
    page_icon="⚖️",
    layout="wide"
)

def load_data(jsonl_path: str = "data/case_data.jsonl"):
    if not os.path.exists(jsonl_path):
        return pd.DataFrame()
    
    data = []
    with open(jsonl_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                data.append(json.loads(line))
    return pd.DataFrame(data)

def load_dashboard_data():
    # Mocking dashboard analytics since DB is removed
    queries = pd.DataFrame([
        {"Topic": "Insolvency", "Count": 45},
        {"Topic": "Contract Breach", "Count": 32},
        {"Topic": "Trusts", "Count": 18},
        {"Topic": "Defamation", "Count": 12},
        {"Topic": "Employment", "Count": 8}
    ]).set_index("Topic")
    
    reports = pd.DataFrame([
        {"Report Title": "Q1 Insolvency Trends", "Original Query": "bankruptcy", "Date Created": "2026-02-20"},
        {"Report Title": "Breach of Contract Analysis", "Original Query": "contract", "Date Created": "2026-02-18"}
    ])
    reports["Actions"] = "View & Export"
    
    recent_query_count = 115
    report_count = 2
    
    return queries, reports, recent_query_count, report_count

st.title("⚖️ Singapore Court Case Analytics")
st.caption("Data source: LawNet OpenLaw (Scraped locally)")

# --- Sidebar Scraper UI (Always Visible) ---
with st.sidebar.expander("Add New Cases (Scraper)", expanded=False):
    urls_input = st.text_area("Paste LawNet URLs (one per line)", height=150)
    if st.button("Scrape Cases"):
        if urls_input:
            urls = [u.strip() for u in urls_input.split('\\n') if u.strip()]
            if urls:
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                def run_scraper_subprocess(urls):
                    for i, url in enumerate(urls):
                        status_text.text(f"Scraping {i+1}/{len(urls)}: {url}...")
                        # Run pipeline.py directly via subprocess
                        subprocess.run([sys.executable, "pipeline.py", url, "--force"])
                        progress_bar.progress((i + 1) / len(urls))
                    status_text.success("Scraping completed!")
                
                run_scraper_subprocess(urls)
                
                st.rerun() # Refresh data
            else:
                st.warning("No valid URLs found.")
        else:
            st.warning("Please paste at least one URL.")
# -------------------------------------------

try:
    df = load_data()
    
    if df.empty:
        st.warning("No data found in database. Run scraper first.")
    else:
        # 1. Convert date column robustly
        if "decision_date" not in df.columns:
            df["decision_date"] = None
        
        df["decision_date_dt"] = pd.to_datetime(df["decision_date"], errors='coerce')
        
        # Sidebar Filters
        st.sidebar.header("Filter Options")
        
        # 2. Date Range Slider
        valid_dates = df["decision_date_dt"].dropna()
        if not valid_dates.empty:
            min_date = valid_dates.min().date()
            max_date = valid_dates.max().date()
            
            # Streamlit range sliders crash if min_value == max_value.
            # If we only have 1 case (or all cases are the same day), add a 1 day buffer to max_date
            import datetime
            if min_date == max_date:
                max_date = max_date + datetime.timedelta(days=1)
            
            # Default to full range
            start_date, end_date = st.sidebar.slider(
                "Select Date Range",
                min_value=min_date,
                max_value=max_date,
                value=(min_date, max_date),
                format="YYYY-MM-DD"
            )
            
            # Filter by Date
            df_filtered = df[
                df["decision_date_dt"].isna() | # Keep rows with missing dates in the filter view
                ((df["decision_date_dt"].dt.date >= start_date) & 
                 (df["decision_date_dt"].dt.date <= end_date))
            ]
        else:
            df_filtered = df

        # 2. Existing Text Filters
        search_query = st.sidebar.text_input("Search Cases (Title/Citation)", "")
        if search_query:
            df_filtered = df_filtered[
                df_filtered["case_name"].str.contains(search_query, case=False, na=False) |
                df_filtered["citation"].str.contains(search_query, case=False, na=False)
            ]

        st.title("Singapore Court Case Analytics")
        
        # --- Analytics Tabs ---
        tab0, tab1, tab_people, tab2 = st.tabs(["📊 Research Dashboard", "📈 Cluster Analytics", "👨‍⚖️ People Analytics", "🔌 API Documentation"])

        # --- TAB 0: Research Dashboard---
        with tab0:
            st.markdown("### Overview")
            
            # Load extra dashboard data
            try:
                top_queries, recent_reports, query_stats, report_stats = load_dashboard_data()
            except Exception as e:
                st.error(f"Error loading dashboard stats: {e}")
                top_queries, recent_reports, query_stats, report_stats = pd.DataFrame(), pd.DataFrame(), 0, 0
            
            # Top Metrics Row
            m1, m2, m3, m4 = st.columns(4)
            
            # 1. Total Cases
            total_cases = len(df)
            m1.metric("Total Cases Analyzed", f"{total_cases:,}", delta="+1 locally")
            
            # 2. Reports Generated
            m2.metric("JSONL File Size", f"{os.path.getsize('data/case_data.jsonl') // 1024} KB" if os.path.exists('data/case_data.jsonl') else "0 KB")
            
            # 3. Recent Queries
            m3.metric("Recent Queries", f"{query_stats}", "in the last 7 days")
            
            # 4. Top Case Category
            if not df["area_of_law"].empty:
                all_areas = []
                for areas in df["area_of_law"].dropna():
                    all_areas.extend([a.strip() for a in areas.split(';')])
                
                if all_areas:
                    top_cat = pd.Series(all_areas).mode()[0]
                else:
                    top_cat = "N/A"
            else:
                top_cat = "N/A"
            m4.metric("Top Case Category", top_cat, "Most frequent overall")

            st.divider()

            # Middle Row: Charts
            c1, c2 = st.columns(2)
            
            with c1:
                st.subheader("Case Categories")
                st.caption("Breakdown of all analyzed cases by primary area of law.")
                if not df.empty and all_areas:
                    # Parse all areas properly
                    all_areas_series = pd.Series(all_areas)
                    cat_counts = all_areas_series.value_counts().head(5).reset_index()
                    cat_counts.columns = ["Category", "Count"]
                    
                    if not cat_counts.empty:
                        # Horizontal Bar Chart - Blue
                        chart = alt.Chart(cat_counts).mark_bar(color="#0084ff", cornerRadiusEnd=3).encode(
                            x=alt.X("Count", title=None),
                            y=alt.Y("Category", sort="-x", title=None),
                            tooltip=["Category", "Count"]
                        ).properties(height=300)
                        
                        # Add text labels
                        text = chart.mark_text(
                            align='left',
                            baseline='middle',
                            dx=3
                        ).encode(
                            text='Count'
                        )
                        
                        st.altair_chart(chart + text, use_container_width=True)
                    else:
                        st.info("No category data.")
                else:
                    st.info("No data available.")

            with c2:
                st.subheader("Recent Query Topics")
                st.caption("Most common research topics in the last 30 days.")
                if not top_queries.empty:
                    # Reset index to get Topic column back
                    queries_df = top_queries.reset_index()
                    
                    # Horizontal Bar Chart - Grey
                    chart = alt.Chart(queries_df).mark_bar(color="#6c757d", cornerRadiusEnd=3).encode(
                        x=alt.X("Count", title=None),
                        y=alt.Y("Topic", sort="-x", title=None),
                        tooltip=["Topic", "Count"]
                    ).properties(height=300)

                    # Add text labels
                    text = chart.mark_text(
                        align='left',
                        baseline='middle',
                        dx=3
                    ).encode(
                        text='Count'
                    )

                    st.altair_chart(chart + text, use_container_width=True)
                else:
                    st.info("No queries yet.")

            st.divider()
            
            # Bottom Row: Show the actual case dataset
            st.subheader("Extracted Cases")
            st.caption("Click any row to view full details.")
            
            # Interactive Dataframe Selection
            df_display = df_filtered[[
                "citation", "case_name", "decision_date", 
                "area_of_law", "outcome", "judge_name"
            ]].copy()
            
            def format_areas(x):
                if pd.isna(x): return "N/A"
                areas = [a.strip() for a in str(x).split(';') if a.strip()]
                return " : ".join(areas) if areas else "N/A"
                
            df_display["area_of_law"] = df_display["area_of_law"].apply(format_areas)
            
            selection = st.dataframe(
                df_display,
                width='stretch',
                hide_index=True,
                on_select="rerun",
                selection_mode="single-row"
            )
            
            # Show Detailed Case View if a row is selected
            if selection and selection.selection.rows:
                selected_index = selection.selection.rows[0]
                case = df_filtered.iloc[selected_index]
                
                st.divider()
                st.subheader(f"Case Inspector: {case['citation']}")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**Case Name:** {case['case_name']}")
                    st.markdown(f"**Date:** {case['decision_date']}")
                    st.markdown(f"**Judge:** {case['judge_name']}")
                
                with col2:
                    st.markdown(f"**Plaintiff:** {case['plaintiff_name']}")
                    st.markdown(f"**Defendant:** {case['defendant_name']}")
                    st.markdown(f"**Counsel:** {case['plaintiff_counsel']} / {case['defendant_counsel']}")

                st.info(f"**Outcome:** {case['outcome']}")
                
                area_val = case.get('area_of_law')
                if pd.isna(area_val):
                    area_formatted = "N/A"
                else:
                    areas_list = [a.strip() for a in str(area_val).split(';') if a.strip()]
                    area_formatted = " : ".join(areas_list) if areas_list else "N/A"
                    
                st.caption(f"**Area of Law:** {area_formatted}")
                
                with st.expander("Read Judgment Text", expanded=True):
                    st.text(case.get("raw_judgment_text", "No text available."))

        # --- TAB 1: Cluster Analytics ---
        with tab1:
            st.subheader(f"Cluster Overview ({len(df_filtered)} Cases)")
            
            if not df_filtered.empty:
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("**Cases by Area of Law**")
                    if "area_of_law" in df_filtered.columns and not df_filtered["area_of_law"].empty:
                        expanded_areas = df_filtered["area_of_law"].dropna().astype(str).str.split(';').explode().str.strip()
                        expanded_areas = expanded_areas[expanded_areas != ""]
                        area_counts = expanded_areas.value_counts()
                        if not area_counts.empty:
                            st.bar_chart(area_counts)
                        else:
                            st.caption("No data.")
                    else:
                        st.caption("No data.")
                    
                with col2:
                    st.write("**Outcomes Distribution**")
                    outcome_counts = df_filtered["outcome"].value_counts()
                    if not outcome_counts.empty:
                        st.bar_chart(outcome_counts)
                    else:
                        st.caption("No data.")

                st.write("**Timeline of Cases**")
                # Group by Month-Year (Use 'M' to avoid ValueError)
                if "decision_date_dt" in df_filtered.columns and not df_filtered["decision_date_dt"].isna().all():
                    timeline = df_filtered.dropna(subset=["decision_date_dt"]).groupby([df_filtered["decision_date_dt"].dt.to_period("M")]).size()
                    if not timeline.empty:
                        timeline.index = timeline.index.astype(str) # Flatten for chart
                        st.line_chart(timeline)
                    else:
                        st.caption("No timeline data.")
                else:
                    st.caption("No timeline data.")
            else:
                st.info("No cases found in this cluster/range.")
                
        # --- TAB PEOPLE: People Analytics ---
        with tab_people:
            st.subheader("People Analytics (Judges & Lawyers)")
            st.caption("Insights into cases handled by specific judges and legal counsel based on the current filters. Click a row to view their specific cases.")
            
            if not df_filtered.empty:
                import itertools
                def parse_lawyers_list(counsel_str):
                    if pd.isna(counsel_str) or not str(counsel_str).strip():
                        return []
                    import re
                    clean_str = re.sub(r'\(.*?\)', '', str(counsel_str))
                    clean_str = re.sub(r'for the .*', '', clean_str, flags=re.IGNORECASE)
                    parts = re.split(r',|\band\b', clean_str)
                    return [p.strip() for p in parts if p.strip()]

                all_lawyers = []
                lawyer_to_cases = {}
                judge_to_cases = {}
                co_counsel_pairs = []
                lawyer_judge_pairs = []

                for _, row in df_filtered.iterrows():
                    p_counsel = parse_lawyers_list(row.get("plaintiff_counsel", ""))
                    d_counsel = parse_lawyers_list(row.get("defendant_counsel", ""))
                    
                    case_lawyers = list(set(p_counsel + d_counsel))
                    all_lawyers.extend(case_lawyers)
                    
                    for l in case_lawyers:
                        lawyer_to_cases.setdefault(l, []).append(row)
                        
                    judge = row.get("judge_name")
                    if pd.notna(judge) and str(judge).strip():
                        j_name = str(judge).strip()
                        judge_to_cases.setdefault(j_name, []).append(row)
                        for l in case_lawyers:
                            lawyer_judge_pairs.append({"Lawyer": l, "Judge": j_name})
                            
                    # Co-counsel pairs (combining within plaintiff or within defendant)
                    for pair in itertools.combinations(sorted(list(set(p_counsel))), 2):
                        co_counsel_pairs.append({"Lawyer A": pair[0], "Lawyer B": pair[1]})
                    for pair in itertools.combinations(sorted(list(set(d_counsel))), 2):
                        co_counsel_pairs.append({"Lawyer A": pair[0], "Lawyer B": pair[1]})

                lawyer_counts = pd.Series([l for l in all_lawyers if l]).value_counts().reset_index()
                lawyer_counts.columns = ["Lawyer", "Case Count"]
                
                if "judge_name" in df_filtered.columns:
                    judge_counts = df_filtered["judge_name"].dropna().apply(lambda x: str(x).strip()).value_counts().reset_index()
                    judge_counts.columns = ["Judge", "Case Count"]
                else:
                    judge_counts = pd.DataFrame(columns=["Judge", "Case Count"])

                st.markdown("### Top Practitioners")
                col1, col2 = st.columns(2)
                with col1:
                    st.write("**Top Lawyers by Case Count**")
                    if not lawyer_counts.empty:
                        lawyer_disp = lawyer_counts.head(20)
                        lawyer_selection = st.dataframe(lawyer_disp, hide_index=True, use_container_width=True, on_select="rerun", selection_mode="single-row")
                    else:
                        st.caption("No lawyer data found.")
                        lawyer_selection = None
                        
                with col2:
                    st.write("**Judges by Case Count**")
                    if not judge_counts.empty:
                        judge_disp = judge_counts.head(20)
                        judge_selection = st.dataframe(judge_disp, hide_index=True, use_container_width=True, on_select="rerun", selection_mode="single-row")
                    else:
                        st.caption("No judge data found.")
                        judge_selection = None

                # Selection Details
                if lawyer_selection and lawyer_selection.selection.rows:
                    sel_idx = lawyer_selection.selection.rows[0]
                    sel_lawyer = lawyer_disp.iloc[sel_idx]["Lawyer"]
                    st.divider()
                    st.subheader(f"Cases Handled by: {sel_lawyer}")
                    cases_for_lawyer = pd.DataFrame(lawyer_to_cases.get(sel_lawyer, []))
                    if not cases_for_lawyer.empty:
                        # Format the Data Table
                        cases_disp_l = cases_for_lawyer[["citation", "case_name", "decision_date", "area_of_law", "outcome"]].copy()
                        if "area_of_law" in cases_disp_l.columns:
                            cases_disp_l["area_of_law"] = cases_disp_l["area_of_law"].apply(lambda x: str(x).replace(" : ", "; ") if pd.notnull(x) else x)
                        
                        # 1. Provide High-Level Charts
                        lc1, lc2 = st.columns(2)
                        with lc1:
                            st.write(f"**{sel_lawyer}'s Areas of Law**")
                            if "area_of_law" in cases_for_lawyer.columns:
                                expanded_law = cases_for_lawyer["area_of_law"].dropna().astype(str).str.split(';').explode().str.strip()
                                expanded_law = expanded_law[(expanded_law != "") & (expanded_law != "N/A")]
                                if not expanded_law.empty:
                                    st.bar_chart(expanded_law.value_counts())
                                else:
                                    st.caption("No area of law data.")
                        with lc2:
                            st.write(f"**{sel_lawyer}'s Timeline**")
                            if "decision_date_dt" in cases_for_lawyer.columns and not cases_for_lawyer["decision_date_dt"].isna().all():
                                timeline = cases_for_lawyer.dropna(subset=["decision_date_dt"])
                                timeline_grouped = timeline.groupby(timeline["decision_date_dt"].dt.to_period("M")).size().reset_index(name="Case Count")
                                timeline_grouped["decision_date_dt"] = timeline_grouped["decision_date_dt"].dt.to_timestamp()
                                
                                if not timeline_grouped.empty:
                                    import plotly.express as px
                                    fig = px.line(timeline_grouped, x="decision_date_dt", y="Case Count", markers=True, color_discrete_sequence=["#4CAF50"])
                                    fig.update_layout(xaxis_title="Timeline", yaxis_title="Cases", margin=dict(l=0, r=0, t=10, b=0))
                                    st.plotly_chart(fig, use_container_width=True)
                                else:
                                    st.caption("No timeline data.")
                            else:
                                st.caption("No timeline data.")
                                
                        # 2. Provide the Data Table
                        st.write(f"**Case List ({len(cases_disp_l)} Cases)**")
                        st.dataframe(cases_disp_l, hide_index=True, use_container_width=True)

                if judge_selection and judge_selection.selection.rows:
                    sel_idx = judge_selection.selection.rows[0]
                    sel_judge = judge_disp.iloc[sel_idx]["Judge"]
                    st.divider()
                    st.subheader(f"Cases Heard by: {sel_judge}")
                    cases_for_judge = pd.DataFrame(judge_to_cases.get(sel_judge, []))
                    if not cases_for_judge.empty:
                        # Format the Data Table
                        cases_disp_j = cases_for_judge[["citation", "case_name", "decision_date", "area_of_law", "outcome"]].copy()
                        if "area_of_law" in cases_disp_j.columns:
                            cases_disp_j["area_of_law"] = cases_disp_j["area_of_law"].apply(lambda x: str(x).replace(" : ", "; ") if pd.notnull(x) else x)
                        
                         # 1. Provide High-Level Charts
                        jc1, jc2 = st.columns(2)
                        with jc1:
                            st.write(f"**{sel_judge}'s Areas of Law**")
                            if "area_of_law" in cases_for_judge.columns:
                                expanded_law = cases_for_judge["area_of_law"].dropna().astype(str).str.split(';').explode().str.strip()
                                expanded_law = expanded_law[(expanded_law != "") & (expanded_law != "N/A")]
                                if not expanded_law.empty:
                                    st.bar_chart(expanded_law.value_counts())
                                else:
                                    st.caption("No area of law data.")
                        with jc2:
                            st.write(f"**{sel_judge}'s Timeline**")
                            if "decision_date_dt" in cases_for_judge.columns and not cases_for_judge["decision_date_dt"].isna().all():
                                timeline = cases_for_judge.dropna(subset=["decision_date_dt"])
                                timeline_grouped = timeline.groupby(timeline["decision_date_dt"].dt.to_period("M")).size().reset_index(name="Case Count")
                                timeline_grouped["decision_date_dt"] = timeline_grouped["decision_date_dt"].dt.to_timestamp()
                                
                                if not timeline_grouped.empty:
                                    import plotly.express as px
                                    fig = px.line(timeline_grouped, x="decision_date_dt", y="Case Count", markers=True, color_discrete_sequence=["#FF9800"])
                                    fig.update_layout(xaxis_title="Timeline", yaxis_title="Cases", margin=dict(l=0, r=0, t=10, b=0))
                                    st.plotly_chart(fig, use_container_width=True)
                                else:
                                    st.caption("No timeline data.")
                            else:
                                st.caption("No timeline data.")
                                
                        # 2. Provide the Data Table
                        st.write(f"**Case List ({len(cases_disp_j)} Cases)**")
                        st.dataframe(cases_disp_j, hide_index=True, use_container_width=True)

                st.divider()
                st.markdown("### Entity Relationships")
                rel_col1, rel_col2 = st.columns(2)
                with rel_col1:
                    st.write("**Lawyers (Co-Counsel Network)**")
                    st.caption("Select a lawyer to view their co-counsels.")
                    if co_counsel_pairs:
                        co_counsel_df = pd.DataFrame(co_counsel_pairs)
                        all_co_lawyers = list(co_counsel_df["Lawyer A"]) + list(co_counsel_df["Lawyer B"])
                        co_lawyer_counts = pd.Series(all_co_lawyers).value_counts().reset_index()
                        co_lawyer_counts.columns = ["Lawyer", "Total Collaborations"]
                        co_counsel_selection = st.dataframe(co_lawyer_counts.head(20), hide_index=True, use_container_width=True, on_select="rerun", selection_mode="single-row")
                    else:
                        st.caption("No co-counsel data found.")
                with rel_col2:
                    st.write("**Judges (Lawyer Appearances)**")
                    st.caption("Select a judge to view lawyers who appeared before them.")
                    if lawyer_judge_pairs:
                        lj_df = pd.DataFrame(lawyer_judge_pairs)
                        lj_unique_judges = lj_df["Judge"].value_counts().reset_index()
                        lj_unique_judges.columns = ["Judge", "Total Appearances Heard"]
                        lawyer_judge_selection = st.dataframe(lj_unique_judges.head(20), hide_index=True, use_container_width=True, on_select="rerun", selection_mode="single-row")
                    else:
                        st.caption("No lawyer-judge data found.")

                if co_counsel_pairs and co_counsel_selection and co_counsel_selection.selection.rows:
                    sel_idx = co_counsel_selection.selection.rows[0]
                    sel_lawyer = co_lawyer_counts.iloc[sel_idx]["Lawyer"]
                    st.divider()
                    st.subheader(f"Co-Counsels for {sel_lawyer}")
                    mask_a = co_counsel_df["Lawyer A"] == sel_lawyer
                    mask_b = co_counsel_df["Lawyer B"] == sel_lawyer
                    collaborations = pd.concat([
                        co_counsel_df[mask_a]["Lawyer B"],
                        co_counsel_df[mask_b]["Lawyer A"]
                    ]).value_counts().reset_index()
                    collaborations.columns = ["Co-Counsel", "Collaborations"]
                    st.dataframe(collaborations, hide_index=True, use_container_width=True)

                if lawyer_judge_pairs and lawyer_judge_selection and lawyer_judge_selection.selection.rows:
                    sel_idx = lawyer_judge_selection.selection.rows[0]
                    sel_judge = lj_unique_judges.iloc[sel_idx]["Judge"]
                    st.divider()
                    st.subheader(f"Lawyers Appearing Before {sel_judge}")
                    mask_j = lj_df["Judge"] == sel_judge
                    appearances = lj_df[mask_j]["Lawyer"].value_counts().reset_index()
                    appearances.columns = ["Lawyer", "Appearances"]
                    st.dataframe(appearances, hide_index=True, use_container_width=True)
            else:
                st.info("No cases found in this cluster/range.")

        # --- TAB 2: API Documentation ---
        with tab2:
            st.markdown("## System API Reference")
            st.caption("The application exposes a REST API via `FastAPI` in `api.py`. You can use this to integrate with other systems.")
            
            st.info("To start the API server, run: `uvicorn api:app --reload` in your terminal.")
            
            st.divider()

            st.info("""
            **Architecture Note**: 
            - **Data**: Stored in **JSONL** locally (`data/case_data.jsonl`). All endpoints use this real, local dataset.
            - **API Server**: Currently running **locally** (`localhost`). 
            - **Implementation**: The API logic is centered in `api.py`, and scraping tasks utilize `pipeline.py`.
            """)
            
            # Use Railway public URL if available, otherwise default to localhost
            default_api_url = os.getenv("RAILWAY_PUBLIC_DOMAIN", "localhost:8000")
            if not default_api_url.startswith("http"):
                default_api_url = f"http://{default_api_url}"
                
            base_url = st.text_input("API Base URL", value=default_api_url)
            
            # --- Endpoint 1: GET /cases ---
            st.subheader("1. List Cases")
            st.markdown("`GET /cases`")
            st.markdown("Retrieves a paginated list of analyzed cases from the database.")
            
            with st.expander("Implementation Details & Usage"):
                st.markdown("""
                **Files**: `api.py`  
                **Data Source**: `data/case_data.jsonl` (Real Data)  
                **Logic**: Reads the local JSONL file line by line, sorts by newest first, and returns a paginated list of cases.
                """)
                tab_curl, tab_py = st.tabs(["cURL", "Python"])
                
                with tab_curl:
                    st.code(f"""
curl -X 'GET' \\
  '{base_url}/cases?limit=10&offset=0' \\
  -H 'accept: application/json'
                    """, language="bash")
                    
                with tab_py:
                    st.code(f"""
import requests

response = requests.get("{base_url}/cases", params={{"limit": 10}})
print(response.json())
                    """, language="python")

            # --- Endpoint 2: POST /cases/scrape ---
            st.divider()
            st.subheader("2. Trigger Scraper")
            st.markdown("`POST /cases/scrape`")
            st.markdown("Triggers a background job to scrape and process a list of LawNet URLs.")
            
            with st.expander("Implementation Details & Usage"):
                st.markdown("""
                **Files**: `api.py`, `pipeline.py`  
                **Data Source**: LawNet (Scraping)  
                **Logic**: Uses FastAPI's `BackgroundTasks` to trigger `process_case` from `pipeline.py` without blocking the API response.
                """)
                tab_curl, tab_py = st.tabs(["cURL", "Python"])
                
                with tab_curl:
                    st.code(f"""
curl -X 'POST' \\
  '{base_url}/cases/scrape' \\
  -H 'Content-Type: application/json' \\
  -d '{{
  "urls": [
    "https://www.lawnet.com/openlaw/cases/citation/[2026]+SGHC+27?ref=sg-sc"
  ],
  "force": true
}}'
                    """, language="bash")
                    
                with tab_py:
                    st.code(f"""
import requests

payload = {{
    "urls": ["https://www.lawnet.com/openlaw/cases/citation/[2026]+SGHC+27?ref=sg-sc"],
    "force": True
}}
response = requests.post("{base_url}/cases/scrape", json=payload)
print(response.json())
                    """, language="python")

            # --- Endpoint 3: Lawyers ---
            st.divider()
            st.subheader("3. List Lawyers")
            st.markdown("`GET /lawyers` / `GET /judges`")
            st.markdown("Retrieves statistics on unique lawyers or judges and their case counts.")
            with st.expander("Implementation Details & Usage"):
                 st.markdown("""
                **Files**: `api.py`  
                **Data Source**: `data/case_data.jsonl` (Real Data)  
                **Logic**: For lawyers, it parses counsel strings using regex to extract individual names (stripping firm names and roles). For judges, it counts occurrences of `judge_name`.
                """)
                 st.code('curl -X GET "http://localhost:8000/lawyers?limit=10"', language="bash")
                 st.code('curl -X GET "http://localhost:8000/judges?limit=10"', language="bash")

            # --- Endpoint 5: Health Check ---
            st.divider()
            st.subheader("5. Health Check")
            st.markdown("`GET /`")
            st.markdown("Simple health check to verify API status.")
            st.code('curl -X GET "http://localhost:8000/"', language="bash")

            st.divider()
            st.markdown("### Interactive Documentation")
            st.markdown("Once the API is running, visit `http://localhost:8000/docs` for the interactive Swagger UI.")

except Exception as e:
    st.error(f"Error loading dashboard: {e}")
    st.info("Check if data/case_data.jsonl format is valid.")
