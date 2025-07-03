from django.contrib import admin
from django.db.models import Max
from .models import ScreeningRecord, TechnicalScreeningRecord

@admin.register(ScreeningRecord)
class ScreeningRecordAdmin(admin.ModelAdmin):
    list_display    = (
        'proposal', 'cycle', 'admin_evaluator', 'admin_decision',
        'evaluated_document', 'admin_screened_at', 'technical_evaluated'
    )
    list_filter     = ('admin_decision', 'cycle', 'admin_evaluator')
    search_fields   = ('proposal__proposal_id',)
    ordering        = ('-admin_screened_at',)

    exclude         = ('cycle',)
    readonly_fields = ('cycle',)

    def save_model(self, request, obj, form, change):
        # On creation, calculate the next cycle and set evaluator
        if not change:
            last_cycle = (
                ScreeningRecord.objects
                .filter(proposal=obj.proposal)
                .aggregate(max_cycle=Max('cycle'))
                .get('max_cycle') or 0
            )
            obj.cycle = last_cycle + 1
            obj.admin_evaluator = request.user
        super().save_model(request, obj, form, change)


@admin.register(TechnicalScreeningRecord)
class TechnicalScreeningRecordAdmin(admin.ModelAdmin):
    list_display  = (
        'screening_record', 'technical_evaluator', 'technical_decision',
        'technical_marks', 'technical_document', 'technical_screened_at'
    )
    list_filter   = ('technical_decision', 'technical_evaluator')
    search_fields = ('screening_record__proposal__proposal_id',)
    ordering      = ('-technical_screened_at',)
