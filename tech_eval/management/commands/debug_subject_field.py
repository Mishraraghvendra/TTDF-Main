# tech_eval/management/commands/debug_subject_field.py

from django.core.management.base import BaseCommand
from tech_eval.models import TechnicalEvaluationRound

class Command(BaseCommand):
    help = 'Quick debug of FormSubmission subject field'
    
    def handle(self, *args, **options):
        self.stdout.write("=== DEBUGGING SUBJECT FIELD ===")
        
        # Get first 5 evaluation rounds with proposals
        eval_rounds = TechnicalEvaluationRound.objects.filter(
            proposal__isnull=False
        ).select_related('proposal', 'proposal__applicant')[:5]
        
        if not eval_rounds.exists():
            self.stdout.write("No evaluation rounds found!")
            return
        
        for i, eval_round in enumerate(eval_rounds, 1):
            proposal = eval_round.proposal
            proposal_id = getattr(proposal, 'proposal_id', f'Round-{eval_round.id}')
            
            self.stdout.write(f"\n--- PROPOSAL {i}: {proposal_id} ---")
            
            # Check all possible subject-related fields
            fields_to_check = [
                'subject', 'title', 'project_title', 'proposal_title',
                'description', 'abstract', 'project_description',
                'org_type', 'applicant_type', 'organization_type',
                'contact_name', 'contact_email'
            ]
            
            for field in fields_to_check:
                try:
                    value = getattr(proposal, field, None)
                    if value:
                        display_value = str(value)[:80] + ('...' if len(str(value)) > 80 else '')
                        self.stdout.write(f"  ✓ {field}: {display_value}")
                    else:
                        self.stdout.write(f"  ✗ {field}: None/Empty")
                except Exception as e:
                    self.stdout.write(f"  ✗ {field}: ERROR - {e}")
            
            # Check User fields
            if proposal.applicant:
                self.stdout.write(f"  User.full_name: {getattr(proposal.applicant, 'full_name', 'None')}")
                self.stdout.write(f"  User.email: {getattr(proposal.applicant, 'email', 'None')}")
                self.stdout.write(f"  User.organization: {getattr(proposal.applicant, 'organization', 'None')}")
            
            # Check cached data
            if hasattr(eval_round, 'cached_proposal_data') and eval_round.cached_proposal_data:
                cached = eval_round.cached_proposal_data
                self.stdout.write(f"  CACHED subject: {cached.get('subject', 'None')}")
                self.stdout.write(f"  CACHED org_name: {cached.get('org_name', 'None')}")
                self.stdout.write(f"  CACHED contact_person: {cached.get('contact_person', 'None')}")
            else:
                self.stdout.write(f"  CACHED: No cached data")
        
        # Show FormSubmission model fields that contain actual data
        self.stdout.write(f"\n=== CHECKING ACTUAL DATA IN FORMSUBMISSION ===")
        first_proposal = eval_rounds.first().proposal
        
        populated_fields = []
        for field in first_proposal._meta.fields:
            try:
                value = getattr(first_proposal, field.name, None)
                if value and str(value).strip() and str(value) not in ['', 'None', 'null']:
                    populated_fields.append({
                        'name': field.name,
                        'value': str(value)[:50] + ('...' if len(str(value)) > 50 else ''),
                        'type': field.__class__.__name__
                    })
            except:
                pass
        
        self.stdout.write(f"Found {len(populated_fields)} fields with data:")
        for field in populated_fields[:20]:  # Show first 20
            self.stdout.write(f"  {field['name']}: {field['value']} ({field['type']})")
        
        # Check specific critical fields
        critical_fields = ['subject', 'description', 'org_type', 'contact_name', 'contact_email']
        self.stdout.write(f"\n=== CRITICAL FIELDS STATUS ===")
        
        for field in critical_fields:
            count_with_data = 0
            total_checked = 0
            
            for eval_round in eval_rounds:
                proposal = eval_round.proposal
                total_checked += 1
                try:
                    value = getattr(proposal, field, None)
                    if value and str(value).strip():
                        count_with_data += 1
                except:
                    pass
            
            percentage = (count_with_data / total_checked * 100) if total_checked > 0 else 0
            status = "✓" if percentage > 50 else "⚠" if percentage > 0 else "✗"
            self.stdout.write(f"  {status} {field}: {count_with_data}/{total_checked} ({percentage:.1f}%) have data")