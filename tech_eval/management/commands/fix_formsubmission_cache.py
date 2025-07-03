# tech_eval/management/commands/fix_formsubmission_cache.py

from django.core.management.base import BaseCommand
from tech_eval.models import TechnicalEvaluationRound
from django.db import transaction
import time

class Command(BaseCommand):
    help = 'Fix FormSubmission field mapping in cached proposal data using actual model fields'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--batch-size',
            type=int,
            default=50,
            help='Batch size for processing'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed output'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force update all cached proposal data (even if already exists)'
        )
        parser.add_argument(
            '--analyze-only',
            action='store_true',
            help='Only analyze FormSubmission structure without updating'
        )
    
    def handle(self, *args, **options):
        batch_size = options['batch_size']
        verbose = options['verbose']
        force = options['force']
        analyze_only = options['analyze_only']
        
        start_time = time.time()
        
        self.stdout.write("=== FIXING FORMSUBMISSION CACHE MAPPING ===")
        
        if analyze_only:
            self.analyze_formsubmission_structure()
            return
        
        # Find rounds that need updating
        if force:
            # Update all rounds with proposals
            rounds_to_update = TechnicalEvaluationRound.objects.filter(
                proposal__isnull=False
            )
            self.stdout.write("Force mode: updating ALL rounds with proposals")
        else:
            # Only update rounds with missing cached data
            rounds_to_update = TechnicalEvaluationRound.objects.filter(
                proposal__isnull=False,
                cached_proposal_data__isnull=True
            )
        
        total_count = rounds_to_update.count()
        self.stdout.write(f"Found {total_count} rounds to update")
        
        if total_count == 0:
            self.stdout.write("No rounds need updating!")
            return
        
        fixed_count = 0
        error_count = 0
        
        # Process in batches
        for i in range(0, total_count, batch_size):
            batch = rounds_to_update[i:i + batch_size]
            
            with transaction.atomic():
                for eval_round in batch:
                    try:
                        self.fix_round_proposal_cache(eval_round, verbose)
                        fixed_count += 1
                        
                        if verbose:
                            proposal_id = self._safe_get_proposal_id(eval_round)
                            self.stdout.write(f"  ✓ Fixed {proposal_id}")
                        
                    except Exception as e:
                        error_count += 1
                        proposal_id = self._safe_get_proposal_id(eval_round)
                        self.stdout.write(f"  ✗ Error fixing {proposal_id}: {e}")
            
            # Show progress
            progress = min(i + batch_size, total_count)
            self.stdout.write(f"Progress: {progress}/{total_count} rounds processed")
        
        elapsed = time.time() - start_time
        self.stdout.write(f"\n✓ Fixed {fixed_count}/{total_count} rounds in {elapsed:.2f} seconds")
        if error_count > 0:
            self.stdout.write(f"⚠ {error_count} errors occurred")
        
        # Verify the fix
        self.verify_fix()
    
    def analyze_formsubmission_structure(self):
        """Analyze FormSubmission model structure"""
        self.stdout.write("=== ANALYZING FORMSUBMISSION MODEL ===")
        
        # Get sample of evaluation rounds with proposals
        sample_rounds = TechnicalEvaluationRound.objects.filter(
            proposal__isnull=False
        ).select_related('proposal', 'proposal__applicant', 'proposal__service')[:5]
        
        if not sample_rounds.exists():
            self.stdout.write("No evaluation rounds with proposals found!")
            return
        
        # Get FormSubmission model fields
        first_proposal = sample_rounds.first().proposal
        model_fields = []
        for field in first_proposal._meta.fields:
            field_info = {
                'name': field.name,
                'type': field.__class__.__name__,
                'null': field.null,
                'blank': field.blank,
            }
            model_fields.append(field_info)
        
        self.stdout.write(f"\n--- FORMSUBMISSION MODEL FIELDS ({len(model_fields)}) ---")
        for field in model_fields:
            self.stdout.write(f"  {field['name']}: {field['type']} (null={field['null']}, blank={field['blank']})")
        
        # Show field mapping
        self.stdout.write(f"\n--- FIELD MAPPING STRATEGY ---")
        self.stdout.write("✓ subject: FormSubmission.subject")
        self.stdout.write("✓ description: FormSubmission.description") 
        self.stdout.write("✓ org_type: FormSubmission.org_type")
        self.stdout.write("✓ org_name: FormSubmission.org_address_line1")
        self.stdout.write("✓ contact_person: User.full_name OR FormSubmission.contact_name")
        self.stdout.write("✓ contact_email: User.email OR FormSubmission.contact_email")
        self.stdout.write("✓ contact_phone: FormSubmission.org_mobile")
        self.stdout.write("✓ current_trl: FormSubmission.current_trl")
        self.stdout.write("✓ call_name: Service.name")
        
        # Show sample data
        self.stdout.write(f"\n--- SAMPLE DATA FROM {len(sample_rounds)} PROPOSALS ---")
        for i, eval_round in enumerate(sample_rounds, 1):
            proposal = eval_round.proposal
            proposal_id = getattr(proposal, 'proposal_id', f'ID-{eval_round.id}')
            
            self.stdout.write(f"\n--- PROPOSAL {i}: {proposal_id} ---")
            
            # Show key field values
            key_fields = {
                'subject': getattr(proposal, 'subject', None),
                'description': getattr(proposal, 'description', None),
                'org_type': getattr(proposal, 'org_type', None),
                'org_address_line1': getattr(proposal, 'org_address_line1', None),
                'contact_name': getattr(proposal, 'contact_name', None),
                'contact_email': getattr(proposal, 'contact_email', None),
                'org_mobile': getattr(proposal, 'org_mobile', None),
                'current_trl': getattr(proposal, 'current_trl', None),
            }
            
            for field, value in key_fields.items():
                display_value = str(value)[:50] + ('...' if len(str(value)) > 50 else '') if value else 'None'
                self.stdout.write(f"  {field}: {display_value}")
            
            # Show User fields
            if proposal.applicant:
                self.stdout.write(f"  User.full_name: {getattr(proposal.applicant, 'full_name', 'None')}")
                self.stdout.write(f"  User.email: {getattr(proposal.applicant, 'email', 'None')}")
                self.stdout.write(f"  User.organization: {getattr(proposal.applicant, 'organization', 'None')}")
            
            # Show Service name
            if proposal.service:
                self.stdout.write(f"  Service.name: {getattr(proposal.service, 'name', 'None')}")
    
    def _safe_get_proposal_id(self, eval_round):
        """Safely get proposal ID"""
        try:
            if eval_round.proposal:
                return getattr(eval_round.proposal, 'proposal_id', f'ID-{eval_round.id}')
            return f'ID-{eval_round.id}'
        except:
            return f'ID-{eval_round.id}'
    
    def _safe_get_field(self, obj, field_name, default='N/A'):
        """Safely get field value with proper handling"""
        try:
            value = getattr(obj, field_name, None)
            if value is None or value == '':
                return default
            return str(value).strip()
        except Exception:
            return default
    
    def fix_round_proposal_cache(self, eval_round, verbose=False):
        """Fix the proposal cache for a specific round using FormSubmission fields"""
        
        proposal = eval_round.proposal
        if not proposal:
            if verbose:
                self.stdout.write(f"    No proposal found for round {eval_round.id}")
            return
        
        # Get applicant data safely
        applicant = proposal.applicant if proposal.applicant else None
        applicant_name = 'N/A'
        applicant_email = 'N/A'
        applicant_org = 'N/A'
        
        if applicant:
            # User model has full_name field
            applicant_name = self._safe_get_field(applicant, 'full_name')
            applicant_email = self._safe_get_field(applicant, 'email')
            applicant_org = self._safe_get_field(applicant, 'organization')
        
        # Get service name
        service_name = 'N/A'
        if proposal.service:
            service_name = self._safe_get_field(proposal.service, 'name')
        
        # Build proposal data using actual FormSubmission fields
        proposal_data = {
            'proposal_id': self._safe_get_field(proposal, 'proposal_id'),
            'call': service_name,
            'org_type': self._safe_get_field(proposal, 'org_type'),
            'subject': self._safe_get_field(proposal, 'subject'),
            'description': self._safe_get_field(proposal, 'description'),
            
            # Organization name: try multiple sources
            'org_name': (
                applicant_org if applicant_org != 'N/A' else 
                self._safe_get_field(proposal, 'org_address_line1')
            ),
            
            # Contact person: prefer User.full_name, fallback to FormSubmission.contact_name
            'contact_person': (
                applicant_name if applicant_name != 'N/A' else 
                self._safe_get_field(proposal, 'contact_name')
            ),
            
            # Contact email: prefer User.email, fallback to FormSubmission.contact_email
            'contact_email': (
                applicant_email if applicant_email != 'N/A' else 
                self._safe_get_field(proposal, 'contact_email')
            ),
            
            # Contact phone: from FormSubmission
            'contact_phone': self._safe_get_field(proposal, 'org_mobile'),
            
            # Additional fields
            'current_trl': self._safe_get_field(proposal, 'current_trl'),
            'abstract': self._safe_get_field(proposal, 'abstract'),
            'technical_feasibility': self._safe_get_field(proposal, 'technical_feasibility'),
            'potential_impact': self._safe_get_field(proposal, 'potential_impact'),
            'commercialization_strategy': self._safe_get_field(proposal, 'commercialization_strategy'),
            'applicant_type': self._safe_get_field(proposal, 'applicant_type'),
            'grants_from_ttdf': self._safe_get_field(proposal, 'grants_from_ttdf'),
            'created_at': proposal.created_at.isoformat() if hasattr(proposal, 'created_at') and proposal.created_at else None,
        }
        
        # Update the evaluation round
        eval_round.cached_proposal_data = proposal_data
        eval_round.cache_updated_at = time.time()
        
        # Save with specific fields to avoid triggering signals
        eval_round.save(update_fields=['cached_proposal_data', 'cache_updated_at'])
        
        if verbose:
            subject = proposal_data.get('subject', 'N/A')[:50]
            org_name = proposal_data.get('org_name', 'N/A')[:30] 
            contact_person = proposal_data.get('contact_person', 'N/A')[:30]
            self.stdout.write(f"    Updated: {subject} | {org_name} | {contact_person}")
    
    def verify_fix(self):
        """Verify that the fix worked"""
        self.stdout.write("\n=== VERIFICATION ===")
        
        # Count rounds with cached proposal data
        with_cached_data = TechnicalEvaluationRound.objects.exclude(
            cached_proposal_data__isnull=True
        ).count()
        
        # Count rounds with proposals but missing cache
        missing_cache = TechnicalEvaluationRound.objects.filter(
            proposal__isnull=False,
            cached_proposal_data__isnull=True
        ).count()
        
        total_with_proposals = TechnicalEvaluationRound.objects.filter(
            proposal__isnull=False
        ).count()
        
        self.stdout.write(f"Total rounds with proposals: {total_with_proposals}")
        self.stdout.write(f"Rounds with cached proposal data: {with_cached_data}")
        self.stdout.write(f"Still missing cached data: {missing_cache}")
        
        # Calculate completion percentage
        if total_with_proposals > 0:
            completion_rate = (with_cached_data / total_with_proposals) * 100
            self.stdout.write(f"Cache completion rate: {completion_rate:.1f}%")
        
        if missing_cache == 0:
            self.stdout.write(self.style.SUCCESS("✓ All proposal cache data fixed!"))
        else:
            self.stdout.write(self.style.WARNING(f"⚠ {missing_cache} rounds still need fixing"))
        
        # Show sample of fixed data
        sample_round = TechnicalEvaluationRound.objects.exclude(
            cached_proposal_data__isnull=True
        ).first()
        
        if sample_round and sample_round.cached_proposal_data:
            self.stdout.write(f"\nSample fixed proposal data:")
            proposal_sample = sample_round.cached_proposal_data
            for key, value in proposal_sample.items():
                display_value = str(value)[:50] + ('...' if len(str(value)) > 50 else '')
                self.stdout.write(f"  {key}: {display_value}")
        
        # Check field completeness
        self.check_field_completeness()
    
    def check_field_completeness(self):
        """Check how many records have valid values for each field"""
        self.stdout.write(f"\n=== FIELD COMPLETENESS ANALYSIS ===")
        
        rounds_with_cache = TechnicalEvaluationRound.objects.exclude(
            cached_proposal_data__isnull=True
        )
        
        total_count = rounds_with_cache.count()
        if total_count == 0:
            self.stdout.write("No cached data to analyze")
            return
        
        field_stats = {}
        key_fields = ['subject', 'org_name', 'contact_person', 'contact_email', 'org_type']
        
        for round_obj in rounds_with_cache:
            proposal_data = round_obj.cached_proposal_data
            if not proposal_data:
                continue
            
            for field in key_fields:
                if field not in field_stats:
                    field_stats[field] = {'valid': 0, 'missing': 0}
                
                value = proposal_data.get(field, 'N/A')
                if value and value not in ['N/A', 'null', '', None]:
                    field_stats[field]['valid'] += 1
                else:
                    field_stats[field]['missing'] += 1
        
        self.stdout.write(f"Analysis of {total_count} cached records:")
        for field, stats in field_stats.items():
            valid_pct = (stats['valid'] / total_count) * 100 if total_count > 0 else 0
            status_icon = "✓" if valid_pct > 80 else "⚠" if valid_pct > 50 else "✗"
            self.stdout.write(f"  {status_icon} {field}: {stats['valid']}/{total_count} ({valid_pct:.1f}%) valid")
        
        # Show sample of problematic records
        self.stdout.write(f"\nSample of records with missing key fields:")
        problematic_count = 0
        for round_obj in rounds_with_cache[:10]:  # Check first 10
            proposal_data = round_obj.cached_proposal_data or {}
            missing_fields = []
            
            for field in key_fields:
                value = proposal_data.get(field, 'N/A')
                if not value or value in ['N/A', 'null', '', None]:
                    missing_fields.append(field)
            
            if len(missing_fields) > 2:  # More than 2 missing fields
                proposal_id = self._safe_get_proposal_id(round_obj)
                self.stdout.write(f"  {proposal_id}: missing {missing_fields}")
                problematic_count += 1
        
        if problematic_count == 0:
            self.stdout.write("  No significantly problematic records found!")
        
        # Show field sources for debugging
        self.stdout.write(f"\n=== FIELD SOURCE MAPPING ===")
        self.stdout.write("subject: FormSubmission.subject")
        self.stdout.write("org_type: FormSubmission.org_type") 
        self.stdout.write("org_name: User.organization OR FormSubmission.org_address_line1")
        self.stdout.write("contact_person: User.full_name OR FormSubmission.contact_name")
        self.stdout.write("contact_email: User.email OR FormSubmission.contact_email")
        self.stdout.write("contact_phone: FormSubmission.org_mobile")
        self.stdout.write("description: FormSubmission.description")
        self.stdout.write("current_trl: FormSubmission.current_trl")
        self.stdout.write("call: Service.name")