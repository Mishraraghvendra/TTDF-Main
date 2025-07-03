# management/commands/debug_categorization.py
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from dynamic_form.models import FormSubmission
from applicant_dashboard.models import DashboardStats

User = get_user_model()

class Command(BaseCommand):
    help = 'Debug and fix proposal categorization discrepancies'

    def add_arguments(self, parser):
        parser.add_argument(
            '--proposal-id',
            type=str,
            help='Specific proposal ID to debug',
        )
        parser.add_argument(
            '--user-email',
            type=str,
            help='User email to debug their proposals',
        )
        parser.add_argument(
            '--fix-all-users',
            action='store_true',
            help='Fix categorization for all users in the system',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be changed without making actual changes',
        )

    def handle(self, *args, **options):
        if options['fix_all_users']:
            self.fix_all_users(dry_run=options['dry_run'])
        elif options['proposal_id']:
            self.debug_single_proposal(options['proposal_id'])
        elif options['user_email']:
            self.debug_user_proposals(options['user_email'])
        else:
            self.stdout.write(
                self.style.ERROR('Please provide either --proposal-id, --user-email, or --fix-all-users')
            )

    def fix_all_users(self, dry_run=False):
        """Fix categorization for all users in the system"""
        # Get all users who have submitted proposals - FIXED FIELD NAME
        users_with_proposals = User.objects.filter(
            form_submissions__isnull=False
        ).distinct()
        
        total_users = users_with_proposals.count()
        self.stdout.write(f"\n=== FIXING CATEGORIZATION FOR ALL USERS ===")
        self.stdout.write(f"Found {total_users} users with proposals")
        
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN - No changes will be made"))
        
        updated_count = 0
        error_count = 0
        
        for i, user in enumerate(users_with_proposals, 1):
            try:
                self.stdout.write(f"\n[{i}/{total_users}] Processing user: {user.email}")
                
                # Get current stats
                old_stats = self.get_user_stats_summary(user)
                
                if not dry_run:
                    # Refresh stats using new logic
                    stats, created = DashboardStats.objects.get_or_create(user=user)
                    stats.refresh_stats()
                    new_stats = self.get_user_stats_summary(user)
                else:
                    # Simulate new stats
                    new_stats = self.calculate_new_stats(user)
                
                # Show changes
                if old_stats != new_stats:
                    self.stdout.write(self.style.SUCCESS(f"  📊 STATS CHANGED:"))
                    self.stdout.write(f"     OLD: {old_stats}")
                    self.stdout.write(f"     NEW: {new_stats}")
                    if not dry_run:
                        updated_count += 1
                else:
                    self.stdout.write(f"  ✅ No changes needed")
                
                # Show individual proposals if there were changes
                if old_stats != new_stats:
                    proposals = FormSubmission.objects.filter(applicant=user).exclude(status=FormSubmission.DRAFT)
                    for proposal in proposals:
                        proposal_id = proposal.proposal_id or proposal.form_id
                        category = self.categorize_proposal(proposal)
                        self.stdout.write(f"     - {proposal_id}: {category}")
                
            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(f"  ❌ Error processing {user.email}: {str(e)}")
                )
        
        # Final summary
        self.stdout.write(f"\n=== SUMMARY ===")
        if not dry_run:
            self.stdout.write(f"✅ Successfully updated: {updated_count} users")
        else:
            self.stdout.write(f"📊 Would update: {updated_count} users")
        
        if error_count > 0:
            self.stdout.write(f"❌ Errors encountered: {error_count} users")
        
        self.stdout.write(f"🔍 Total users processed: {total_users}")

    def get_user_stats_summary(self, user):
        """Get current dashboard stats for a user"""
        try:
            stats = DashboardStats.objects.get(user=user)
            return f"T:{stats.total_proposals} A:{stats.approved_proposals} E:{stats.under_evaluation} N:{stats.not_shortlisted}"
        except DashboardStats.DoesNotExist:
            return "T:0 A:0 E:0 N:0"

    def calculate_new_stats(self, user):
        """Calculate what the new stats would be"""
        proposals = FormSubmission.objects.filter(applicant=user).exclude(status=FormSubmission.DRAFT)
        
        total = proposals.count()
        approved = 0
        under_eval = 0
        not_shortlisted = 0
        
        for proposal in proposals:
            category = self.categorize_proposal(proposal)
            
            if category == 'Approved':
                approved += 1
            elif category in ['Evaluation', 'Interview']:
                under_eval += 1
            elif category == 'Not Shortlisted':
                not_shortlisted += 1
        
        return f"T:{total} A:{approved} E:{under_eval} N:{not_shortlisted}"

    def debug_single_proposal(self, proposal_id):
        """Debug a single proposal"""
        try:
            proposal = FormSubmission.objects.get(proposal_id=proposal_id)
            self.stdout.write(f"\n=== DEBUGGING PROPOSAL {proposal_id} ===")
            
            # Check workflow state
            self.analyze_proposal_workflow(proposal)
            
            # Test categorization
            category = self.categorize_proposal(proposal)
            self.stdout.write(f"📊 CATEGORIZATION RESULT: {category}")
            
            # Check dashboard stats
            if proposal.applicant:
                old_stats = self.get_user_stats_summary(proposal.applicant)
                stats, created = DashboardStats.objects.get_or_create(user=proposal.applicant)
                stats.refresh_stats()
                new_stats = self.get_user_stats_summary(proposal.applicant)
                
                self.stdout.write(f"📈 DASHBOARD STATS:")
                if old_stats != new_stats:
                    self.stdout.write(f"   OLD: {old_stats}")
                    self.stdout.write(f"   NEW: {new_stats}")
                else:
                    self.stdout.write(f"   {new_stats} (no change)")
                
        except FormSubmission.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'Proposal {proposal_id} not found')
            )

    def debug_user_proposals(self, user_email):
        """Debug all proposals for a user"""
        try:
            user = User.objects.get(email=user_email)
            proposals = FormSubmission.objects.filter(applicant=user).exclude(status=FormSubmission.DRAFT)
            
            self.stdout.write(f"\n=== DEBUGGING USER {user_email} ===")
            self.stdout.write(f"Found {proposals.count()} proposals")
            
            for proposal in proposals:
                proposal_id = proposal.proposal_id or proposal.form_id
                category = self.categorize_proposal(proposal)
                self.stdout.write(f"  {proposal_id}: {category}")
            
            # Show stats before and after refresh
            old_stats = self.get_user_stats_summary(user)
            stats, created = DashboardStats.objects.get_or_create(user=user)
            stats.refresh_stats()
            new_stats = self.get_user_stats_summary(user)
            
            self.stdout.write(f"\n📈 DASHBOARD STATS:")
            if old_stats != new_stats:
                self.stdout.write(f"   OLD: {old_stats}")
                self.stdout.write(f"   NEW: {new_stats}")
            else:
                self.stdout.write(f"   {new_stats} (no change)")
                
        except User.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'User {user_email} not found')
            )

    def analyze_proposal_workflow(self, proposal):
        """Analyze the workflow state of a proposal"""
        self.stdout.write(f"🔍 WORKFLOW ANALYSIS:")
        self.stdout.write(f"   FormSubmission Status: {proposal.status}")
        
        # Check screening
        latest_screening = proposal.screening_records.order_by('-cycle').first()
        if latest_screening:
            self.stdout.write(f"   Admin Screening: {latest_screening.admin_decision}")
            
            tech_record = getattr(latest_screening, 'technical_record', None)
            if tech_record:
                self.stdout.write(f"   Technical Screening: {tech_record.technical_decision}")
            else:
                self.stdout.write(f"   Technical Screening: None")
        else:
            self.stdout.write(f"   Screening: None")
        
        # Check technical evaluation
        tech_eval = proposal.technical_evaluation_rounds.first()
        if tech_eval:
            self.stdout.write(f"   Tech Eval Status: {tech_eval.assignment_status}")
            self.stdout.write(f"   Tech Eval Decision: {tech_eval.overall_decision}")
        else:
            self.stdout.write(f"   Technical Evaluation: None")
        
        # Check presentation
        presentation = proposal.presentations.first()
        if presentation:
            self.stdout.write(f"   Presentation Decision: {presentation.final_decision}")
            self.stdout.write(f"   Evaluator: {presentation.evaluator}")
            self.stdout.write(f"   Admin: {presentation.admin}")
        else:
            self.stdout.write(f"   Presentation: None")

    def categorize_proposal(self, proposal):
        """Use the same categorization logic as the views"""
        # Get workflow records
        latest_screening = proposal.screening_records.order_by('-cycle').first()
        tech_eval = proposal.technical_evaluation_rounds.first()
        presentation = proposal.presentations.first()

        # PRIORITY 1: Check presentation final_decision first (if exists)
        if presentation:
            if presentation.final_decision == 'shortlisted':
                return 'Approved'
            elif presentation.final_decision in ['not_shortlisted', 'rejected']:
                return 'Not Shortlisted'
            elif presentation.final_decision in ['pending', 'assigned', 'evaluated']:
                return 'Interview'

        # PRIORITY 2: Check FormSubmission status for definitive states
        if proposal.status == FormSubmission.APPROVED:
            return 'Approved'
        elif proposal.status == FormSubmission.REJECTED:
            return 'Not Shortlisted'

        # PRIORITY 3: For SUBMITTED status, follow the workflow logic
        if proposal.status == FormSubmission.SUBMITTED:
            # Check if we have any screening
            if not latest_screening:
                return 'Submitted'
            
            # Check admin screening decision
            if latest_screening.admin_decision == 'pending':
                return 'Submitted'
            elif latest_screening.admin_decision == 'not shortlisted':
                return 'Not Shortlisted'
            elif latest_screening.admin_decision == 'shortlisted':
                # Check technical screening
                tech_record = getattr(latest_screening, 'technical_record', None)
                if not tech_record:
                    return 'Screening'
                
                if tech_record.technical_decision == 'pending':
                    return 'Screening'
                elif tech_record.technical_decision == 'not shortlisted':
                    return 'Not Shortlisted'
                elif tech_record.technical_decision == 'shortlisted':
                    # Check technical evaluation
                    if not tech_eval:
                        return 'Evaluation'
                    
                    if tech_eval.assignment_status == 'pending':
                        return 'Evaluation'
                    elif tech_eval.assignment_status == 'assigned':
                        return 'Evaluation'
                    elif tech_eval.assignment_status == 'completed':
                        if tech_eval.overall_decision == 'recommended':
                            # Should have presentation at this point
                            if not presentation:
                                return 'Interview'  # Waiting for presentation creation
                            # Presentation cases handled in PRIORITY 1 above
                            return 'Interview'
                        elif tech_eval.overall_decision == 'not_recommended':
                            return 'Not Shortlisted'
                        else:  # pending
                            return 'Evaluation'
                    else:
                        return 'Evaluation'
                else:
                    return 'Not Shortlisted'
            else:
                return 'Not Shortlisted'
        
        # Default case
        return 'History'