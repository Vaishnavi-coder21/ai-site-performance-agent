import streamlit as st
import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from config import logger, Config
from services.data_loader import RealEstateDataPipeline, DataIngestionException
from services.data_validator import DataValidator
from services.data_linker import DataLinkingEngine
from services.rules_engine import BusinessRulesEngine
from agents.workflow import build_workflow, AgentState
from services.report_generator import ReportGenerator

st.set_page_config(page_title="AI Site Performance Agent", layout="wide", initial_sidebar_state="expanded")

# Custom CSS for Dashboard Polish
st.markdown("""
<style>
    .metric-card {
        background-color: #f8f9fa;
        border: 1px solid #e9ecef;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.05);
    }
    .metric-card h3 {
        margin-top: 0;
        font-size: 1.1rem;
        color: #495057;
    }
    .metric-card h2 {
        margin: 0;
        font-size: 2rem;
        color: #2b90d9;
    }
</style>
""", unsafe_allow_html=True)

st.title("🏗️ AI Site Performance & Cash Flow Dashboard")
st.markdown("Automate month-end site performance reviews, analyze cash flow, and generate actionable leadership-ready reports.")

st.sidebar.header("📁 Upload Data Files")
sales_file = st.sidebar.file_uploader("Upload Sales File", type=['xlsx'], key="sales")
construction_file = st.sidebar.file_uploader("Upload Construction File", type=['xlsx'], key="construction")
collections_file = st.sidebar.file_uploader("Upload Collections File", type=['xlsx'], key="collections")
aop_file = st.sidebar.file_uploader("Upload AOP Targets File", type=['xlsx'], key="aop")
analyze_btn = st.sidebar.button("🚀 Analyze & Generate Dashboard", type="primary", use_container_width=True)

dashboard_placeholder = st.container()

