import streamlit as st
import oracledb
import pandas as pd
import time
from testquery import DB_HOST, DB_SID, DB_USER, DB_PASSWORD, DB_PORT, INSTANT_CLIENT_PATH

def create_connection(max_retries=3, retry_delay=2):
    for attempt in range(max_retries):
        try:
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

st.set_page_config(layout="wide")

# Initialize Oracle client
try:
    oracledb.init_oracle_client(lib_dir=INSTANT_CLIENT_PATH)
except oracledb.Error as e:
    st.error(f"Oracle Client Initialization Error: {e}")
    st.stop()

# Create connection with retry
conn = create_connection()
cur = conn.cursor()

# Dropdown for year selection
years = [
    "25_26", "24_25", "23_24", "22_23", "21_22", "20_21", "19_20", "18_19", "17_18"
]
year_labels = {
    "25_26": "2025-26", "24_25": "2024-25", "23_24": "2023-24",
    "22_23": "2022-23", "21_22": "2021-22", "20_21": "2020-21",
    "19_20": "2019-20", "18_19": "2018-19", "17_18": "2017-18"
}

# Add month selection with fiscal year order
months = {
    "April": "04", "May": "05", "June": "06", "July": "07", "August": "08",
    "September": "09", "October": "10", "November": "11", "December": "12",
    "January": "01", "February": "02", "March": "03"
}

# Create two-column layout for selections
col1, col2 = st.columns(2)
with col1:
    selected_year = st.selectbox("Select Year", [year_labels[y] for y in years])
with col2:
    selected_month = st.selectbox("Select Month", list(months.keys()))

selected_table = f"carr_apmt_excl_adv_{years[list(year_labels.values()).index(selected_year)]}"

# Get 5 years (selected and either previous or next years to make total of 5)
selected_idx = years.index(years[list(year_labels.values()).index(selected_year)])
start_idx = min(selected_idx, len(years) - 5)  # Ensure we don't go out of bounds
table_years = years[start_idx:start_idx + 5]
table_years = list(reversed(table_years))  # Reverse to show oldest first
year_tables = [f"carr_apmt_excl_adv_{y}" for y in table_years]

# Create empty dictionary to store DataFrames
dfs = {}

