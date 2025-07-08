# dynamic_form
from django.db import models
import uuid
from datetime import datetime
from django.conf import settings
from .utils.pdf_generator import generate_submission_pdf
from functools import partial

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

Village_CHOICES = [
    ('delhi 1','Delhi 1 '),
    ('delhi 2','Delhi 2'),
    ('delhi 3','Delhi3'),
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



def upload_to_dynamic(instance, filename, subfolder=None):
    # Handles both direct file fields and related models if needed
    service = getattr(instance, 'service', None)
    if not service and hasattr(instance, 'form_submission'):
        service = getattr(instance.form_submission, 'service', None)
    service_name = getattr(service, 'name', 'unknown') if service else "unknown"
    service_name = service_name.replace(" ", "_").lower()
    folder = subfolder or "docs"
    return f"{folder}/{service_name}/{filename}"



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
    applicationDocument = models.FileField(upload_to=partial(upload_to_dynamic, subfolder="pdf"), blank=True, null=True)
    is_active    = models.BooleanField(default=True)
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)
    committee_assigned = models.BooleanField(default=False)
    current_trl            = models.PositiveIntegerField(null=True,blank=True,help_text="Can be filled later")
    grants_from_ttdf           = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    # ——— 1. Basic Information ——————————————————
    individual_pan    = models.CharField(max_length=20,blank=True, null=True)
    pan_file          = models.FileField(upload_to=partial(upload_to_dynamic, subfolder="pan"),blank=True, null=True)
    applicant_type    = models.CharField(max_length=20, choices=APPLICANT_TYPE_CHOICES,blank=True, null=True)
    passport_file     = models.FileField(upload_to=partial(upload_to_dynamic, subfolder="passport"),blank=True, null=True)
    resume_upload     = models.FileField(upload_to=partial(upload_to_dynamic, subfolder="resume"),blank=True, null=True)
    subject           = models.CharField(max_length=255,blank=True, null=True)
    org_type          = models.CharField(max_length=255,blank=True, null=True)
    description       = models.CharField(max_length=255,blank=True, null=True)
    org_mobile                      = models.CharField(max_length=15,blank=True, null=True)

    # ———2. Collaborator Details ————————
    collaborator_name  = models.CharField(max_length=200,blank=True, null=True)
    collaborator_type  = models.CharField(max_length=50,blank=True, null=True)
    collaborator_mou   = models.FileField(upload_to=partial(upload_to_dynamic, subfolder="mou"),blank=True, null=True)
    consortiumPartner =  models.CharField(max_length=200,blank=True, null=True)
    # --- Other Section ---
    ttdf_applied_before = models.CharField(max_length=3, choices=YES_NO_CHOICES, blank=True, null=True)


    # --- 4 Equipment Section ---
    equipment_item = models.CharField(max_length=255, blank=True, null=True)
    equipment_unit_price = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    equipment_quantity = models.PositiveIntegerField(blank=True, null=True)
    equipment_amount = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    equipment_contributor_type = models.CharField(max_length=255, blank=True, null=True)

    # --- 5.Share Holder Details ---
    share_holder_name = models.CharField(max_length=255, blank=True, null=True)
    share_percentage = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    identity_document = models.FileField(
        upload_to=partial(upload_to_dynamic, subfolder="shareholder_docs"),
        blank=True,
        null=True
    )


    # ——— 6. RD Staff & Equipment (variable rows) ——    
    rd_staff_name = models.CharField(max_length=255, blank=True, null=True)
    rd_staff_designation = models.CharField(max_length=255, blank=True, null=True)
    rd_staff_email = models.EmailField(blank=True, null=True)
    rd_staff_highest_qualification = models.CharField(max_length=255, blank=True, null=True)
    rd_staff_mobile = models.CharField(max_length=20, blank=True, null=True)
    rd_staff_resume = models.FileField(
        upload_to=partial(upload_to_dynamic, subfolder="rd_staff_resumes"),
        blank=True,
        null=True
    )
    rd_staff_epf_details = models.CharField(max_length=255, blank=True, null=True)


    # ---7. Fund loan Details Section ---
    has_loan = models.CharField(
        max_length=3, choices=YES_NO_CHOICES, blank=True, null=True
    )
    fund_loan_description = models.TextField(blank=True, null=True)
    fund_loan_amount = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    fund_loan_documents = models.JSONField(blank=True, null=True, default=list, help_text="List of uploaded file paths")


    # ---8. Contribution Details Section ---

    contribution_expected_source = models.CharField(max_length=255, blank=True, null=True)
    contribution_item = models.CharField(max_length=255, blank=True, null=True)
    contribution_amount = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)

    # ---8. Fund Details Section ---
    fund_source_details = models.CharField(max_length=255, blank=True, null=True)
    fund_item = models.CharField(max_length=255, blank=True, null=True)
    fund_amount = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)

    # ---9. Summary Section ---
    grant_from_ttdf = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    contribution_applicant = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    expected_other_contribution = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    other_source_funding = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    total_project_cost = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)


    # ---10 Key Information Section ---
    proposal_brief = models.TextField(blank=True, null=True)
    contribution_percentage = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    grant_to_turnover_ratio = models.DecimalField(max_digits=10, decimal_places=4, blank=True, null=True)

    # ---11 Proposal Summary Section ---
    proposed_village = models.CharField(max_length=255,choices=Village_CHOICES ,blank=True, null=True)
    use_case = models.CharField(max_length=255, blank=True, null=True)
    proposal_abstract = models.TextField(blank=True, null=True)
    potential_impact = models.TextField(blank=True, null=True)
    end_to_end_solution = models.TextField(blank=True, null=True)
    team = models.TextField(blank=True, null=True)
    data_security_measures = models.TextField(blank=True, null=True)
    required_support_details = models.TextField(blank=True, null=True)
    model_village = models.CharField(max_length=255, blank=True, null=True)


    # ---12 Essence of Proposal Section ---
    national_importance = models.TextField(blank=True, null=True)
    commercialization_potential = models.TextField(blank=True, null=True)
    risk_factors = models.TextField(blank=True, null=True)
    preliminary_work_done = models.TextField(blank=True, null=True)
    technology_status = models.TextField(blank=True, null=True)
    business_strategy = models.TextField(blank=True, null=True)

    # ---13 IP Regulatory Details Section ---
    based_on_ipr = models.TextField(blank=True, null=True)
    ip_ownership_details = models.TextField(blank=True, null=True)
    ip_proposal = models.TextField(blank=True, null=True)
    regulatory_approvals = models.TextField(blank=True, null=True)
    status_approvals = models.TextField(blank=True, null=True)
    proof_of_status = models.TextField(blank=True, null=True)

    # ---14 Telecom Service Provider Section ---
    tsp_name = models.CharField(max_length=255, blank=True, null=True)
    tsp_designation = models.CharField(max_length=255, blank=True, null=True)
    tsp_mobile_number = models.CharField(max_length=20, blank=True, null=True)
    tsp_email = models.EmailField(blank=True, null=True)
    tsp_address = models.TextField(blank=True, null=True)
    tsp_support_letter = models.FileField(
        upload_to=partial(upload_to_dynamic, subfolder="tsp_support_letters"),
        blank=True,
        null=True
    )


    # --- Architecture And Project Chart Section ---
    gantt_chart = models.FileField(
        upload_to=partial(upload_to_dynamic, subfolder="gantt_charts"),
        blank=True,
        null=True
    )
    technical_proposal = models.FileField(
        upload_to=partial(upload_to_dynamic, subfolder="technical_proposals"),
        blank=True,
        null=True
    )
    proposal_presentation = models.FileField(
        upload_to=partial(upload_to_dynamic, subfolder="proposal_presentations"),
        blank=True,
        null=True
    )

    # --- Manpower Details Section ---
    manpower_details = models.JSONField(
        blank=True,
        null=True,
        default=list,
        help_text=(
            "List of manpower entries. "
            "Each entry: {jobTitle, minimumQualification, ageLimit, roleInProject, numberOfPositions, durationMonths, proposedMonthlySalary, totalCost, totalProposalMonthlySalary}"
        )
    )

    # --- Other Requirements Section ---
    other_requirements = models.JSONField(
        blank=True,
        null=True,
        default=list,
        help_text=(
            "List of other requirement entries. "
            "Each entry: {item, quantity, unitPrice, totalPrice, specifications, certification, remarks}"
        )
    )


    # --- Budget Estimate Section ---
    budget_estimate = models.JSONField(
        blank=True,
        null=True,
        default=dict,
        help_text="Nested budget: {'tables':[{'id':'','title':'','serviceOfferings':[{'id':'','name':'','items':[{'id':'','description':'','financials':{'capex':{'year0':{...}},'opex':{'year1':{...}}}}]}]}]}"
    )
    

    # --- Income Estimate Section ---
    income_estimate = models.JSONField(
        blank=True,
        null=True,
        default=dict,
        help_text=(
            "Nested income estimate: "
            "{'rows':[{'id':'','serviceOffering':'','year1':{'estimatedTransactions':'','userCharge':'','estimatedRevenue':''},'year2':{'estimatedTransactions':'','userCharge':'','estimatedRevenue':''}}]}"
        )
    )



    # --- Proposal Cost Breakdown Section ---

    network_core = models.JSONField(blank=True,null=True,default=dict,
        help_text=(
            '{"items": [{"item": "", "unit": "", "unitPrice": 0, "totalPrice": 0}], "sectionTotal": 0}'
        )
    )

    radio_access_network = models.JSONField(blank=True,null=True,default=dict,help_text=(
            '{"items": [{"item": "", "unit": "", "unitPrice": 0, "totalPrice": 0}], "sectionTotal": 0}'
        )
    )

    fixed_wireless_access = models.JSONField(blank=True,null=True,default=dict,
        help_text=(
            '{"items": [{"item": "", "unit": "", "unitPrice": 0, "totalPrice": 0}], "sectionTotal": 0}'
        )
    )

    civil_electrical_infrastructure = models.JSONField(blank=True,null=True,default=dict,
        help_text=(
            '{"items": [{"item": "", "unit": "", "unitPrice": 0, "totalPrice": 0}], "sectionTotal": 0}'
        )
    )

    centralised_servers_and_edge_analytics = models.JSONField(blank=True,null=True,default=dict,
        help_text=(
            '{"items": [{"item": "", "unit": "", "unitPrice": 0, "totalPrice": 0}], "sectionTotal": 0}'
        )
    )

    passive_components = models.JSONField(
        blank=True,
        null=True,
        default=dict,
        help_text=(
            '{"items": [{"item": "", "unit": "", "unitPrice": 0, "totalPrice": 0}], "sectionTotal": 0}'
        )
    )

    software_components = models.JSONField(
        blank=True,
        null=True,
        default=dict,
        help_text=(
            '{"items": [{"item": "", "unit": "", "unitPrice": 0, "totalPrice": 0}], "sectionTotal": 0}'
        )
    )

    sensor_network_costs = models.JSONField(
        blank=True,
        null=True,
        default=dict,
        help_text=(
            '{'
            '"smartPanchayat": {"items": [{"item": "", "unit": "", "unitPrice": 0, "totalPrice": 0}], "sectionTotal": 0}, '
            '"smartAgriculture": {"items": [{"item": "", "unit": "", "unitPrice": 0, "totalPrice": 0}], "sectionTotal": 0}, '
            '"smartEducation": {"items": [{"item": "", "unit": "", "unitPrice": 0, "totalPrice": 0}], "sectionTotal": 0}, '
            '"smartHealth": {"items": [{"item": "", "unit": "", "unitPrice": 0, "totalPrice": 0}], "sectionTotal": 0} '
            '}'
        )
    )

    installation_infrastructure_and_commissioning = models.JSONField(
        blank=True,
        null=True,
        default=dict,
        help_text=(
            '{"items": [{"item": "", "unit": "", "unitPrice": 0, "totalPrice": 0}], "sectionTotal": 0}'
        )
    )

    operation_maintenance_and_warranty = models.JSONField(
        blank=True,
        null=True,
        default=dict,
        help_text=(
            '{"items": [{"item": "", "unit": "", "unitPrice": 0, "totalPrice": 0}], "sectionTotal": 0}'
        )
    )

    total_proposal_cost = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        blank=True,
        null=True
    )


  
   

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

    
# class FundLoanDocument(models.Model):
#     form_submission = models.ForeignKey(
#         "dynamic_form.FormSubmission",
#         on_delete=models.CASCADE,
#         related_name="fund_loan_documents"
#     )
#     document = models.FileField(
#         upload_to=service_folder_path("fund_loan_docs"),
#         blank=True,
#         null=True
#     )

#     def __str__(self):
#         return self.document.name if self.document else "No file"
