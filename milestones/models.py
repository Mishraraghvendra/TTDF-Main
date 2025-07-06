# milestones/models.py

import uuid
from django.db import models
from django.conf import settings
from dynamic_form.models import FormSubmission
import json
from django.core.serializers.json import DjangoJSONEncoder
import datetime



def service_based_upload_path(subfolder):
    def _upload_to(instance, filename):
        service = (instance.service.name or 'unknown').replace(' ', '_').lower() if instance.service else 'unknown'
        proposal_id = (instance.proposal_id or 'unknown').replace('/', '').replace('\\', '')
        ext = filename.split('.')[-1] if '.' in filename else 'pdf'
        return f"milestones/{subfolder}/{service}/{proposal_id}.{ext}"
    return _upload_to

def upload_to_mou(instance, filename):
    service = None
    proposal_id = None
    if hasattr(instance, 'service') and instance.service:
        service = instance.service.name
    elif hasattr(instance, 'proposal') and instance.proposal and hasattr(instance.proposal, 'service') and instance.proposal.service:
        service = instance.proposal.service.name
    else:
        service = 'unknown'

    if hasattr(instance, 'proposal_id') and instance.proposal_id:
        proposal_id = instance.proposal_id
    elif hasattr(instance, 'proposal') and instance.proposal and hasattr(instance.proposal, 'proposal_id'):
        proposal_id = instance.proposal.proposal_id
    else:
        proposal_id = 'unknown'
    service = (service or 'unknown').replace(' ', '_').lower()
    proposal_id = (proposal_id or 'unknown').replace('/', '').replace('\\', '')
    ext = filename.split('.')[-1] if '.' in filename else 'pdf'
    return f"milestones/mou/{service}/{proposal_id}.{ext}"

def upload_to_agreement(instance, filename):
    # Same logic, just change folder name
    # ... copy from upload_to_mou but folder is agreements ...
    service = None
    proposal_id = None
    if hasattr(instance, 'service') and instance.service:
        service = instance.service.name
    elif hasattr(instance, 'proposal') and instance.proposal and hasattr(instance.proposal, 'service') and instance.proposal.service:
        service = instance.proposal.service.name
    else:
        service = 'unknown'
    if hasattr(instance, 'proposal_id') and instance.proposal_id:
        proposal_id = instance.proposal_id
    elif hasattr(instance, 'proposal') and instance.proposal and hasattr(instance.proposal, 'proposal_id'):
        proposal_id = instance.proposal.proposal_id
    else:
        proposal_id = 'unknown'
    service = (service or 'unknown').replace(' ', '_').lower()
    proposal_id = (proposal_id or 'unknown').replace('/', '').replace('\\', '')
    ext = filename.split('.')[-1] if '.' in filename else 'pdf'
    return f"milestones/agreements/{service}/{proposal_id}.{ext}"

def upload_to_mpr(instance, filename):
    # ... same, folder is mpr ...
    service = None
    proposal_id = None
    if hasattr(instance, 'service') and instance.service:
        service = instance.service.name
    elif hasattr(instance, 'proposal') and instance.proposal and hasattr(instance.proposal, 'service') and instance.proposal.service:
        service = instance.proposal.service.name
    else:
        service = 'unknown'
    if hasattr(instance, 'proposal_id') and instance.proposal_id:
        proposal_id = instance.proposal_id
    elif hasattr(instance, 'proposal') and instance.proposal and hasattr(instance.proposal, 'proposal_id'):
        proposal_id = instance.proposal.proposal_id
    else:
        proposal_id = 'unknown'
    service = (service or 'unknown').replace(' ', '_').lower()
    proposal_id = (proposal_id or 'unknown').replace('/', '').replace('\\', '')
    ext = filename.split('.')[-1] if '.' in filename else 'pdf'
    return f"milestones/mpr/{service}/{proposal_id}.{ext}"

