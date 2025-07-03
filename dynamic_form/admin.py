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
    list_display = ('title', 'is_active', 'start_date', 'end_date')


@admin.register(FormSubmission)
class FormSubmissionAdmin(admin.ModelAdmin):
    list_display = ('proposal_id', 'template','service','applicant', 'org_type','status', 'created_at')
    readonly_fields = ['form_id', 'proposal_id', 'created_at', 'updated_at']
    search_fields = ['form_id', 'proposal_id', 'subject', 'description',]

    fieldsets = (
        (None, {
            'fields': (
                'template',
                'service',
                'applicant',
                'status',
                'form_id',
                'proposal_id',
                'contact_name',
                'contact_email',
                'applicationDocument',
                'committee_assigned',
                
            )
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
        }),
        ('Basic Documents', {
            'fields': (
                'individual_pan',
                'pan_file',
                'applicant_type',
                'passport_file',
                'resume_upload',
                'description','subject',
            )
        }),
        ('Organization Details', {
            'fields': (
                'org_address_line1',
                'org_address_line2',
                'org_street_village',
                'org_city_town',
                'org_state',
                'org_pin_code',
                'org_landline',
                'org_mobile',
                'org_official_email',
                'org_website',
                'org_shares_51pct_indian_citizens',
                'org_tan_pan_cin_file',
                'org_registration_certificate',
                'org_approval_certificate',
                'org_registration_certificate_2',
                'org_annual_report',
                'org_industry_auth_letter',
                'org_shareholding_pattern_file',
            )
        }),
        # … you can add more sections here for Proposal Summary, Collaborator,
        # Finance Details, IPR, Patents, Manpower, etc., using the fields
        # that still exist on your model …
        ('Declaration', {
            'fields': (
                'declaration_document',
                'declaration_1',
                'declaration_2',
                'declaration_3',
                'declaration_4',
                'declaration_5',
            )
        }),
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

  