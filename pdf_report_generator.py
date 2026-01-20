#!/usr/bin/env python3
"""
PDF Report Generator Module

Generates professional, branded PDF audiometry reports using ReportLab.
Includes patient details, audiogram image, test results, and interpretation.

Author: Audiometry Application
"""

import os
import io
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import inch, cm
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        Image, HRFlowable, PageBreak
    )
    from reportlab.pdfgen import canvas
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False
    logging.warning("ReportLab not installed. PDF generation will not be available.")

# Configure logging
logger = logging.getLogger(__name__)


class PDFReportGenerator:
    """
    Professional PDF report generator for audiometry results.
    
    Creates branded PDF reports containing:
    - Hospital header/logo
    - Patient demographics
    - Audiogram image
    - Test results table
    - Interpretation and remarks
    - Doctor signature section
    
    Example Usage:
        >>> generator = PDFReportGenerator(
        ...     patient_data={'name': 'John Doe', 'age': 45, 'id': 'REF-001'},
        ...     test_results={'left': {500: 25, 1000: 30}, 'right': {500: 20, 1000: 25}},
        ...     interpretation={'summary': 'Mild bilateral hearing loss'}
        ... )
        >>> pdf_path = generator.generate_report('/path/to/output.pdf')
    """
    
    # Hospital branding
    HOSPITAL_NAME = "Dukh Niwaran Mission"
    HOSPITAL_SUBTITLE = "Audiometry Department"
    HOSPITAL_ADDRESS = ""  # Can be customized
    
    # Standard audiometric frequencies
    FREQUENCIES = [250, 500, 1000, 2000, 4000, 8000]
    
    # Colors
    COLOR_PRIMARY = colors.HexColor('#1A5CFF')
    COLOR_HEADER = colors.HexColor('#00838F')
    COLOR_TEXT = colors.HexColor('#333333')
    COLOR_MUTED = colors.HexColor('#666666')
    COLOR_LEFT_EAR = colors.HexColor('#3B82F6')  # Blue
    COLOR_RIGHT_EAR = colors.HexColor('#EF4444')  # Red
    
    def __init__(
        self,
        patient_data: Dict[str, Any],
        test_results: Dict[str, Dict[int, float]],
        interpretation: Optional[Dict[str, Any]] = None,
        audiogram_path: Optional[str] = None,
        audiogram_base64: Optional[str] = None,
        test_date: Optional[datetime] = None,
        doctor_name: Optional[str] = None,
        remarks: Optional[str] = None
    ):
        """
        Initialize the PDF generator.
        
        Args:
            patient_data: Dict with patient info (name, age, id, gender, phone).
            test_results: Dict with 'left' and 'right' ear data {freq: dB}.
            interpretation: Dict from InterpretationEngine.analyze().
            audiogram_path: Path to the audiogram PNG image.
            audiogram_base64: Base64-encoded audiogram image (alternative).
            test_date: Date of the test (defaults to now).
            doctor_name: Name of the examining doctor.
            remarks: Additional remarks from the doctor.
        """
        if not HAS_REPORTLAB:
            raise ImportError("ReportLab is required for PDF generation. Install with: pip install reportlab")
        
        self.patient_data = patient_data
        self.test_results = test_results
        self.interpretation = interpretation or {}
        self.audiogram_path = audiogram_path
        self.audiogram_base64 = audiogram_base64
        self.test_date = test_date or datetime.now()
        self.doctor_name = doctor_name or ""
        self.remarks = remarks or ""
        
        # Initialize styles
        self._setup_styles()
    
    def _setup_styles(self):
        """Set up paragraph and text styles."""
        self.styles = getSampleStyleSheet()
        
        # Hospital header style
        self.styles.add(ParagraphStyle(
            name='HospitalName',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=self.COLOR_HEADER,
            alignment=TA_CENTER,
            spaceAfter=6
        ))
        
        self.styles.add(ParagraphStyle(
            name='HospitalSubtitle',
            parent=self.styles['Normal'],
            fontSize=12,
            textColor=self.COLOR_MUTED,
            alignment=TA_CENTER,
            spaceAfter=20
        ))
        
        # Section header style
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=14,
            textColor=self.COLOR_HEADER,
            spaceBefore=20,
            spaceAfter=10,
            borderPadding=5
        ))
        
        # Normal text styles
        self.styles.add(ParagraphStyle(
            name='FieldLabel',
            parent=self.styles['Normal'],
            fontSize=9,
            textColor=self.COLOR_MUTED,
            spaceAfter=2
        ))
        
        self.styles.add(ParagraphStyle(
            name='FieldValue',
            parent=self.styles['Normal'],
            fontSize=11,
            textColor=self.COLOR_TEXT,
            spaceAfter=8
        ))
        
        self.styles.add(ParagraphStyle(
            name='Remark',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=self.COLOR_TEXT,
            leftIndent=20,
            bulletIndent=10,
            spaceBefore=4
        ))
        
        self.styles.add(ParagraphStyle(
            name='Footer',
            parent=self.styles['Normal'],
            fontSize=8,
            textColor=self.COLOR_MUTED,
            alignment=TA_CENTER
        ))
    
    def generate_report(self, output_path: str) -> str:
        """
        Generate the PDF report.
        
        Args:
            output_path: Path where the PDF will be saved.
            
        Returns:
            The path to the generated PDF file.
        """
        # Ensure directory exists
        os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else '.', exist_ok=True)
        
        # Create the document
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            rightMargin=1.5*cm,
            leftMargin=1.5*cm,
            topMargin=1.5*cm,
            bottomMargin=2*cm
        )
        
        # Build the content
        story = []
        
        # Header
        story.extend(self._build_header())
        
        # Patient information
        story.extend(self._build_patient_section())
        
        # Audiogram image
        story.extend(self._build_audiogram_section())
        
        # Results table
        story.extend(self._build_results_table())
        
        # Interpretation
        story.extend(self._build_interpretation_section())
        
        # Signature section
        story.extend(self._build_signature_section())
        
        # Build the PDF
        doc.build(story, onFirstPage=self._add_footer, onLaterPages=self._add_footer)
        
        logger.info(f"PDF report generated: {output_path}")
        return output_path
    
    def _build_header(self) -> List:
        """Build the hospital header section."""
        elements = []
        
        # Hospital name
        elements.append(Paragraph(self.HOSPITAL_NAME, self.styles['HospitalName']))
        
        # Subtitle
        elements.append(Paragraph(self.HOSPITAL_SUBTITLE, self.styles['HospitalSubtitle']))
        
        # Report title
        elements.append(Paragraph(
            "AUDIOMETRY TEST REPORT",
            ParagraphStyle(
                name='ReportTitle',
                parent=self.styles['Heading2'],
                fontSize=16,
                textColor=self.COLOR_PRIMARY,
                alignment=TA_CENTER,
                spaceAfter=10
            )
        ))
        
        # Horizontal line
        elements.append(HRFlowable(
            width="100%",
            thickness=1,
            color=self.COLOR_HEADER,
            spaceBefore=5,
            spaceAfter=20
        ))
        
        return elements
    
    def _build_patient_section(self) -> List:
        """Build the patient information section."""
        elements = []
        
        elements.append(Paragraph("Patient Information", self.styles['SectionHeader']))
        
        # Patient details in a table format
        patient = self.patient_data
        
        data = [
            ["Name:", patient.get('name', '--'), "ID:", patient.get('id', '--')],
            ["Age:", str(patient.get('age', '--')), "Gender:", patient.get('gender', '--').title()],
            ["Phone:", patient.get('phone', '--'), "Test Date:", self.test_date.strftime("%d-%m-%Y %H:%M")],
        ]
        
        # Add referring physician if available
        if patient.get('referring_physician'):
            data.append(["Referring Physician:", patient.get('referring_physician'), "", ""])
        
        table = Table(data, colWidths=[2.5*cm, 5*cm, 2.5*cm, 5*cm])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
            ('TEXTCOLOR', (0, 0), (0, -1), self.COLOR_MUTED),
            ('TEXTCOLOR', (2, 0), (2, -1), self.COLOR_MUTED),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 15))
        
        return elements
    
    def _build_audiogram_section(self) -> List:
        """Build the audiogram image section."""
        elements = []
        
        elements.append(Paragraph("Pure Tone Audiogram", self.styles['SectionHeader']))
        
        # Try to include the audiogram image
        if self.audiogram_path and os.path.exists(self.audiogram_path):
            try:
                img = Image(self.audiogram_path)
                # Scale to fit page width while maintaining aspect ratio
                img_width = 15 * cm
                img_height = 12 * cm
                img.drawWidth = img_width
                img.drawHeight = img_height
                elements.append(img)
            except Exception as e:
                logger.error(f"Failed to include audiogram image: {e}")
                elements.append(Paragraph("[Audiogram image could not be loaded]", self.styles['Normal']))
        elif self.audiogram_base64:
            try:
                import base64
                img_data = base64.b64decode(self.audiogram_base64)
                img_buffer = io.BytesIO(img_data)
                img = Image(img_buffer)
                img_width = 15 * cm
                img_height = 12 * cm
                img.drawWidth = img_width
                img.drawHeight = img_height
                elements.append(img)
            except Exception as e:
                logger.error(f"Failed to decode base64 audiogram: {e}")
                elements.append(Paragraph("[Audiogram image could not be loaded]", self.styles['Normal']))
        else:
            elements.append(Paragraph("[Audiogram image not available]", self.styles['Normal']))
        
        elements.append(Spacer(1, 15))
        
        return elements
    
    def _build_results_table(self) -> List:
        """Build the test results table."""
        elements = []
        
        elements.append(Paragraph("Test Results", self.styles['SectionHeader']))
        
        # Header row
        header = ["Ear / Frequency"] + [f"{f} Hz" for f in self.FREQUENCIES]
        
        # Left ear row
        left_data = self.test_results.get('left', {})
        left_row = ["Left Ear (X)"] + [
            f"{left_data.get(f, left_data.get(str(f), '--'))} dB" 
            for f in self.FREQUENCIES
        ]
        
        # Right ear row
        right_data = self.test_results.get('right', {})
        right_row = ["Right Ear (O)"] + [
            f"{right_data.get(f, right_data.get(str(f), '--'))} dB" 
            for f in self.FREQUENCIES
        ]
        
        # PTA row
        left_pta = self.interpretation.get('left_ear', {}).get('pta', '--')
        right_pta = self.interpretation.get('right_ear', {}).get('pta', '--')
        pta_row = ["PTA (dB HL)"] + [""] * (len(self.FREQUENCIES) - 1) + [
            f"Left: {left_pta}, Right: {right_pta}"
        ]
        
        table_data = [header, left_row, right_row]
        
        col_widths = [3.5*cm] + [2*cm] * len(self.FREQUENCIES)
        table = Table(table_data, colWidths=col_widths)
        
        table.setStyle(TableStyle([
            # Header style
            ('BACKGROUND', (0, 0), (-1, 0), self.COLOR_HEADER),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            
            # Left ear row
            ('BACKGROUND', (0, 1), (0, 1), self.COLOR_LEFT_EAR),
            ('TEXTCOLOR', (0, 1), (0, 1), colors.white),
            ('FONTNAME', (0, 1), (0, 1), 'Helvetica-Bold'),
            
            # Right ear row
            ('BACKGROUND', (0, 2), (0, 2), self.COLOR_RIGHT_EAR),
            ('TEXTCOLOR', (0, 2), (0, 2), colors.white),
            ('FONTNAME', (0, 2), (0, 2), 'Helvetica-Bold'),
            
            # Data cells
            ('FONTNAME', (1, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            
            # Grid
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
        ]))
        
        elements.append(table)
        
        # PTA summary
        if left_pta != '--' or right_pta != '--':
            pta_text = f"<b>Pure Tone Average (PTA):</b> Left Ear: {left_pta} dB HL | Right Ear: {right_pta} dB HL"
            elements.append(Spacer(1, 10))
            elements.append(Paragraph(pta_text, self.styles['Normal']))
        
        elements.append(Spacer(1, 15))
        
        return elements
    
    def _build_interpretation_section(self) -> List:
        """Build the interpretation and remarks section."""
        elements = []
        
        elements.append(Paragraph("Interpretation", self.styles['SectionHeader']))
        
        # Summary
        summary = self.interpretation.get('summary', 'No interpretation available.')
        elements.append(Paragraph(f"<b>Summary:</b> {summary}", self.styles['Normal']))
        elements.append(Spacer(1, 10))
        
        # Classification
        left_class = self.interpretation.get('left_ear', {}).get('classification', 'N/A')
        right_class = self.interpretation.get('right_ear', {}).get('classification', 'N/A')
        elements.append(Paragraph(
            f"<b>Classification:</b> Left Ear: {left_class} | Right Ear: {right_class}",
            self.styles['Normal']
        ))
        elements.append(Spacer(1, 10))
        
        # Remarks from interpretation engine
        remarks = self.interpretation.get('remarks', [])
        if remarks:
            elements.append(Paragraph("<b>Clinical Findings:</b>", self.styles['Normal']))
            for remark in remarks:
                elements.append(Paragraph(f"• {remark}", self.styles['Remark']))
        
        # Recommendations
        recommendations = self.interpretation.get('recommendations', [])
        if recommendations:
            elements.append(Spacer(1, 10))
            elements.append(Paragraph("<b>Recommendations:</b>", self.styles['Normal']))
            for rec in recommendations:
                elements.append(Paragraph(f"• {rec}", self.styles['Remark']))
        
        # Doctor's additional remarks
        if self.remarks:
            elements.append(Spacer(1, 15))
            elements.append(Paragraph("<b>Additional Remarks:</b>", self.styles['Normal']))
            elements.append(Paragraph(self.remarks, self.styles['Normal']))
        
        elements.append(Spacer(1, 30))
        
        return elements
    
    def _build_signature_section(self) -> List:
        """Build the signature section."""
        elements = []
        
        # Signature table
        sig_data = [
            ["", ""],
            ["_" * 35, "_" * 35],
            ["Patient Signature", "Audiologist/Doctor Signature"],
            ["", self.doctor_name if self.doctor_name else ""],
            ["", ""],
            [f"Date: {self.test_date.strftime('%d-%m-%Y')}", f"Date: {self.test_date.strftime('%d-%m-%Y')}"],
        ]
        
        table = Table(sig_data, colWidths=[8*cm, 8*cm])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('FONTNAME', (0, 2), (-1, 2), 'Helvetica-Bold'),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        
        elements.append(table)
        
        return elements
    
    def _add_footer(self, canvas_obj, doc):
        """Add footer to each page."""
        canvas_obj.saveState()
        
        # Page number
        page_num = canvas_obj.getPageNumber()
        footer_text = f"Page {page_num} | Generated on {datetime.now().strftime('%d-%m-%Y %H:%M')} | {self.HOSPITAL_NAME}"
        
        canvas_obj.setFont('Helvetica', 8)
        canvas_obj.setFillColor(self.COLOR_MUTED)
        canvas_obj.drawCentredString(A4[0] / 2, 1.5 * cm, footer_text)
        
        # Confidentiality notice
        conf_text = "This report is confidential and intended for medical use only."
        canvas_obj.setFont('Helvetica-Oblique', 7)
        canvas_obj.drawCentredString(A4[0] / 2, 1 * cm, conf_text)
        
        canvas_obj.restoreState()
    
    def generate_report_bytes(self) -> bytes:
        """
        Generate the PDF and return as bytes (for sending via API).
        
        Returns:
            PDF content as bytes.
        """
        buffer = io.BytesIO()
        
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=1.5*cm,
            leftMargin=1.5*cm,
            topMargin=1.5*cm,
            bottomMargin=2*cm
        )
        
        story = []
        story.extend(self._build_header())
        story.extend(self._build_patient_section())
        story.extend(self._build_audiogram_section())
        story.extend(self._build_results_table())
        story.extend(self._build_interpretation_section())
        story.extend(self._build_signature_section())
        
        doc.build(story, onFirstPage=self._add_footer, onLaterPages=self._add_footer)
        
        buffer.seek(0)
        return buffer.read()


# Module test
if __name__ == '__main__':
    import tempfile
    
    if not HAS_REPORTLAB:
        print("ReportLab not installed. Run: pip install reportlab")
        exit(1)
    
    # Test data
    patient = {
        'name': 'John Doe',
        'age': 45,
        'id': 'REF-001',
        'gender': 'male',
        'phone': '9876543210',
        'referring_physician': 'Dr. Smith'
    }
    
    results = {
        'left': {250: 20, 500: 25, 1000: 30, 2000: 35, 4000: 45, 8000: 40},
        'right': {250: 15, 500: 20, 1000: 25, 2000: 30, 4000: 35, 8000: 30}
    }
    
    interpretation = {
        'summary': 'Mild bilateral hearing loss with high-frequency involvement.',
        'left_ear': {'classification': 'Mild Loss', 'pta': 30.0},
        'right_ear': {'classification': 'Mild Loss', 'pta': 25.0},
        'remarks': [
            'Signs of Noise-Induced Hearing Loss detected (4kHz notch pattern)',
            'Asymmetric hearing loss noted'
        ],
        'recommendations': [
            'Follow-up audiometry in 6 months',
            'Hearing protection recommended in noisy environments'
        ]
    }
    
    # Generate test PDF
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
        output_path = f.name
    
    generator = PDFReportGenerator(
        patient_data=patient,
        test_results=results,
        interpretation=interpretation,
        doctor_name="Dr. audiologist",
        remarks="Patient reports occupational noise exposure over 20 years."
    )
    
    pdf_path = generator.generate_report(output_path)
    print(f"PDF generated: {pdf_path}")
    print(f"Open with: start {pdf_path}")
