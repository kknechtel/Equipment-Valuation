import streamlit as st
import pandas as pd
import os
import json
import base64
from pathlib import Path
from datetime import datetime

# Import valuation engine
from backend.valuation_engine.claude_valuation import process_equipment_item, process_equipment_list
from backend.data_processors.data_processor import load_data, validate_equipment_data
from backend.utils.report_generator import generate_pdf_report

# Set page configuration
st.set_page_config(
    page_title="Equipment Valuation System",
    page_icon="🚜",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'equipment_data' not in st.session_state:
    st.session_state.equipment_data = None
if 'valuation_results' not in st.session_state:
    st.session_state.valuation_results = {}
if 'selected_equipment' not in st.session_state:
    st.session_state.selected_equipment = None
    
# Application header
col1, col2 = st.columns([1, 5])
with col1:
    st.image("frontend/public/logos/logo.png", width=100)
with col2:
    st.title("Automated Equipment Valuation System")
    st.caption("Powered by Claude API")

# Sidebar
st.sidebar.header("Controls")

upload_option = st.sidebar.radio("Choose input method:", ["Upload File", "Use Sample Data"])

if upload_option == "Upload File":
    uploaded_file = st.sidebar.file_uploader("Upload equipment list", type=["csv", "xlsx", "xls"])
    if uploaded_file is not None:
        try:
            # Load and validate data
            df = load_data(uploaded_file)
            validated_df = validate_equipment_data(df)
            st.session_state.equipment_data = validated_df
            
            if 'validation_issues' in validated_df.columns:
                issues_count = validated_df['validation_issues'].str.len().sum()
                if issues_count > 0:
                    st.sidebar.warning(f"Found {issues_count} potential data issues")
        except Exception as e:
            st.sidebar.error(f"Error loading file: {str(e)}")
else:
    if st.sidebar.button("Load Sample Data"):
        sample_path = "data/sample_data/sample_equipment_list.csv"
        if os.path.exists(sample_path):
            df = load_data(sample_path)
            validated_df = validate_equipment_data(df)
            st.session_state.equipment_data = validated_df
            st.sidebar.success("Sample data loaded successfully!")
        else:
            st.sidebar.error("Sample data file not found")

# Process button
if st.session_state.equipment_data is not None:
    if st.sidebar.button("Process Valuations"):
        with st.spinner("Processing equipment valuations..."):
            results = {}
            for idx, row in st.session_state.equipment_data.iterrows():
                unit_id = row['Unit #']
                st.sidebar.text(f"Processing: {unit_id}")
                result = process_equipment_item(row)
                results[unit_id] = result
            st.session_state.valuation_results = results
            st.sidebar.success("Valuation complete!")

# Main content area
if st.session_state.equipment_data is not None:
    # Display equipment list
    st.header("Equipment List")
    
    # Add filters
    col1, col2, col3 = st.columns(3)
    with col1:
        if 'Year' in st.session_state.equipment_data.columns:
            years = st.session_state.equipment_data['Year'].astype(str).unique().tolist()
            selected_years = st.multiselect("Filter by Year", years)
    with col2:
        if 'Location' in st.session_state.equipment_data.columns:
            locations = st.session_state.equipment_data['Location'].unique().tolist()
            selected_locations = st.multiselect("Filter by Location", locations)
    with col3:
        if 'Condition' in st.session_state.equipment_data.columns:
            conditions = st.session_state.equipment_data['Condition'].unique().tolist()
            selected_conditions = st.multiselect("Filter by Condition", conditions)
    
    # Apply filters
    filtered_data = st.session_state.equipment_data.copy()
    if 'Year' in filtered_data.columns and selected_years:
        filtered_data = filtered_data[filtered_data['Year'].astype(str).isin(selected_years)]
    if 'Location' in filtered_data.columns and selected_locations:
        filtered_data = filtered_data[filtered_data['Location'].isin(selected_locations)]
    if 'Condition' in filtered_data.columns and selected_conditions:
        filtered_data = filtered_data[filtered_data['Condition'].isin(selected_conditions)]
    
    # Display data table with clickable rows
    def highlight_row(df):
        return [
            'background-color: #e6f3ff' if i == st.session_state.selected_equipment else '' 
            for i in range(len(df))
        ]
    
    if not filtered_data.empty:
        st.dataframe(filtered_data.style.apply(highlight_row, axis=0), use_container_width=True)
        
        # Equipment selection
        selected_unit = st.selectbox("Select equipment for detailed valuation", 
                                     filtered_data['Unit #'].tolist())
        
        if selected_unit:
            st.session_state.selected_equipment = filtered_data[filtered_data['Unit #'] == selected_unit].index[0]
            selected_row = filtered_data[filtered_data['Unit #'] == selected_unit].iloc[0]
            
            # Display detailed equipment info
            st.header(f"Equipment Details: {selected_unit}")
            
            col1, col2 = st.columns([2, 3])
            
            with col1:
                st.subheader("Specifications")
                specs = {
                    "Unit #": selected_row['Unit #'],
                    "Description": selected_row['Description'],
                    "Year": selected_row['Year'] if 'Year' in selected_row else "N/A",
                    "Location": selected_row['Location'] if 'Location' in selected_row else "N/A",
                    "Condition": selected_row['Condition'] if 'Condition' in selected_row else "N/A"
                }
                
                for key, value in specs.items():
                    st.text(f"{key}: {value}")
                
                # Check if we have valuation results
                if st.session_state.valuation_results and selected_unit in st.session_state.valuation_results:
                    valuation = st.session_state.valuation_results[selected_unit]
                    
                    # Generate PDF report
                    if st.button("Generate PDF Report"):
                        pdf_path = generate_pdf_report(selected_row, valuation)
                        
                        # Create download link
                        with open(pdf_path, "rb") as pdf_file:
                            pdf_bytes = pdf_file.read()
                            b64 = base64.b64encode(pdf_bytes).decode()
                            href = f'<a href="data:application/pdf;base64,{b64}" download="{selected_unit}_valuation.pdf">Download PDF Report</a>'
                            st.markdown(href, unsafe_allow_html=True)
            
            with col2:
                # Display valuation results if available
                if st.session_state.valuation_results and selected_unit in st.session_state.valuation_results:
                    valuation = st.session_state.valuation_results[selected_unit]
                    
                    if isinstance(valuation, dict):
                        st.subheader("Valuation Results")
                        
                        if 'new_value' in valuation:
                            st.metric("Value When New", f"${valuation['new_value']:,.2f}")
                        
                        if 'current_value_range' in valuation:
                            min_val, max_val = valuation['current_value_range']
                            st.metric("Current Value Range", f"${min_val:,.2f} - ${max_val:,.2f}")
                            
                        if 'confidence' in valuation:
                            confidence = valuation['confidence']
                            confidence_color = {
                                'high': 'green',
                                'medium': 'orange',
                                'low': 'red'
                            }.get(confidence.lower(), 'gray')
                            st.markdown(f"Confidence: <span style='color:{confidence_color};font-weight:bold'>{confidence.upper()}</span>", unsafe_allow_html=True)
                        
                        if 'justification' in valuation:
                            with st.expander("Valuation Justification", expanded=True):
                                st.write(valuation['justification'])
                                
                        if 'comparable_sales' in valuation and valuation['comparable_sales']:
                            with st.expander("Comparable Sales"):
                                for i, comp in enumerate(valuation['comparable_sales']):
                                    st.markdown(f"**{i+1}. {comp['title']}**")
                                    st.markdown(f"Price: ${comp['price']:,.2f}")
                                    st.markdown(f"Date: {comp['date']}")
                                    st.markdown(f"[Source]({comp['url']})")
                                    if i < len(valuation['comparable_sales']) - 1:
                                        st.markdown("---")
                        
                        if 'key_factors' in valuation:
                            with st.expander("Key Factors Affecting Value"):
                                for factor in valuation['key_factors']:
                                    st.markdown(f"- {factor}")
                    else:
                        # Raw response display
                        with st.expander("Raw Valuation Response"):
                            st.write(valuation)
                else:
                    st.info("Click 'Process Valuations' in the sidebar to generate a valuation for this equipment")
    else:
        st.info("No equipment matches the selected filters")
else:
    st.info("Please upload an equipment list or use the sample data to begin")

# Footer
st.markdown("---")
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    st.markdown("<div style='text-align: center'>© 2025 White Forrest Resources Inc.</div>", unsafe_allow_html=True)
    st.markdown(f"<div style='text-align: center'>Generated on {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC</div>", unsafe_allow_html=True)