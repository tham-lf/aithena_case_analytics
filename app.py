import streamlit as st
import pandas as pd
import sqlite3
import src.database as db

st.set_page_config(
    page_title="Singapore Court Case Analytics",
    page_icon="⚖️",
    layout="wide"
)

def load_data(db_name: str = "data/cases.db"):
    conn = db.get_db_connection(db_name)
    df = pd.read_sql_query("SELECT * FROM court_cases", conn)
    conn.close()
    return df
def load_dashboard_data(db_name: str = "data/cases.db"):
    conn = db.get_db_connection(db_name)
    queries = pd.read_sql_query("SELECT query_text as Topic, count as Count FROM search_queries ORDER BY count DESC LIMIT 5", conn)
    reports = pd.read_sql_query("SELECT title as 'Report Title', original_query as 'Original Query', created_at as 'Date Created' FROM generated_reports ORDER BY created_at DESC LIMIT 5", conn)
    reports["Actions"] = "View & Export" # Add static link for now
    
    # Get recent query count
    recent_query_count = conn.execute("SELECT sum(count) FROM search_queries").fetchone()[0] or 0
    report_count = conn.execute("SELECT count(*) FROM generated_reports").fetchone()[0] or 0
    
    conn.close()
    return queries.set_index("Topic"), reports, recent_query_count, report_count

st.title("⚖️ Singapore Court Case Analytics")
st.caption("Data source: LawNet OpenLaw (Scraped locally)")

try:
    df = load_data()
    
    if df.empty:
        st.warning("No data found in database. Run scraper first.")
    else:
        # Convert date column to datetime
        df["decision_date_dt"] = pd.to_datetime(df["decision_date"], errors='coerce')
        
        # Sidebar Filters
        st.sidebar.header("Filter Options")
        
        # 1. Date Range Slider
        if not df["decision_date_dt"].isnull().all():
            min_date = df["decision_date_dt"].min().date()
            max_date = df["decision_date_dt"].max().date()
            
            # Default to full range
            start_date, end_date = st.sidebar.slider(
                "Select Date Range",
                min_value=min_date,
                max_value=max_date,
                value=(min_date, max_date)
            )
            
            # Filter by Date
            df_filtered = df[
                (df["decision_date_dt"].dt.date >= start_date) & 
                (df["decision_date_dt"].dt.date <= end_date)
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
        tab0, tab1, tab2 = st.tabs(["📊 Research Dashboard", "📈 Cluster Analytics", "📄 Single Case View"])

        # --- TAB 0: Research Dashboard ---
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
            m1.metric("Total Cases Analyzed", f"{total_cases:,}", delta="+12% from last month")
            
            # 2. Reports Generated
            m2.metric("Reports Generated", f"{report_stats}", delta="+8 this month")
            
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
                    cat_counts = all_areas_series.value_counts().head(5)
                    if not cat_counts.empty:
                        st.bar_chart(cat_counts)
                    else:
                        st.info("No category data.")
                else:
                    st.info("No data available.")

            with c2:
                st.subheader("Recent Query Topics")
                st.caption("Most common research topics in the last 30 days.")
                if not top_queries.empty:
                    st.bar_chart(top_queries)
                else:
                    st.info("No queries yet.")

            st.divider()
            
            # Bottom Row: Recent Reports Table
            st.subheader("Recent Reports")
            st.caption("Your latest generated reports, ready for download.")
            
            if not recent_reports.empty:
                st.dataframe(
                    recent_reports,
                    width='stretch',
                    column_config={
                        "Actions": st.column_config.LinkColumn("Actions", display_text="View & Export")
                    },
                    hide_index=True
                )
            else:
                st.info("No reports generated yet.")


        # --- TAB 1: Cluster Analytics ---
        with tab1:
            st.subheader(f"Cluster Overview ({len(df_filtered)} Cases)")
            
            if not df_filtered.empty:
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("**Cases by Area of Law**")
                    area_counts = df_filtered["area_of_law"].value_counts()
                    if not area_counts.empty:
                        st.bar_chart(area_counts)
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
                # Group by Month-Year
                timeline = df_filtered.groupby([df_filtered["decision_date_dt"].dt.to_period("M")]).size()
                if not timeline.empty:
                    timeline.index = timeline.index.astype(str) # Flatten for chart
                    st.line_chart(timeline)
                else:
                    st.caption("No timeline data.")
            else:
                st.info("No cases found in this cluster/range.")
                
        # --- TAB 2: Single Case View ---
        with tab2:
            st.subheader("Detailed Case List")
        
            # Main Data Table
            st.dataframe(
                df_filtered[[
                    "citation", "case_name", "decision_date", 
                    "area_of_law", "outcome", "judge_name"
                ]],
                width='stretch'
            )

            st.divider()
            st.subheader("Case Inspector")
            
            citations = df_filtered["citation"].unique().tolist()
            if citations:
                selected_citation = st.selectbox("Select Case to View", citations)

                if selected_citation:
                    case = df_filtered[df_filtered["citation"] == selected_citation].iloc[0]
                    
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
                    st.caption(f"**Area of Law:** {case['area_of_law']}")
                    
                    with st.expander("Read Judgment Text"):
                        st.text(case["raw_judgment_text"])
            else:
                st.warning("No cases available to inspect.")

except sqlite3.OperationalError:
    st.error("Database not found! Please run the pipeline script first to generate `cases.db`.")

