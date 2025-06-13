import oracledb
import pandas as pd
import streamlit as st
from datetime import datetime
import re
from io import BytesIO
import plotly.express as px

# --- Oracle Instant Client Configuration ---
INSTANT_CLIENT_PATH = r"C:\Users\Abishek\Downloads\instantclient-basic-windows.x64-23.8.0.25.04\instantclient_23_8"

# --- Database Connection Parameters ---
DB_USER = "intern"
DB_PASSWORD = "inT##2025"
DB_HOST = "10.3.9.4"
DB_PORT = 1523
DB_SID = "traffic"

# --- Constants ---
TARGET_SCHEMA = "FOISGOODS"
DATE_COLUMNS = ["YYMM", "YYCMO", "YYMO"]  # Possible date column names
ZONE_COLUMN = "ZONE_FRM"
DSN = f"{DB_HOST}:{DB_PORT}/{DB_SID}"

# Financial year months (April to March)
FINANCIAL_MONTHS = [
    "April", "May", "June", "July", "August", "September",
    "October", "November", "December", "January", "February", "March"
]

# Map financial years to table suffixes (e.g., 2024-2025 -> 24_25)
FINANCIAL_YEARS = {
    "2024-2025": "24_25",
    "2023-2024": "23_24",
    "2022-2023": "22_23",
    "2021-2022": "21_22",
    "2020-2021": "20_21",
    "2019-2020": "19_20",
    "2018-2019": "18_19",
    "2017-2018": "17_18"
}

# --- Additional Constants ---
SQL_BASE_QUERY = """
    SELECT {columns} 
    FROM {schema}.{table} 
    WHERE 1=1 
    {where_clause}
    {limit_clause}
"""

@st.cache_resource
def init_oracle_client():
    try:
        oracledb.init_oracle_client(lib_dir=INSTANT_CLIENT_PATH)
        return True
    except oracledb.Error as e:
        st.error(f"Oracle Client Error: {e}")
        return False

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

def filter_data(df, start_month=None, end_month=None, zone=None):
    """Minimal local filtering if needed."""
    if df.empty:
        return df
    return df.drop(['temp_date'], axis=1, errors='ignore')

def main():
    st.set_page_config("Oracle Excel Exporter", layout="wide")
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
        table_name = get_table_name(selected_fy)
        
        st.header("2. Filter Options")
        
        # Month range selection
        st.subheader("Month Range (April-March)")
        col1, col2 = st.columns(2)
        with col1:
            start_month = st.selectbox(
                "From",
                options=["All"] + FINANCIAL_MONTHS,
                index=0
            )
        with col2:
            end_month = st.selectbox(
                "To",
                options=["All"] + FINANCIAL_MONTHS,
                index=0 if start_month == "All" else FINANCIAL_MONTHS.index(start_month)
            )
        
        # Get zones for selection
        with oracledb.connect(user=DB_USER, password=DB_PASSWORD, dsn=DSN) as conn:
            zones_query = f"SELECT DISTINCT {ZONE_COLUMN} FROM {TARGET_SCHEMA}.{table_name}"
            zones_df = pd.read_sql(zones_query, conn)
            zone_options = ["All"] + sorted(zones_df[ZONE_COLUMN].dropna().unique().tolist())
        
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

if __name__ == "__main__":
    main()