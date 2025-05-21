import os
import json
from datetime import datetime
from fpdf import FPDF
import tempfile

def generate_pdf_report(equipment_row, valuation_data):
    """
    Generate a PDF valuation report
    
    Args:
        equipment_row: DataFrame row with equipment details
        valuation_data: Dictionary with valuation results
        
    Returns:
        Path to the generated PDF file
    """
    # Create PDF object
    pdf = FPDF()
    pdf.add_page()
    
    # Set up fonts
    pdf.add_font('DejaVu', '', 'frontend/fonts/DejaVuSans.ttf', uni=True)
    pdf.add_font('DejaVuB', '', 'frontend/fonts/DejaVuSans-Bold.ttf', uni=True)
    pdf.set_font('DejaVu', '', 12)
    
    # Add header with logo
    if os.path.exists("frontend/public/logos/logo.png"):
        pdf.image("frontend/public/logos/logo.png", 10, 8, 30)
    
    pdf.set_font('DejaVuB', '', 18)
    pdf.cell(0, 10, "Equipment Valuation Report", ln=True, align='C')
    pdf.set_font('DejaVu', '', 12)
    pdf.cell(0, 10, f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True, align='C')
    
    # Add equipment details
    pdf.ln(10)
    pdf.set_font('DejaVuB', '', 14)
    pdf.cell(0, 10, "Equipment Details", ln=True)
    
    pdf.set_font('DejaVu', '', 12)
    fields = [
        ("Unit #", equipment_row.get('Unit #', 'N/A')),
        ("Description", equipment_row.get('Description', 'N/A')),
        ("Year", equipment_row.get('Year', 'N/A')),
        ("Location", equipment_row.get('Location', 'N/A')),
        ("Condition", equipment_row.get('Condition', 'N/A'))
    ]
    
    for label, value in fields:
        pdf.cell(40, 10, label, 0)
        pdf.cell(0, 10, str(value), 0, ln=True)
    
    # Add valuation results
    pdf.ln(10)
    pdf.set_font('DejaVuB', '', 14)
    pdf.cell(0, 10, "Valuation Results", ln=True)
    
    pdf.set_font('DejaVu', '', 12)
    
    if isinstance(valuation_data, dict):
        # Value when new
        if 'new_value' in valuation_data:
            pdf.cell(80, 10, "Value When New:", 0)
            pdf.cell(0, 10, f"${valuation_data['new_value']:,.2f}", 0, ln=True)
        
        # Current value range
        if 'current_value_range' in valuation_data:
            min_val, max_val = valuation_data['current_value_range']
            pdf.cell(80, 10, "Current Value Range:", 0)
            pdf.cell(0, 10, f"${min_val:,.2f} - ${max_val:,.2f}", 0, ln=True)
        
        # Confidence level
        if 'confidence' in valuation_data:
            pdf.cell(80, 10, "Confidence Level:", 0)
            pdf.cell(0, 10, valuation_data['confidence'].upper(), 0, ln=True)
        
        # Justification
        if 'justification' in valuation_data:
            pdf.ln(5)
            pdf.set_font('DejaVuB', '', 12)
            pdf.cell(0, 10, "Valuation Justification:", ln=True)
            pdf.set_font('DejaVu', '', 12)
            
            # Split justification into paragraphs and add them
            justification = valuation_data['justification']
            paragraphs = justification.split('\n')
            for para in paragraphs:
                if para.strip():
                    pdf.multi_cell(0, 6, para)
                    pdf.ln(3)
        
        # Comparable sales
        if 'comparable_sales' in valuation_data and valuation_data['comparable_sales']:
            pdf.ln(5)
            pdf.set_font('DejaVuB', '', 12)
            pdf.cell(0, 10, "Comparable Sales:", ln=True)
            pdf.set_font('DejaVu', '', 12)
            
            for i, comp in enumerate(valuation_data['comparable_sales']):
                pdf.cell(0, 6, f"{i+1}. {comp['title']}", ln=True)
                pdf.cell(30, 6, "Price:", 0)
                pdf.cell(0, 6, f"${comp['price']:,.2f}", 0, ln=True)
                pdf.cell(30, 6, "Date:", 0)
                pdf.cell(0, 6, comp['date'], 0, ln=True)
                pdf.cell(30, 6, "Source:", 0)
                pdf.cell(0, 6, comp['url'], 0, ln=True)
                pdf.ln(3)
        
        # Key factors
        if 'key_factors' in valuation_data:
            pdf.ln(5)
            pdf.set_font('DejaVuB', '', 12)
            pdf.cell(0, 10, "Key Factors Affecting Value:", ln=True)
            pdf.set_font('DejaVu', '', 12)
            
            for factor in valuation_data['key_factors']:
                pdf.cell(10, 6, "•", 0)
                pdf.multi_cell(0, 6, factor)
        
        # Enhanced analysis if available
        if 'enhanced_analysis' in valuation_data:
            pdf.ln(5)
            pdf.set_font('DejaVuB', '', 12)
            pdf.cell(0, 10, "Enhanced Analysis:", ln=True)
            pdf.set_font('DejaVu', '', 12)
            
            # Split enhanced analysis into paragraphs
            enhanced = valuation_data['enhanced_analysis']
            paragraphs = enhanced.split('\n')
            for para in paragraphs:
                if para.strip():
                    pdf.multi_cell(0, 6, para)
                    pdf.ln(3)
    else:
        # For raw text response
        pdf.multi_cell(0, 10, "Raw Valuation Data:", ln=True)
        pdf.multi_cell(0, 6, str(valuation_data))
    
    # Add footer
    pdf.ln(10)
    pdf.set_font('DejaVu', '', 10)
    footer_text = "© 2025 White Forrest Resources Inc. - This report is provided for informational purposes only."
    pdf.cell(0, 10, footer_text, ln=True, align='C')
    
    # Save PDF to temp file
    temp_dir = tempfile.mkdtemp()
    unit_id = str(equipment_row.get('Unit #', 'equipment')).replace('/', '-')
    pdf_path = os.path.join(temp_dir, f"{unit_id}_valuation.pdf")
    pdf.output(pdf_path)
    
    return pdf_path