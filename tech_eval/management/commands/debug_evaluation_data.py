# tech_eval/management/commands/debug_evaluation_data.py

from django.core.management.base import BaseCommand
from tech_eval.models import TechnicalEvaluationRound, EvaluatorAssignment, CriteriaEvaluation
from dynamic_form.models import FormSubmission
import json

class Command(BaseCommand):
    help = 'Debug technical evaluation data to see what we have'
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=== Technical Evaluation Data Debug ==='))
        
        # 1. Check FormSubmissions
        self.stdout.write('\n1. FormSubmission Data:')
        total_forms = FormSubmission.objects.count()
        submitted_forms = FormSubmission.objects.filter(status='submitted').count()
        
        self.stdout.write(f'  Total FormSubmissions: {total_forms}')
        self.stdout.write(f'  Submitted FormSubmissions: {submitted_forms}')
        
        if total_forms > 0:
            sample_form = FormSubmission.objects.first()
            self.stdout.write(f'  Sample FormSubmission:')
            self.stdout.write(f'    ID: {sample_form.id}')
            self.stdout.write(f'    Proposal ID: {sample_form.proposal_id}')
            self.stdout.write(f'    Status: {sample_form.status}')
            self.stdout.write(f'    Subject: {sample_form.subject}')
            self.stdout.write(f'    Service: {sample_form.service.name if sample_form.service else "None"}')
        
        # 2. Check TechnicalEvaluationRounds
        self.stdout.write('\n2. TechnicalEvaluationRound Data:')
        total_rounds = TechnicalEvaluationRound.objects.count()
        self.stdout.write(f'  Total Evaluation Rounds: {total_rounds}')
        
        if total_rounds > 0:
            # Check status distribution
            status_counts = {}
            decision_counts = {}
            
            for round_obj in TechnicalEvaluationRound.objects.all():
                status = round_obj.assignment_status
                decision = round_obj.overall_decision
                
                status_counts[status] = status_counts.get(status, 0) + 1
                decision_counts[decision] = decision_counts.get(decision, 0) + 1
            
            self.stdout.write(f'  Assignment Status Distribution:')
            for status, count in status_counts.items():
                self.stdout.write(f'    {status}: {count}')
            
            self.stdout.write(f'  Decision Distribution:')
            for decision, count in decision_counts.items():
                self.stdout.write(f'    {decision}: {count}')
            
            # Sample round details
            sample_round = TechnicalEvaluationRound.objects.first()
            self.stdout.write(f'  Sample Round:')
            self.stdout.write(f'    ID: {sample_round.id}')
            self.stdout.write(f'    Assignment Status: {sample_round.assignment_status}')
            self.stdout.write(f'    Overall Decision: {sample_round.overall_decision}')
            self.stdout.write(f'    Cached Assigned Count: {sample_round.cached_assigned_count}')
            self.stdout.write(f'    Cached Completed Count: {sample_round.cached_completed_count}')
            
            if sample_round.proposal:
                self.stdout.write(f'    Proposal ID: {sample_round.proposal.proposal_id}')
                self.stdout.write(f'    Proposal Subject: {sample_round.proposal.subject}')
        
        # 3. Check EvaluatorAssignments
        self.stdout.write('\n3. EvaluatorAssignment Data:')
        total_assignments = EvaluatorAssignment.objects.count()
        completed_assignments = EvaluatorAssignment.objects.filter(is_completed=True).count()
        
        self.stdout.write(f'  Total Assignments: {total_assignments}')
        self.stdout.write(f'  Completed Assignments: {completed_assignments}')
        
        # 4. Check what the API would return
        self.stdout.write('\n4. API Filter Analysis:')
        
        # Pending tab filter
        pending_rounds = TechnicalEvaluationRound.objects.filter(
            assignment_status='pending'
        ).count()
        self.stdout.write(f'  Pending tab would show: {pending_rounds} rounds')
        
        # Assigned tab filter  
        assigned_rounds = TechnicalEvaluationRound.objects.filter(
            assignment_status='assigned'
        ).count()
        self.stdout.write(f'  Assigned tab would show: {assigned_rounds} rounds')
        
        # Evaluated tab filter (what you're looking at)
        evaluated_rounds = TechnicalEvaluationRound.objects.filter(
            assignment_status='completed',
            overall_decision__in=['recommended', 'not_recommended']
        ).count()
        self.stdout.write(f'  Evaluated tab would show: {evaluated_rounds} rounds')
        
        # 5. Suggest actions
        self.stdout.write('\n5. Suggested Actions:')
        
        if total_rounds == 0:
            self.stdout.write('  ❌ No TechnicalEvaluationRounds found!')
            self.stdout.write('  ➡️  You need to create evaluation rounds for your FormSubmissions')
            self.stdout.write('  ➡️  Run: python manage.py create_evaluation_rounds')
        
        elif pending_rounds > 0:
            self.stdout.write(f'  ✅ You have {pending_rounds} pending rounds')
            self.stdout.write('  ➡️  Check the "Pending" tab instead of "Evaluated"')
            self.stdout.write('  ➡️  Assign evaluators to move them to "Assigned" status')
        
        elif assigned_rounds > 0:
            self.stdout.write(f'  ✅ You have {assigned_rounds} assigned rounds')  
            self.stdout.write('  ➡️  Check the "Assigned" tab instead of "Evaluated"')
            self.stdout.write('  ➡️  Complete evaluations to move them to "Evaluated" status')
        
        elif evaluated_rounds == 0 and total_rounds > 0:
            self.stdout.write('  ⚠️  You have evaluation rounds but none are completed yet')
            self.stdout.write('  ➡️  Complete the evaluation process to see data in "Evaluated" tab')
        
        # 6. Sample API call simulation
        self.stdout.write('\n6. API Response Preview:')
        try:
            from tech_eval.views import TechnicalEvaluationRoundViewSet
            from django.test import RequestFactory
            from django.contrib.auth import get_user_model
            
            User = get_user_model()
            
            # Try to get a superuser for testing
            admin_user = User.objects.filter(is_superuser=True).first()
            if admin_user:
                factory = RequestFactory()
                request = factory.get('/api/tech-eval/technical-evaluations/admin-list/')
                request.user = admin_user
                
                viewset = TechnicalEvaluationRoundViewSet()
                viewset.request = request
                
                # Get first few rounds
                queryset = viewset.get_queryset()[:3]
                serialized = viewset._lightning_fast_serialize(queryset)
                
                self.stdout.write(f'  API would return {len(serialized)} items')
                if serialized:
                    sample = serialized[0]
                    self.stdout.write(f'  Sample item:')
                    self.stdout.write(f'    Proposal ID: {sample.get("proposal_id")}')
                    self.stdout.write(f'    Assignment Status: {sample.get("assignment_status")}')
                    self.stdout.write(f'    Overall Decision: {sample.get("overall_decision")}')
            else:
                self.stdout.write('  ⚠️  No superuser found for API testing')
                
        except Exception as e:
            self.stdout.write(f'  ⚠️  API test failed: {e}')
        
        self.stdout.write('\n' + '='*50)
        self.stdout.write('Debug complete! Check the suggestions above.')