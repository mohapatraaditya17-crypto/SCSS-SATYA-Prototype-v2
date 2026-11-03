import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict, List

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image as RLImage,
    KeepTogether,
    HRFlowable,
)
from reportlab.pdfgen import canvas

from app.core.config import settings
from app.database.models import Examination


class NumberedCanvas(canvas.Canvas):
    """
    Two-pass canvas to dynamically compute and print 'Page X of Y' along with header/footer.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, total_pages: int):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748B"))

        # Header (Pages > 1)
        if self._pageNumber > 1:
            self.drawString(54, 750, "SCSS SATYA — Forensic Image Authenticity Screening Report")
            self.drawRightString(612 - 54, 750, f"Case: {getattr(self, 'case_id', 'EVIDENCE')}")
            self.setStrokeColor(colors.HexColor("#CBD5E1"))
            self.setLineWidth(0.5)
            self.line(54, 744, 612 - 54, 744)

        # Footer
        footer_y = 36
        self.setStrokeColor(colors.HexColor("#CBD5E1"))
        self.setLineWidth(0.5)
        self.line(54, footer_y + 12, 612 - 54, footer_y + 12)

        self.drawString(54, footer_y, "SURE CLUE SCIENTIFIC SOLUTIONS (SCSS) • PRELIMINARY SCREENING RECORD")
        page_str = f"Page {self._pageNumber} of {total_pages}"
        self.drawRightString(612 - 54, footer_y, page_str)
        self.restoreState()


class PDFReportGenerator:
    @classmethod
    def generate(cls, exam: Examination, output_path: Path) -> Path:
        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=letter,
            leftMargin=54,
            rightMargin=54,
            topMargin=54,
            bottomMargin=54,
        )

        styles = getSampleStyleSheet()

        # Custom typography styles
        title_style = ParagraphStyle(
            "DocTitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=22,
            textColor=colors.HexColor("#0F1E36"),  # SCSS Navy
        )

        subtitle_style = ParagraphStyle(
            "DocSubtitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#C5A059"),  # Refined Gold
        )

        meta_label_style = ParagraphStyle(
            "MetaLabel",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#334155"),
        )

        meta_val_style = ParagraphStyle(
            "MetaVal",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#1E293B"),
        )

        heading_style = ParagraphStyle(
            "SectionHeading",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=16,
            textColor=colors.HexColor("#0F1E36"),
            spaceBefore=12,
            spaceAfter=6,
        )

        body_style = ParagraphStyle(
            "Body",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=12,
            textColor=colors.HexColor("#1E293B"),
        )

        disclaimer_style = ParagraphStyle(
            "Disclaimer",
            parent=styles["Normal"],
            fontName="Helvetica-Oblique",
            fontSize=7.5,
            leading=10.5,
            textColor=colors.HexColor("#475569"),
        )

        story = []

        # Header Block
        story.append(Paragraph("SCSS SATYA FORENSIC EXAMINATION REPORT", title_style))
        story.append(Paragraph("DIGITAL IMAGE AUTHENTICITY SCREENING & INTEGRITY AUDIT", subtitle_style))
        story.append(Spacer(1, 8))
        story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#0F1E36"), spaceAfter=10))

        # Prominent Mandatory Disclaimer Callout Box
        disclaimer_text = f"<b>IMPORTANT FORENSIC NOTICE:</b> {settings.MANDATORY_DISCLAIMER}"
        disclaimer_table = Table(
            [[Paragraph(disclaimer_text, disclaimer_style)]],
            colWidths=[504],
        )
        disclaimer_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
                ("BOX", (0, 0), (-1, -1), 0.75, colors.HexColor("#C5A059")),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ])
        )
        story.append(disclaimer_table)
        story.append(Spacer(1, 10))

        # Evidence & Case Summary Table
        story.append(Paragraph("1. EVIDENCE RECORD & METRIC SUMMARY", heading_style))
        exam_time_str = exam.upload_timestamp.strftime("%Y-%m-%d %H:%M:%S UTC") if exam.upload_timestamp else "N/A"
        report_time_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        evidence_data = [
            [Paragraph("Examination ID", meta_label_style), Paragraph(exam.examination_id, meta_val_style),
             Paragraph("Upload Timestamp", meta_label_style), Paragraph(exam_time_str, meta_val_style)],
            [Paragraph("Original Filename", meta_label_style), Paragraph(exam.original_filename, meta_val_style),
             Paragraph("Report Generated", meta_label_style), Paragraph(report_time_str, meta_val_style)],
            [Paragraph("File Size", meta_label_style), Paragraph(f"{exam.file_size_bytes} bytes ({exam.file_size_bytes/1024:.1f} KB)", meta_val_style),
             Paragraph("Media Type", meta_label_style), Paragraph(exam.detected_media_type, meta_val_style)],
            [Paragraph("Image Resolution", meta_label_style), Paragraph(f"{exam.image_width} x {exam.image_height} px ({exam.color_mode})", meta_val_style),
             Paragraph("Pipeline Version", meta_label_style), Paragraph(f"v{exam.analysis_pipeline_version} (App: v{exam.application_version})", meta_val_style)],
            [Paragraph("SHA-256 Digest", meta_label_style), Paragraph(f"<b>{exam.sha256_digest}</b>", meta_val_style),
             Paragraph("Workflow Status", meta_label_style), Paragraph(f"<b>{exam.overall_assessment.replace('_', ' ').upper()}</b>", meta_val_style)],
            [Paragraph("Technical Assessment", meta_label_style), Paragraph(f"<b>{exam.decision_assessment or 'INCONCLUSIVE'}</b>", meta_val_style),
             Paragraph("Evidence Strength", meta_label_style), Paragraph(f"<b>{exam.evidence_strength or 'NONE'}</b>", meta_val_style)],
            [Paragraph("Decision Confidence", meta_label_style), Paragraph("<b>Not calibrated</b>" if exam.decision_confidence is None else f"<b>{exam.decision_confidence}%</b>", meta_val_style),
             Paragraph("Human Review", meta_label_style), Paragraph("<b>REQUIRED</b>", meta_val_style)],
        ]
        evidence_table = Table(evidence_data, colWidths=[100, 160, 100, 144])
        evidence_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FFFFFF")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F1F5F9")),
                ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#F1F5F9")),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ])
        )
        story.append(evidence_table)
        story.append(Spacer(1, 10))

        # Extracted Format & Structural Metadata Table if present
        meta_dict = exam.extracted_metadata or {}
        if meta_dict:
            story.append(Paragraph("2. EXTRACTED IMAGE & STRUCTURAL METADATA", heading_style))
            meta_rows = []
            keys = list(meta_dict.keys())[:12]  # Cap at top 12 relevant headers
            for i in range(0, len(keys), 2):
                k1 = keys[i]
                v1 = str(meta_dict[k1])
                k2 = keys[i + 1] if i + 1 < len(keys) else ""
                v2 = str(meta_dict[k2]) if k2 else ""
                meta_rows.append([
                    Paragraph(k1, meta_label_style), Paragraph(v1, meta_val_style),
                    Paragraph(k2, meta_label_style), Paragraph(v2, meta_val_style)
                ])

            meta_table = Table(meta_rows, colWidths=[110, 150, 110, 134])
            meta_table.setStyle(TableStyle([
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F8FAFC")),
                ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#F8FAFC")),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ]))
            story.append(meta_table)
            story.append(Spacer(1, 10))

        # Screening Tests Section
        story.append(Paragraph("3. AUTOMATED SCREENING TEST RESULTS & INDICATORS", heading_style))

        test_records = exam.test_results or []
        for idx, t in enumerate(test_records, 1):
            indicator_val = t.get("indicator", "inconclusive")
            badge_color = "#10B981" if indicator_val == "no_indicator_detected" else ("#EF4444" if indicator_val == "indicator_detected" else "#F59E0B")

            header_text = f"<b>Test {idx}: {t.get('method', '').replace('_', ' ').title()}</b> (v{t.get('version', '1.0.0')})"
            status_text = f"<font color='{badge_color}'><b>{t.get('indicator_label', indicator_val).upper()}</b></font>"

            obs_list = "<br/>• ".join(t.get("observations", []))
            if obs_list:
                obs_list = "• " + obs_list
            else:
                obs_list = "No specific observations recorded."

            card_data = [
                [Paragraph(header_text, meta_label_style), Paragraph(status_text, meta_val_style)],
                [Paragraph("<b>Technical Findings & Explanation:</b>", meta_label_style), Paragraph(t.get("explanation", ""), body_style)],
                [Paragraph("<b>Observations:</b>", meta_label_style), Paragraph(obs_list, body_style)],
            ]

            card_table = Table(card_data, colWidths=[120, 384])
            card_table.setStyle(
                TableStyle([
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F8FAFC")),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ])
            )
            story.append(card_table)
            story.append(Spacer(1, 6))

        story.append(Spacer(1, 8))

        # Section 4: Derived Visual Laboratory Exhibits
        artifacts = exam.artifacts or {}
        exhibits_to_render = []

        if "composite_evidence_map" in artifacts:
            exhibits_to_render.append(("Exhibit A: Composite Forensic Evidence Heatmap (Multi-Detector Spatial Convergence)", artifacts["composite_evidence_map"]))
        if "ela_heatmap" in artifacts:
            exhibits_to_render.append(("Exhibit B: Error Level Analysis (ELA) Heatmap (JPEG Q=90 Recompression Residual)", artifacts["ela_heatmap"]))
        if "noise_residual_map" in artifacts:
            exhibits_to_render.append(("Exhibit B2: Multi-Scale Noise Inconsistency & Residual Heatmap (Local Variance Map)", artifacts["noise_residual_map"]))
        if "fft_spectrum" in artifacts:
            exhibits_to_render.append(("Exhibit C: 2D Fourier Frequency Spectrum (Spatial Frequency & Harmonic Energy)", artifacts["fft_spectrum"]))
        if "copymove_map" in artifacts:
            exhibits_to_render.append(("Exhibit D: Copy-Move Forgery Detection (ORB Keypoint Spatial Matching Vectors)", artifacts["copymove_map"]))
        if "ai_synthetic_map" in artifacts:
            exhibits_to_render.append(("Exhibit E: AI Generative Classifier Heatmap (Spectral Decay & Diffusion Traces)", artifacts["ai_synthetic_map"]))
        if "typography_map" in artifacts:
            exhibits_to_render.append(("Exhibit F: Document Typography & Alignment Map (Glyph Baseline & Edge Inconsistencies)", artifacts["typography_map"]))

        if exhibits_to_render:
            story.append(Paragraph("4. DERIVED FORENSIC VISUAL EXHIBITS", heading_style))
            for title, fname in exhibits_to_render:
                art_file = settings.ARTIFACTS_DIR / fname
                if art_file.exists():
                    story.append(Paragraph(f"<b>{title}</b>", meta_label_style))
                    story.append(Spacer(1, 3))
                    try:
                        rl_img = RLImage(str(art_file), width=4.0 * inch, height=2.4 * inch)
                        img_table = Table([[rl_img]], colWidths=[504])
                        img_table.setStyle(TableStyle([
                            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#0F172A")),
                            ("TOPPADDING", (0, 0), (-1, -1), 4),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                        ]))
                        story.append(img_table)
                        story.append(Spacer(1, 8))
                    except Exception:
                        pass

        # Section 5: Human Forensic Review Section
        story.append(Paragraph("5. QUALIFIED HUMAN FORENSIC REVIEW & ATTESTATION", heading_style))
        review_stat = exam.human_review_status.replace("_", " ").title()
        rev_date = exam.review_timestamp.strftime("%Y-%m-%d %H:%M:%S UTC") if exam.review_timestamp else "Pending"

        review_data = [
            [Paragraph("Review Status", meta_label_style), Paragraph(f"<b>{review_stat}</b>", meta_val_style),
             Paragraph("Review Timestamp", meta_label_style), Paragraph(rev_date, meta_val_style)],
            [Paragraph("Examiner Name", meta_label_style), Paragraph(exam.reviewer_name or "Not yet assigned", meta_val_style),
             Paragraph("Designation", meta_label_style), Paragraph(exam.reviewer_designation or "Forensic Examiner", meta_val_style)],
            [Paragraph("Organization", meta_label_style), Paragraph(exam.reviewer_organization or settings.ORGANIZATION, meta_val_style),
             Paragraph("Attestation", meta_label_style), Paragraph("Confirmed by Examiner" if exam.review_attestation else "Pending Examiner Attestation", meta_val_style)],
            [Paragraph("Examiner Case Notes", meta_label_style), Paragraph(exam.review_notes or "No qualitative notes recorded yet.", body_style),
             Paragraph("", meta_label_style), Paragraph("", meta_val_style)],
        ]

        review_table = Table(review_data, colWidths=[100, 160, 100, 144])
        review_table.setStyle(
            TableStyle([
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F8FAFC")),
                ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#F8FAFC")),
                ("SPAN", (1, 3), (3, 3)),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ])
        )
        story.append(review_table)
        story.append(Spacer(1, 10))

        # Section 6: Limitations & Suggested Checks
        story.append(Paragraph("6. SCIENTIFIC LIMITATIONS & SUGGESTED MANUAL CHECKS", heading_style))

        lim_items = "<br/>• ".join(exam.known_limitations or [])
        lim_p = Paragraph(f"<b>Methodological Limitations:</b><br/>• {lim_items}", body_style)

        checks_items = "<br/>• ".join(exam.suggested_manual_checks or [])
        checks_p = Paragraph(f"<b>Recommended Manual Examiner Checks:</b><br/>• {checks_items}", body_style)

        rec_table = Table([[lim_p], [checks_p]], colWidths=[504])
        rec_table.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FFFFFF")),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(rec_table)

        # Build PDF with NumberedCanvas
        doc.build(story, canvasmaker=NumberedCanvas)
        return output_path
