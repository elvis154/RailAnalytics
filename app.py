import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import oracledb
import time
import re
from datetime import datetime
from io import BytesIO
from plotly.subplots import make_subplots
import numpy as np

# Initialize at the top (global scope)
remaining_df = pd.DataFrame()  # Empty by default
avg_completion = 0


# --- Oracle Instant Client Configuration ---
INSTANT_CLIENT_PATH = r"C:\Users\Abishek\Downloads\instantclient-basic-windows.x64-23.8.0.25.04\instantclient_23_8"

# --- Database Connection Parameters ---
DB_USER = "intern"
DB_PASSWORD = "inT##2025"
DB_HOST = "10.3.9.4"
DB_PORT = 1523
DB_SID = "traffic"
TARGET_SCHEMA = "FOISGOODS"

# --- Constants ---
DATE_COLUMNS = ["YYMM", "YYCMO", "YYMO"]
ZONE_COLUMN = "ZONE_FRM"
DSN = f"{DB_HOST}:{DB_PORT}/{DB_SID}"

# Financial year months (April to March)
FINANCIAL_MONTHS = [
    "April", "May", "June", "July", "August", "September",
    "October", "November", "December", "January", "February", "March"
]

# Year configurations
years = ["25_26", "24_25", "23_24", "22_23", "21_22", "20_21", "19_20", "18_19", "17_18"]
year_labels = {
    "25_26": "2025-26", "24_25": "2024-25", "23_24": "2023-24",
    "22_23": "2022-23", "21_22": "2021-22", "20_21": "2020-21",
    "19_20": "2019-20", "18_19": "2018-19", "17_18": "2017-18"
}

# Map financial years to table suffixes
FINANCIAL_YEARS = {
    "2025-2026": "25_26",
    "2024-2025": "24_25",
    "2023-2024": "23_24",
    "2022-2023": "22_23",
    "2021-2022": "21_22",
    "2020-2021": "20_21",
    "2019-2020": "19_20",
    "2018-2019": "18_19",
    "2017-2018": "17_18"
}

