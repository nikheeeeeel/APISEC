"""PDF report generation service."""
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors

from app.core.config import settings


class PDFReportGenerator:
    """Service for generating PDF reports."""
    
    def __init__(self):
        """Initialize PDF report generator."""
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Setup custom paragraph styles."""
        self.styles.add(ParagraphStyle(
            name="Disclaimer",
            parent=self.styles["Normal"],
            fontSize=9,
            textColor=colors.grey,
            fontName="Helvetica-Oblique"
        ))
        
        self.styles.add(ParagraphStyle(
            name="Endpoint",
            parent=self.styles["Normal"],
            fontSize=10,
            fontName="Courier"
        ))
    
    def generate(
        self,
        api_uri: str,
        openapi_spec: Dict[str, Any],
        discovery_method: str,
        output_filename: Optional[str] = None
    ) -> Path:
        """
        Generate PDF report from OpenAPI specification.
        
        Args:
            api_uri: Target API URI
            openapi_spec: OpenAPI specification dictionary
            discovery_method: How the spec was discovered ("existing" or "inferred")
            output_filename: Optional custom filename
            
        Returns:
            Path to generated PDF file
        """
        if output_filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_uri = api_uri.replace("://", "_").replace("/", "_").replace(":", "_")[:50]
            output_filename = f"apisec_report_{safe_uri}_{timestamp}.pdf"
        
        output_path = settings.REPORTS_DIR / output_filename
        
        doc = SimpleDocTemplate(str(output_path), pagesize=letter)
        elements = []
        
        # Title
        elements.append(Paragraph("APISEC v1 - API Documentation Report", self.styles["Title"]))
        elements.append(Spacer(1, 0.2 * inch))
        
        # Metadata
        elements.append(Paragraph(f"<b>Target API:</b> {api_uri}", self.styles["Normal"]))
        elements.append(Paragraph(
            f"<b>Discovery Method:</b> {discovery_method.capitalize()}",
            self.styles["Normal"]
        ))
        elements.append(Paragraph(
            f"<b>Generated:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}",
            self.styles["Normal"]
        ))
        elements.append(Spacer(1, 0.2 * inch))
        
        # Disclaimer
        elements.append(Paragraph(
            "<b>DISCLAIMER:</b>",
            self.styles["Heading3"]
        ))
        disclaimer_text = (
            "This documentation was automatically generated and is provided on a best-effort basis. "
            "It may be incomplete or inaccurate. Auth-protected endpoints, dynamic endpoints, and "
            "non-GET endpoints may not be detected. Use at your own risk."
        )
        elements.append(Paragraph(disclaimer_text, self.styles["Disclaimer"]))
        elements.append(Spacer(1, 0.3 * inch))
        
        # OpenAPI Info
        info = openapi_spec.get("info", {})
        elements.append(Paragraph("<b>OpenAPI Information:</b>", self.styles["Heading3"]))
        elements.append(Paragraph(f"Title: {info.get('title', 'N/A')}", self.styles["Normal"]))
        elements.append(Paragraph(f"Version: {info.get('version', 'N/A')}", self.styles["Normal"]))
        if info.get("description"):
            elements.append(Paragraph(f"Description: {info.get('description')}", self.styles["Normal"]))
        elements.append(Spacer(1, 0.2 * inch))
        
        # Limitations (if inferred)
        if openapi_spec.get("x-generated") == "inferred":
            limitations = openapi_spec.get("x-limitations", [])
            if limitations:
                elements.append(Paragraph("<b>Known Limitations:</b>", self.styles["Heading3"]))
                for limitation in limitations:
                    elements.append(Paragraph(f"• {limitation}", self.styles["Normal"]))
                elements.append(Spacer(1, 0.2 * inch))
        
        # Endpoints Summary
        paths = openapi_spec.get("paths", {})
        endpoint_count = len(paths)
        elements.append(Paragraph(
            f"<b>Discovered Endpoints: {endpoint_count}</b>",
            self.styles["Heading3"]
        ))
        elements.append(Spacer(1, 0.1 * inch))
        
        # Endpoints Table
        if paths:
            table_data = [["Path", "Method", "Status"]]
            for path, methods in paths.items():
                for method, details in methods.items():
                    if isinstance(details, dict):
                        operation_id = details.get("operationId", "N/A")
                        table_data.append([path, method.upper(), operation_id])
            
            table = Table(table_data, colWidths=[4 * inch, 1 * inch, 2 * inch])
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 10),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ("FONTSIZE", (0, 1), (-1, -1), 9),
            ]))
            elements.append(table)
        else:
            elements.append(Paragraph("No endpoints discovered.", self.styles["Normal"]))
        
        elements.append(Spacer(1, 0.3 * inch))
        
        # Footer note
        elements.append(Paragraph(
            "Generated by APISEC v1 - Automated OpenAPI Documentation Generator",
            self.styles["Disclaimer"]
        ))
        
        doc.build(elements)
        return output_path