try:
    # Get data for each year
    for year, table in zip(table_years, year_tables):
        year_start = "20" + year.split("_")[0]
        year_end = "20" + year.split("_")[1]
        selected_month_num = int(months[selected_month])
        
        # First query: Get data up to selected month (existing query)
        query = f"""
            SELECT 
                TRIM(CMDT) as Commodity,
                SUM(WR) as Apportioned_Revenue
            FROM FOISGOODS.{table}
            WHERE CMDT IS NOT NULL
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
            GROUP BY TRIM(CMDT)
        """
        
        # Second query: Get full year data for percentage calculation
        full_year_query = f"""
            SELECT 
                TRIM(CMDT) as Commodity,
                SUM(WR) as Full_Year_Revenue
            FROM FOISGOODS.{table}
            WHERE CMDT IS NOT NULL
                AND (
                    (SUBSTR(YYMM, 1, 4) = '{year_start}'
                     AND TO_NUMBER(SUBSTR(YYMM, 5, 2)) >= 4)
                    OR 
                    (SUBSTR(YYMM, 1, 4) = '{year_end}'
                     AND TO_NUMBER(SUBSTR(YYMM, 5, 2)) < 4)
                )
            GROUP BY TRIM(CMDT)
        """
        
        # Execute queries and create DataFrames
        cur.execute(query)
        results = cur.fetchall()
        year_df = pd.DataFrame(results, columns=['Commodity', f'Revenue_{year}'])
        
        cur.execute(full_year_query)
        full_year_results = cur.fetchall()
        full_year_df = pd.DataFrame(full_year_results, columns=['Commodity', f'Full_Year_{year}'])
        
        # Merge partial and full year data
        year_df = year_df.merge(full_year_df, on='Commodity', how='left')
        
        # Calculate percentage as (partial revenue / full year revenue * 100)
        year_df[f'Percentage_{year}'] = (year_df[f'Revenue_{year}'] / year_df[f'Full_Year_{year}'] * 100).round(2)
        
        # Convert revenue to crores
        year_df[f'Revenue_{year}'] = (year_df[f'Revenue_{year}'] / 1e7).round(2)
        
        # Drop full year column before storing
        year_df = year_df.drop(f'Full_Year_{year}', axis=1)
        dfs[year] = year_df

    # Start with first year's complete data
    first_year = table_years[0]
    final_df = dfs[first_year].copy()
    
    # Merge remaining years one by one
    for year in table_years[1:]:
        final_df = final_df.merge(
            dfs[year],
            on='Commodity',
            how='outer'
        )

    # Fill NaN values
    revenue_cols = [f'Revenue_{y}' for y in table_years]
    percentage_cols = [f'Percentage_{y}' for y in table_years]
    final_df[revenue_cols] = final_df[revenue_cols].fillna(0)
    final_df[percentage_cols] = final_df[percentage_cols].fillna(0)

    # Calculate totals with proper percentages
    totals = {'Commodity': 'Total'}
    for year in table_years:
        # Get full year total for percentage calculation
        cur.execute(f"""
            SELECT SUM(WR) as Full_Year_Total
            FROM FOISGOODS.carr_apmt_excl_adv_{year}
            WHERE CMDT IS NOT NULL
                AND (
                    (SUBSTR(YYMM, 1, 4) = '20{year.split("_")[0]}'
                     AND TO_NUMBER(SUBSTR(YYMM, 5, 2)) >= 4)
                    OR 
                    (SUBSTR(YYMM, 1, 4) = '20{year.split("_")[1]}'
                     AND TO_NUMBER(SUBSTR(YYMM, 5, 2)) < 4)
                )
        """)
        full_year_total = cur.fetchone()[0] / 1e7  # Convert to crores
        current_total = final_df[f'Revenue_{year}'].sum()
        
        # Set revenue and calculate percentage against full year
        totals[f'Revenue_{year}'] = current_total
        totals[f'Percentage_{year}'] = round((current_total / full_year_total * 100), 2)

    # Create separate DataFrames for data and totals
    main_df = final_df.copy()
    totals_df = pd.DataFrame([totals])

    # Format percentages for main data only
    for year in table_years:
        main_df[f'Percentage_{year}'] = main_df[f'Percentage_{year}'].apply(lambda x: f"{x:.2f}%" if pd.notnull(x) else "")
        # Keep totals percentage as is, don't format
        totals_df[f'Percentage_{year}'] = totals_df[f'Percentage_{year}'].astype(str) + "%"

    # Calculate average percentages only for main DataFrame
    avg_percentages = []
    for _, row in final_df.iterrows():
        pct_values = [row[f'Percentage_{y}'] for y in table_years]
        avg = sum(pct_values) / len(pct_values)
        avg_percentages.append(f"{avg:.2f}%")
    main_df['Avg %'] = avg_percentages

    # Display tables
    period_text = (f"Data Period: April {year_start} to {selected_month} {year_end}" 
                  if selected_month_num < 4 
                  else f"Data Period: April to {selected_month} {year_start}")
    st.markdown(f"**Commodity-wise Revenue Analysis (Last 5 Years)**  \n{period_text}")
    
    # Main data table with averages
    st.dataframe(
        main_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            'Commodity': st.column_config.Column(width="small"),
            **{f'Revenue_{y}': st.column_config.NumberColumn(
                f"{year_labels[y]}", 
                width="small",
                format="%.2f"
            ) for y in table_years},
            **{f'Percentage_{y}': st.column_config.Column(
                f"% of FY",
                width="small"
            ) for y in table_years},
            'Avg %': st.column_config.Column(width="small")
        }
    )
    
    # Totals row without averages
    st.dataframe(
        totals_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            'Commodity': st.column_config.Column(width="small"),
            **{f'Revenue_{y}': st.column_config.NumberColumn(
                f"{year_labels[y]}",
                width="small",
                format="%.2f"
            ) for y in table_years},
            **{f'Percentage_{y}': st.column_config.Column(
                "%",
                width="small"
            ) for y in table_years}
        }
    )

    # Add second table for remaining months
    remaining_dfs = {}
    
    # Define the remaining period text
    remaining_period = ""
    if selected_month_num < 12:
        next_month = list(months.keys())[list(months.values()).index(str(selected_month_num).zfill(2)) + 1]
        remaining_period = f"Remaining Period: {next_month} to March"

    # Get selected year code
    selected_year_code = years[list(year_labels.values()).index(selected_year)]
    
    # Calculate historical pattern from past years' totals
    past_years = [y for y in table_years if y != selected_year_code][:4]
    past_percentages = [float(str(totals[f'Percentage_{y}']).rstrip('%')) for y in past_years]
    historical_completion_pct = sum(past_percentages) / len(past_percentages)
    remaining_percentage = 100 - historical_completion_pct
    
    # Calculate predictions for selected year only using historical pattern
    remaining_df = pd.DataFrame()
    remaining_df['Commodity'] = final_df['Commodity']
    current_total = totals[f'Revenue_{selected_year_code}']

    # Calculate commodity-wise predictions based on their current proportions
    current_proportions = final_df[f'Revenue_{selected_year_code}'] / current_total
    predicted_remaining = (current_total * remaining_percentage) / historical_completion_pct
    remaining_df[f'Revenue_{selected_year_code}'] = current_proportions * predicted_remaining
    remaining_df[f'Percentage_{selected_year_code}'] = remaining_percentage

    # Format percentages for display
    remaining_df[f'Percentage_{selected_year_code}'] = remaining_df[f'Percentage_{selected_year_code}'].apply(
        lambda x: f"{x:.2f}%"
    )
    
    # Display predicted data
    if remaining_period:
        st.markdown(f"**{remaining_period} (Predicted revenue based on {historical_completion_pct:.1f}% completion)**")
        st.dataframe(remaining_df, use_container_width=True, hide_index=True)
        
        prediction_totals = {
            'Commodity': f'Predicted Total ({remaining_period})',
            f'Revenue_{selected_year_code}': remaining_df[f'Revenue_{selected_year_code}'].sum(),
            f'Percentage_{selected_year_code}': f"{remaining_percentage:.2f}%"
        }
        st.dataframe(pd.DataFrame([prediction_totals]), use_container_width=True, hide_index=True)
        
        # Add total prediction summary
        current_year_total = totals[f'Revenue_{selected_year_code}']
        predicted_remaining_total = remaining_df[f'Revenue_{selected_year_code}'].sum()
        total_predicted = current_year_total + predicted_remaining_total
        
        st.markdown(f"""
        **Predicted Apportioned Revenue for {year_labels[selected_year_code]}:**
        - Current Revenue (up to {selected_month}): {current_year_total:.2f} Crores
        - Predicted Remaining: {predicted_remaining_total:.2f} Crores
        - Total Predicted: {total_predicted:.2f} Crores
        """)

except Exception as e:
    st.error(f"Error: {e}")

finally:
    cur.close()
    conn.close()
