# dynamic_form
from django.db import models
import uuid
from datetime import datetime
from django.conf import settings
from .utils.pdf_generator import generate_submission_pdf
from functools import partial
from django.utils import timezone

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
    ('ari_umri_mp', 'Ari & Umri (Block Guna, Madhya Pradesh)'),
    ('narakoduru_ap', 'Narakoduru (Block Chebrolu, Andhra Pradesh)'),
    ('chaurawala_up', 'Chaurawala (Block Morna, Uttar Pradesh)'),
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


# def upload_to_dynamic(instance, filename, subfolder=None):
#     # Handles both direct file fields and related models if needed
#     service = getattr(instance, 'service', None)
#     if not service and hasattr(instance, 'form_submission'):
#         service = getattr(instance.form_submission, 'service', None)
#     service_name = getattr(service, 'name', 'unknown') if service else "unknown"
#     service_name = service_name.replace(" ", "_").lower()
#     folder = subfolder or "docs"
#     return f"{folder}/{service_name}/{filename}"

def upload_to_dynamic(instance, filename, subfolder=None):
    # Try to get template from instance or form_submission
    template = getattr(instance, 'template', None)
    if not template and hasattr(instance, 'form_submission'):
        template = getattr(instance.form_submission, 'template', None)
    template_name = getattr(template, 'title', 'unknown') if template else "unknown"
    template_name = template_name.replace(" ", "_").lower()
    folder = subfolder or "docs"
    # Get proposal_id
    proposal_id = getattr(instance, 'proposal_id', None)
    if not proposal_id and hasattr(instance, 'form_submission'):
        proposal_id = getattr(instance.form_submission, 'proposal_id', None)
    if not proposal_id:
        proposal_id = "draft"
    return f"templates/{template_name}/{proposal_id}/{folder}/{filename}"



import os
from django.core.files.base import File

