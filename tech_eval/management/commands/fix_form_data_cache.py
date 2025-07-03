# tech_eval/management/commands/fix_form_data_cache.py

from django.core.management.base import BaseCommand
from tech_eval.models import TechnicalEvaluationRound
from django.db import transaction
import json
import time

class Command(BaseCommand):
    help = 'Fix FormSubmission field mapping in cached proposal data'
    
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
            help='Only analyze form_data structure without updating'
        )
    
    def handle(self, *args, **options):
        batch_size = options['batch_size']
        verbose = options['verbose']
        force = options['force']
        analyze_only = options['analyze_only']
        
        start_time = time.time()
        
        self.stdout.write("=== FIXING FORM DATA CACHE MAPPING ===")
        
        if analyze_only:
            self.analyze_form_data_structure()
            return
        
        # Find rounds that need updating
        if force:
            # Update all rounds with proposals
            rounds_to_update = TechnicalEvaluationRound.objects.filter(
                proposal__isnull=False
            )
            self.stdout.write("Force mode: updating ALL rounds with proposals")
        else:
            # Only update rounds with missing or incorrect cached data
            rounds_to_update = TechnicalEvaluationRound.objects.filter(
                proposal__isnull=False
            ).filter(
                # Missing cached_proposal_data OR cached data doesn't have correct fields
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
    
    def analyze_form_data_structure(self):
        """Analyze FormSubmission form_data structure to understand the schema"""
        self.stdout.write("=== ANALYZING FORM DATA STRUCTURE ===")
        
        # Get sample of evaluation rounds with proposals
        sample_rounds = TechnicalEvaluationRound.objects.filter(
            proposal__isnull=False
        ).select_related('proposal', 'proposal__applicant', 'proposal__service')[:10]
        
        field_patterns = {}
        user_fields = set()
        service_fields = set()
        
        for eval_round in sample_rounds:
            proposal = eval_round.proposal
            if not proposal:
                continue
            
            # Analyze form_data
            form_data = getattr(proposal, 'form_data', {})
            if form_data:
                try:
                    if isinstance(form_data, str):
                        data = json.loads(form_data)
                    else:
                        data = form_data
                    
                    if isinstance(data, dict):
                        for key, value in data.items():
                            if key not in field_patterns:
                                field_patterns[key] = []
                            field_patterns[key].append(str(value)[:50] if value else 'None')
                except Exception as e:
                    self.stdout.write(f"Error parsing form_data: {e}")
            
            # Analyze User fields
            if proposal.applicant:
                for field in proposal.applicant._meta.fields:
                    user_fields.add(field.name)
            
            # Analyze Service fields
            if proposal.service:
                for field in proposal.service._meta.fields:
                    service_fields.add(field.name)
        
        # Display analysis
        self.stdout.write("\n--- FORM DATA FIELDS FOUND ---")
        for field, samples in sorted(field_patterns.items()):
            unique_samples = list(set(samples))[:3]  # Show max 3 unique samples
            self.stdout.write(f"{field}: {unique_samples}")
        
        self.stdout.write(f"\n--- USER MODEL FIELDS ({len(user_fields)}) ---")
        self.stdout.write(f"{', '.join(sorted(user_fields))}")
        
        self.stdout.write(f"\n--- SERVICE MODEL FIELDS ({len(service_fields)}) ---")
        self.stdout.write(f"{', '.join(sorted(service_fields))}")
        
        # Suggest field mappings
        self.suggest_field_mappings(field_patterns)
    
    def suggest_field_mappings(self, field_patterns):
        """Suggest field mappings based on found form_data fields"""
        self.stdout.write("\n--- SUGGESTED FIELD MAPPINGS ---")
        
        # Define what we're looking for
        target_fields = {
            'subject': ['project_title', 'title', 'subject', 'project_name', 'proposal_title'],
            'description': ['project_description', 'description', 'abstract', 'project_summary', 'project_details'],
            'org_type': ['organization_type', 'org_type', 'orgType', 'applicant_type', 'entity_type'],
            'org_name': ['organization_name', 'org_name', 'orgName', 'company_name', 'institution_name'],
            'contact_person': ['contact_person', 'principal_investigator', 'pi_name', 'applicant_name', 'contact_name'],
            'contact_email': ['contact_email', 'email', 'pi_email', 'applicant_email', 'principal_email'],
            'contact_phone': ['contact_phone', 'phone', 'mobile', 'pi_phone', 'contact_mobile'],
            'funds_requested': ['funds_requested', 'funding_amount', 'budget', 'total_cost', 'requested_amount'],
            'current_trl': ['current_trl', 'trl_level', 'technology_readiness', 'trl_current'],
        }
        
        found_mappings = {}
        
        for target, possible_keys in target_fields.items():
            matches = []
            for key in field_patterns.keys():
                if key.lower() in [pk.lower() for pk in possible_keys]:
                    matches.append(key)
            
            if matches:
                found_mappings[target] = matches[0]  # Take first match
                self.stdout.write(f"✓ {target}: {matches[0]} (alternatives: {matches[1:] if len(matches) > 1 else 'none'})")
            else:
                # Look for partial matches
                partial_matches = []
                for key in field_patterns.keys():
                    for pk in possible_keys:
                        if pk.lower() in key.lower() or key.lower() in pk.lower():
                            partial_matches.append(key)
                
                if partial_matches:
                    found_mappings[target] = partial_matches[0]
                    self.stdout.write(f"? {target}: {partial_matches[0]} (partial match)")
                else:
                    self.stdout.write(f"✗ {target}: NOT FOUND")
        
        return found_mappings
    
    def _parse_form_data(self, form_data, field_name, default='N/A'):
        """Parse form_data JSON to extract specific field"""
        try:
            if not form_data:
                return default
            
            # Parse JSON if it's a string
            if isinstance(form_data, str):
                data = json.loads(form_data)
            else:
                data = form_data
            
            # Map of field names to possible keys in form_data
            field_mapping = {
                'subject': ['project_title', 'title', 'subject', 'project_name', 'proposal_title'],
                'description': ['project_description', 'description', 'abstract', 'project_summary', 'project_details'],
                'org_type': ['organization_type', 'org_type', 'orgType', 'applicant_type', 'entity_type'],
                'org_name': ['organization_name', 'org_name', 'orgName', 'company_name', 'institution_name'],
                'contact_person': ['contact_person', 'principal_investigator', 'pi_name', 'applicant_name', 'contact_name'],
                'contact_email': ['contact_email', 'email', 'pi_email', 'applicant_email', 'principal_email'],
                'contact_phone': ['contact_phone', 'phone', 'mobile', 'pi_phone', 'contact_mobile'],
                'funds_requested': ['funds_requested', 'funding_amount', 'budget', 'total_cost', 'requested_amount'],
                'current_trl': ['current_trl', 'trl_level', 'technology_readiness', 'trl_current'],
                'call_name': ['call_name', 'service_name', 'program_name', 'scheme_name'],
            }
            
            # Try to find the field using different possible keys
            if field_name in field_mapping:
                for key in field_mapping[field_name]:
                    if key in data and data[key] not in [None, '', 'null']:
                        return str(data[key])
            
            # Direct key lookup as fallback
            if field_name in data and data[field_name] not in [None, '', 'null']:
                return str(data[field_name])
            
            return default
            
        except Exception as e:
            return default
    
    def _safe_get_proposal_id(self, eval_round):
        """Safely get proposal ID"""
        try:
            if eval_round.proposal:
                return getattr(eval_round.proposal, 'proposal_id', f'ID-{eval_round.id}')
            return f'ID-{eval_round.id}'
        except:
            return f'ID-{eval_round.id}'
    
    def fix_round_proposal_cache(self, eval_round, verbose=False):
        """Fix the proposal cache for a specific round"""
        
        proposal = eval_round.proposal
        if not proposal:
            if verbose:
                self.stdout.write(f"    No proposal found for round {eval_round.id}")
            return
        
        # Parse form_data for most fields
        form_data = getattr(proposal, 'form_data', {})
        
        # Get applicant data safely
        applicant = proposal.applicant if proposal.applicant else None
        applicant_name = 'N/A'
        applicant_email = 'N/A'
        applicant_org = 'N/A'
        
        if applicant:
            # User model has full_name field (not first_name/last_name)
            applicant_name = getattr(applicant, 'full_name', '').strip()
            if not applicant_name:
                applicant_name = getattr(applicant, 'email', 'N/A')
            
            # Get email
            applicant_email = getattr(applicant, 'email', 'N/A')
            
            # User model has organization field (not organization_name)
            applicant_org = getattr(applicant, 'organization', '').strip()
            if not applicant_org:
                applicant_org = 'N/A'
        
        # Get service name
        service_name = 'N/A'
        if proposal.service:
            service_name = getattr(proposal.service, 'name', 'N/A')
        
        # Build corrected proposal data
        proposal_data = {
            'proposal_id': getattr(proposal, 'proposal_id', 'N/A'),
            'call': service_name or self._parse_form_data(form_data, 'call_name'),
            'org_type': self._parse_form_data(form_data, 'org_type'),
            'subject': self._parse_form_data(form_data, 'subject'),
            'description': self._parse_form_data(form_data, 'description'),
            'org_name': applicant_org if applicant_org != 'N/A' else self._parse_form_data(form_data, 'org_name'),
            'contact_person': applicant_name if applicant_name != 'N/A' else self._parse_form_data(form_data, 'contact_person'),
            'contact_email': applicant_email if applicant_email != 'N/A' else self._parse_form_data(form_data, 'contact_email'),
            'contact_phone': self._parse_form_data(form_data, 'contact_phone'),
            'funds_requested': self._parse_form_data(form_data, 'funds_requested'),
            'current_trl': self._parse_form_data(form_data, 'current_trl'),
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
            self.stdout.write(f"    Updated: {subject} | {org_name}")
    
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
            self.stdout.write(f"\nSample proposal data structure:")
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
        required_fields = ['subject', 'org_name', 'contact_person', 'contact_email', 'org_type']
        
        for round_obj in rounds_with_cache:
            proposal_data = round_obj.cached_proposal_data
            if not proposal_data:
                continue
            
            for field in required_fields:
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
        
        # Show records with most missing data
        self.stdout.write(f"\nRecords with most missing data:")
        problematic_count = 0
        for round_obj in rounds_with_cache[:10]:  # Check first 10
            proposal_data = round_obj.cached_proposal_data or {}
            missing_fields = []
            
            for field in required_fields:
                value = proposal_data.get(field, 'N/A')
                if not value or value in ['N/A', 'null', '', None]:
                    missing_fields.append(field)
            
            if len(missing_fields) > 2:  # More than 2 missing fields
                proposal_id = self._safe_get_proposal_id(round_obj)
                self.stdout.write(f"  {proposal_id}: missing {missing_fields}")
                problematic_count += 1
        
        if problematic_count == 0:
            self.stdout.write("  No significantly problematic records found!")