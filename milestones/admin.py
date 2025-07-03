# milestones/admin.py

from django.contrib import admin
from .models import (
    Milestone, SubMilestone,
    FinanceRequest, PaymentClaim,FinanceSanction
)

from .models import Milestone, SubMilestone, MilestoneDocument, SubMilestoneDocument,MilestoneHistory,ProposalMouDocument


@admin.register(ProposalMouDocument)
class ProposalMouDocumentAdmin(admin.ModelAdmin):
    list_display = ('id', 'proposal', 'document', 'uploaded_at')
    search_fields = ('proposal__proposal_id',)
    readonly_fields = ('uploaded_at',)

# Inline for MilestoneHistory (read-only)
class MilestoneHistoryInline(admin.TabularInline):
    model = MilestoneHistory
    extra = 0
    can_delete = False
    readonly_fields = ('snapshot', 'created_at')
    show_change_link = True

class MilestoneDocumentInline(admin.TabularInline):
    model = MilestoneDocument
    extra = 1
    fields = (
        'mpr', 'mpr_status', 'mcr', 'mcr_status', 'uc', 'uc_status', 'assets', 'assets_status', 'uploaded_at'
    )
    readonly_fields = ('uploaded_at',)

class SubMilestoneDocumentInline(admin.TabularInline):
    model = SubMilestoneDocument
    extra = 1
    fields = (
        'mpr', 'mpr_status', 'mcr', 'mcr_status', 'uc', 'uc_status', 'assets', 'assets_status', 'uploaded_at'
    )
    readonly_fields = ('uploaded_at',)

class SubMilestoneInline(admin.TabularInline):
    model = SubMilestone
    extra = 1

@admin.register(Milestone)
class MilestoneAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'proposal', 'created_by', 'created_at')
    inlines = [MilestoneDocumentInline, SubMilestoneInline, MilestoneHistoryInline]
    search_fields = ('title', 'proposal__proposal_id')
    list_filter = ('created_at',)

@admin.register(SubMilestone)
class SubMilestoneAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'title',
        'milestone_id_display',
        'milestone_title_display',
        'created_by',
        'created_at'
    )
    inlines = [SubMilestoneDocumentInline]
    search_fields = ('title', 'milestone__title')
    list_filter = ('created_at',)

    def milestone_id_display(self, obj):
        return obj.milestone.id if obj.milestone else "-"
    milestone_id_display.short_description = 'Milestone ID'

    def milestone_title_display(self, obj):
        return obj.milestone.title if obj.milestone else "-"
    milestone_title_display.short_description = 'Milestone Name'

@admin.register(MilestoneDocument)
class MilestoneDocumentAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'milestone',
        'mpr_status', 'mcr_status', 'uc_status', 'assets_status',
        'uploaded_at'
    )
    list_filter = ('mpr_status', 'mcr_status', 'uc_status', 'assets_status')
    search_fields = ('milestone__title',)

@admin.register(SubMilestoneDocument)
class SubMilestoneDocumentAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'submilestone',
        'mpr_status', 'mcr_status', 'uc_status', 'assets_status',
        'uploaded_at'
    )
    list_filter = ('mpr_status', 'mcr_status', 'uc_status', 'assets_status')
    search_fields = ('submilestone__title',)

@admin.register(MilestoneHistory)
class MilestoneHistoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'milestone', 'created_at')
    readonly_fields = ('milestone', 'snapshot', 'created_at')
    search_fields = ('milestone__title',)
    list_filter = ('created_at',)



@admin.register(FinanceRequest)
class FinanceRequestAdmin(admin.ModelAdmin):
    list_display  = (
        'id','milestone','submilestone','applicant','status',
        'ia_remark','created_by','reviewed_at','updated_by','updated_at'
    )
    list_filter   = ('status','created_at','reviewed_at')
    search_fields = ('milestone__title','applicant__email')

@admin.register(PaymentClaim)
class PaymentClaimAdmin(admin.ModelAdmin):
    list_display = [
        'id', 
        'proposal', 
        'finance_request', 
        'ia_user', 
        'status',
        'ia_action',        # show new IA action status
        'advance_payment', 
        'net_claim_amount',
        'created_at', 
        'updated_at'
    ]
    list_filter = [
        'status', 
        'advance_payment', 
        'ia_action',        # filter by IA action
        'created_at', 
        'updated_at'
    ]
    search_fields = [
        'proposal__proposal_id', 
        'finance_request__id',
        'ia_user__email', 
        'ia_remark',       # search by IA action remark
        'jf_remark'
    ]
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        (None, {
            'fields': (
                'proposal', 
                'finance_request', 
                'ia_user', 
                'status',
                'jf_remark',
                'advance_payment',
                'penalty_amount',
                'adjustment_amount',
                'net_claim_amount',
            )
        }),
        ('IA Action', {
            'fields': (
                'ia_action', 
                'ia_remark',
            )
        }),
        ('Audit', {
            'fields': (
                'created_at', 
                'reviewed_at', 
                'updated_by', 
                'updated_at'
            )
        }),
    )


@admin.register(FinanceSanction)
class FinanceSanctionAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'finance_request', 'sanction_amount', 'status', 'sanction_date', 'jf_user'
    )
    list_filter = ('status', 'sanction_date')
    search_fields = ('finance_request__id', 'payment_claim__id')
    readonly_fields = ('created_by', 'created_at', 'updated_by', 'updated_at', 'jf_user', 'reviewed_at')

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        obj.updated_by = request.user

        # Automatically set jf_user/reviewed_at if JF user changes status
        if request.user.groups.filter(name='JF').exists() and 'status' in form.changed_data:
            obj.jf_user = request.user
            obj.reviewed_at = timezone.now()
        super().save_model(request, obj, form, change)







# IA 
# 
from django.contrib import admin
from .models import ImplementationAgency

@admin.register(ImplementationAgency)
class ImplementationAgencyAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "admin_name",
        "user_count",
        "assigned_proposal_count",
    )
    search_fields = ("name", "admin__email", "users__email")
    filter_horizontal = ("users",)
    readonly_fields = ("assigned_proposals_pretty",)

    def admin_name(self, obj):
        return obj.admin.get_full_name() if obj.admin else ""
    admin_name.short_description = "IA Admin"

    def user_count(self, obj):
        return obj.users.count()
    user_count.short_description = "User Count"

    def assigned_proposal_count(self, obj):
        return len(obj.assigned_proposals) if obj.assigned_proposals else 0
    assigned_proposal_count.short_description = "Assigned Proposals"

    def assigned_proposals_pretty(self, obj):
        # Nicely formatted list of proposal IDs (read-only in the admin form)
        return ", ".join(obj.assigned_proposals or [])
    assigned_proposals_pretty.short_description = "Assigned Proposal IDs"
        