def upload_to_mcr(instance, filename):
    # ... same, folder is mcr ...
    service = None
    proposal_id = None
    if hasattr(instance, 'service') and instance.service:
        service = instance.service.name
    elif hasattr(instance, 'proposal') and instance.proposal and hasattr(instance.proposal, 'service') and instance.proposal.service:
        service = instance.proposal.service.name
    else:
        service = 'unknown'
    if hasattr(instance, 'proposal_id') and instance.proposal_id:
        proposal_id = instance.proposal_id
    elif hasattr(instance, 'proposal') and instance.proposal and hasattr(instance.proposal, 'proposal_id'):
        proposal_id = instance.proposal.proposal_id
    else:
        proposal_id = 'unknown'
    service = (service or 'unknown').replace(' ', '_').lower()
    proposal_id = (proposal_id or 'unknown').replace('/', '').replace('\\', '')
    ext = filename.split('.')[-1] if '.' in filename else 'pdf'
    return f"milestones/mcr/{service}/{proposal_id}.{ext}"

def upload_to_uc(instance, filename):
    # ... same, folder is uc ...
    service = None
    proposal_id = None
    if hasattr(instance, 'service') and instance.service:
        service = instance.service.name
    elif hasattr(instance, 'proposal') and instance.proposal and hasattr(instance.proposal, 'service') and instance.proposal.service:
        service = instance.proposal.service.name
    else:
        service = 'unknown'
    if hasattr(instance, 'proposal_id') and instance.proposal_id:
        proposal_id = instance.proposal_id
    elif hasattr(instance, 'proposal') and instance.proposal and hasattr(instance.proposal, 'proposal_id'):
        proposal_id = instance.proposal.proposal_id
    else:
        proposal_id = 'unknown'
    service = (service or 'unknown').replace(' ', '_').lower()
    proposal_id = (proposal_id or 'unknown').replace('/', '').replace('\\', '')
    ext = filename.split('.')[-1] if '.' in filename else 'pdf'
    return f"milestones/uc/{service}/{proposal_id}.{ext}"

def upload_to_assets(instance, filename):
    # ... same, folder is assets ...
    service = None
    proposal_id = None
    if hasattr(instance, 'service') and instance.service:
        service = instance.service.name
    elif hasattr(instance, 'proposal') and instance.proposal and hasattr(instance.proposal, 'service') and instance.proposal.service:
        service = instance.proposal.service.name
    else:
        service = 'unknown'
    if hasattr(instance, 'proposal_id') and instance.proposal_id:
        proposal_id = instance.proposal_id
    elif hasattr(instance, 'proposal') and instance.proposal and hasattr(instance.proposal, 'proposal_id'):
        proposal_id = instance.proposal.proposal_id
    else:
        proposal_id = 'unknown'
    service = (service or 'unknown').replace(' ', '_').lower()
    proposal_id = (proposal_id or 'unknown').replace('/', '').replace('\\', '')
    ext = filename.split('.')[-1] if '.' in filename else 'pdf'
    return f"milestones/assets/{service}/{proposal_id}.{ext}"

def upload_to_finance(instance, filename):
    # ... same, folder is finance ...
    service = None
    proposal_id = None
    if hasattr(instance, 'service') and instance.service:
        service = instance.service.name
    elif hasattr(instance, 'proposal') and instance.proposal and hasattr(instance.proposal, 'service') and instance.proposal.service:
        service = instance.proposal.service.name
    else:
        service = 'unknown'
    if hasattr(instance, 'proposal_id') and instance.proposal_id:
        proposal_id = instance.proposal_id
    elif hasattr(instance, 'proposal') and instance.proposal and hasattr(instance.proposal, 'proposal_id'):
        proposal_id = instance.proposal.proposal_id
    else:
        proposal_id = 'unknown'
    service = (service or 'unknown').replace(' ', '_').lower()
    proposal_id = (proposal_id or 'unknown').replace('/', '').replace('\\', '')
    ext = filename.split('.')[-1] if '.' in filename else 'pdf'
    return f"milestones/finance/{service}/{proposal_id}.{ext}"