# def move_file_to_proposal_folder(file_field, instance, old_path, new_path):
#     """
#     Move a file from old_path to new_path using Django's storage system,
#     then update the file_field on the instance.
#     """
#     if not file_field or not old_path or not new_path or old_path == new_path:
#         return False
#     storage = file_field.storage
#     if not storage.exists(old_path):
#         return False
#     # Read file content
#     with storage.open(old_path, 'rb') as f:
#         content = File(f)
#         storage.save(new_path, content)
#     storage.delete(old_path)
#     file_field.name = new_path  # update field value (unsaved)
#     return True


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
    completed_sections = models.JSONField(
        blank=True,
        null=True,
        default=list,
        help_text="List of completed section indices"
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


     # ---9. Summary Section ---
    funds_requested= models.PositiveIntegerField(null=True,blank=True) 
    grant_from_ttdf = models.DecimalField(max_digits=15, decimal_places=5, blank=True, null=True)
    contribution_applicant = models.DecimalField(max_digits=15, decimal_places=5, blank=True, null=True)
    expected_other_contribution = models.DecimalField(max_digits=15, decimal_places=5, blank=True, null=True)
    other_source_funding = models.DecimalField(max_digits=15, decimal_places=5, blank=True, null=True)
    total_project_cost = models.DecimalField(max_digits=15, decimal_places=5, blank=True, null=True)
    actual_contribution_applicant = models.DecimalField(max_digits=15, decimal_places=5, blank=True, null=True)

    

    # ——— 1. Basic Information ——————————————————
    individual_pan    = models.CharField(max_length=20,blank=True, null=True)
    pan_file          = models.FileField(upload_to=partial(upload_to_dynamic, subfolder="pan"),blank=True, null=True)
    applicant_type    = models.CharField(max_length=20, choices=APPLICANT_TYPE_CHOICES,blank=True, null=True)
    passport_file     = models.FileField(upload_to=partial(upload_to_dynamic, subfolder="passport"),blank=True, null=True)
    resume_upload     = models.FileField(upload_to=partial(upload_to_dynamic, subfolder="resume"),blank=True, null=True)
    subject           = models.CharField(max_length=1000,blank=True, null=True)
    org_type          = models.CharField(max_length=255,blank=True, null=True)
    description       = models.CharField(max_length=1000,blank=True, null=True)
    

    # # ———2. Collaborator Details ————————
    # collaborator_name  = models.CharField(max_length=200,blank=True, null=True)
    # collaborator_type  = models.CharField(max_length=50,blank=True, null=True)
    # collaborator_mou   = models.FileField(upload_to=partial(upload_to_dynamic, subfolder="mou"),blank=True, null=True)
    # consortiumPartner =  models.CharField(max_length=200,blank=True, null=True)
    # --- Other Section ---
    ttdf_applied_before = models.CharField(max_length=3, choices=YES_NO_CHOICES, blank=True, null=True)



    # ---7. Fund loan Details Section ---
    has_loan = models.CharField(
        max_length=3, choices=YES_NO_CHOICES, blank=True, null=True
    )
    fund_loan_description = models.TextField(blank=True, null=True)
    fund_loan_amount = models.DecimalField(max_digits=15, decimal_places=5, blank=True, null=True)
    # fund_loan_documents = models.JSONField(blank=True, null=True, default=list, help_text="List of uploaded file paths")


    # ---8. Contribution Details Section ---

    contribution_expected_source = models.CharField(max_length=255, blank=True, null=True)
    contribution_item = models.CharField(max_length=255, blank=True, null=True)
    contribution_amount = models.DecimalField(max_digits=15, decimal_places=5, blank=True, null=True)

    # ---8. Fund Details Section ---
    fund_source_details = models.CharField(max_length=255, blank=True, null=True)
    fund_item = models.CharField(max_length=255, blank=True, null=True)
    fund_amount = models.DecimalField(max_digits=15, decimal_places=5, blank=True, null=True)
    contribution_rows = models.JSONField(blank=True, null=True, default=list, help_text="Array of contribution entries")
    fund_rows = models.JSONField(blank=True, null=True, default=list, help_text="Array of fund entries")

   

    # ---10 Key Information Section ---
    proposal_brief = models.TextField(blank=True, null=True)
    contribution_percentage = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    grant_to_turnover_ratio = models.DecimalField(max_digits=10, decimal_places=4, blank=True, null=True)

    # ---11 Proposal Summary Section ---
    proposed_village = models.CharField(max_length=255,choices=Village_CHOICES ,blank=True, null=True)
    use_case = models.CharField(max_length=1000, blank=True, null=True)
    proposal_abstract = models.TextField(blank=True, null=True)
    potential_impact = models.TextField(blank=True, null=True)
    end_to_end_solution = models.TextField(blank=True, null=True)
    team = models.TextField(blank=True, null=True)
    data_security_measures = models.TextField(blank=True, null=True)
    required_support_details = models.TextField(blank=True, null=True)
    model_village = models.CharField(max_length=255, blank=True, null=True)


    # # ---12 Essence of Proposal Section ---
    # national_importance = models.TextField(blank=True, null=True)
    # commercialization_potential = models.TextField(blank=True, null=True)
    # risk_factors = models.TextField(blank=True, null=True)
    # preliminary_work_done = models.TextField(blank=True, null=True)
    # technology_status = models.TextField(blank=True, null=True)
    # business_strategy = models.TextField(blank=True, null=True)

    # # ---13 IP Regulatory Details Section ---
    # based_on_ipr = models.TextField(blank=True, null=True)
    # ip_ownership_details = models.TextField(blank=True, null=True)
    # ip_proposal = models.TextField(blank=True, null=True)
    # regulatory_approvals = models.TextField(blank=True, null=True)
    # status_approvals = models.TextField(blank=True, null=True)
    # proof_of_status = models.TextField(blank=True, null=True)

    # # ---14 Telecom Service Provider Section ---
    # tsp_name = models.CharField(max_length=255, blank=True, null=True)
    # tsp_designation = models.CharField(max_length=255, blank=True, null=True)
    # tsp_mobile_number = models.CharField(max_length=20, blank=True, null=True)
    # tsp_email = models.EmailField(blank=True, null=True)
    # tsp_address = models.TextField(blank=True, null=True)
    # tsp_support_letter = models.FileField(
    #     upload_to=partial(upload_to_dynamic, subfolder="tsp_support_letters"),
    #     blank=True,
    #     null=True
    # )


    # --- Architecture And Project Chart Section ---
    gantt_chart = models.FileField(
        upload_to=partial(upload_to_dynamic, subfolder="gantt_charts"),
        blank=True,
        null=True,
        max_length=500
        )

    technical_proposal = models.FileField(
        upload_to=partial(upload_to_dynamic, subfolder="technical_proposals"),
        blank=True,
        null=True,
        max_length=500
    )

    proposal_presentation = models.FileField(
        upload_to=partial(upload_to_dynamic, subfolder="proposal_presentations"),
        blank=True,
        null=True,
        max_length=500
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
    budget_estimate_sample_doc = models.FileField(upload_to=partial(upload_to_dynamic, subfolder="Sample Document"),blank=True, null=True)
    

    equipment_overhead = models.JSONField(
        blank=True,
        null=True,
        default=dict,
        help_text=(
            "Nested equipment overhead: "
            "{'tables':[{'id':'','title':'','serviceOfferings':[{'id':'','name':'','items':[{'id':'','description':'','financials':{'capex':{'year0':{...}},'opex':{'year1':{...},'year2':{...}}}}]}]}]}"
        )
    )

    equipment_overhead_sample_doc = models.FileField(upload_to=partial(upload_to_dynamic, subfolder="Sample Document"),blank=True, null=True)
    

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

    income_estimate_sample_doc = models.FileField(upload_to=partial(upload_to_dynamic, subfolder="Sample Document"),blank=True, null=True)


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

    presentation = models.FileField(
            upload_to=partial(upload_to_dynamic, subfolder="Presentation"),
            blank=True,
            null=True
        )
    
    dpr = models.FileField(
            upload_to=partial(upload_to_dynamic, subfolder="DPR"),
            blank=True,
            null=True
        )


###################################################################################################################################################
  
 # ———For All Old Calls (Befour 5G Inteligent Village)  —————————————————

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
    org_website                     = models.URLField(blank=True, null=True)
    org_shares_51pct_indian_citizens= models.CharField(max_length=3, choices=YES_NO_CHOICES,blank=True, null=True)
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
    abstract               = models.TextField(blank=True, null=True)
    novelty                = models.TextField(blank=True, null=True)
    technical_feasibility  = models.TextField(blank=True, null=True)
    potential_impact       = models.TextField(blank=True, null=True)
    end_to_end_solution    = models.TextField(blank=True, null=True)
    cyber_security         = models.TextField(help_text="Write 'NA' if none",blank=True, null=True)
    commercialization_strategy = models.TextField(blank=True, null=True)
    support_required            = models.TextField(blank=True, null=True)
    alternate_technology_info    = models.TextField(blank=True, null=True)

    # ——— 4. RD Staff & Equipment (variable rows) ——
    rd_staff           = models.JSONField(help_text="List of RD staff entries: …",blank=True, null=True, default=list)
    equipment          = models.JSONField(help_text="List of equipment entries: …",blank=True, null=True, default=list)
    proposal_info      = models.TextField(blank=True, null=True)  # static free-form answers

    # ——— 5. Collaborator Details ————————
    # collaborator_name  = models.CharField(max_length=200,blank=True, null=True)
    # collaborator_type  = models.CharField(max_length=50,blank=True, null=True)
    
    # collaborator_mou   = models.FileField(upload_to='mou/',blank=True, null=True)
    # consortiumPartner =  models.CharField(max_length=200,blank=True, null=True)

    # ——— 6. Finance Details —————————
    finance_outstanding_loan    = models.CharField(max_length=3, choices=YES_NO_CHOICES,blank=True, null=True)
    finance_gov_t_funding       = models.CharField(max_length=3, choices=YES_NO_CHOICES,blank=True, null=True)
    bank_name                   = models.CharField(max_length=200,blank=True, null=True)
    bank_branch                 = models.CharField(max_length=200,blank=True, null=True)
    account_type                = models.CharField(max_length=50,blank=True, null=True)
    bank_account_number         = models.CharField(max_length=30,blank=True, null=True)
    ifsc_code                   = models.CharField(max_length=20,blank=True, null=True)
    expected_source_contribution = models.DecimalField(max_digits=12, decimal_places=5,blank=True, null=True)
    details_source_funding = models.DecimalField(max_digits=12, decimal_places=5,blank=True, null=True)

    
    # ——— 7. Highlight Proposal ——————
    significance_impact      = models.TextField(blank=True, null=True)
    rationale                = models.TextField(blank=True, null=True)
    inventive_step           = models.TextField(blank=True, null=True)
    national_importance      = models.TextField(blank=True, null=True)
    commercialization_potential = models.TextField(blank=True, null=True)
    potential_competitors    = models.TextField(blank=True, null=True)
    risk_factors             = models.TextField(blank=True, null=True)
    preliminary_work_done    = models.TextField(blank=True, null=True)
    technology_status        = models.TextField(blank=True, null=True)
    business_strategy        = models.TextField(blank=True, null=True)

    # ——— 8. IPR Details —————————
    ipr_dot_related                  = models.TextField(blank=True, null=True)
    ipr_based_on_ip                  = models.TextField(blank=True, null=True)
    ipr_ownership_details            = models.TextField(blank=True, null=True)
    ipr_proposal_details             = models.TextField(blank=True, null=True)
    ipr_potential_impact             = models.TextField(blank=True, null=True)
    ipr_patent_file                  = models.FileField(upload_to='ipr/', blank=True, null=True)
    ipr_registered_no                = models.CharField(max_length=50, blank=True)
    ipr_background_details           = models.TextField(blank=True, null=True)
    ipr_generate_new_ip              = models.CharField(max_length=3, choices=YES_NO_CHOICES,blank=True, null=True)
    ipr_countries_jurisdiction       = models.TextField(blank=True, null=True)
    ipr_licensed_regulatory_approvals= models.TextField(blank=True, null=True)
    ipr_status_approvals             = models.TextField(blank=True, null=True)
    ipr_status_approval_proof        = models.TextField(blank=True, null=True)
    ipr_previous_submission          = models.CharField(max_length=3, choices=YES_NO_CHOICES,blank=True, null=True)
    ipr_regulatory_info              = models.CharField(max_length=3, choices=YES_NO_CHOICES,blank=True, null=True)
    ipr_incubation                   = models.CharField(max_length=3, choices=YES_NO_CHOICES,blank=True, null=True)
    ipr_approval_details             = models.TextField(blank=True, null=True)
    ipr_architecture_chart           = models.FileField(upload_to='ipr/', blank=True, null=True)

    # ——— 9. Patents ——————————
    patent_number   = models.CharField(max_length=50, blank=True, null=True)
    patent_title    = models.CharField(max_length=200, blank=True, null=True)

    # ——— 10. Manpower Details ——————
    manpower_job_title         = models.CharField(max_length=200, blank=True, null=True)
    manpower_min_qualification = models.CharField(max_length=200, blank=True, null=True)
    manpower_experience_years  = models.PositiveIntegerField(null=True, blank=True)
    manpower_role              = models.CharField(max_length=200, blank=True, null=True)
    manpower_positions         = models.PositiveIntegerField(null=True, blank=True)
    manpower_duration_months   = models.PositiveIntegerField(null=True, blank=True)
    manpower_proposed_salary   = models.DecimalField(max_digits=12, decimal_places=5, null=True, blank=True)
    manpower_total_cost        = models.DecimalField(max_digits=12, decimal_places=5, null=True, blank=True)

    # ——— 11. Other Requirements ——————
    other_req_items            = models.JSONField(help_text="List of items: …",blank=True, null=True, default=list)

    # ——— 12. Capital Expenditure ——————
    capex_items                = models.JSONField(help_text="List of capex: …",blank=True, null=True, default=list)

    # ——— 13. Finance Budget ——————
    budget_other_source_desc   = models.TextField(blank=True, null=True)
    budget_amount_1            = models.DecimalField(max_digits=12, decimal_places=5, null=True, blank=True)
    budget_other_source_2_desc = models.TextField(blank=True, null=True)
    budget_amount_2            = models.DecimalField(max_digits=12, decimal_places=5, null=True, blank=True)

    # ——— 14. Activities & Timelines ——————
    scope_of_work              = models.TextField(blank=True, null=True)
    time_required_months       = models.PositiveIntegerField(null=True, blank=True)
    activities                 = models.TextField(blank=True, null=True)
    applicant_contribution     = models.DecimalField(max_digits=12, decimal_places=5, null=True, blank=True)
    grants_from_ttdf           = models.DecimalField(max_digits=12, decimal_places=5, null=True, blank=True)

    # ——— 15. Declaration ——————
    declaration_document       = models.FileField(upload_to='declarations/',blank=True, null=True)
    declaration_1              = models.BooleanField(default=False)
    declaration_2              = models.BooleanField(default=False)
    declaration_3              = models.BooleanField(default=False)
    declaration_4              = models.BooleanField(default=False)
    declaration_5              = models.BooleanField(default=False)


####################################################################################################################################################
   

    def generate_form_id(self):
        year = datetime.now().year
        # Use the last 6 digits of the UUID for uniqueness, or use the whole UUID if you prefer
        return f"FORM/{year}/{str(self.pk)[-6:].upper()}"

    # def generate_proposal_id(self):
    #     year = datetime.now().year
    #     service_name = self.service.name.upper() if self.service and self.service.name else "GENERAL"
    #     service_name = "".join(c for c in service_name if c.isalnum())
    #     count = FormSubmission.objects.filter(
    #         status=self.SUBMITTED,
    #         created_at__year=year,
    #         service=self.service
    #     ).count() + 1
    #     return f"TTDF/{service_name}/{year}/{count:05d}"

    def generate_proposal_id(self):
        year = datetime.now().year
        # Use template title instead of service name
        template_name = self.template.title.upper() if self.template and self.template.title else "GENERAL"
        # Remove non-alphanumeric characters for ID safety
        template_name = "".join(c for c in template_name if c.isalnum())
        # Count per template for the year (not per service)
        count = FormSubmission.objects.filter(
            status=self.SUBMITTED,
            created_at__year=year,
            template=self.template
        ).count() + 1
        return f"TTDF/{template_name}/{year}/{count:05d}"



    # def save(self, *args, **kwargs):
    #     is_new_submission = not self.pk  # True if this is a new object
    #     was_draft = False

    #     if self.status == self.SUBMITTED:
    #         self.committee_assigned = True

    #     if not is_new_submission:
    #         try:
    #             existing = FormSubmission.objects.get(pk=self.pk)
    #             was_draft = (existing.status == self.DRAFT)
    #         except FormSubmission.DoesNotExist:
    #             pass

    #     if not self.form_id:
    #         self.form_id = self.generate_form_id()

    # # On first submission, generate a proposal_id if it's not already set
    #     if self.status == self.SUBMITTED and not self.proposal_id:
    #         self.proposal_id = self.generate_proposal_id()

    # # Save the object to the database
    #     super().save(*args, **kwargs)

    # # Generate PDF when the status changes to SUBMITTED from DRAFT or it's a new submission
    #     if self.status == self.SUBMITTED and (is_new_submission or was_draft):
    #         pdf_file = generate_submission_pdf(self)
    #         filename = f"{self.proposal_id or self.form_id}.pdf"
    #         self.applicationDocument.save(filename, pdf_file, save=True)

    def save(self, *args, **kwargs):
        is_new_submission = not self.pk  # True if this is a new object
        was_draft = False

        # if self.status == self.SUBMITTED:
        #     self.committee_assigned = True

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

        # ---- 1. Save the object to the database (MUST DO THIS FIRST!) ----
        super().save(*args, **kwargs)

        # ---- 2. If just submitted, move files out of /draft/ to final location ----
        if self.status == self.SUBMITTED and (is_new_submission or was_draft):
            # self.move_all_files_to_proposal_folder()
            # Save again to update file fields with new paths
            super().save(update_fields=[f.name for f in self._meta.fields if isinstance(f, models.FileField)])

            # ---- 3. Now, generate the PDF (so PDF also ends up in correct folder) ----
            pdf_file = generate_submission_pdf(self)
            filename = f"{self.proposal_id or self.form_id}.pdf"
            self.applicationDocument.save(filename, pdf_file, save=True)



    # def move_all_files_to_proposal_folder(self):
    #     file_fields = [
    #         'pan_file', 'passport_file', 'resume_upload', 'gantt_chart', 'technical_proposal',
    #         'proposal_presentation', 'budget_estimate_sample_doc', 'equipment_overhead_sample_doc',
    #         'income_estimate_sample_doc', 'presentation', 'dpr', 'applicationDocument'
    #     ]
    #     for field in file_fields:
    #         file = getattr(self, field, None)
    #         if file and file.name and '/draft/' in file.name:
    #             new_path = file.name.replace('/draft/', f'/{self.proposal_id}/')
    #             move_file_to_proposal_folder(file, self, file.name, new_path)
    #             setattr(self, field, new_path)

    #     relateds = [
    #         (self.fund_loan_documents.all(), ['document']),
    #         (self.iprdetails.all(), ['t_support_letter']),
    #         (self.collaborators.all(), ['pan_file_collab', 'mou_file_collab']),
    #         (self.rdstaff.all(), ['rd_staf_resume']),
    #         (self.shareholders.all(), ['identity_document']),
    #         (self.sub_shareholders.all(), ['identity_document']),
    #     ]
    #     for queryset, fields in relateds:
    #         for obj in queryset:
    #             for field in fields:
    #                 file = getattr(obj, field, None)
    #                 if file and file.name and '/draft/' in file.name:
    #                     new_path = file.name.replace('/draft/', f'/{self.proposal_id}/')
    #                     move_file_to_proposal_folder(file, obj, file.name, new_path)
    #                     setattr(obj, field, new_path)
    #                     obj.save(update_fields=[field])

    # # The file moving helper
    # def move_file_to_proposal_folder(file_field, instance, old_path, new_path):
    #     storage = file_field.storage
    #     if not storage.exists(old_path) or old_path == new_path:
    #         return False
    #     from django.core.files.base import File
    #     with storage.open(old_path, 'rb') as f:
    #         content = File(f)
    #         storage.save(new_path, content)
    #     storage.delete(old_path)
    #     file_field.name = new_path
    #     return True



    # def can_edit(self):
    #     now = datetime.now()
    #     if self.status == self.DRAFT:
    #         return True
    #     if self.status == self.SUBMITTED and self.updated_at < self.template.end_date:
    #         return True
    #     return False


    def can_edit(self):
        now = timezone.now()  # Use Django's timezone-aware now
        # Allow edits if still draft
        if self.status == self.DRAFT:
            return True

        # Allow edits if submitted, only if dates are present and updated_at is before template.end_date
        if (
            self.status == self.SUBMITTED
            and self.updated_at is not None
            and self.template is not None
            and getattr(self.template, 'end_date', None) is not None
        ):
            return self.updated_at < self.template.end_date

        # Default: not editable
        return False


    def __str__(self):
        return f"{self.form_id} ({self.get_status_display()})"

class IPRDetails(models.Model):
    submission = models.ForeignKey(FormSubmission, related_name='iprdetails', on_delete=models.CASCADE)
    name = models.CharField(max_length=255, help_text="Unique name or label for this form entry",blank=True, null=True)

    # Essence of Proposal
    national_importance = models.TextField(blank=True, null=True)
    commercialization_potential = models.TextField(blank=True, null=True)
    risk_factors = models.TextField(blank=True, null=True)
    preliminary_work_done = models.TextField(blank=True, null=True)
    technology_status = models.TextField(blank=True, null=True)
    business_strategy = models.TextField(blank=True, null=True)

    # IP Regulatory Details
    based_on_ipr = models.TextField(blank=True, null=True)
    ip_ownership_details = models.TextField(blank=True, null=True)
    ip_proposal = models.TextField(blank=True, null=True)
    regulatory_approvals = models.TextField(blank=True, null=True)
    status_approvals = models.TextField(blank=True, null=True)
    proof_of_status = models.FileField(
        upload_to=partial(upload_to_dynamic, subfolder="ipr_proof"),
        blank=True,
        null=True
    )

    # Telecom Service Provider
    t_name = models.CharField(max_length=255, blank=True, null=True)
    t_designation = models.CharField(max_length=255, blank=True, null=True)
    t_mobile_number = models.CharField(max_length=20, blank=True, null=True)
    t_email = models.EmailField(blank=True, null=True)
    t_address = models.TextField(blank=True, null=True)
    t_support_letter = models.FileField(
        upload_to=partial(upload_to_dynamic, subfolder="support_letters"),
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

class FundLoanDocument(models.Model):
    form_submission = models.ForeignKey(
        FormSubmission,
        on_delete=models.CASCADE,
        related_name="fund_loan_documents"
    )
    document = models.FileField(
        upload_to=partial(upload_to_dynamic, subfolder="Loan"),
        blank=True,
        null=True
    )
    def __str__(self):
        return self.document.name if self.document else "No file"

TTDF_COMPANY_CHOICES = [
    ('domestic_company', 'Domestic companies with focus on telecom R&D, Use case development'),
    ('startup_msme', 'Start-ups/MSMEs'),
    ('academic', 'Academic institutions'),
    ('rnd_section8_govt', 'R&D institutions, Section 8 companies / Societies, Central & State government entities / PSUs /Autonomous Bodies/SPVs / Limited liability partnerships'),
]
 
COLLABORATOR_CHOICES=[

('principalApplicant','principalApplicant'),
('consortiumPartner','consortiumPartner'),

]

class Collaborator(models.Model):
    form_submission = models.ForeignKey(FormSubmission, related_name="collaborators", on_delete=models.CASCADE)
    collaborator_type = models.CharField(max_length=50, choices=COLLABORATOR_CHOICES,blank=True, null=True)
    contact_person_name_collab = models.CharField(max_length=200, blank=True, null=True)
    organization_name_collab = models.CharField(max_length=200, blank=True, null=True)
    organization_type_collab = models.CharField(max_length=50, blank=True, null=True)
    ttdf_company = models.CharField(max_length=1000,blank=True,null=True)
    pan_file_collab = models.FileField(upload_to=partial(upload_to_dynamic, subfolder="collaborator/pan"), blank=True, null=True)
    pan_file_name_collab = models.CharField(max_length=255, blank=True, null=True)
    mou_file_collab = models.FileField(upload_to=partial(upload_to_dynamic, subfolder="collaborator/mou"), blank=True, null=True)
    mou_file_name_collab = models.CharField(max_length=255, blank=True, null=True)

class Equipment(models.Model):
    form_submission = models.ForeignKey(FormSubmission, related_name="equipments", on_delete=models.CASCADE)
    item = models.CharField(max_length=1000, blank=True, null=True)
    unit_price = models.DecimalField(max_digits=12, decimal_places=5, blank=True, null=True)
    quantity = models.PositiveIntegerField(blank=True, null=True)
    amount = models.DecimalField(max_digits=12, decimal_places=5, blank=True, null=True)
    contributor_type = models.CharField(max_length=255, blank=True, null=True)

class ShareHolder(models.Model):
    form_submission = models.ForeignKey(FormSubmission, related_name="shareholders", on_delete=models.CASCADE)
    share_holder_name = models.CharField(max_length=255, blank=True, null=True)
    share_percentage = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    identity_document = models.FileField(upload_to=partial(upload_to_dynamic, subfolder="shareholder/docs"), blank=True, null=True)
    identity_document_name = models.CharField(max_length=255, blank=True, null=True)

class RDStaff(models.Model):
    form_submission = models.ForeignKey(FormSubmission, related_name="rdstaff", on_delete=models.CASCADE)
    name = models.CharField(max_length=255, blank=True, null=True)
    designation = models.CharField(max_length=255, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    highest_qualification = models.CharField(max_length=255, blank=True, null=True)
    mobile = models.CharField(max_length=20, blank=True, null=True)
    rd_staf_resume = models.FileField(upload_to=partial(upload_to_dynamic, subfolder="rdstaff/resume"), blank=True, null=True)
    epf_details = models.CharField(max_length=255, blank=True, null=True)

class SubShareHolder(models.Model):
    form_submission = models.ForeignKey(FormSubmission, related_name="sub_shareholders", on_delete=models.CASCADE)
    share_holder_name = models.CharField(max_length=255, blank=True, null=True)
    share_percentage = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    identity_document = models.FileField(upload_to=partial(upload_to_dynamic, subfolder="subshareholder/docs"), blank=True, null=True)
    identity_document_name = models.CharField(max_length=255, blank=True, null=True)
    organization_name_subholder = models.CharField(max_length=200, blank=True, null=True)


class TeamMember(models.Model):
    form_submission = models.ForeignKey(FormSubmission, related_name="team_members", on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    resumefile = models.FileField(upload_to=partial(upload_to_dynamic, subfolder="Team Resumes/"), blank=True, null=True)
    resumetext = models.TextField(blank=True, null=True)
    otherdetails = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = ('form_submission', 'name', 'otherdetails') 





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


   

