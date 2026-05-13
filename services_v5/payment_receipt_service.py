"""
Payment Receipt generation service for B-Lite Billing v6.0.
"""

import os
from datetime import datetime

try:
    from reportlab.pdfgen import canvas as rl_canvas
    from reportlab.lib.units import mm
except ImportError:
    rl_canvas = None

from print_utils import center_text, right_align, separator
from branding import get_invoice_branding


def generate_settlement_text(data: dict) -> str:
    """Generate monospace text layout for the settlement receipt."""
    width = 42 # 80mm standard width
    
    brand_data = get_invoice_branding()
    salon_name = brand_data.get("name", "B-Lite Salon")
    address = brand_data.get("address", "")
    phone = brand_data.get("phone", "")
    
    lines = []
    lines.append(center_text(salon_name, width))
    if address:
        lines.append(center_text(address, width))
    if phone:
        lines.append(center_text(f"Ph: {phone}", width))
    
    lines.append(separator(width, "="))
    lines.append(center_text("DUE SETTLEMENT RECEIPT", width))
    lines.append(separator(width, "="))
    
    lines.append(f"Receipt No: {data.get('receipt_no', '')}")
    lines.append(f"Date      : {data.get('date', '')}")
    lines.append(f"Staff     : {data.get('handled_by', 'Admin')}")
    
    lines.append(separator(width, "-"))
    
    lines.append(f"Customer  : {data.get('customer_name', '')}")
    lines.append(f"Phone     : {data.get('customer_phone', '')}")
    
    lines.append(separator(width, "-"))
    
    lines.append(right_align("Previous Due:", f"Rs.{data.get('previous_due', 0):.2f}", width))
    lines.append(right_align("Amount Paid :", f"Rs.{data.get('amount_paid', 0):.2f}", width))
    lines.append(separator(width, "-"))
    lines.append(right_align("Remaining Due:", f"Rs.{data.get('new_due', 0):.2f}", width))
    
    lines.append(separator(width, "-"))
    lines.append(f"Payment Mode: {data.get('payment_method', 'Cash')}")
    
    lines.append(separator(width, "="))
    lines.append(center_text("Thank you!", width))
    lines.append(separator(width, "="))
    lines.append("")
    lines.append("")
    
    return "\n".join(lines)


def generate_settlement_receipt(data: dict, output_path: str) -> str:
    """
    Generate a thermal-style PDF receipt for a due settlement.
    Returns the path to the saved PDF.
    """
    if not rl_canvas:
        raise ImportError("reportlab is required to generate PDF receipts.")
        
    text_content = generate_settlement_text(data)
    lines = text_content.split("\n")
    
    font_size = 8
    line_gap = font_size + 3
    
    # Calculate required height based on lines
    page_h = (len(lines) + 2) * line_gap
    page_w = 80 * mm
    
    c = rl_canvas.Canvas(output_path, pagesize=(page_w, page_h))
    
    # Usually Courier or Helvetica
    c.setFont("Courier", font_size)
    
    y = page_h - line_gap
    x = 2 * mm # margin
    
    for line in lines:
        c.drawString(x, y, line)
        y -= line_gap
        
    c.showPage()
    c.save()
    
    return output_path