class ProposalMouDocument(models.Model):
    proposal = models.OneToOneField(FormSubmission, on_delete=models.CASCADE, related_name='mou_document')
    document = models.FileField(upload_to=upload_to_mou, null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    is_mou_signed = models.BooleanField(default=False, help_text="Mark as True when MOU is signed")


    def __str__(self):
        return f"MOU for {self.proposal.proposal_id}"

class MilestoneHistory(models.Model):
    milestone = models.ForeignKey('Milestone', on_delete=models.CASCADE, related_name='histories')
    snapshot = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"History for {self.milestone.title} at {self.created_at:%Y-%m-%d %H:%M}"

class Milestone(models.Model):
    proposal = models.ForeignKey(FormSubmission, on_delete=models.CASCADE, related_name='milestones')    
    title = models.CharField(max_length=200)
    
    time_required = models.PositiveIntegerField(null=True,blank=True)
    revised_time_required = models.PositiveIntegerField(null=True,blank=True)

    funds_requested= models.PositiveIntegerField(null=True,blank=True)    
    grant_from_ttdf = models.PositiveIntegerField(null=True,blank=True)

    initial_contri_applicant = models.PositiveIntegerField(null=True,blank=True)
    revised_contri_applicant = models.PositiveIntegerField(null=True,blank=True)

    initial_grant_from_ttdf = models.PositiveIntegerField(null=True,blank=True)
    revised_grant_from_ttdf = models.PositiveIntegerField(null=True,blank=True)

    description = models.TextField(blank=True)
    activities = models.TextField(blank=True)

    agreement = models.FileField(upload_to=upload_to_agreement, null=True, blank=True)
    mou_document = models.FileField(upload_to=upload_to_mou, null=True, blank=True)
    

    status = models.CharField(max_length=20, choices=[('completed','Completed'),('in_progress','In Progress'),('delayed','Delayed'),('on_time','On Time')], default='in_progress')
    due_date = models.DateField(null=True, blank=True)
    start_date = models.DateField(null=True, blank=True, help_text="Milestone start date")

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='created_milestones')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='updated_milestones')
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} – {self.proposal.proposal_id}"
   

    import json
    from django.core.serializers.json import DjangoJSONEncoder

    def save_snapshot_to_history(self):
        data = {
        "proposal_id": self.proposal.proposal_id if self.proposal and self.proposal.proposal_id else None,
        "proposal_pk": str(self.proposal.id) if self.proposal and self.proposal.id else None,
        "title": self.title,
        "time_required": self.time_required,
        "revised_time_required": self.revised_time_required,
        "grant_from_ttdf": self.grant_from_ttdf,
        "initial_contri_applicant": self.initial_contri_applicant,
        "revised_contri_applicant": self.revised_contri_applicant,
        "initial_grant_from_ttdf": self.initial_grant_from_ttdf,
        "revised_grant_from_ttdf": self.revised_grant_from_ttdf,
        "description": self.description,
        "agreement": self.agreement.url if self.agreement else None,
        "mou_document": self.mou_document.url if self.mou_document else None,
        "created_by": str(self.created_by_id) if self.created_by_id else None,
        "created_at": self.created_at.isoformat() if self.created_at else None,
        "updated_by": str(self.updated_by_id) if self.updated_by_id else None,
        "updated_at": self.updated_at.isoformat() if self.updated_at else None,
    }
        json_snapshot = json.dumps(data, cls=DjangoJSONEncoder)
        safe_data = json.loads(json_snapshot)
        from .models import MilestoneHistory
        MilestoneHistory.objects.create(milestone=self, snapshot=safe_data)

class DocumentStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    ACCEPTED = 'accepted', 'Accepted'
    REJECTED = 'rejected', 'Rejected'

class MilestoneDocument(models.Model):
    milestone = models.ForeignKey(Milestone, on_delete=models.CASCADE, related_name='documents')
    mpr = models.FileField(upload_to=upload_to_mpr, null=True, blank=True)
    mpr_for_month = models.DateField(null=True, blank=True, help_text="Month this MPR covers (any date in the target month)")
    mpr_status = models.CharField(max_length=10, choices=DocumentStatus.choices, default=DocumentStatus.PENDING)
    mcr = models.FileField(upload_to=upload_to_mcr, null=True, blank=True)
    mcr_status = models.CharField(max_length=10, choices=DocumentStatus.choices, default=DocumentStatus.PENDING)
    uc = models.FileField(upload_to=upload_to_uc, null=True, blank=True)
    uc_status = models.CharField(max_length=10, choices=DocumentStatus.choices, default=DocumentStatus.PENDING)
    assets = models.FileField(upload_to=upload_to_assets, null=True, blank=True)
    assets_status = models.CharField(max_length=10, choices=DocumentStatus.choices, default=DocumentStatus.PENDING)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    remarks = models.TextField(blank=True, null=True, help_text="Additional remarks for milestone documents")

