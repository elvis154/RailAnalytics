import streamlit as st
import oracledb
import pandas as pd
import time
import plotly.express as px
import plotly.graph_objects as go
from testquery import DB_HOST, DB_SID, DB_USER, DB_PASSWORD, DB_PORT, INSTANT_CLIENT_PATH

# =============================================
# PAGE CONFIGURATION (MUST BE FIRST STREAMLIT COMMAND)
# =============================================
st.set_page_config(
    page_title="Railway Revenue Analytics",
    page_icon="🚆",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =============================================
# CUSTOM STYLING
# =============================================
st.markdown("""
    <style>
        /* Main container styling */
        .main {
            background-color: #f8fafc;
        }
        
        /* Header styling */
        .header {
            padding: 1rem 0;
            border-bottom: 1px solid #e2e8f0;
            margin-bottom: 2rem;
        }
        
        /* Card styling */
        .card {
            background: white;
            border-radius: 0.5rem;
            padding: 1.5rem;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
            margin-bottom: 1.5rem;
        }
        
        /* Metric styling */
        .metric-title {
            font-size: 0.875rem;
            color: #64748b;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        
        .metric-value {
            font-size: 1.875rem;
            font-weight: 700;
            color: #1e293b;
            margin: 0.5rem 0;
        }
        
        .metric-change {
            font-size: 0.875rem;
            font-weight: 500;
        }
        
        .positive {
            color: #10b981;
        }
        
        .negative {
            color: #ef4444;
        }
        
        /* Table styling */
        .dataframe {
            border-radius: 0.5rem;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        }
        
        /* Select box styling */
        .stSelectbox > div > div {
            border-radius: 0.375rem !important;
        }
        
        /* Tabs styling */
        .stTabs [data-baseweb="tab-list"] {
            gap: 0.5rem;
        }
        
        .stTabs [data-baseweb="tab"] {
            padding: 0.5rem 1rem;
            border-radius: 0.375rem;
            background-color: #f1f5f9;
            transition: all 0.2s;
        }
        
        .stTabs [aria-selected="true"] {
            background-color: #3b82f6;
            color: white;
        }
    </style>
""", unsafe_allow_html=True)

# =============================================
# UTILITY FUNCTIONS
# =============================================
def create_connection(max_retries=3, retry_delay=2):
    """Create database connection with retry logic"""
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

def format_currency(value):
    """Format value as Indian currency"""
    return f"₹{value:,.2f} Cr"

def create_trend_chart(data, years, selected_year):
    """Create trend chart for revenue comparison"""
    fig = go.Figure()
    
    # Add traces for each year
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
    
    # Update layout
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

# =============================================
# INITIALIZATION
# =============================================
# Initialize Oracle client
try:
    oracledb.init_oracle_client(lib_dir=INSTANT_CLIENT_PATH)
except oracledb.Error as e:
    st.error(f"Oracle Client Initialization Error: {e}")
    st.stop()

# Create connection with retry
conn = create_connection()
cur = conn.cursor()

# Year and month configurations
years = ["25_26", "24_25", "23_24", "22_23", "21_22", "20_21", "19_20", "18_19", "17_18"]
year_labels = {
    "25_26": "2025-26", "24_25": "2024-25", "23_24": "2023-24",
    "22_23": "2022-23", "21_22": "2021-22", "20_21": "2020-21",
    "19_20": "2019-20", "18_19": "2018-19", "17_18": "2017-18"
}

months = {
    "April": "04", "May": "05", "June": "06", "July": "07", "August": "08",
    "September": "09", "October": "10", "November": "11", "December": "12",
    "January": "01", "February": "02", "March": "03"
}

# =============================================
# PAGE LAYOUT
# =============================================
# Header section
st.markdown("""
    <div class="header">
        <h1 style="color: #1e40af; margin-bottom: 0.5rem;">Railway Commodity Revenue Analytics</h1>
        <p style="color: #64748b; margin-top: 0;">Comprehensive analysis of apportioned revenue by commodity</p>
    </div>
""", unsafe_allow_html=True)

# Filters section
with st.container():
    col1, col2 = st.columns(2)
    with col1:
        selected_year = st.selectbox(
            "Select Fiscal Year",
            [year_labels[y] for y in years],
            index=1  # Default to current year
        )
    with col2:
        selected_month = st.selectbox(
            "Select Month", 
            list(months.keys()),
            index=3  # Default to July
        )

# Get selected year code
selected_year_code = years[list(year_labels.values()).index(selected_year)]
selected_table = f"carr_apmt_excl_adv_{selected_year_code}"

# =============================================
# DATA PROCESSING
# =============================================
try:
    # Get 5 years for comparison (selected year + 4 previous)
    selected_idx = years.index(selected_year_code)
    start_idx = max(0, selected_idx - 4)  # Ensure we get 5 years
    table_years = years[start_idx:start_idx + 5]
    table_years = list(reversed(table_years))  # Show oldest first
    
    # Create empty dictionary to store DataFrames
    dfs = {}

    # Get data for each year
    for year in table_years:
        year_start = "20" + year.split("_")[0]
        year_end = "20" + year.split("_")[1]
        selected_month_num = int(months[selected_month])
        table = f"carr_apmt_excl_adv_{year}"
        
        # Query for selected period
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
        
        # Full year query for percentage calculation
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
        
        # Execute queries
        cur.execute(query)
        results = cur.fetchall()
        year_df = pd.DataFrame(results, columns=['Commodity', f'Revenue_{year}'])
        
        cur.execute(full_year_query)
        full_year_results = cur.fetchall()
        full_year_df = pd.DataFrame(full_year_results, columns=['Commodity', f'Full_Year_{year}'])
        
        # Merge and calculate metrics
        year_df = year_df.merge(full_year_df, on='Commodity', how='left')
        year_df[f'Percentage_{year}'] = (year_df[f'Revenue_{year}'] / year_df[f'Full_Year_{year}'] * 100).round(2)
        year_df[f'Revenue_{year}'] = (year_df[f'Revenue_{year}'] / 1e7).round(2)
        year_df = year_df.drop(f'Full_Year_{year}', axis=1)
        dfs[year] = year_df

    # Merge all years' data
    final_df = dfs[table_years[0]].copy()
    for year in table_years[1:]:
        final_df = final_df.merge(dfs[year], on='Commodity', how='outer')

    # Fill NaN values
    revenue_cols = [f'Revenue_{y}' for y in table_years]
    percentage_cols = [f'Percentage_{y}' for y in table_years]
    final_df[revenue_cols] = final_df[revenue_cols].fillna(0)
    final_df[percentage_cols] = final_df[percentage_cols].fillna(0)

    # Calculate totals
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
        
        totals[f'Revenue_{year}'] = current_total
        totals[f'Percentage_{year}'] = round((current_total / full_year_total * 100), 2)

    # Prepare DataFrames for display
    main_df = final_df.copy()
    totals_df = pd.DataFrame([totals])

    # Format percentages
    for year in table_years:
        main_df[f'Percentage_{year}'] = main_df[f'Percentage_{year}'].apply(lambda x: f"{x:.2f}%" if pd.notnull(x) else "")
        totals_df[f'Percentage_{year}'] = totals_df[f'Percentage_{year}'].astype(str) + "%"

    # Calculate average percentages
    avg_percentages = []
    for _, row in final_df.iterrows():
        pct_values = [row[f'Percentage_{y}'] for y in table_years]
        avg = sum(pct_values) / len(pct_values)
        avg_percentages.append(f"{avg:.2f}%")
    main_df['Avg %'] = avg_percentages

    # =============================================
    # DASHBOARD COMPONENTS
    # =============================================
    # Key Metrics
    current_rev = totals[f'Revenue_{selected_year_code}']
    prev_year = table_years[-2] if len(table_years) > 1 else table_years[0]
    prev_rev = totals[f'Revenue_{prev_year}']
    growth = ((current_rev - prev_rev) / prev_rev * 100) if prev_rev != 0 else 0
    completion_pct = totals[f'Percentage_{selected_year_code}']
    avg_completion = sum(float(totals[f'Percentage_{y}']) for y in table_years[:-1]) / len(table_years[:-1]) if len(table_years) > 1 else 0
    
    with st.container():
        st.markdown("### Performance Overview")
        cols = st.columns(4)
        
        with cols[0]:
            st.markdown(f"""
                <div class="card">
                    <div class="metric-title">Current Year Revenue</div>
                    <div class="metric-value">{format_currency(current_rev)}</div>
                    <div class="metric-change">vs {year_labels[prev_year]}</div>
                </div>
            """, unsafe_allow_html=True)
        
        with cols[1]:
            st.markdown(f"""
                <div class="card">
                    <div class="metric-title">Year-over-Year Growth</div>
                    <div class="metric-value {'positive' if growth >= 0 else 'negative'}">{growth:+.1f}%</div>
                    <div class="metric-change">vs {year_labels[prev_year]}</div>
                </div>
            """, unsafe_allow_html=True)
        
        with cols[2]:
            st.markdown(f"""
                <div class="card">
                    <div class="metric-title">Annual Completion</div>
                    <div class="metric-value">{completion_pct:.1f}%</div>
                    <div class="metric-change">of full year target</div>
                </div>
            """, unsafe_allow_html=True)
        
        with cols[3]:
            st.markdown(f"""
                <div class="card">
                    <div class="metric-title">5-Year Avg Completion</div>
                    <div class="metric-value">{avg_completion:.1f}%</div>
                    <div class="metric-change">historical average</div>
                </div>
            """, unsafe_allow_html=True)

    # Data Period Information
    year_start = "20" + selected_year_code.split("_")[0]
    year_end = "20" + selected_year_code.split("_")[1]
    selected_month_num = int(months[selected_month])
    
    period_text = (f"April {year_start} to {selected_month} {year_end}" 
                  if selected_month_num < 4 
                  else f"April to {selected_month} {year_start}")
    
    st.markdown(f"""
        <div style="color: #64748b; margin-bottom: 1.5rem;">
            <strong>Data Period:</strong> {period_text} | <strong>Last Updated:</strong> {pd.Timestamp.now().strftime('%d %b %Y %H:%M')}
        </div>
    """, unsafe_allow_html=True)

    # Visualization Tabs
    tab1, tab2, tab3 = st.tabs(["Revenue Trend", "Commodity Comparison", "Detailed Data"])

    with tab1:
        # Trend chart
        st.plotly_chart(
            create_trend_chart(final_df, table_years, selected_year_code),
            use_container_width=True
        )
        
        # Stacked bar chart for current year
        current_df = main_df[['Commodity', f'Revenue_{selected_year_code}']].sort_values(
            f'Revenue_{selected_year_code}', ascending=False
        )
        fig = px.bar(
            current_df,
            x='Commodity',
            y=f'Revenue_{selected_year_code}',
            title=f"Revenue by Commodity ({year_labels[selected_year_code]})",
            labels={f'Revenue_{selected_year_code}': 'Revenue (₹ Crores)'},
            color=f'Revenue_{selected_year_code}',
            color_continuous_scale='blues'
        )
        fig.update_layout(height=500)
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        # Heatmap of completion percentages
        heatmap_df = final_df.set_index('Commodity')
        heatmap_df = heatmap_df[[f'Percentage_{y}' for y in table_years]]
        heatmap_df.columns = [year_labels[y] for y in table_years]
        
        fig = px.imshow(
            heatmap_df,
            labels=dict(x="Fiscal Year", y="Commodity", color="Completion %"),
            color_continuous_scale='blues',
            aspect="auto"
        )
        fig.update_layout(
            height=600,
            title="Annual Completion Percentage by Commodity"
        )
        st.plotly_chart(fig, use_container_width=True)

    with tab3:
        # Detailed data table
        st.markdown("#### Detailed Revenue Data")
        st.dataframe(
            main_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                'Commodity': st.column_config.Column("Commodity", width="medium"),
                **{f'Revenue_{y}': st.column_config.NumberColumn(
                    year_labels[y], 
                    format="₹%.2f Cr"
                ) for y in table_years},
                **{f'Percentage_{y}': st.column_config.Column(
                    f"% of FY",
                    width="small"
                ) for y in table_years},
                'Avg %': st.column_config.Column("5-Yr Avg %")
            }
        )
        
        # Totals row
        st.dataframe(
            totals_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                'Commodity': st.column_config.Column(width="medium"),
                **{f'Revenue_{y}': st.column_config.NumberColumn(
                    year_labels[y],
                    format="₹%.2f Cr"
                ) for y in table_years},
                **{f'Percentage_{y}': st.column_config.Column(
                    "%",
                    width="small"
                ) for y in table_years}
            }
        )

    # =============================================
    # PROJECTIONS SECTION
    # =============================================
    remaining_period = ""
    if selected_month_num < 12:
        next_month = list(months.keys())[list(months.values()).index(str(selected_month_num).zfill(2)) + 1]
        remaining_period = f"{next_month} to March"
    
    if remaining_period:
        st.markdown("---")
        st.markdown("### Revenue Projections")
        
        # Calculate historical completion pattern
        past_years = [y for y in table_years if y != selected_year_code][:4]
        past_percentages = [float(totals[f'Percentage_{y}']) for y in past_years]
        historical_completion_pct = sum(past_percentages) / len(past_percentages) if past_percentages else 0
        remaining_percentage = 100 - historical_completion_pct
        
        # Calculate predictions
        remaining_df = pd.DataFrame()
        remaining_df['Commodity'] = final_df['Commodity']
        current_total = totals[f'Revenue_{selected_year_code}']
        
        # Calculate commodity-wise predictions
        current_proportions = final_df[f'Revenue_{selected_year_code}'] / current_total
        predicted_remaining = (current_total * remaining_percentage) / historical_completion_pct if historical_completion_pct != 0 else 0
        remaining_df[f'Revenue_{selected_year_code}'] = current_proportions * predicted_remaining
        remaining_df[f'Percentage_{selected_year_code}'] = remaining_percentage

        # Format for display
        remaining_df[f'Percentage_{selected_year_code}'] = remaining_df[f'Percentage_{selected_year_code}'].apply(
            lambda x: f"{x:.2f}%"
        )
        
        # Projection metrics
        predicted_remaining_total = remaining_df[f'Revenue_{selected_year_code}'].sum()
        total_predicted = current_total + predicted_remaining_total
        
        # Projection cards
        cols = st.columns(3)
        with cols[0]:
            st.markdown(f"""
                <div class="card">
                    <div class="metric-title">Projected Remaining Revenue</div>
                    <div class="metric-value">{format_currency(predicted_remaining_total)}</div>
                    <div class="metric-change">{remaining_period} period</div>
                </div>
            """, unsafe_allow_html=True)
        
        with cols[1]:
            st.markdown(f"""
                <div class="card">
                    <div class="metric-title">Projected Full Year</div>
                    <div class="metric-value">{format_currency(total_predicted)}</div>
                    <div class="metric-change">based on {historical_completion_pct:.1f}% completion</div>
                </div>
            """, unsafe_allow_html=True)
        
        with cols[2]:
            st.markdown(f"""
                <div class="card">
                    <div class="metric-title">Projected Growth</div>
                    <div class="metric-value {'positive' if total_predicted >= prev_rev else 'negative'}">
                        {((total_predicted - prev_rev) / prev_rev * 100):+.1f}%
                    </div>
                    <div class="metric-change">vs {year_labels[prev_year]}</div>
                </div>
            """, unsafe_allow_html=True)
        
        # Projection visualization
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            x=['Current', 'Projected', 'Full Year'],
            y=[current_total, predicted_remaining_total, total_predicted],
            text=[format_currency(x) for x in [current_total, predicted_remaining_total, total_predicted]],
            textposition='auto',
            marker_color=['#3b82f6', '#93c5fd', '#1e40af']
        ))
        
        fig.update_layout(
            title=f"Revenue Projection for {year_labels[selected_year_code]}",
            yaxis_title="Revenue (₹ Crores)",
            height=400,
            showlegend=False
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Projection details
        with st.expander("View Detailed Projections by Commodity"):
            st.dataframe(
                remaining_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    'Commodity': st.column_config.Column(width="medium"),
                    f'Revenue_{selected_year_code}': st.column_config.NumberColumn(
                        "Projected Revenue",
                        format="₹%.2f Cr"
                    ),
                    f'Percentage_{selected_year_code}': st.column_config.Column(
                        "Remaining %",
                        width="small"
                    )
                }
            )

except Exception as e:
    st.error(f"An error occurred while processing the data: {str(e)}")
    st.error("Please try adjusting your filters or contact support if the issue persists.")

finally:
    # Close database connections
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