if analyze_btn:
    if not (sales_file and construction_file and collections_file and aop_file):
        st.sidebar.warning("⚠️ Please upload all four input files to begin analysis.")
    else:
        with st.spinner("⏳ Running Data Pipeline and AI LangGraph Agents..."):
            pipeline = RealEstateDataPipeline()
            try:
                # 1. Pipeline Execution
                pipeline.ingest_all(sales_file, construction_file, collections_file, aop_file)
                validator = DataValidator(pipeline.data)
                dq_report = validator.validate()
                linker = DataLinkingEngine(pipeline.data)
                master_df, unmatched_report = linker.generate_master_dataframe()
                rules_engine = BusinessRulesEngine()
                action_items_df = rules_engine.run_all(master_df, pipeline.data)
                
                # 2. AI Execution
                action_items_dict = action_items_df.to_dict('records') if not action_items_df.empty else []
                app_workflow = build_workflow()
                initial_state = AgentState(action_items=action_items_dict, sales_summary="", collections_summary="", construction_summary="", cash_flow_summary="", risk_summary="", communications=[], final_report="")
                final_state = app_workflow.invoke(initial_state)
                
                # 3. Excel Gen
                report_gen = ReportGenerator(master_df=master_df, data=pipeline.data, dq_report=dq_report, unmatched_report=unmatched_report, action_items=action_items_df, ai_state=final_state)
                excel_bytes = report_gen.generate_excel_bytes()

                # --- 4. DASHBOARD UI ---
                st.sidebar.success("✅ Analysis Complete!")
                st.sidebar.download_button(
                    label="📥 Download Full Review Package",
                    data=excel_bytes,
                    file_name="Monthly_Site_Review_Package.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )

                with dashboard_placeholder:
                    # --- KPI CARDS ---
                    st.subheader("📊 Executive Overview")
                    col1, col2, col3, col4 = st.columns(4)
                    
                    sales_val = pipeline.data['sales']['Booking Value'].sum() if 'Booking Value' in pipeline.data.get('sales', pd.DataFrame()).columns else 0
                    col_val = pipeline.data['collections']['Amount Collected'].sum() if 'Amount Collected' in pipeline.data.get('collections', pd.DataFrame()).columns else 0
                    const_cost = pipeline.data['construction']['Cost Impact'].sum() if 'Cost Impact' in pipeline.data.get('construction', pd.DataFrame()).columns else 0
                    cf_val = col_val - const_cost

                    with col1:
                        st.markdown(f"<div class='metric-card'><h3>💰 Total Sales</h3><h2>${sales_val:,.0f}</h2></div>", unsafe_allow_html=True)
                    with col2:
                        st.markdown(f"<div class='metric-card'><h3>📈 Total Collections</h3><h2>${col_val:,.0f}</h2></div>", unsafe_allow_html=True)
                    with col3:
                        st.markdown(f"<div class='metric-card'><h3>🏗️ Construction Cost</h3><h2>${const_cost:,.0f}</h2></div>", unsafe_allow_html=True)
                    with col4:
                        color = "#00c04b" if cf_val >= 0 else "#ff4b4b"
                        st.markdown(f"<div class='metric-card'><h3>🏦 Net Cash Flow</h3><h2 style='color:{color}'>${cf_val:,.0f}</h2></div>", unsafe_allow_html=True)

                    st.write("") # Spacer

                    # --- CHARTS ROW 1 ---
                    chart_col1, chart_col2 = st.columns(2)
                    
                    with chart_col1:
                        # Risk Distribution Pie Chart
                        if not action_items_df.empty:
                            risk_counts = action_items_df['Severity'].value_counts().reset_index()
                            risk_counts.columns = ['Severity', 'Count']
                            color_map = {'Critical': '#8b0000', 'High': '#ff4b4b', 'Medium': '#ffa421', 'Low': '#00c04b'}
                            fig_pie = px.pie(risk_counts, values='Count', names='Severity', title="Risk Distribution by Severity",
                                             color='Severity', color_discrete_map=color_map, hole=0.4)
                            st.plotly_chart(fig_pie, use_container_width=True)
                        else:
                            st.info("No risks detected.")

                    with chart_col2:
                        # Cash Flow Waterfall / Bar
                        fig_bar = go.Figure(data=[
                            go.Bar(name='Inflow (Collections)', x=['Cash Flow'], y=[col_val], marker_color='#00c04b'),
                            go.Bar(name='Outflow (Construction)', x=['Cash Flow'], y=[const_cost], marker_color='#ff4b4b')
                        ])
                        fig_bar.update_layout(title="Inflow vs Outflow", barmode='group')
                        st.plotly_chart(fig_bar, use_container_width=True)

                    # --- CHARTS ROW 2 ---
                    chart_col3, chart_col4 = st.columns(2)
                    
                    with chart_col3:
                        # Top Overdue Customers
                        col_df = pipeline.data.get('collections', pd.DataFrame())
                        overdue_col = next((c for c in col_df.columns if 'overdue' in c.lower() and 'days' in c.lower()), None)
                        if overdue_col and not col_df.empty:
                            # Convert to numeric safely
                            col_df[overdue_col] = pd.to_numeric(col_df[overdue_col], errors='coerce')
                            top_overdue = col_df.nlargest(5, overdue_col)[['Customer Code', overdue_col, 'Amount Collected']]
                            top_overdue = top_overdue.fillna(0)
                            if not top_overdue.empty:
                                fig_overdue = px.bar(top_overdue, x='Customer Code', y=overdue_col, 
                                                     title="Top 5 Overdue Customers (Days)", text=overdue_col,
                                                     color=overdue_col, color_continuous_scale='Reds')
                                st.plotly_chart(fig_overdue, use_container_width=True)
                            else:
                                st.info("No overdue customers found.")
                        else:
                            st.info("Overdue days data unavailable.")
                            
                    with chart_col4:
                        # Progress Chart (Sales by Project)
                        if not master_df.empty and 'Project' in master_df.columns and 'Booking Value' in master_df.columns:
                            master_df['Booking Value'] = pd.to_numeric(master_df['Booking Value'], errors='coerce')
                            proj_sales = master_df.groupby('Project')['Booking Value'].sum().reset_index()
                            fig_proj = px.bar(proj_sales, x='Project', y='Booking Value', title="Total Sales by Project", 
                                              color='Project', template="plotly_white")
                            st.plotly_chart(fig_proj, use_container_width=True)
                        else:
                            st.info("Project progress data unavailable.")

                    # --- TABBED DETAILS ---
                    st.divider()
                    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📑 Leadership Report", "✉️ Draft Communications", "🚨 Action Items", "🧹 Data Quality", "🔗 Orphaned Records"])
                    
                    with tab1:
                        st.markdown(final_state['final_report'])
                    with tab2:
                        for idx, comm in enumerate(final_state['communications']):
                            st.info(f"**Draft {idx+1}:**\n\n{comm}")
                    with tab3:
                        if not action_items_df.empty:
                            st.dataframe(action_items_df, use_container_width=True)
                    with tab4:
                        if not dq_report.empty:
                            st.dataframe(dq_report, use_container_width=True)
                        else:
                            st.success("🎉 No data quality issues found.")
                    with tab5:
                        if not unmatched_report.empty:
                            st.dataframe(unmatched_report, use_container_width=True)
                        else:
                            st.success("🎉 All records matched perfectly.")

            except Exception as e:
                st.error(f"❌ An error occurred: {str(e)}")
                logger.error(f"Dashboard Exception: {str(e)}")
