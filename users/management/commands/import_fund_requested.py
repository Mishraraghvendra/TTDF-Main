import csv
from django.core.management.base import BaseCommand

def normalize_header(header):
    return header.strip().lower().replace(' ', '_').replace('\ufeff', '')

class Command(BaseCommand):
    help = 'Update funds_requested on FormSubmission from CSV. No Milestone, Presentation, or TechnicalEvaluationRound logic.'

    def add_arguments(self, parser):
        parser.add_argument('csv_path', type=str, help='Path to the CSV file to import')

    def handle(self, *args, **options):
        from dynamic_form.models import FormSubmission

        csv_path = options['csv_path']
        with open(csv_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            header_map = {normalize_header(col): col for col in reader.fieldnames}

            def val(row, name, default=''):
                raw = row.get(header_map.get(normalize_header(name)), default)
                if raw is None:
                    return default
                return str(raw).strip()

            def val_int(row, name, default=0):
                try:
                    return int(float(val(row, name, default)))
                except (ValueError, TypeError):
                    return default

            for idx, row in enumerate(reader, start=1):
                proposal_id = val(row, 'ID') or val(row, 'proposal_id') or val(row, 'id') or val(row, 'Proposal ID')
                if not proposal_id:
                    print(f"[Row {idx}] Skipping: no proposal_id found")
                    continue

                try:
                    proposal = FormSubmission.objects.get(proposal_id=proposal_id)
                except FormSubmission.DoesNotExist:
                    print(f"[Row {idx}] No proposal found for proposal_id {proposal_id}")
                    continue

                csv_funds_requested = val_int(row, 'Funds Requested', 0)
                print(f"[Row {idx}] Proposal {proposal_id}: funds_requested BEFORE = {proposal.funds_requested}, CSV = {csv_funds_requested}")
                proposal.funds_requested = csv_funds_requested
                proposal.save(update_fields=['funds_requested'])
                proposal.refresh_from_db()
                print(f"[Row {idx}] Proposal {proposal_id}: funds_requested AFTER = {proposal.funds_requested}")

        print("Import completed!")