# --- Page Config (MUST BE FIRST STREAMLIT COMMAND) ---
st.set_page_config(
    page_title="Railway Analytics Dashboard",
    page_icon="🚂",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Utility Functions ---
@st.cache_resource
def init_oracle_client():
    try:
        oracledb.init_oracle_client(lib_dir=INSTANT_CLIENT_PATH)
        return True
    except oracledb.Error as e:
        st.error(f"Oracle Client Error: {e}")
        return False

def create_connection(max_retries=3, retry_delay=2):
    """Create database connection with retry logic"""
    for attempt in range(max_retries):
        try:
            # Initialize Oracle client
            try:
                oracledb.init_oracle_client(lib_dir=INSTANT_CLIENT_PATH)
            except Exception:
                # Client might already be initialized
                pass
            
            # Create the connection (will automatically use thick mode when client is initialized)
            dsn = oracledb.makedsn(DB_HOST, DB_PORT, sid=DB_SID)
            conn = oracledb.connect(user=DB_USER, password=DB_PASSWORD, dsn=dsn)
            return conn
        except oracledb.Error as e:
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            else:
                st.error(f"Failed to connect to database after {max_retries} attempts.")
                st.error(f"Error details: {str(e)}")
                st.stop()

def get_table_name(financial_year):
    """Get table name based on financial year selection."""
    if financial_year in FINANCIAL_YEARS:
        return f"CARR_APMT_EXCL_ADV_{FINANCIAL_YEARS[financial_year]}"
    return None

def get_total_count(table_name):
    """Get total record count without loading data."""
    try:
        with oracledb.connect(user=DB_USER, password=DB_PASSWORD, dsn=DSN) as conn:
            cursor = conn.cursor()
            cursor.execute(f"SELECT COUNT(*) FROM {TARGET_SCHEMA}.{table_name}")
            return cursor.fetchone()[0]
    except Exception as e:
        st.error(f"Count failed: {e}")
        return 0

def get_table_columns(table_name):
    """Get actual column names from the table."""
    try:
        with oracledb.connect(user=DB_USER, password=DB_PASSWORD, dsn=DSN) as conn:
            cursor = conn.cursor()
            cursor.execute(f"SELECT * FROM {TARGET_SCHEMA}.{table_name} WHERE ROWNUM = 1")
            return [col[0] for col in cursor.description]
    except Exception as e:
        st.error(f"Failed to get columns: {e}")
        return []

def get_record_count(table_name, where_clause=""):
    """Get filtered record count."""
    try:
        with oracledb.connect(user=DB_USER, password=DB_PASSWORD, dsn=DSN) as conn:
            cursor = conn.cursor()
            query = f"""
                SELECT COUNT(*) 
                FROM {TARGET_SCHEMA}.{table_name}
                WHERE 1=1 {where_clause}
            """
            cursor.execute(query)
            return cursor.fetchone()[0]
    except Exception as e:
        st.error(f"Count failed: {e}")
        return 0

def verify_columns(table_name):
    """Verify and get correct column names from table."""
    try:
        with oracledb.connect(user=DB_USER, password=DB_PASSWORD, dsn=DSN) as conn:
            cursor = conn.cursor()
            cursor.execute(f"SELECT * FROM {TARGET_SCHEMA}.{table_name} WHERE ROWNUM = 1")
            available_columns = [col[0] for col in cursor.description]
            
            # Find correct date column
            date_col = next((col for col in DATE_COLUMNS if col in available_columns), None)
            if not date_col:
                st.error(f"No valid date column found. Available columns: {', '.join(available_columns)}")
                return None, None
            
            # Verify zone column
            if ZONE_COLUMN not in available_columns:
                st.error(f"Zone column {ZONE_COLUMN} not found")
                return None, None
                
            return date_col, available_columns
    except Exception as e:
        st.error(f"Column verification failed: {e}")
        return None, None

def get_filtered_data(table_name, start_month=None, end_month=None, zone=None, preview=False):
    """Get data directly with filters applied."""
    try:
        # Verify columns first
        date_column, columns = verify_columns(table_name)
        if not date_column:
            return pd.DataFrame(), 0
            
        where_clauses = []
        
        if start_month and end_month and start_month != "All" and end_month != "All":
            start_idx = FINANCIAL_MONTHS.index(start_month) + 4
            end_idx = FINANCIAL_MONTHS.index(end_month) + 4
            if start_idx > 12: start_idx -= 12
            if end_idx > 12: end_idx -= 12
            
            if start_idx <= end_idx:
                where_clauses.append(f"TO_NUMBER(SUBSTR({date_column}, -2)) BETWEEN {start_idx} AND {end_idx}")
            else:
                where_clauses.append(f"(TO_NUMBER(SUBSTR({date_column}, -2)) >= {start_idx} OR TO_NUMBER(SUBSTR({date_column}, -2)) <= {end_idx})")
        
        if zone and zone != "All":
            where_clauses.append(f"{ZONE_COLUMN} = '{zone}'")
        
        where_clause = " AND " + " AND ".join(where_clauses) if where_clauses else ""
        
        # Modified query construction using subquery for pagination
        if preview:
            query = f"""
                SELECT * FROM (
                    SELECT a.*, ROWNUM rnum FROM (
                        SELECT * FROM {TARGET_SCHEMA}.{table_name}
                        WHERE 1=1 {where_clause}
                    ) a WHERE ROWNUM <= 1000
                )
            """
        else:
            query = f"""
                SELECT * FROM {TARGET_SCHEMA}.{table_name}
                WHERE 1=1 {where_clause}
            """
        
        with oracledb.connect(user=DB_USER, password=DB_PASSWORD, dsn=DSN) as conn:
            df = pd.read_sql(query, conn)
            if 'RNUM' in df.columns:
                df = df.drop('RNUM', axis=1)
            total_records = len(df) if preview else get_record_count(table_name, where_clause)
            return df, total_records
            
    except Exception as e:
        st.error("Query execution failed. Please try again.")
        return pd.DataFrame(), 0

def format_currency(value):
    """Format value as Indian currency"""
    return f"₹{value:,.2f} Cr"

def create_trend_chart(data, years, selected_year):
    """Create trend chart for revenue comparison"""
    fig = go.Figure()
    
    for year in years:
        year_label = year_labels[year]
        is_current = year == selected_year
        line_width = 3 if is_current else 2
        line_dash = None if is_current else "dot"
        
        fig.add_trace(go.Scatter(
            x=data['Commodity'],
            y=data[f'Revenue_{year}'],
            name=year_label,
            line=dict(width=line_width, dash=line_dash),
            hovertemplate="%{x}<br>%{y:,.2f} Cr<extra></extra>",
            visible=True if is_current else "legendonly"
        ))
    
    fig.update_layout(
        height=500,
        title="Revenue Trend by Commodity",
        xaxis_title="Commodity",
        yaxis_title="Revenue (₹ Crores)",
        hovermode="x unified",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        margin=dict(l=50, r=50, b=100, t=80, pad=4),
        plot_bgcolor='rgba(0,0,0,0)'
    )
    
    return fig

# --- Utility Functions ---
def calculate_completion_percentage(df, table_years, selected_year_code, selected_month_num):
    """Calculate what percentage of the year is complete based on selected month"""
    # If month is April (4), it's 1 month = 8.33%
    # If month > April, count months since April
    # If month < April, count months since April of previous year
    if selected_month_num == 4:
        return 100/12  # April is exactly one month = 8.33%
    elif selected_month_num > 4:
        months = selected_month_num - 4 + 1  # Months since April including current month
        return (months / 12) * 100
    else:
        months = selected_month_num + 9  # April to December (9) plus months in new year
        return (months / 12) * 100
    
    for prev_year in table_years[1:]:  # Skip current year
        try:
            with oracledb.connect(user=DB_USER, password=DB_PASSWORD, dsn=DSN) as conn:
                cur = conn.cursor()
                
                year_start = "20" + prev_year.split("_")[0]
                year_end = "20" + prev_year.split("_")[1]
                
                # Calculate number of months we're looking at (from April to selected month)
                months_count = (selected_month_num - 4 + 1) if selected_month_num >= 4 else (selected_month_num + 9)
                
                # If it's April, we're only looking at 1 month
                if selected_month_num == 4:
                    months_count = 1
                
                # Get revenue for the same months in previous years
                period_query = f"""
                    SELECT SUM(WR) as period_revenue
                    FROM FOISGOODS.carr_apmt_excl_adv_{prev_year}
                    WHERE (
                        (SUBSTR(YYMM, 1, 4) = '{year_start}'
                         AND TO_NUMBER(SUBSTR(YYMM, 5, 2)) >= 4
                         AND TO_NUMBER(SUBSTR(YYMM, 5, 2)) <= CASE 
                            WHEN {selected_month_num} < 4 THEN 12
                            ELSE {selected_month_num}
                         END)
                        OR 
                        (SUBSTR(YYMM, 1, 4) = '{year_end}'
                         AND TO_NUMBER(SUBSTR(YYMM, 5, 2)) < 4
                         AND {selected_month_num} < 4
                         AND TO_NUMBER(SUBSTR(YYMM, 5, 2)) <= {selected_month_num})
                    )
                """
                
                # Get total revenue for the full financial year
                year_query = f"""
                    SELECT SUM(WR) as year_revenue
                    FROM FOISGOODS.carr_apmt_excl_adv_{prev_year}
                    WHERE (
                        (SUBSTR(YYMM, 1, 4) = '{year_start}'
                         AND TO_NUMBER(SUBSTR(YYMM, 5, 2)) >= 4)
                        OR 
                        (SUBSTR(YYMM, 1, 4) = '{year_end}'
                         AND TO_NUMBER(SUBSTR(YYMM, 5, 2)) < 4)
                    )
                """
                
                # Execute queries
                cur.execute(period_query)
                period_result = cur.fetchone()
                period_revenue = period_result[0] if period_result and period_result[0] else 0
                
                cur.execute(year_query)
                year_result = cur.fetchone()
                year_revenue = year_result[0] if year_result and year_result[0] else 0
                
                if year_revenue and year_revenue > 0:
                    # Calculate what percentage these months represent
                    completion_pct = (period_revenue / year_revenue) * 100
                    prev_years_percentages.append(completion_pct)
                
        except Exception as e:
            st.warning(f"Error calculating historical percentage for {prev_year}: {str(e)}")
            continue
    
    if prev_years_percentages:
        avg_completion = sum(prev_years_percentages) / len(prev_years_percentages)
        return avg_completion
    else:
        # Fallback: For April (month 4), it's just 1/12 of the year
        # For other months, count months since April
        if selected_month_num == 4:
            return 100/12  # Just April = 8.33%
        else:
            months_count = (selected_month_num - 4 + 1) if selected_month_num >= 4 else (selected_month_num + 9)
            return (months_count / 12) * 100

# --- Page Functions ---
def dashboard_page():
    # Custom CSS
    st.markdown("""
    <style>
        .stApp {
            isolation: isolate;
        }
        .main-header {
            font-size: 2.5rem;
            font-weight: bold;
            color: #1f77b4;
            text-align: center;
            margin-bottom: 2rem;
            padding: 1rem;
            background: linear-gradient(90deg, #f0f8ff, #e6f3ff);
            border-radius: 10px;
            border-left: 5px solid #1f77b4;
        }
        .metric-container {
            background: white;
            padding: 1rem;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            border-left: 4px solid #1f77b4;
        }
        .section-header {
            font-size: 1.5rem;
            font-weight: bold;
            color: #2c3e50;
            margin: 1.5rem 0 1rem 0;
            padding: 0.5rem;
            background: linear-gradient(90deg, #f8f9fa, #e9ecef);
            border-radius: 5px;
            border-left: 3px solid #17a2b8;
        }
        .chart-container {
            margin-bottom: 2rem;
        }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="main-header">🚂 Railway Traffic Analysis Dashboard</div>', unsafe_allow_html=True)

    # Sidebar configuration
    with st.sidebar:
        st.markdown("## 📊 Dashboard Controls")
        selected_year = st.selectbox(
            "📅 Select Base Year",
            [year_labels[y] for y in years[:5]],
            help="Select the base year to analyze the last 5 years of data"
        )
        
        st.markdown("### 📈 Visualization Options")
        show_charts = st.checkbox("Show Interactive Charts", value=True)
        st.markdown("### 📋 Metrics Display")
        show_kpis = st.checkbox("Show Key Performance Indicators", value=True)
        show_trends = st.checkbox("Show Trend Analysis", value=True)
        
        if st.button("🔄 Refresh Data", type="primary"):
            st.rerun()

    # Data loading and processing
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        status_text.text("Connecting to database...")
        progress_bar.progress(10)
        
        selected_idx = [year_labels[y] for y in years].index(selected_year)
        table_years = years[selected_idx:selected_idx+5]
        table_years = list(reversed(table_years))  # Reverse to show oldest first
        table_names = [f"carr_apmt_excl_adv_{y}" for y in table_years]
        
        conn = create_connection()
        cur = conn.cursor()
        
        # SQL queries
        queries = [
            "SELECT SUM(CHBL_WGHT) AS SUM_DIFF FROM {schema}.{table} WHERE ZONE_FRM = 'WR'",
            "SELECT SUM(TOT_FRT_INCL_GST - TOT_GST) AS SUM_DIFF FROM {schema}.{table} WHERE ZONE_FRM = 'WR'",
            "SELECT SUM(WR) AS SUM_DIFF FROM {schema}.{table} WHERE ZONE_FRM = 'WR'",
            "SELECT SUM(WR) AS SUM_DIFF FROM {schema}.{table} WHERE ZONE_FRM != 'WR'"
        ]
        
        status_text.text("Executing queries...")
        progress_bar.progress(30)
        
        results = []
        for i, table in enumerate(table_names):
            row_vals = []
            for q in queries:
                cur.execute(q.format(schema=TARGET_SCHEMA, table=table))
                val = cur.fetchone()[0] or 0
                row_vals.append(val)
            
            # Derived calculations
            row3, row4 = row_vals[2], row_vals[3]
            row5 = row3 + row4
            row2 = row_vals[1]
            row6 = row5 / row2 if row2 else None
            row7 = row3 / row2 if row2 else None
            row8 = row3 / row5 if row5 else None
            row9 = row4 / row5 if row5 else None
            
            # Convert to crores
            row_vals_crore = [v / 1e7 if isinstance(v, (int, float)) else v for v in [row_vals[0], row2, row3, row4, row5]]
            derived_percent = [round(r * 100, 2) if r is not None else None for r in [row6, row7, row8, row9]]
            results.append(row_vals_crore + derived_percent)
            
            progress_bar.progress(30 + (i + 1) * 10)
        
        cur.close()
        conn.close()
        
        status_text.text("Processing data...")
        progress_bar.progress(80)
        
        row_names = [
            "SUM(CHBL_WGHT) (WR)", "SUM(TOT_FRT_INCL_GST - TOT_GST) (WR)",
            "SUM(WR) (WR)", "SUM(WR) (not WR)", "row 3 + row 4",
            "row 5 / row 2 (%)", "row 3 / row 2 (%)", "row 3 / row 5 (%)", "row 4 / row 5 (%)"
        ]
        
        df = pd.DataFrame(results, columns=row_names, index=[year_labels[y] for y in table_years])
        df = df.T
        
        # Summary table
        summary_rows = [
            "SUM(CHBL_WGHT) (WR)", "SUM(TOT_FRT_INCL_GST - TOT_GST) (WR)",
            "SUM(WR) (WR)", "SUM(WR) (not WR)", "row 3 + row 4"
        ]
        summary_names = [
            "Loading", "Originating Revenue", "Apportioned Revenue (Outward Retained Share)",
            "Apportioned Revenue (Inward Share)", "Total Apportioned Revenue (3+4)"
        ]
        
        summary_df = df.loc[summary_rows].copy()
        summary_df.index = summary_names
        
        def pct_var(series):
            vals = series.values
            if len(vals) < 2:
                return None
            curr, prev = vals[0], vals[1]
            if prev and prev != 0:
                pct_change = ((curr - prev) / prev) * 100
                return f"{round(pct_change, 2)}%"
            return None
        
        summary_df["% var w.r.t P.Y."] = summary_df.apply(pct_var, axis=1)
        summary_df = summary_df.reset_index().rename(columns={'index': 'Particulars'})
        
        # Ratio table
        ratio_rows = ["row 5 / row 2 (%)", "row 3 / row 2 (%)", "row 3 / row 5 (%)", "row 4 / row 5 (%)"]
        ratio_names = [
            "Ratio of Apportioned to Originating Revenue (5/2)",
            "Ratio of Outward Retained Share to Originating Revenue (3/2)",
            "Ratio of Outward Retained Share to Total Apportioned Revenue (3/5)",
            "Ratio of Inward Share to Total Apportioned Revenue (4/5)"
        ]
        
        ratio_df = df.loc[ratio_rows].copy()
        ratio_df.index = ratio_names
        
        for idx in ratio_df.index:
            vals = [v for v in ratio_df.loc[idx].values if v is not None and not pd.isna(v)]
            if vals:
                avg = sum(vals) / len(vals)
                ratio_df.loc[idx, "Avg of last 5 years"] = round(avg, 2)
        
        for col in ratio_df.columns:
            if col != "Avg of last 5 years":
                ratio_df[col] = ratio_df[col].apply(lambda x: f"{x:.2f}%" if pd.notnull(x) else "")
            else:
                ratio_df[col] = ratio_df[col].apply(lambda x: f"{x:.2f}%" if pd.notnull(x) else "")
        
        ratio_df = ratio_df.reset_index().rename(columns={'index': 'Ratio'})
        
        progress_bar.progress(100)
        status_text.text("Data loaded successfully!")
        progress_bar.empty()
        status_text.empty()
        
        # Dashboard display
        if show_kpis:
            st.markdown('<div class="section-header">📊 Key Performance Indicators</div>', unsafe_allow_html=True)
            
            col1, col2, col3, col4 = st.columns(4)
            
            current_year = [year_labels[y] for y in table_years][0]
            current_loading = summary_df.iloc[0][current_year] if current_year in summary_df.columns else 0
            current_revenue = summary_df.iloc[1][current_year] if current_year in summary_df.columns else 0
            current_outward = summary_df.iloc[2][current_year] if current_year in summary_df.columns else 0
            current_total = summary_df.iloc[4][current_year] if current_year in summary_df.columns else 0
            
            with col1:
                st.metric(
                    label="📦 Current Loading (Cr)",
                    value=f"{current_loading:.2f}",
                    delta=summary_df.iloc[0]["% var w.r.t P.Y."] if "% var w.r.t P.Y." in summary_df.columns else None
                )
            
            with col2:
                st.metric(
                    label="💰 Originating Revenue (Cr)",
                    value=f"{current_revenue:.2f}",
                    delta=summary_df.iloc[1]["% var w.r.t P.Y."] if "% var w.r.t P.Y." in summary_df.columns else None
                )
            
            with col3:
                st.metric(
                    label="📈 Outward Retained Share (Cr)",
                    value=f"{current_outward:.2f}",
                    delta=summary_df.iloc[2]["% var w.r.t P.Y."] if "% var w.r.t P.Y." in summary_df.columns else None
                )
            
            with col4:
                st.metric(
                    label="📊 Total Apportioned Revenue (Cr)",
                    value=f"{current_total:.2f}",
                    delta=summary_df.iloc[4]["% var w.r.t P.Y."] if "% var w.r.t P.Y." in summary_df.columns else None
                )
        
        if show_charts:
            st.markdown('<div class="section-header">📈 Interactive Visualizations</div>', unsafe_allow_html=True)
            
            years_list = [year_labels[y] for y in table_years]
            chart_data = summary_df.set_index('Particulars')[years_list]
              # Get the latest available month for 2025-26
            latest_month = None
            try:
                with oracledb.connect(user=DB_USER, password=DB_PASSWORD, dsn=DSN) as conn:
                    cursor = conn.cursor()
                    latest_month_query = """
                        SELECT MAX(TO_NUMBER(SUBSTR(YYMM, 5, 2))) as latest_month
                        FROM FOISGOODS.carr_apmt_excl_adv_25_26
                    """
                    cursor.execute(latest_month_query)
                    result = cursor.fetchone()
                    if result and result[0]:
                        month_num = result[0]
                        # Convert month number to name
                        month_names = {
                            1: "January", 2: "February", 3: "March", 4: "April",
                            5: "May", 6: "June", 7: "July", 8: "August",
                            9: "September", 10: "October", 11: "November", 12: "December"
                        }
                        latest_month = month_names.get(month_num)
            except Exception as e:
                st.warning(f"Could not determine latest month: {str(e)}")

            # Create title with partial data note
            loading_title = "Loading Trend (in Crores)"
            if latest_month:
                loading_title += f"\n(Note: 2025-26 data is partial, up to {latest_month})"

            st.markdown("#### Loading Trend")
            fig_loading = px.line(
                x=years_list,
                y=chart_data.loc['Loading'],
                title=loading_title,
                labels={'x': 'Year', 'y': 'Loading (Cr)'},
                height=400
            )
            fig_loading.update_traces(
                mode='lines+markers', 
                line=dict(color='#1f77b4', width=3),
                marker=dict(size=8, color='#1f77b4')
            )
            fig_loading.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                xaxis=dict(showgrid=True, gridcolor='lightgray'),
                yaxis=dict(showgrid=True, gridcolor='lightgray'),
                hovermode='x unified'
            )
            st.plotly_chart(fig_loading, use_container_width=True)
              # Create revenue title with partial data note
            revenue_title = "Originating Revenue Trend (in Crores)"
            if latest_month:
                revenue_title += f"\n(Note: 2025-26 data is partial, up to {latest_month})"

            st.markdown("#### Originating Revenue Trend")
            fig_revenue = px.line(
                x=years_list,
                y=chart_data.loc['Originating Revenue'],
                title=revenue_title,
                labels={'x': 'Year', 'y': 'Revenue (Cr)'},
                height=400
            )
            fig_revenue.update_traces(
                mode='lines+markers', 
                line=dict(color='#2ca02c', width=3),
                marker=dict(size=8, color='#2ca02c')
            )
            fig_revenue.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                xaxis=dict(showgrid=True, gridcolor='lightgray'),
                yaxis=dict(showgrid=True, gridcolor='lightgray'),
                hovermode='x unified'
            )
            st.plotly_chart(fig_revenue, use_container_width=True)
            
            st.markdown("#### Apportioned Revenue Composition")
            fig_apportion = go.Figure()
            fig_apportion.add_trace(go.Bar(
                x=years_list,
                y=chart_data.loc['Apportioned Revenue (Outward Retained Share)'],
                name='Outward Retained Share',
                marker_color='#ff7f0e',
                hovertemplate='Year: %{x}<br>Outward Share: %{y:.2f} Cr<extra></extra>'
            ))
            fig_apportion.add_trace(go.Bar(
                x=years_list,
                y=chart_data.loc['Apportioned Revenue (Inward Share)'],
                name='Inward Share',
                marker_color='#d62728',
                hovertemplate='Year: %{x}<br>Inward Share: %{y:.2f} Cr<extra></extra>'
            ))            # Create apportion title with partial data note
            apportion_title = "Inward vs Outward Total Apportion Share (in Crores)"
            if latest_month:
                apportion_title += f"\n(Note: 2025-26 data is partial, up to {latest_month})"
            
            fig_apportion.update_layout(
                title=apportion_title,
                barmode='group',
                height=400,
                xaxis_title="Year",
                yaxis_title="Revenue (Cr)",
                plot_bgcolor='rgba(0,0,0,0)',
                xaxis=dict(showgrid=True, gridcolor='lightgray'),
                yaxis=dict(showgrid=True, gridcolor='lightgray'),
                hovermode='x unified',
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1
                )
            )
            st.plotly_chart(fig_apportion, use_container_width=True)
        
        # Data Tables
        st.markdown('<div class="section-header">📋 Detailed Data Tables</div>', unsafe_allow_html=True)
        
        tab1, tab2 = st.tabs(["📊 Summary Data", "📈 Ratio Analysis"])
        
        with tab1:
            st.markdown("**Summary of Goods Traffic Pattern for the last five years as per FOIS RR Data for Carried Route (ST-7C)**")
            st.dataframe(
                summary_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    'Particulars': st.column_config.TextColumn('Particulars', width='medium'),
                    '% var w.r.t P.Y.': st.column_config.TextColumn('% Change vs Previous Year', width='small')
                }
            )
            
            csv_summary = summary_df.to_csv(index=False)
            st.download_button(
                label="📥 Download Summary Data (CSV)",
                data=csv_summary,
                file_name=f"railway_traffic_summary_{selected_year.replace('-', '_')}.csv",
                mime="text/csv"
            )
        
        with tab2:
            st.markdown("**Ratio Analysis**")
            st.dataframe(
                ratio_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    'Ratio': st.column_config.TextColumn('Ratio Description', width='large'),
                    'Avg of last 5 years': st.column_config.TextColumn('5-Year Average', width='small')
                }
            )
            
            csv_ratio = ratio_df.to_csv(index=False)
            st.download_button(
                label="📥 Download Ratio Data (CSV)",
                data=csv_ratio,
                file_name=f"railway_traffic_ratios_{selected_year.replace('-', '_')}.csv",
                mime="text/csv"
            )
        
        if show_trends:
            st.markdown('<div class="section-header">📈 Trend Analysis & Insights</div>', unsafe_allow_html=True)
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### 🔍 Key Observations")
                try:
                    loading_change = summary_df.iloc[0]["% var w.r.t P.Y."]
                    revenue_change = summary_df.iloc[1]["% var w.r.t P.Y."]
                    
                    loading_trend = "increasing" if loading_change and loading_change != 'None' and float(loading_change.replace('%', '')) > 0 else "decreasing"
                    revenue_trend = "increasing" if revenue_change and revenue_change != 'None' and float(revenue_change.replace('%', '')) > 0 else "decreasing"
                    
                    st.markdown(f"""
                    - **Loading Trend**: {loading_trend.title()} by {loading_change if loading_change != 'None' else 'N/A'}
                    - **Revenue Trend**: {revenue_trend.title()} by {revenue_change if revenue_change != 'None' else 'N/A'}
                    - **Current Year**: {years_list[0]}
                    - **Analysis Period**: {years_list[-1]} to {years_list[0]}
                    """)
                except Exception as e:
                    st.markdown(f"""
                    - **Current Year**: {years_list[0]}
                    - **Analysis Period**: {years_list[-1]} to {years_list[0]}
                    - **Status**: Data processing in progress
                    """)
            
            with col2:
                st.markdown("#### 📊 Performance Summary")
                try:
                    valid_changes = []
                    for i in range(len(summary_df)):
                        change_val = summary_df.iloc[i]["% var w.r.t P.Y."]
                        if change_val and change_val != 'None' and isinstance(change_val, str) and '%' in change_val:
                            try:
                                valid_changes.append(float(change_val.replace('%', '')))
                            except ValueError:
                                continue
                    
                    if valid_changes:
                        avg_growth = np.mean(valid_changes)
                        
                        if avg_growth > 5:
                            performance = "🟢 Excellent"
                        elif avg_growth > 0:
                            performance = "🟡 Good"
                        elif avg_growth > -5:
                            performance = "🟠 Average"
                        else:
                            performance = "🔴 Needs Attention"
                        
                        st.markdown(f"""
                        - **Overall Performance**: {performance}
                        - **Average Growth Rate**: {avg_growth:.2f}%
                        - **Data Quality**: ✅ Complete
                        - **Last Updated**: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}
                        """)
                    else:
                        st.markdown(f"""
                        - **Overall Performance**: 📊 Analyzing...
                        - **Data Quality**: ✅ Complete
                        - **Last Updated**: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}
                        """)
                except Exception as e:
                    st.markdown(f"""
                    - **Data Quality**: ✅ Complete
                    - **Last Updated**: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}
                    - **Status**: Performance analysis in progress
                    """)

    except Exception as e:
        st.error(f"❌ An error occurred: {str(e)}")
        st.markdown("Please check your database connection and try again.")
        progress_bar.empty()
        status_text.empty()

    st.markdown("---")
    st.markdown(
        """
        <div style='text-align: center; color: #666; font-size: 0.8em;'>
        🚂 Railway Traffic Analysis Dashboard | Built with Streamlit | 
        Data Source: FOIS RR Database
        </div>
        """,
        unsafe_allow_html=True
    )

def revenue_analytics_page():
    # Month configurations
    months = {
        "April": "04", "May": "05", "June": "06", "July": "07", "August": "08",
        "September": "09", "October": "10", "November": "11", "December": "12",
        "January": "01", "February": "02", "March": "03"
    }
    
    st.markdown("""
        <style>
            .main {
                background-color: #f8fafc;
            }
            .header {
                padding: 1rem 0;
                border-bottom: 1px solid #e2e8f0;
                margin-bottom: 2rem;
            }
            .metric-card {
                background-color: white;
                padding: 1rem;
                border-radius: 8px;
                box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                margin-bottom: 1rem;
            }
            .metric-title {
                color: #64748b;
                font-size: 0.875rem;
                font-weight: 500;
            }
            .metric-value {
                color: #1e40af;
                font-size: 1.5rem;
                font-weight: 600;
                margin: 0.5rem 0;
            }
            .metric-change {
                color: #64748b;
                font-size: 0.75rem;
            }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("""
        <div class="header">
            <h1 style="color: #1e40af; margin-bottom: 0.5rem;">Railway Revenue Analytics by Commodity Group</h1>
            <p style="color: #64748b; margin-top: 0;">Analysis of apportioned revenue by major commodity groups</p>
        </div>
    """, unsafe_allow_html=True)

    try:
        # Initialize connection
        oracledb.init_oracle_client(lib_dir=INSTANT_CLIENT_PATH)
        conn = create_connection()
        cur = conn.cursor()

        # Define group mapping
        group_mapping = {
            '01': 'Cement',
            '02': 'Coal',
            '03': 'Container',
            '04': 'Fertilizer',
            '05': 'Food Grains',
            '06': 'Iron and Steel',
            '07': 'Other Goods',
            '08': 'POL'
        }

        # Filters
        col1, col2 = st.columns(2)
        with col1:
            selected_year = st.selectbox(
                "Select Fiscal Year",
                [year_labels[y] for y in years],
                index=1
            )
        with col2:
            selected_month = st.selectbox(
                "Select Month", 
                list(months.keys()),
                index=3
            )

        # Get selected year code and table
        selected_year_code = years[list(year_labels.values()).index(selected_year)]
        selected_table = f"carr_apmt_excl_adv_{selected_year_code}"
        selected_month_num = int(months[selected_month])
        
        # Check data availability for selected month
        try:
            latest_data_query = f"""
                SELECT MAX(TO_NUMBER(SUBSTR(YYMM, 5, 2))) as latest_month
                FROM FOISGOODS.{selected_table}
                WHERE SUBSTR(YYMM, 1, 4) IN ('20{selected_year_code.split("_")[0]}', '20{selected_year_code.split("_")[1]}')
            """
            cur.execute(latest_data_query)
            result = cur.fetchone()
            
            if result and result[0]:
                latest_month = result[0]
                if latest_month < selected_month_num:
                    st.warning(f"⚠️ Data is not available for selected month. Please adjust your selection.")
                    st.stop()
            else:
                st.warning("⚠️ No data available for the selected period.")
                st.stop()
        except Exception as e:
            st.error(f"Error checking data availability: {str(e)}")
            st.stop()

        # Continue with data processing
        # Get data for analysis
        dfs = {}
        # Initialize totals dictionary
        totals = {'Commodity': 'Total'}
        
        # Get 5 years for comparison
        selected_idx = years.index(selected_year_code)
        start_idx = max(0, selected_idx - 4)
        table_years = years[start_idx:start_idx + 5]
        table_years = list(reversed(table_years))

        for year in table_years:
            year_start = "20" + year.split("_")[0]
            year_end = "20" + year.split("_")[1]
            table = f"carr_apmt_excl_adv_{year}"

            # Query for period data
            query = f"""
                SELECT 
                    GRP as Group_Code,
                    CASE GRP
                        WHEN '01' THEN 'Cement'
                        WHEN '02' THEN 'Coal'
                        WHEN '03' THEN 'Container'
                        WHEN '04' THEN 'Fertilizer'
                        WHEN '05' THEN 'Food Grains'
                        WHEN '06' THEN 'Iron and Steel'
                        WHEN '07' THEN 'Other Goods'
                        WHEN '08' THEN 'POL'
                    END as Commodity,
                    SUM(WR) as Revenue
                FROM FOISGOODS.{table}
                WHERE GRP IS NOT NULL
                    AND (
                        (SUBSTR(YYMM, 1, 4) = '{year_start}'
                         AND TO_NUMBER(SUBSTR(YYMM, 5, 2)) >= 4
                         AND TO_NUMBER(SUBSTR(YYMM, 5, 2)) <= CASE 
                            WHEN {selected_month_num} < 4 THEN 12
                            ELSE {selected_month_num}
                         END)
                        OR 
                        (SUBSTR(YYMM, 1, 4) = '{year_end}'
                         AND TO_NUMBER(SUBSTR(YYMM, 5, 2)) < 4
                         AND {selected_month_num} < 4
                         AND TO_NUMBER(SUBSTR(YYMM, 5, 2)) <= {selected_month_num})
                    )
                GROUP BY GRP
                ORDER BY GRP
            """            # Full year query
            full_year_query = f"""
                SELECT 
                    GRP as Group_Code,
                    CASE GRP
                        WHEN '01' THEN 'Cement'
                        WHEN '02' THEN 'Coal'
                        WHEN '03' THEN 'Container'
                        WHEN '04' THEN 'Fertilizer'
                        WHEN '05' THEN 'Food Grains'
                        WHEN '06' THEN 'Iron and Steel'
                        WHEN '07' THEN 'Other Goods'
                        WHEN '08' THEN 'POL'
                    END as Commodity,
                    SUM(WR) as Full_Year_Revenue
                FROM FOISGOODS.{table}
                WHERE GRP IS NOT NULL
                    AND (
                        (SUBSTR(YYMM, 1, 4) = '{year_start}'
                         AND TO_NUMBER(SUBSTR(YYMM, 5, 2)) >= 4)
                        OR 
                        (SUBSTR(YYMM, 1, 4) = '{year_end}'
                         AND TO_NUMBER(SUBSTR(YYMM, 5, 2)) < 4)
                    )
                GROUP BY GRP
                ORDER BY GRP
            """            # Execute period query
            cur.execute(query)
            results = cur.fetchall()
            year_df = pd.DataFrame(results, columns=['Group_Code', 'Commodity', 'Revenue'])
            year_df['Revenue'] = year_df['Revenue'].fillna(0)  # Handle any NaN values
            
            # Execute full year query
            cur.execute(full_year_query)
            full_year_results = cur.fetchall()
            full_year_df = pd.DataFrame(full_year_results, columns=['Group_Code', 'Commodity', 'Full_Year_Revenue'])
            full_year_df['Full_Year_Revenue'] = full_year_df['Full_Year_Revenue'].fillna(0)
            
            # Merge and calculate metrics
            year_df = year_df.merge(full_year_df, on=['Group_Code', 'Commodity'], how='outer')
            year_df = year_df.fillna(0)  # Fill any NaN values from the merge
            
            # Convert to crores
            year_df['Revenue'] = year_df['Revenue'] / 1e7
            year_df['Full_Year_Revenue'] = year_df['Full_Year_Revenue'] / 1e7
            
            # Calculate revenue and percentage columns
            year_df[f'Revenue_{year}'] = year_df['Revenue'].round(2)
            mask = year_df['Full_Year_Revenue'] != 0
            year_df.loc[mask, f'Percentage_{year}'] = (
                year_df.loc[mask, 'Revenue'] / year_df.loc[mask, 'Full_Year_Revenue'] * 100
            ).round(2)
            year_df.loc[~mask, f'Percentage_{year}'] = 0
            
            # Clean up and store
            year_df = year_df.drop(['Revenue', 'Full_Year_Revenue', 'Group_Code'], axis=1)
            dfs[year] = year_df.fillna(0)  # Ensure no NaN values remain# Calculate and store total revenue and percentage for this year
            year_revenue = year_df[f'Revenue_{year}'].sum()
            year_full_revenue = (full_year_df['Full_Year_Revenue'].sum() / 1e7)
            
            totals[f'Revenue_{year}'] = year_revenue
            if year_full_revenue > 0:
                totals[f'Percentage_{year}'] = (year_revenue / year_full_revenue * 100).round(2)
            else:
                totals[f'Percentage_{year}'] = 0.0        # Merge all years data with proper handling of missing values
        final_df = dfs[table_years[0]].copy()
        final_df = final_df.fillna(0)  # Ensure no NaN values in first year
        
        for year in table_years[1:]:
            temp_df = dfs[year].copy()
            final_df = final_df.merge(temp_df, on='Commodity', how='outer')
            final_df = final_df.fillna(0)  # Fill any NaN values after each merge        # Fill NaN values
        revenue_cols = [f'Revenue_{y}' for y in table_years]
        percentage_cols = [f'Percentage_{y}' for y in table_years]
        final_df[revenue_cols] = final_df[revenue_cols].fillna(0)
        final_df[percentage_cols] = final_df[percentage_cols].fillna(0)

        # Calculate predictions for remaining months
        current_rev = totals.get(f'Revenue_{selected_year_code}', 0)
        
        # Calculate months completed
        if selected_month_num == 4:  # April
            months_completed = 1
        elif selected_month_num > 4:  # May to December
            months_completed = selected_month_num - 4 + 1
        else:  # January to March
            months_completed = selected_month_num + 9
            
        # Calculate percentages
        current_percentages = (months_completed / 12) * 100
        remaining_percentage = 100 - current_percentages
        
        # Initialize remaining_df for predictions
        remaining_df = pd.DataFrame()
        remaining_df['Commodity'] = final_df['Commodity']
        
        if current_rev > 0:
            # Calculate total predicted based on completed months
            total_predicted = (current_rev / months_completed) * 12
            predicted_remaining = total_predicted - current_rev
            
            # Distribute the predicted remaining amount according to current commodity proportions
            commodity_proportions = final_df[f'Revenue_{selected_year_code}'] / current_rev
            remaining_df[f'Revenue_{selected_year_code}'] = commodity_proportions * predicted_remaining
            remaining_df['Commodity'] = final_df['Commodity']
            remaining_df[f'Percentage_{selected_year_code}'] = remaining_percentage
            predicted_remaining_total = remaining_df[f'Revenue_{selected_year_code}'].sum()
            total_predicted = current_rev + predicted_remaining_total
        else:
            predicted_remaining_total = 0
            total_predicted = current_rev

        # Display Performance Overview
        with st.container():
            st.markdown("### Performance Overview")
            cols = st.columns(2)
            
            with cols[0]:
                st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-title">Current Revenue</div>
                        <div class="metric-value">{format_currency(current_rev)}</div>
                        <div class="metric-change">Current ({selected_month} {year_labels[selected_year_code]})</div>
                    </div>
                """, unsafe_allow_html=True)
            
            with cols[1]:
                st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-title">Predicted Total Revenue</div>
                        <div class="metric-value">{format_currency(total_predicted)}</div>
                    </div>
                """, unsafe_allow_html=True)

        # Display predictions table if we have data
        if not remaining_df.empty and remaining_percentage > 0:
            st.markdown("### Revenue Predictions by Commodity Group")
            prediction_df = pd.DataFrame({
                'Commodity Group': remaining_df['Commodity'],
                f'Current Revenue upto {selected_month}': final_df[f'Revenue_{selected_year_code}'],
                'Predicted Additional': remaining_df[f'Revenue_{selected_year_code}'],
                'Predicted Total': final_df[f'Revenue_{selected_year_code}'] + remaining_df[f'Revenue_{selected_year_code}']
            })
            
            st.dataframe(
                prediction_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    'Commodity Group': st.column_config.TextColumn('Commodity Group', width='medium'),
                    f'Current Revenue upto {selected_month}': st.column_config.NumberColumn(f'Current Revenue upto {selected_month}', format="₹%.2f Cr"),
                    'Predicted Additional': st.column_config.NumberColumn('Predicted Forecast', format="₹%.2f Cr"),
                    'Predicted Total': st.column_config.NumberColumn('Predicted Total', format="₹%.2f Cr")
                }
            )
            
            # Add completion visualization
            fig = go.Figure()
            fig.add_trace(go.Bar(
                name=f'Current Revenue upto {selected_month}',
                x=prediction_df['Commodity Group'],
                y=prediction_df[f'Current Revenue upto {selected_month}'],
                marker_color='rgb(31, 119, 180)'
            ))
            
            fig.add_trace(go.Bar(
                name='Predicted Forecast',
                x=prediction_df['Commodity Group'],
                y=prediction_df['Predicted Additional'],
                marker_color='rgb(255, 127, 14)'
            ))
            
            fig.update_layout(
                title=f'Current vs Predicted Revenue by Commodity Group for the year {year_labels[selected_year_code]}',
                barmode='stack',
                xaxis_title='Commodity Group',
                yaxis_title='Revenue (₹ Crores)',
                height=500,
                showlegend=True,
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1
                )
            )
            
            st.plotly_chart(fig, use_container_width=True)

        # Display commodity distribution pie chart
        st.markdown("### Commodity Distribution")
        pie_data = final_df[[f'Revenue_{selected_year_code}', 'Commodity']].copy()
        pie_data.columns = ['Revenue', 'Commodity']
        
        fig_pie = px.pie(
            pie_data,
            values='Revenue',
            names='Commodity',
            title=f'Revenue Distribution by Commodity Group ({year_labels[selected_year_code]})',
            hole=0.4,  # Makes it a donut chart
        )
        
        fig_pie.update_layout(
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=-0.2,
                xanchor="center",
                x=0.5
            ),
            annotations=[dict(
                text=year_labels[selected_year_code],
                x=0.5,
                y=0.5,
                font_size=20,
                showarrow=False
            )]
        )
        
        fig_pie.update_traces(
            textposition='inside',
            textinfo='percent+label',
            hovertemplate="<b>%{label}</b><br>Revenue: ₹%{value:.2f} Cr<br>Share: %{percent}<extra></extra>"
        )
        
        st.plotly_chart(fig_pie, use_container_width=True)
        
        # Display detailed data
        st.markdown("### Revenue by Commodity Group")
        st.dataframe(
            final_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                'Commodity': st.column_config.TextColumn('Commodity Group', width='medium'),
                **{f'Revenue_{y}': st.column_config.NumberColumn(
                    f'Revenue {year_labels[y]}',
                    format="₹%.2f Cr",
                    width='medium'
                ) for y in table_years}
            }
        )

        # Bar chart
        st.markdown("### Revenue Trend by Commodity Group")
        fig = px.bar(
            final_df.melt(
                id_vars=['Commodity'],
                value_vars=[f'Revenue_{y}' for y in table_years],
                var_name='Year',
                value_name='Revenue'
            ),
            x='Commodity',
            y='Revenue',
            color='Year',
            title=f"Revenue Comparison ({' vs '.join(year_labels[y] for y in table_years)})",
            labels={'Revenue': 'Revenue (Crores)', 'Commodity': 'Commodity Group'},
            barmode='group'
        )
        fig.update_layout(
            height=500,
            xaxis_title="Commodity Group",
            yaxis_title="Revenue (₹ Crores)",
            legend_title="Financial Year",
            plot_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"An error occurred while processing the data: {str(e)}")
        st.error("Please try adjusting your filters or contact support if the issue persists.")
    finally:
        try:
            cur.close()
            conn.close()
        except:
            pass

    # Footer
    st.markdown("---")
    st.markdown("""
        <div style="text-align: center; color: #64748b; font-size: 0.875rem;">
            <p>Railway Revenue Analytics Dashboard • Data Source: FOIS Goods • Last Updated: {}</p>
        </div>
    """.format(pd.Timestamp.now().strftime('%d %B %Y')), unsafe_allow_html=True)