class SubMilestone(models.Model):
    milestone = models.ForeignKey(Milestone, on_delete=models.CASCADE, related_name='submilestones')
    title = models.CharField(max_length=200)
    time_required = models.PositiveIntegerField(null=True,blank=True)
    revised_time_required = models.PositiveIntegerField(null=True,blank=True)
    grant_from_ttdf = models.PositiveIntegerField(null=True,blank=True)
    initial_contri_applicant = models.PositiveIntegerField(null=True,blank=True)
    revised_contri_applicant = models.PositiveIntegerField(null=True,blank=True)
    initial_grant_from_ttdf = models.PositiveIntegerField(null=True,blank=True)
    revised_grant_from_ttdf = models.PositiveIntegerField(null=True,blank=True)
    description = models.TextField(blank=True)
    activities = models.TextField(blank=True)

    status = models.CharField(max_length=20, choices=[('completed','Completed'),('in_progress','In Progress'),('delayed','Delayed'),('on_time','On Time')], default='in_progress')
    due_date = models.DateField(null=True, blank=True)
    remarks = models.TextField(blank=True, null=True, help_text="Additional remarks for submilestone documents")

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='created_submilestones')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='updated_submilestones')
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} – {self.milestone.title}"

class SubMilestoneDocument(models.Model):
    submilestone = models.ForeignKey(SubMilestone, on_delete=models.CASCADE, related_name='documents')
    mpr = models.FileField(upload_to='submilestones/mpr/', null=True, blank=True)
    mpr_for_month = models.DateField(null=True, blank=True, help_text="Month this MPR covers (any date in the target month)")
    mpr_status = models.CharField(max_length=10, choices=DocumentStatus.choices, default=DocumentStatus.PENDING)
    mcr = models.FileField(upload_to='submilestones/mcr/', null=True, blank=True)
    mcr_status = models.CharField(max_length=10, choices=DocumentStatus.choices, default=DocumentStatus.PENDING)
    uc = models.FileField(upload_to='submilestones/uc/', null=True, blank=True)
    uc_status = models.CharField(max_length=10, choices=DocumentStatus.choices, default=DocumentStatus.PENDING)
    assets = models.FileField(upload_to='submilestones/assets/', null=True, blank=True)
    assets_status = models.CharField(max_length=10, choices=DocumentStatus.choices, default=DocumentStatus.PENDING)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    remarks = models.TextField(blank=True, null=True, help_text="Document description/remarks for submilestone documents")



class FinanceRequest(models.Model):
    PENDING_IA  = 'PENDING_IA'
    IA_REJECTED = 'IA_REJECTED'
    IA_APPROVED = 'IA_APPROVED'
    STATUS_CHOICES = (
        (PENDING_IA,  'Pending IA'),
        (IA_REJECTED, 'IA Rejected'),
        (IA_APPROVED, 'IA Approved'),
    )

    proposal = models.ForeignKey(
        FormSubmission,
        to_field='proposal_id',
        on_delete=models.CASCADE,
        related_name='finance_requests'
    )
    milestone    = models.ForeignKey(Milestone, on_delete=models.CASCADE, related_name='finance_requests')
    submilestone = models.ForeignKey(SubMilestone, on_delete=models.CASCADE,
                                     related_name='finance_requests', null=True, blank=True)
    applicant    = models.ForeignKey(settings.AUTH_USER_MODEL,
                                     on_delete=models.CASCADE, related_name='finance_requests')
    document = models.FileField(upload_to=upload_to_finance)
    status       = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING_IA)
    ia_remark    = models.TextField(blank=True, null=True)

    created_by   = models.ForeignKey(settings.AUTH_USER_MODEL,
                                     on_delete=models.SET_NULL, null=True,
                                     blank=True, related_name='created_finance_requests')
    created_at   = models.DateTimeField(auto_now_add=True)
    reviewed_at  = models.DateTimeField(null=True, blank=True)
    updated_by   = models.ForeignKey(settings.AUTH_USER_MODEL,
                                     on_delete=models.SET_NULL, null=True,
                                     blank=True, related_name='updated_finance_requests')
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"FinanceRequest {self.id} ({self.status})"


