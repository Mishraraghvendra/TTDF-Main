from django.db import models
from django.contrib.auth import get_user_model
from datetime import datetime
import uuid
from configuration.models import Service  # Adjust this import to your actual app

User = get_user_model()

def generate_form_id():
    return f"FORM-{uuid.uuid4().hex[:8].upper()}"

def generate_proposal_id(service_code, count):
    year = datetime.now().year
    return f"TTDF-{service_code.upper()}-{year}-{count:05d}"

class StaticForm(models.Model):
    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
    )

    form_id = models.CharField(max_length=20, unique=True, default=generate_form_id)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='static_forms')
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='static_forms')

    name = models.CharField(max_length=255)
    email = models.EmailField()
    mobile = models.CharField(max_length=15)

    profile_image = models.ImageField(upload_to='static_forms/profile_images/', blank=True, null=True)
    highest_qualification = models.CharField(max_length=255, blank=True, null=True)
    applicant_type = models.CharField(max_length=100)  # Dropdown options in frontend
    registration_info = models.CharField(max_length=255)  # Dropdown options in frontend

    registration_certificate = models.FileField(upload_to='static_forms/docs/', blank=True, null=True)
    annual_report = models.FileField(upload_to='static_forms/docs/', blank=True, null=True)
    approval_certificate = models.FileField(upload_to='static_forms/docs/', blank=True, null=True)
    industry_authorisation_letter = models.FileField(upload_to='static_forms/docs/', blank=True, null=True)
    share_holding_pattern_certificate = models.FileField(upload_to='static_forms/docs/', blank=True, null=True)

    address = models.TextField(blank=True, null=True)
    qualification = models.CharField(max_length=255, blank=True, null=True)
    document = models.FileField(upload_to='static_forms/docs/', blank=True, null=True)

    justification = models.TextField(blank=True, null=True)
    other_sources_contribution = models.TextField(blank=True, null=True)
    other_sources_amount = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    funding_received_details = models.TextField(blank=True, null=True)
    funding_received_amount = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)

    approx_cost = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    applicant_contribution = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)

    declaration_document = models.FileField(upload_to='static_forms/declarations/', blank=True, null=True)

    proposal_id = models.CharField(max_length=50, unique=True, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')

    pdf_file = models.FileField(upload_to='static_forms/pdfs/', blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def generate_and_save_proposal_id(self):
        count = StaticForm.objects.filter(service=self.service, proposal_id__isnull=False).count() + 1
        service_code = self.service.code if hasattr(self.service, 'code') else self.service.name[:4].upper()
        self.proposal_id = generate_proposal_id(service_code, count)
        self.status = 'submitted'
        self.save()

        from .utils import render_to_pdf
        from django.core.files.base import ContentFile

        pdf_bytes = render_to_pdf('static_form/form_pdf.html', {'form': self})
        if pdf_bytes:
            self.pdf_file.save(f"{self.form_id}_application.pdf", ContentFile(pdf_bytes))


class Shareholder(models.Model):
    static_form = models.ForeignKey(StaticForm, on_delete=models.CASCADE, related_name='shareholders')
    name = models.CharField(max_length=255)
    percentage = models.DecimalField(max_digits=5, decimal_places=2)
    document_id = models.CharField(max_length=50)  # Aadhaar/Passport No.


class Item(models.Model):
    static_form = models.ForeignKey(StaticForm, on_delete=models.CASCADE, related_name='items')
    name = models.CharField(max_length=255)
    quantity = models.PositiveIntegerField()
    cost_per_item = models.DecimalField(max_digits=12, decimal_places=2)

    @property
    def total_amount(self):
        return self.quantity * self.cost_per_item

