# dynamic_form
from django.db import models
import uuid
from datetime import datetime
from django.conf import settings
from .utils.pdf_generator import generate_submission_pdf



YES_NO_CHOICES = [
    ('yes','Yes'),
    ('no','No'),
]



GENDER_CHOICES = [
    ('M','Male'),
    ('F','Female'),
    ('O','Other'),
]

APPLICANT_TYPE_CHOICES = [
    ('individual','Individual'),
    ('organization','Organization'),
    # add more as needed
]


class FormTemplate(models.Model):
    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title      = models.CharField(max_length=255)
    is_active  = models.BooleanField(default=False)
    start_date = models.DateTimeField(null=True, blank=True)
    end_date   = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

def service_folder_path(subfolder):
    def _upload_to(instance, filename):
        service_name = instance.service.name if instance.service and instance.service.name else "unknown"
        service_name = service_name.replace(" ", "_").lower()
        return f"{subfolder}/{service_name}/{filename}"
    return _upload_to



class FormSubmission(models.Model):
    # statuses move you through admin/technical rounds, etc.
    DRAFT      = 'draft'
    SUBMITTED  = 'submitted'
    EVALUATED  = 'evaluated'
    TECHNICAL  = 'technical'
    APPROVED   = 'approved'
    REJECTED   = 'rejected'

    STATUS_CHOICES = [
        (DRAFT,      'Draft'),
        (SUBMITTED,  'Submitted'),
        (EVALUATED,  'Admin‐Screened'),
        (TECHNICAL,  'Technical Evaluated'),
        (APPROVED,   'Approved'),
        (REJECTED,   'Rejected'),
    ]

    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    template     = models.ForeignKey(
        'dynamic_form.FormTemplate',
        on_delete=models.PROTECT,
        related_name='submissions'
    )
    service      = models.ForeignKey(
        'configuration.Service',
        on_delete=models.PROTECT,
        related_name='form_submissions',
    null=True, blank=True
    )
    applicant    = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='form_submissions'
    )
    status       = models.CharField(max_length=20, choices=STATUS_CHOICES, default=DRAFT)
    form_id      = models.CharField(max_length=50, unique=True, editable=False)
    proposal_id  = models.CharField(max_length=50, unique=True, null=True, blank=True, editable=False)
    contact_name = models.CharField(max_length=200, blank=True)
    contact_email= models.EmailField(blank=True)
    applicationDocument = models.FileField(upload_to='pdfs/', blank=True, null=True)
    is_active    = models.BooleanField(default=True)
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)
    committee_assigned = models.BooleanField(default=False)

    # ——— 1. Basic Information ——————————————————
    individual_pan    = models.CharField(max_length=20,blank=True, null=True)
    pan_file          = models.FileField(upload_to='pan/',blank=True, null=True)
    applicant_type    = models.CharField(max_length=20, choices=APPLICANT_TYPE_CHOICES)
    passport_file     = models.FileField(upload_to='passport/',blank=True, null=True)
    resume_upload     = models.FileField(upload_to='resumes/',blank=True, null=True)
    subject           = models.CharField(max_length=255,blank=True, null=True)
    org_type          = models.CharField(max_length=255,blank=True, null=True)
    description       = models.CharField(max_length=255,blank=True, null=True)

    # ——— 2. Organization Details —————————————————
    org_address_line1               = models.CharField(max_length=255,blank=True, null=True)
    org_address_line2               = models.CharField(max_length=255, blank=True)
    org_street_village              = models.CharField(max_length=255,blank=True, null=True)
    org_city_town                   = models.CharField(max_length=200,blank=True, null=True)
    org_state                       = models.CharField(max_length=100,blank=True, null=True)
    org_pin_code                    = models.CharField(max_length=10,blank=True, null=True)
    org_landline                    = models.CharField(max_length=20, blank=True, null=True)
    org_mobile                      = models.CharField(max_length=15,blank=True, null=True)
    org_official_email              = models.EmailField(blank=True, null=True)
    org_website                     = models.URLField(blank=True)
    org_shares_51pct_indian_citizens= models.CharField(max_length=3, choices=YES_NO_CHOICES)
    org_tan_pan_cin_file            = models.FileField(upload_to='org_docs/',blank=True, null=True)
    org_registration_certificate    = models.FileField(upload_to='org_docs/',blank=True, null=True)
    org_approval_certificate        = models.FileField(upload_to='org_docs/',blank=True, null=True)
    org_registration_certificate_2  = models.FileField(upload_to='org_docs/', blank=True, null=True)
    org_annual_report               = models.FileField(upload_to='org_docs/', blank=True, null=True)
    org_industry_auth_letter        = models.FileField(upload_to='org_docs/', blank=True, null=True)
    org_shareholding_pattern_file   = models.FileField(upload_to='org_docs/', blank=True, null=True)

    # ——— 3. Proposal Summary ——————————————————
    current_trl            = models.PositiveIntegerField(null=True,blank=True,help_text="Can be filled later")
    # expected_trl           = models.PositiveIntegerField(null=True,blank=True,help_text="Can be filled later")
    abstract               = models.TextField()
    novelty                = models.TextField()
    technical_feasibility  = models.TextField()
    potential_impact       = models.TextField()
    end_to_end_solution    = models.TextField()
    cyber_security         = models.TextField(help_text="Write 'NA' if none")
    commercialization_strategy = models.TextField()
    support_required            = models.TextField()
    alternate_technology_info    = models.TextField()

    # ——— 4. RD Staff & Equipment (variable rows) ——
    rd_staff           = models.JSONField(help_text="List of RD staff entries: …",blank=True, null=True, default=list)
    equipment          = models.JSONField(help_text="List of equipment entries: …",blank=True, null=True, default=list)
    proposal_info      = models.TextField()  # static free-form answers

    # ——— 5. Collaborator Details ————————
    collaborator_name  = models.CharField(max_length=200)
    collaborator_type  = models.CharField(max_length=50)
    collaborator_mou   = models.FileField(upload_to='mou/')
    consortiumPartner =  models.CharField(max_length=200)

    # ——— 6. Finance Details —————————
    finance_outstanding_loan    = models.CharField(max_length=3, choices=YES_NO_CHOICES)
    finance_gov_t_funding       = models.CharField(max_length=3, choices=YES_NO_CHOICES)
    bank_name                   = models.CharField(max_length=200)
    bank_branch                 = models.CharField(max_length=200)
    account_type                = models.CharField(max_length=50)
    bank_account_number         = models.CharField(max_length=30)
    ifsc_code                   = models.CharField(max_length=20)
    expected_source_contribution = models.DecimalField(max_digits=12, decimal_places=2,blank=True, null=True)
    details_source_funding = models.DecimalField(max_digits=12, decimal_places=2,blank=True, null=True)

    
    # ——— 7. Highlight Proposal ——————
    significance_impact      = models.TextField()
    rationale                = models.TextField()
    inventive_step           = models.TextField()
    national_importance      = models.TextField()
    commercialization_potential = models.TextField()
    potential_competitors    = models.TextField()
    risk_factors             = models.TextField()
    preliminary_work_done    = models.TextField()
    technology_status        = models.TextField()
    business_strategy        = models.TextField()

    # ——— 8. IPR Details —————————
    ipr_dot_related                  = models.TextField()
    ipr_based_on_ip                  = models.TextField()
    ipr_ownership_details            = models.TextField()
    ipr_proposal_details             = models.TextField()
    ipr_potential_impact             = models.TextField()
    ipr_patent_file                  = models.FileField(upload_to='ipr/', blank=True, null=True)
    ipr_registered_no                = models.CharField(max_length=50, blank=True)
    ipr_background_details           = models.TextField(blank=True)
    ipr_generate_new_ip              = models.CharField(max_length=3, choices=YES_NO_CHOICES)
    ipr_countries_jurisdiction       = models.TextField(blank=True)
    ipr_licensed_regulatory_approvals= models.TextField(blank=True)
    ipr_status_approvals             = models.TextField(blank=True)
    ipr_status_approval_proof        = models.TextField(blank=True)
    ipr_previous_submission          = models.CharField(max_length=3, choices=YES_NO_CHOICES)
    ipr_regulatory_info              = models.CharField(max_length=3, choices=YES_NO_CHOICES)
    ipr_incubation                   = models.CharField(max_length=3, choices=YES_NO_CHOICES)
    ipr_approval_details             = models.TextField(blank=True)
    ipr_architecture_chart           = models.FileField(upload_to='ipr/', blank=True, null=True)

    # ——— 9. Patents ——————————
    patent_number   = models.CharField(max_length=50, blank=True)
    patent_title    = models.CharField(max_length=200, blank=True)

    # ——— 10. Manpower Details ——————
    manpower_job_title         = models.CharField(max_length=200, blank=True)
    manpower_min_qualification = models.CharField(max_length=200, blank=True)
    manpower_experience_years  = models.PositiveIntegerField(null=True, blank=True)
    manpower_role              = models.CharField(max_length=200, blank=True)
    manpower_positions         = models.PositiveIntegerField(null=True, blank=True)
    manpower_duration_months   = models.PositiveIntegerField(null=True, blank=True)
    manpower_proposed_salary   = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    manpower_total_cost        = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    # ——— 11. Other Requirements ——————
    other_req_items            = models.JSONField(help_text="List of items: …",blank=True, null=True, default=list)

    # ——— 12. Capital Expenditure ——————
    capex_items                = models.JSONField(help_text="List of capex: …",blank=True, null=True, default=list)

    # ——— 13. Finance Budget ——————
    budget_other_source_desc   = models.TextField(blank=True)
    budget_amount_1            = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    budget_other_source_2_desc = models.TextField(blank=True)
    budget_amount_2            = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    # ——— 14. Activities & Timelines ——————
    scope_of_work              = models.TextField(blank=True)
    time_required_months       = models.PositiveIntegerField(null=True, blank=True)
    activities                 = models.TextField(blank=True)
    applicant_contribution     = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    grants_from_ttdf           = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    # ——— 15. Declaration ——————
    declaration_document       = models.FileField(upload_to='declarations/',blank=True, null=True)
    declaration_1              = models.BooleanField(default=False)
    declaration_2              = models.BooleanField(default=False)
    declaration_3              = models.BooleanField(default=False)
    declaration_4              = models.BooleanField(default=False)
    declaration_5              = models.BooleanField(default=False)

    def generate_form_id(self):
        year = datetime.now().year
        count = FormSubmission.objects.filter(created_at__year=year).count() + 1
        return f"FORM/{year}/{count:05d}"

    def generate_proposal_id(self):
        year = datetime.now().year
        service_name = self.service.name.upper() if self.service and self.service.name else "GENERAL"
        service_name = "".join(c for c in service_name if c.isalnum())
        count = FormSubmission.objects.filter(
            status=self.SUBMITTED,
            created_at__year=year,
            service=self.service
        ).count() + 1
        return f"TTDF/{service_name}/{year}/{count:05d}"

    def save(self, *args, **kwargs):
        is_new_submission = not self.pk  # True if this is a new object
        was_draft = False

        if self.status == self.SUBMITTED:
            self.committee_assigned = True

        if not is_new_submission:
            try:
                existing = FormSubmission.objects.get(pk=self.pk)
                was_draft = (existing.status == self.DRAFT)
            except FormSubmission.DoesNotExist:
                pass

        if not self.form_id:
            self.form_id = self.generate_form_id()

    # On first submission, generate a proposal_id if it's not already set
        if self.status == self.SUBMITTED and not self.proposal_id:
            self.proposal_id = self.generate_proposal_id()

    # Save the object to the database
        super().save(*args, **kwargs)

    # Generate PDF when the status changes to SUBMITTED from DRAFT or it's a new submission
        if self.status == self.SUBMITTED and (is_new_submission or was_draft):
            pdf_file = generate_submission_pdf(self)
            filename = f"{self.proposal_id or self.form_id}.pdf"
            self.applicationDocument.save(filename, pdf_file, save=True)

    def can_edit(self):
        now = datetime.now()
        if self.status == self.DRAFT:
            return True
        if self.status == self.SUBMITTED and self.updated_at < self.template.end_date:
            return True
        return False

    def __str__(self):
        return f"{self.form_id} ({self.get_status_display()})"





