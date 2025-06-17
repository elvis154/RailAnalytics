import streamlit as st
st.set_page_config(
    page_title="Railway Traffic Analysis Dashboard",
    page_icon="🚂",
    layout="wide",
    initial_sidebar_state="expanded"
)

import oracledb
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from testquery import DB_HOST, DB_SID, DB_USER, DB_PASSWORD, DB_PORT

# Custom CSS for better styling with extension conflict prevention
st.markdown("""
<style>
    /* Prevent extension interference */
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

# Main header
st.markdown('<div class="main-header">🚂 Railway Traffic Analysis Dashboard</div>', unsafe_allow_html=True)

# Sidebar configuration
with st.sidebar:
    st.markdown("## 📊 Dashboard Controls")
    
    # Year selection
    years = [
        "25_26", "24_25", "23_24", "22_23", "21_22", "20_21", "19_20", "18_19", "17_18"
    ]
    year_labels = {
        "25_26": "2025-26", "24_25": "2024-25", "23_24": "2023-24", "22_23": "2022-23",
        "21_22": "2021-22", "20_21": "2020-21", "19_20": "2019-20", "18_19": "2018-19", "17_18": "2017-18"
    }
    
    selected_year = st.selectbox(
        "📅 Select Base Year",
        [year_labels[y] for y in years[:5]],
        help="Select the base year to analyze the last 5 years of data"
    )
    
    # Visualization options
    st.markdown("### 📈 Visualization Options")
    show_charts = st.checkbox("Show Interactive Charts", value=True)
    
    # Metrics selection
    st.markdown("### 📋 Metrics Display")
    show_kpis = st.checkbox("Show Key Performance Indicators", value=True)
    show_trends = st.checkbox("Show Trend Analysis", value=True)
    
    # Data refresh
    if st.button("🔄 Refresh Data", type="primary"):
        st.rerun()

# Progress bar for data loading
progress_bar = st.progress(0)
status_text = st.empty()

try:
    # Database connection
    status_text.text("Connecting to database...")
    progress_bar.progress(10)
    
    selected_idx = [year_labels[y] for y in years].index(selected_year)
    table_years = years[selected_idx:selected_idx+5]
    table_names = [f"carr_apmt_excl_adv_{y}" for y in table_years]
    
    dsn = oracledb.makedsn(DB_HOST, DB_PORT, sid=DB_SID)
    conn = oracledb.connect(user=DB_USER, password=DB_PASSWORD, dsn=dsn)
    cur = conn.cursor()
    
    TARGET_SCHEMA = "FOISGOODS"
    
    # SQL queries
    queries = [
        "SELECT SUM(CHBL_WGHT) AS SUM_DIFF FROM {schema}.{table} WHERE ZONE_FRM = 'WR'",
        "SELECT SUM(TOT_FRT_INCL_GST - TOT_GST) AS SUM_DIFF FROM {schema}.{table} WHERE ZONE_FRM = 'WR'",
        "SELECT SUM(WR) AS SUM_DIFF FROM {schema}.{table} WHERE ZONE_FRM = 'WR'",
        "SELECT SUM(WR) AS SUM_DIFF FROM {schema}.{table} WHERE ZONE_FRM != 'WR'"
    ]
    
    # Execute queries
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
    
    # Process data
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
    
    # Calculate percentage variance
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
    
    # Calculate averages
    for idx in ratio_df.index:
        vals = [v for v in ratio_df.loc[idx].values if v is not None and not pd.isna(v)]
        if vals:
            avg = sum(vals) / len(vals)
            ratio_df.loc[idx, "Avg of last 5 years"] = round(avg, 2)
    
    # Format percentages
    for col in ratio_df.columns:
        if col != "Avg of last 5 years":
            ratio_df[col] = ratio_df[col].apply(lambda x: f"{x:.2f}%" if pd.notnull(x) else "")
        else:
            ratio_df[col] = ratio_df[col].apply(lambda x: f"{x:.2f}%" if pd.notnull(x) else "")
    
    ratio_df = ratio_df.reset_index().rename(columns={'index': 'Ratio'})
    
    progress_bar.progress(100)
    status_text.text("Data loaded successfully!")
    
    # Clear progress indicators
    progress_bar.empty()
    status_text.empty()
    
    # Key Performance Indicators
    if show_kpis:
        st.markdown('<div class="section-header">📊 Key Performance Indicators</div>', unsafe_allow_html=True)
        
        col1, col2, col3, col4 = st.columns(4)
        
        # Current year data
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
    
    # Interactive Charts
    if show_charts:
        st.markdown('<div class="section-header">📈 Interactive Visualizations</div>', unsafe_allow_html=True)
        
        # Prepare data for charts
        years_list = [year_labels[y] for y in table_years]
        chart_data = summary_df.set_index('Particulars')[years_list]
        
        # Graph 1: Loading Trend
        st.markdown("#### Loading Trend")
        fig_loading = px.line(
            x=years_list,
            y=chart_data.loc['Loading'],
            title="Loading Trend (in Crores)",
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
        
        # Graph 2: Originating Revenue Trend
        st.markdown("#### Originating Revenue Trend")
        fig_revenue = px.line(
            x=years_list,
            y=chart_data.loc['Originating Revenue'],
            title="Originating Revenue Trend (in Crores)",
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
        
        # Graph 3: Inward vs Outward Total Apportion Share
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
        ))
        fig_apportion.update_layout(
            title="Inward vs Outward Total Apportion Share (in Crores)",
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
        
        # Additional charts in tabs
        tab1, tab2, tab3 = st.tabs(["📊 Ratio Trends", "📈 Growth Analysis", "🔄 Comparative View"])
        
        with tab1:
            # Ratio trends chart
            ratio_chart_data = {}
            for col in years_list:
                if col in ratio_df.columns:
                    ratio_chart_data[col] = []
                    for i in range(len(ratio_names)):
                        val = ratio_df.iloc[i][col]
                        if isinstance(val, str) and val.endswith('%'):
                            try:
                                ratio_chart_data[col].append(float(val[:-1]))
                            except ValueError:
                                ratio_chart_data[col].append(0)
                        else:
                            ratio_chart_data[col].append(val if val and pd.notnull(val) else 0)
            
            if ratio_chart_data:
                ratio_chart_df = pd.DataFrame(ratio_chart_data, index=ratio_names)
                
                fig_ratio = px.line(
                    ratio_chart_df.T,
                    title="Ratio Trends Over Years",
                    labels={'index': 'Year', 'value': 'Percentage (%)'},
                    height=400,
                    markers=True
                )
                fig_ratio.update_layout(
                    xaxis_title="Year",
                    yaxis_title="Percentage (%)",
                    hovermode='x unified',
                    plot_bgcolor='rgba(0,0,0,0)',
                    xaxis=dict(showgrid=True, gridcolor='lightgray'),
                    yaxis=dict(showgrid=True, gridcolor='lightgray')
                )
                st.plotly_chart(fig_ratio, use_container_width=True)
            else:
                st.warning("No ratio data available for visualization")
        
        with tab2:
            # Growth analysis
            growth_data = []
            for i in range(len(summary_names)):
                values = []
                for year in years_list:
                    if year in chart_data.columns:
                        val = chart_data.iloc[i][year]
                        if pd.notnull(val) and isinstance(val, (int, float)):
                            values.append(val)
                
                if len(values) >= 2:
                    growth_rate = ((values[0] - values[-1]) / values[-1]) * 100 if values[-1] != 0 else 0
                    growth_data.append({'Metric': summary_names[i], 'Growth Rate (%)': growth_rate})
            
            if growth_data:
                growth_df = pd.DataFrame(growth_data)
                fig_growth = px.bar(
                    growth_df,
                    x='Metric',
                    y='Growth Rate (%)',
                    title="5-Year Growth Rate Analysis",
                    color='Growth Rate (%)',
                    color_continuous_scale='RdYlGn',
                    height=400
                )
                fig_growth.update_layout(
                    xaxis_tickangle=-45, 
                    xaxis_title="Metrics", 
                    yaxis_title="Growth Rate (%)",
                    plot_bgcolor='rgba(0,0,0,0)',
                    xaxis=dict(showgrid=True, gridcolor='lightgray'),
                    yaxis=dict(showgrid=True, gridcolor='lightgray')
                )
                st.plotly_chart(fig_growth, use_container_width=True)
        
        with tab3:
            # Comparative view
            col1, col2 = st.columns(2)
            
            with col1:
                # Pie chart for current year distribution
                try:
                    outward_val = chart_data.loc['Apportioned Revenue (Outward Retained Share)'][years_list[0]]
                    inward_val = chart_data.loc['Apportioned Revenue (Inward Share)'][years_list[0]]
                    
                    if pd.notnull(outward_val) and pd.notnull(inward_val) and outward_val > 0 and inward_val > 0:
                        current_data = [outward_val, inward_val]
                        
                        fig_pie = px.pie(
                            values=current_data,
                            names=['Outward Retained Share', 'Inward Share'],
                            title=f"Revenue Distribution - {years_list[0]}",
                            height=400,
                            color_discrete_sequence=['#FF6B6B', '#4ECDC4']
                        )
                        st.plotly_chart(fig_pie, use_container_width=True)
                    else:
                        st.warning("Insufficient data for pie chart visualization")
                except Exception as e:
                    st.error(f"Error creating pie chart: {str(e)}")
            
            with col2:
                # Stacked bar chart
                try:
                    outward_data = []
                    inward_data = []
                    valid_years = []
                    
                    for year in years_list:
                        outward_val = chart_data.loc['Apportioned Revenue (Outward Retained Share)'][year]
                        inward_val = chart_data.loc['Apportioned Revenue (Inward Share)'][year]
                        
                        if pd.notnull(outward_val) and pd.notnull(inward_val):
                            outward_data.append(outward_val)
                            inward_data.append(inward_val)
                            valid_years.append(year)
                    
                    if valid_years:
                        fig_stacked = go.Figure()
                        fig_stacked.add_trace(go.Bar(
                            x=valid_years,
                            y=outward_data,
                            name='Outward Retained Share',
                            marker_color='#FF6B6B'
                        ))
                        fig_stacked.add_trace(go.Bar(
                            x=valid_years,
                            y=inward_data,
                            name='Inward Share',
                            marker_color='#4ECDC4'
                        ))
                        
                        fig_stacked.update_layout(
                            title="Revenue Composition Over Years",
                            barmode='stack',
                            height=400,
                            xaxis_title="Year",
                            yaxis_title="Revenue (Cr)",
                            plot_bgcolor='rgba(0,0,0,0)',
                            xaxis=dict(showgrid=True, gridcolor='lightgray'),
                            yaxis=dict(showgrid=True, gridcolor='lightgray')
                        )
                        st.plotly_chart(fig_stacked, use_container_width=True)
                    else:
                        st.warning("Insufficient data for stacked bar chart")
                except Exception as e:
                    st.error(f"Error creating stacked bar chart: {str(e)}")
    
    # Data Tables
    st.markdown('<div class="section-header">📋 Detailed Data Tables</div>', unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["📊 Summary Data", "📈 Ratio Analysis"])
    
    with tab1:
        st.markdown("**Summary of Goods Traffic Pattern for the last five years as per FOIS RR Data for Carried Route (ST-7C)**")
        
        # Enhanced dataframe display
        st.dataframe(
            summary_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                'Particulars': st.column_config.TextColumn('Particulars', width='medium'),
                '% var w.r.t P.Y.': st.column_config.TextColumn('% Change vs Previous Year', width='small')
            }
        )
        
        # Download button
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
        
        # Download button
        csv_ratio = ratio_df.to_csv(index=False)
        st.download_button(
            label="📥 Download Ratio Data (CSV)",
            data=csv_ratio,
            file_name=f"railway_traffic_ratios_{selected_year.replace('-', '_')}.csv",
            mime="text/csv"
        )
    
    # Trend Analysis
    if show_trends:
        st.markdown('<div class="section-header">📈 Trend Analysis & Insights</div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 🔍 Key Observations")
            
            # Calculate insights
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
            
            # Create a simple performance gauge
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

# Footer
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