class PaymentClaim(models.Model):
    PENDING_JF   = 'PENDING_JF'
    JF_REJECTED  = 'JF_REJECTED'
    JF_APPROVED  = 'JF_APPROVED'
    STATUS_CHOICES = (
        (PENDING_JF,  'Pending JF'),
        (JF_REJECTED, 'JF Rejected'),
        (JF_APPROVED, 'JF Approved'),
    )
    
    # IA ACTIONS (examples)
    
    PENDING_IA   = 'PENDING_IA'
    IA_ACCEPTED    = 'ACCEPTED'
    IA_REJECTED    = 'REJECTED'
    IA_ACTION_CHOICES = (
        
        (PENDING_IA,  'Pending IA'),
        (IA_ACCEPTED,  'Accepted by IA'),
        (IA_REJECTED,  'Rejected by IA'),
    )

    proposal        = models.ForeignKey(
        FormSubmission,
        to_field='proposal_id',
        on_delete=models.CASCADE,
        related_name='payment_claims'
    )
    finance_request  = models.OneToOneField(FinanceRequest, on_delete=models.CASCADE,
                                            related_name='payment_claim',
    null=True, blank=True )

    milestone = models.ForeignKey(
        Milestone, on_delete=models.CASCADE, null=True, blank=True, related_name='payment_claims'
    )
    sub_milestone = models.ForeignKey(
        SubMilestone, on_delete=models.CASCADE, null=True, blank=True, related_name='payment_claims'
    )


    ia_user          = models.ForeignKey(settings.AUTH_USER_MODEL,
                                         on_delete=models.SET_NULL, null=True,
                                         related_name='created_payment_claims')
    status           = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING_JF)
    jf_remark        = models.TextField(blank=True, null=True)

    advance_payment   = models.BooleanField(default=False)
    penalty_amount    = models.DecimalField(max_digits=10, decimal_places=2, default=0,null=True, blank=True)
    ld                = models.DecimalField(max_digits=10, decimal_places=2, default=0,null=True, blank=True)
    adjustment_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0,null=True, blank=True)
    net_claim_amount  = models.DecimalField(max_digits=10, decimal_places=2, default=0,null=True, blank=True)

    # New fields for action taken by IA
    ia_action = models.CharField(
        max_length=20, choices=IA_ACTION_CHOICES, default=PENDING_IA 
    )
    ia_remark = models.TextField(blank=True, null=True)

    created_at       = models.DateTimeField(auto_now_add=True)
    reviewed_at      = models.DateTimeField(null=True, blank=True)
    updated_by       = models.ForeignKey(settings.AUTH_USER_MODEL,
                                         on_delete=models.SET_NULL, null=True,
                                         blank=True, related_name='updated_payment_claims')
    updated_at       = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"PaymentClaim {self.id} ({self.status})"


class FinanceSanction(models.Model):
    PENDING_JF   = 'PENDING_JF'
    JF_REJECTED  = 'JF_REJECTED'
    JF_APPROVED  = 'JF_APPROVED'
    STATUS_CHOICES = (
        (PENDING_JF, 'Pending JF'),
        (JF_REJECTED, 'JF Rejected'),
        (JF_APPROVED, 'JF Approved'),
    )
 
    proposal        = models.ForeignKey(
        FormSubmission,
        to_field='proposal_id',
        on_delete=models.CASCADE,
        related_name='finance_sanctions'
    )
    finance_request = models.ForeignKey('FinanceRequest',on_delete=models.CASCADE,related_name='finance_sanctions')
    payment_claim = models.OneToOneField('PaymentClaim',on_delete=models.CASCADE,related_name='finance_sanction')

    sanction_date = models.DateField()
    sanction_amount = models.DecimalField(max_digits=12, decimal_places=2)
    sanction_note = models.TextField(blank=True, null=True)

    status = models.CharField(max_length=20,choices=STATUS_CHOICES,default=PENDING_JF)
    jf_user = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name='reviewed_finance_sanctions')
    jf_remark = models.TextField(blank=True, null=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    created_by = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name='created_finance_sanctions')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name='updated_finance_sanctions')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-sanction_date']

    def __str__(self):
        return f"FinanceSanction {self.id} - {self.get_status_display()}"



# IA

from django.db import models
from django.conf import settings

class ImplementationAgency(models.Model):
    name = models.CharField(max_length=255, unique=True)
    admin = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="ia_admin_agency"
    )
    users = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True, related_name="ia_agencies"
    )
    assigned_proposals = models.JSONField(default=list, blank=True)  # List of proposal_ids

    def __str__(self):
        return self.name

    def assign_proposal(self, proposal_id):
        if proposal_id not in self.assigned_proposals:
            self.assigned_proposals.append(proposal_id)
            self.save(update_fields=['assigned_proposals'])