class FormPage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    form_template = models.ForeignKey(FormTemplate, related_name='pages', on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    order = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['order']
        
    def __str__(self):
        return f"{self.form_template.title} - {self.title}"

class FormField(models.Model):
    FIELD_TYPES = (
        ('text', 'Text'),
        ('number', 'Number'),
        ('email', 'Email'),
        ('phone', 'Phone'),
        ('dropdown', 'Dropdown'),
        ('checkbox', 'Checkbox'),
        ('radio', 'Radio'),
        ('file', 'File Upload'),
        ('image', 'Image Upload'),
        ('date', 'Date'),
        ('time', 'Time'),
        ('textarea', 'Text Area'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    page = models.ForeignKey(FormPage, related_name='fields', on_delete=models.CASCADE)
    label = models.CharField(max_length=255)
    field_type = models.CharField(max_length=20, choices=FIELD_TYPES)
    required = models.BooleanField(default=False)
    placeholder = models.CharField(max_length=255, blank=True, null=True)
    help_text = models.CharField(max_length=255, blank=True, null=True)
    order = models.PositiveIntegerField()
    options = models.JSONField(blank=True, null=True)  
    validation = models.JSONField(blank=True, null=True)  
    
    class Meta:
        ordering = ['order']
        
    def __str__(self):
        return f"{self.page.title} - {self.label}"

class FieldResponse(models.Model):
   
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    submission = models.ForeignKey(FormSubmission, related_name='responses', on_delete=models.CASCADE)
    field = models.ForeignKey(FormField, on_delete=models.CASCADE)
    value = models.JSONField()  
    
    def __str__(self):
        return f"Response for {self.field.label}"

STATUS_CHOICES = (
    ('draft', 'Draft'),
    ('submitted', 'Submitted'),
    ('pending_review', 'Pending Review'),
    ('approved', 'Approved'),
    ('rejected', 'Rejected'),
)




class ApplicationStatusHistory(models.Model):
    """
    Tracks every status change for a form submission (dynamic application).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Link to the dynamic application submission by its unique proposal_id.
    # Since FormSubmission already has a unique proposal_id, we use a ForeignKey with to_field.
    submission = models.ForeignKey(FormSubmission, to_field='proposal_id', on_delete=models.CASCADE, related_name='status_history')
    previous_status = models.CharField(max_length=50, choices=STATUS_CHOICES)
    new_status = models.CharField(max_length=50, choices=STATUS_CHOICES)
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True )
    change_date = models.DateTimeField(auto_now_add=True)
    comment = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return (f"{self.submission.proposal_id}: "
                f"{self.previous_status} → {self.new_status} "
                f"on {self.change_date.strftime('%Y-%m-%d %H:%M:%S')}")

    class Meta:
        ordering = ['-change_date']

    
