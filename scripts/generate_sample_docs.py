"""
Generate sample trade documents (Bill of Lading, Commercial Invoice) as PDFs.
Creates one clean document and one messy/inconsistent document for testing.
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch, mm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
import os

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "sample_docs")
os.makedirs(OUTPUT_DIR, exist_ok=True)

styles = getSampleStyleSheet()


def _header_style():
    return ParagraphStyle("Header", parent=styles["Heading1"], fontSize=16, alignment=TA_CENTER, spaceAfter=6)


def _subheader_style():
    return ParagraphStyle("SubHeader", parent=styles["Heading2"], fontSize=11, alignment=TA_LEFT, spaceAfter=4)


def _normal():
    return styles["Normal"]


# ── Clean Bill of Lading ──────────────────────────────────────────────

def create_clean_bol():
    path = os.path.join(OUTPUT_DIR, "clean_bill_of_lading.pdf")
    doc = SimpleDocTemplate(path, pagesize=A4, topMargin=0.5 * inch, bottomMargin=0.5 * inch)
    story = []

    # Title
    story.append(Paragraph("BILL OF LADING", _header_style()))
    story.append(Paragraph("B/L No: MAEU-BL-2024-78432", ParagraphStyle("BLNo", parent=_normal(), alignment=TA_RIGHT, fontSize=10)))
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.black))
    story.append(Spacer(1, 10))

    # Shipper / Consignee block
    header_data = [
        [Paragraph("<b>Shipper / Exporter</b>", _normal()),
         Paragraph("<b>Consignee</b>", _normal())],
        [Paragraph("Shenzhen Bright Electronics Co., Ltd.\n"
                    "Block C, Bao'an Industrial Park\n"
                    "Shenzhen, Guangdong 518100, China", _normal()),
         Paragraph("TechWorld Distribution GmbH\n"
                    "Industriestrasse 42\n"
                    "60329 Frankfurt am Main, Germany", _normal())],
    ]
    t = Table(header_data, colWidths=[3.2 * inch, 3.2 * inch])
    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.Color(0.9, 0.9, 0.95)),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(t)
    story.append(Spacer(1, 10))

    # Notify party
    story.append(Paragraph("<b>Notify Party:</b> Same as Consignee", _normal()))
    story.append(Spacer(1, 10))

    # Vessel / Voyage
    vessel_data = [
        [Paragraph("<b>Vessel Name</b>", _normal()),
         Paragraph("<b>Voyage No.</b>", _normal()),
         Paragraph("<b>Port of Loading</b>", _normal()),
         Paragraph("<b>Port of Discharge</b>", _normal())],
        [Paragraph("MSC AURORA", _normal()),
         Paragraph("VA-2024-0312", _normal()),
         Paragraph("Yantian, Shenzhen", _normal()),
         Paragraph("Hamburg, Germany", _normal())],
    ]
    t2 = Table(vessel_data, colWidths=[1.6 * inch] * 4)
    t2.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.Color(0.9, 0.9, 0.95)),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(t2)
    story.append(Spacer(1, 10))

    # Goods description
    story.append(Paragraph("<b>Description of Goods:</b>", _subheader_style()))
    goods_data = [
        [Paragraph("<b>Marks & Numbers</b>", _normal()),
         Paragraph("<b>Description</b>", _normal()),
         Paragraph("<b>HS Code</b>", _normal()),
         Paragraph("<b>Gross Weight</b>", _normal()),
         Paragraph("<b>No. of Packages</b>", _normal())],
        [Paragraph("TWDG-2024-A1", _normal()),
         Paragraph("LED Display Panels, 55-inch\nModel: BD-5500X\nPacked in wooden crates", _normal()),
         Paragraph("8528.72", _normal()),
         Paragraph("4,250.00 KGS", _normal()),
         Paragraph("150 Crates", _normal())],
    ]
    t3 = Table(goods_data, colWidths=[1.1 * inch, 2.0 * inch, 0.9 * inch, 1.1 * inch, 1.1 * inch])
    t3.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.Color(0.9, 0.9, 0.95)),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(t3)
    story.append(Spacer(1, 10))

    # Incoterms & Freight
    terms_data = [
        [Paragraph("<b>Incoterms</b>", _normal()),
         Paragraph("<b>Freight</b>", _normal()),
         Paragraph("<b>Place of Delivery</b>", _normal())],
        [Paragraph("CIF Hamburg", _normal()),
         Paragraph("Prepaid", _normal()),
         Paragraph("Frankfurt am Main, Germany", _normal())],
    ]
    t4 = Table(terms_data, colWidths=[2.1 * inch] * 3)
    t4.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.Color(0.9, 0.9, 0.95)),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(t4)
    story.append(Spacer(1, 15))

    # Footer
    story.append(Paragraph("<b>Date of Issue:</b> March 15, 2024", _normal()))
    story.append(Paragraph("<b>Place of Issue:</b> Shenzhen, China", _normal()))
    story.append(Spacer(1, 20))
    story.append(Paragraph("<b>Carrier's Signature:</b> ____________________________", _normal()))

    doc.build(story)
    print(f"Created: {path}")


# ── Clean Commercial Invoice ─────────────────────────────────────────

def create_clean_invoice():
    path = os.path.join(OUTPUT_DIR, "clean_commercial_invoice.pdf")
    doc = SimpleDocTemplate(path, pagesize=A4, topMargin=0.5 * inch, bottomMargin=0.5 * inch)
    story = []

    story.append(Paragraph("COMMERCIAL INVOICE", _header_style()))
    story.append(Paragraph("Invoice No: SBE-INV-2024-1547", ParagraphStyle("InvNo", parent=_normal(), alignment=TA_RIGHT, fontSize=10)))
    story.append(Paragraph("Date: March 14, 2024", ParagraphStyle("Dt", parent=_normal(), alignment=TA_RIGHT, fontSize=10)))
    story.append(Spacer(1, 6))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.black))
    story.append(Spacer(1, 10))

    # Seller / Buyer
    parties = [
        [Paragraph("<b>Seller / Exporter</b>", _normal()),
         Paragraph("<b>Buyer / Consignee</b>", _normal())],
        [Paragraph("Shenzhen Bright Electronics Co., Ltd.\n"
                    "Block C, Bao'an Industrial Park\n"
                    "Shenzhen, Guangdong 518100, China\n"
                    "Tax ID: CN-440300-78954", _normal()),
         Paragraph("TechWorld Distribution GmbH\n"
                    "Industriestrasse 42\n"
                    "60329 Frankfurt am Main, Germany\n"
                    "VAT: DE-812345678", _normal())],
    ]
    t = Table(parties, colWidths=[3.2 * inch, 3.2 * inch])
    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.Color(0.9, 0.9, 0.95)),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(t)
    story.append(Spacer(1, 10))

    # Shipment reference
    ref_data = [
        [Paragraph("<b>B/L Reference</b>", _normal()),
         Paragraph("<b>Port of Loading</b>", _normal()),
         Paragraph("<b>Port of Discharge</b>", _normal()),
         Paragraph("<b>Incoterms</b>", _normal())],
        [Paragraph("MAEU-BL-2024-78432", _normal()),
         Paragraph("Yantian, Shenzhen", _normal()),
         Paragraph("Hamburg, Germany", _normal()),
         Paragraph("CIF Hamburg", _normal())],
    ]
    t2 = Table(ref_data, colWidths=[1.6 * inch] * 4)
    t2.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.Color(0.9, 0.9, 0.95)),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(t2)
    story.append(Spacer(1, 10))

    # Line items
    story.append(Paragraph("<b>Items:</b>", _subheader_style()))
    items = [
        [Paragraph("<b>Item</b>", _normal()),
         Paragraph("<b>Description</b>", _normal()),
         Paragraph("<b>HS Code</b>", _normal()),
         Paragraph("<b>Qty</b>", _normal()),
         Paragraph("<b>Unit Price (USD)</b>", _normal()),
         Paragraph("<b>Total (USD)</b>", _normal())],
        [Paragraph("1", _normal()),
         Paragraph("LED Display Panel 55\" BD-5500X", _normal()),
         Paragraph("8528.72", _normal()),
         Paragraph("150", _normal()),
         Paragraph("320.00", _normal()),
         Paragraph("48,000.00", _normal())],
    ]
    t3 = Table(items, colWidths=[0.5 * inch, 2.0 * inch, 0.8 * inch, 0.6 * inch, 1.2 * inch, 1.2 * inch])
    t3.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.Color(0.9, 0.9, 0.95)),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(t3)
    story.append(Spacer(1, 8))

    # Totals
    story.append(Paragraph("<b>Gross Weight:</b> 4,250.00 KGS", _normal()))
    story.append(Paragraph("<b>Net Weight:</b> 3,800.00 KGS", _normal()))
    story.append(Paragraph("<b>Total Invoice Value:</b> USD 48,000.00", _normal()))
    story.append(Paragraph("<b>Country of Origin:</b> China", _normal()))
    story.append(Spacer(1, 15))
    story.append(Paragraph("<b>Authorized Signature:</b> ____________________________", _normal()))

    doc.build(story)
    print(f"Created: {path}")


# ── Messy Bill of Lading (deliberate errors) ─────────────────────────

def create_messy_bol():
    """Creates a BoL with deliberate inconsistencies:
    - Consignee name slightly different (TechWorld Dist. GmbH vs TechWorld Distribution GmbH)
    - Wrong HS code (8471.30 instead of 8528.72)
    - Missing Incoterms field
    - Gross weight mismatch (4,100 KGS vs 4,250 KGS on invoice)
    """
    path = os.path.join(OUTPUT_DIR, "messy_bill_of_lading.pdf")
    doc = SimpleDocTemplate(path, pagesize=A4, topMargin=0.5 * inch, bottomMargin=0.5 * inch)
    story = []

    story.append(Paragraph("BILL OF LADING", _header_style()))
    story.append(Paragraph("B/L No: MAEU-BL-2024-78433", ParagraphStyle("BLNo", parent=_normal(), alignment=TA_RIGHT, fontSize=10)))
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.black))
    story.append(Spacer(1, 10))

    # Shipper / Consignee — note the consignee name difference
    header_data = [
        [Paragraph("<b>Shipper / Exporter</b>", _normal()),
         Paragraph("<b>Consignee</b>", _normal())],
        [Paragraph("Guangzhou FineTextile Manufacturing\n"
                    "Unit 7, Haizhu Export Zone\n"
                    "Guangzhou, Guangdong 510000, China", _normal()),
         Paragraph("Nordic Imports A/S\n"
                    "Havnegade 28\n"
                    "2100 Copenhagen, Denmark", _normal())],
    ]
    t = Table(header_data, colWidths=[3.2 * inch, 3.2 * inch])
    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.Color(0.9, 0.9, 0.95)),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(t)
    story.append(Spacer(1, 10))

    # Vessel block
    vessel_data = [
        [Paragraph("<b>Vessel Name</b>", _normal()),
         Paragraph("<b>Voyage No.</b>", _normal()),
         Paragraph("<b>Port of Loading</b>", _normal()),
         Paragraph("<b>Port of Discharge</b>", _normal())],
        [Paragraph("EVER GOLDEN", _normal()),
         Paragraph("EG-2024-0087", _normal()),
         Paragraph("Nansha, Guangzhou", _normal()),
         Paragraph("Copenhagen, Denmark", _normal())],
    ]
    t2 = Table(vessel_data, colWidths=[1.6 * inch] * 4)
    t2.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.Color(0.9, 0.9, 0.95)),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(t2)
    story.append(Spacer(1, 10))

    # Goods — WRONG HS code (6204.62 instead of correct 6204.69)
    story.append(Paragraph("<b>Description of Goods:</b>", _subheader_style()))
    goods_data = [
        [Paragraph("<b>Marks & Numbers</b>", _normal()),
         Paragraph("<b>Description</b>", _normal()),
         Paragraph("<b>HS Code</b>", _normal()),
         Paragraph("<b>Gross Weight</b>", _normal()),
         Paragraph("<b>No. of Packages</b>", _normal())],
        [Paragraph("NI-2024-TX-05", _normal()),
         Paragraph("Women's Cotton Trousers\nAssorted sizes S-XL\nPacked in cartons", _normal()),
         Paragraph("6204.62", _normal()),  # WRONG — should be 6204.69
         Paragraph("2,100.00 KGS", _normal()),  # MISMATCH with invoice (2,350 KGS)
         Paragraph("400 Cartons", _normal())],
    ]
    t3 = Table(goods_data, colWidths=[1.1 * inch, 2.0 * inch, 0.9 * inch, 1.1 * inch, 1.1 * inch])
    t3.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.Color(0.9, 0.9, 0.95)),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(t3)
    story.append(Spacer(1, 10))

    # Incoterms — MISSING (left blank intentionally)
    terms_data = [
        [Paragraph("<b>Incoterms</b>", _normal()),
         Paragraph("<b>Freight</b>", _normal()),
         Paragraph("<b>Place of Delivery</b>", _normal())],
        [Paragraph("", _normal()),  # MISSING
         Paragraph("Collect", _normal()),
         Paragraph("Copenhagen, Denmark", _normal())],
    ]
    t4 = Table(terms_data, colWidths=[2.1 * inch] * 3)
    t4.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.Color(0.9, 0.9, 0.95)),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(t4)
    story.append(Spacer(1, 15))

    story.append(Paragraph("<b>Date of Issue:</b> April 2, 2024", _normal()))
    story.append(Paragraph("<b>Place of Issue:</b> Guangzhou, China", _normal()))
    story.append(Spacer(1, 20))
    story.append(Paragraph("<b>Carrier's Signature:</b> ____________________________", _normal()))

    doc.build(story)
    print(f"Created: {path}")


# ── Messy Commercial Invoice ─────────────────────────────────────────

def create_messy_invoice():
    """Invoice for the messy shipment — has its own values that conflict with the BoL above."""
    path = os.path.join(OUTPUT_DIR, "messy_commercial_invoice.pdf")
    doc = SimpleDocTemplate(path, pagesize=A4, topMargin=0.5 * inch, bottomMargin=0.5 * inch)
    story = []

    story.append(Paragraph("COMMERCIAL INVOICE", _header_style()))
    story.append(Paragraph("Invoice No: GFT-INV-2024-0892", ParagraphStyle("InvNo", parent=_normal(), alignment=TA_RIGHT, fontSize=10)))
    story.append(Paragraph("Date: April 1, 2024", ParagraphStyle("Dt", parent=_normal(), alignment=TA_RIGHT, fontSize=10)))
    story.append(Spacer(1, 6))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.black))
    story.append(Spacer(1, 10))

    parties = [
        [Paragraph("<b>Seller / Exporter</b>", _normal()),
         Paragraph("<b>Buyer / Consignee</b>", _normal())],
        [Paragraph("Guangzhou FineTextile Manufacturing\n"
                    "Unit 7, Haizhu Export Zone\n"
                    "Guangzhou, Guangdong 510000, China", _normal()),
         Paragraph("Nordic Imports ApS\n"   # DIFFERENT ENTITY TYPE (ApS vs A/S)
                    "Havnegade 28\n"
                    "2100 Copenhagen, Denmark", _normal())],
    ]
    t = Table(parties, colWidths=[3.2 * inch, 3.2 * inch])
    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.Color(0.9, 0.9, 0.95)),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(t)
    story.append(Spacer(1, 10))

    ref_data = [
        [Paragraph("<b>B/L Reference</b>", _normal()),
         Paragraph("<b>Port of Loading</b>", _normal()),
         Paragraph("<b>Port of Discharge</b>", _normal()),
         Paragraph("<b>Incoterms</b>", _normal())],
        [Paragraph("MAEU-BL-2024-78433", _normal()),
         Paragraph("Nansha, Guangzhou", _normal()),
         Paragraph("Aarhus, Denmark", _normal()),  # DIFFERENT PORT (Aarhus vs Copenhagen)
         Paragraph("FOB Nansha", _normal())],
    ]
    t2 = Table(ref_data, colWidths=[1.6 * inch] * 4)
    t2.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.Color(0.9, 0.9, 0.95)),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(t2)
    story.append(Spacer(1, 10))

    story.append(Paragraph("<b>Items:</b>", _subheader_style()))
    items = [
        [Paragraph("<b>Item</b>", _normal()),
         Paragraph("<b>Description</b>", _normal()),
         Paragraph("<b>HS Code</b>", _normal()),
         Paragraph("<b>Qty</b>", _normal()),
         Paragraph("<b>Unit Price (USD)</b>", _normal()),
         Paragraph("<b>Total (USD)</b>", _normal())],
        [Paragraph("1", _normal()),
         Paragraph("Women's Cotton Trousers, Asst. Sizes", _normal()),
         Paragraph("6204.69", _normal()),   # CORRECT HS code (conflicts with BoL's 6204.62)
         Paragraph("2,000", _normal()),
         Paragraph("8.50", _normal()),
         Paragraph("17,000.00", _normal())],
    ]
    t3 = Table(items, colWidths=[0.5 * inch, 2.0 * inch, 0.8 * inch, 0.6 * inch, 1.2 * inch, 1.2 * inch])
    t3.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.Color(0.9, 0.9, 0.95)),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(t3)
    story.append(Spacer(1, 8))

    story.append(Paragraph("<b>Gross Weight:</b> 2,350.00 KGS", _normal()))  # MISMATCH with BoL (2,100)
    story.append(Paragraph("<b>Net Weight:</b> 2,000.00 KGS", _normal()))
    story.append(Paragraph("<b>Total Invoice Value:</b> USD 17,000.00", _normal()))
    story.append(Paragraph("<b>Country of Origin:</b> China", _normal()))
    story.append(Spacer(1, 15))
    story.append(Paragraph("<b>Authorized Signature:</b> ____________________________", _normal()))

    doc.build(story)
    print(f"Created: {path}")


if __name__ == "__main__":
    create_clean_bol()
    create_clean_invoice()
    create_messy_bol()
    create_messy_invoice()
    print("\nAll sample documents created in:", os.path.abspath(OUTPUT_DIR))
