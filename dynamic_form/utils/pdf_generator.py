from reportlab.pdfgen import canvas
from django.core.files.base import ContentFile
import io

def generate_submission_pdf(submission):
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer)

    p.setFont("Helvetica", 12)
    p.drawString(100, 800, f"Form ID: {submission.form_id}")
    p.drawString(100, 780, f"Applicant: {submission.applicant.full_name}")
    p.drawString(100, 760, f"Contact Email: {submission.contact_email}")
    p.drawString(100, 740, f"Subject: {submission.subject}")
    p.drawString(100, 720, f"Description: {submission.description}")
    # ... add more fields as needed

    p.showPage()
    p.save()

    pdf_file = ContentFile(buffer.getvalue())
    buffer.close()
    return pdf_file
