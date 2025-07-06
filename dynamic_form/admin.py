from django.contrib import admin
from .models import (
    FormTemplate,
    FormPage,
    FormField,
    FormSubmission,
    FieldResponse,
    ApplicationStatusHistory,
)

@admin.register(FormTemplate)
class FormTemplateAdmin(admin.ModelAdmin):
    list_display = ('id','title', 'is_active', 'start_date', 'end_date')


@admin.register(FormSubmission)
class FormSubmissionAdmin(admin.ModelAdmin):
    list_display = ('id', 'proposal_id', 'template', 'service', 'applicant', 'status', 'created_at')
    readonly_fields = ['form_id', 'proposal_id', 'created_at', 'updated_at']
    search_fields = ['form_id', 'proposal_id', 'subject', 'description']

    fieldsets = (
        ("General Info", {
            'fields': (
                'template', 'service', 'applicant', 'status',
                'form_id', 'proposal_id', 'is_active',
                'contact_name', 'contact_email', 'applicationDocument', 'committee_assigned',
                'created_at', 'updated_at',
            ),
        }),
        ("Basic Documents", {
            'fields': (
                'individual_pan', 'pan_file', 'applicant_type', 'passport_file', 'resume_upload',
                'description', 'subject',
            )
        }),
        ("Shareholder Details", {
            'fields': (
                'share_holder_name', 'share_percentage', 'identity_document',
            )
        }),
        ("RD Staff Section", {
            'fields': (
                'rd_staff_name', 'rd_staff_designation', 'rd_staff_email', 'rd_staff_highest_qualification',
                'rd_staff_mobile', 'rd_staff_resume', 'rd_staff_epf_details',
            )
        }),
        ("Equipment Section", {
            'fields': (
                'equipment_item', 'equipment_unit_price', 'equipment_quantity',
                'equipment_amount', 'equipment_contributor_type',
            )
        }),
        ("Fund Details", {
            'fields': (
                'has_loan', 'fund_loan_description', 'fund_loan_amount',  # For multiple documents, use an inline
            )
        }),
        ("Contribution Details", {
            'fields': (
                'contribution_expected_source', 'contribution_item', 'contribution_amount',
            )
        }),
        ("Fund Source Details", {
            'fields': (
                'fund_source_details', 'fund_item', 'fund_amount',
            )
        }),
        ("Finance Summary", {
            'fields': (
                'grant_from_ttdf', 'contribution_applicant', 'expected_other_contribution',
                'other_source_funding', 'total_project_cost',
            )
        }),
        ("Other Section", {
            'fields': (
                'ttdf_applied_before',
            )
        }),
        # Add other sections as you add fields!
    )


@admin.register(FormPage)
class FormPageAdmin(admin.ModelAdmin):
    list_display = ('title', 'form_template', 'order')


@admin.register(FormField)
class FormFieldAdmin(admin.ModelAdmin):
    list_display = ('label', 'page', 'field_type', 'required', 'order')


@admin.register(FieldResponse)
class FieldResponseAdmin(admin.ModelAdmin):
    list_display = ('submission', 'field', 'value')


@admin.register(ApplicationStatusHistory)
class ApplicationStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ('submission', 'previous_status', 'new_status', 'changed_by', 'change_date')
    readonly_fields = ('change_date',)

























# class FormFieldInline(admin.TabularInline):
#     model = FormField
#     extra = 0
#     fields = ('label', 'field_type', 'required', 'order')

# class FormPageInline(admin.TabularInline):
#     model = FormPage
#     extra = 0
#     fields = ('title', 'order')

# class FieldResponseInline(admin.TabularInline):
#     model = FieldResponse
#     extra = 0
#     readonly_fields = ('field', 'value')
#     can_delete = False
    
#     def has_add_permission(self, request, obj=None):
#         return False

# # @admin.register(FormTemplate)
# # class FormTemplateAdmin(admin.ModelAdmin):
# #     list_display = ('title', 'created_at', 'updated_at', 'page_count', 'submission_count')
# #     search_fields = ('title', 'description')
# #     readonly_fields = ('created_at', 'updated_at')
# #     inlines = [FormPageInline]
    
# #     def page_count(self, obj):
# #         return obj.pages.count()
# #     page_count.short_description = 'Pages'
    
# #     def submission_count(self, obj):
# #         return obj.submissions.count()
# #     submission_count.short_description = 'Submissions'

# @admin.register(FormPage)
# class FormPageAdmin(admin.ModelAdmin):
#     list_display = ('title', 'form_template', 'order', 'field_count')
#     list_filter = ('form_template',)
#     search_fields = ('title', 'form_template__title')
#     inlines = [FormFieldInline]
    
#     def field_count(self, obj):
#         return obj.fields.count()
#     field_count.short_description = 'Fields'

# @admin.register(FormField)
# class FormFieldAdmin(admin.ModelAdmin):
#     list_display = ('label', 'field_type', 'page', 'required', 'order')
#     list_filter = ('field_type', 'required', 'page__form_template')
#     search_fields = ('label', 'page__title', 'page__form_template__title')

# # @admin.register(FormSubmission)
# # class FormSubmissionAdmin(admin.ModelAdmin):
# #     list_display = ( 'submitted_at', 'response_count')
# #     list_filter = ( 'submitted_at',)   
# #     date_hierarchy = 'submitted_at'
# #     inlines = [FieldResponseInline]
    
# #     def response_count(self, obj):
# #         return obj.responses.count()
# #     response_count.short_description = 'Responses'



# # @admin.register(ApplicationStatusHistory)
# # class ApplicationStatusHistoryAdmin(admin.ModelAdmin):
# #     list_display = ('submission', 'previous_status', 'new_status', 'changed_by', 'change_date', 'comment')
# #     list_filter = ('previous_status', 'new_status', 'changed_by')
# #     ordering = ('-change_date',)  


    
# # For Dynamic Form
# # @admin.register(FieldResponse)
# # class FieldResponseAdmin(admin.ModelAdmin):
# #     list_display = ('submission', 'field', 'short_value')
# #     list_filter = ('submission__form_template',)
# #     search_fields = ('field__label', 'submission__form_template__title')
# #     readonly_fields = ('submission', 'field', 'value')
    
# #     def short_value(self, obj):
# #         # Show truncated value for display in list view
# #         value_str = str(obj.value)
# #         if len(value_str) > 50:
# #             return value_str[:47] + "..."
# #         return value_str
# #     short_value.short_description = 'Value'
    
# #     def has_add_permission(self, request):
# #         return False
    
# #     def has_change_permission(self, request, obj=None):
# #         return False    

  