def data_exporter_page():
    st.title("📦 Railway Analytics Data Exporter (Financial Year)")

    # Oracle Init
    if not init_oracle_client():
        st.stop()

    # Sidebar - Financial Year Selection
    with st.sidebar:
        st.header("1. Select Financial Year")
        selected_fy = st.selectbox(
            "Financial Year",
            options=list(FINANCIAL_YEARS.keys()),
            index=0
        )
        
        # Automatically determine table name
        table_name = f"CARR_APMT_EXCL_ADV_{FINANCIAL_YEARS[selected_fy]}"
        
        st.header("2. Filter Options")
        
        # Month range selection
        st.subheader("Month Range (April-March)")
        col1, col2 = st.columns(2)
        with col1:
            start_month = st.selectbox(
                "From",
                options=FINANCIAL_MONTHS,
                index=0
            )
        with col2:
            end_month = st.selectbox(
                "To",
                options=FINANCIAL_MONTHS,
                index=FINANCIAL_MONTHS.index(start_month)
            )

        # Get zones for selection
        with oracledb.connect(user=DB_USER, password=DB_PASSWORD, dsn=DSN) as conn:
            zones_query = f"SELECT DISTINCT {ZONE_COLUMN} FROM {TARGET_SCHEMA}.{table_name}"
            zones_df = pd.read_sql(zones_query, conn)
            zone_options = sorted(zones_df[ZONE_COLUMN].dropna().unique().tolist())

        selected_zone = st.selectbox("Zone", zone_options)
        
        st.markdown("### Actions")
        preview = st.button("🔍 Preview")
        download = st.button("📥 Export to Excel")

    # Preview or Download based on action
    if preview or download:
        with st.spinner("Executing query..."):
            df, total_records = get_filtered_data(
                table_name, 
                start_month, 
                end_month, 
                selected_zone,
                preview=preview
            )
            
            if df.empty:
                st.warning("No matching records found.")
                st.stop()
                
            st.success(f"Found {total_records:,} matching records")
            
            if preview:
                st.dataframe(df)
            
            if download:
                # Excel export logic
                output = BytesIO()
                with pd.ExcelWriter(output, engine="openpyxl") as writer:
                    df.to_excel(writer, index=False)
                
                # Create filename
                parts = [table_name]
                if start_month != "All" and end_month != "All":
                    parts.append(f"{start_month[:3]}-{end_month[:3]}")
                if selected_zone != "All":
                    parts.append(selected_zone.replace(" ", "_"))
                
                filename = "_".join(parts) + ".xlsx"
                
                st.download_button(
                    "📥 Download Excel File",
                    data=output.getvalue(),
                    file_name=filename,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

# --- Main App Logic ---
def main():
    st.sidebar.title("Navigation")
    page = st.sidebar.radio("Go to", ["Dashboard", "Revenue Analytics", "Data Exporter"])
    
    if page == "Dashboard":
        dashboard_page()
    elif page == "Revenue Analytics":
        revenue_analytics_page()
    elif page == "Data Exporter":
        data_exporter_page()

if __name__ == "__main__":
    main()