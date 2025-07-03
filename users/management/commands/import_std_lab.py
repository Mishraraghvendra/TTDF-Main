import csv
import datetime
import uuid

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction

User = get_user_model()

def normalize_header(header):
    return header.strip().lower().replace(' ', '_').replace('\ufeff', '')

class Command(BaseCommand):
    help = 'Import stdlab_part1.csv into FormSubmission and update TechnicalScreeningRecord and ScreeningRecord, setting applicationDocument path from CSV.'

    def add_arguments(self, parser):
        parser.add_argument('csv_path', type=str, help='Path to the CSV file to import')

    @transaction.atomic
    def handle(self, *args, **options):
        from dynamic_form.models import FormSubmission, FormTemplate
        from configuration.models import Service
        from screening.models import ScreeningRecord, TechnicalScreeningRecord

        csv_path = options['csv_path']
        with open(csv_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            header_map = {normalize_header(col): col for col in reader.fieldnames}

            def val(row, name, default=''):
                return row.get(header_map.get(normalize_header(name)), default).strip()

            for row in reader:
                service_name = val(row, 'Service')
                template_title = service_name or 'Default Template'
                org_type      = val(row, 'Organization Type')
                email         = val(row, 'email')
                mobile        = val(row, 'mobile')
                description   = val(row, 'Description')
                subject       = val(row, 'Subject')
                proposal_id   = val(row, 'ID')
                org_name      = val(row, 'Organization Name')
                status        = val(row, 'Status').lower() if val(row, 'Status') else FormSubmission.DRAFT
                proposal_document = val(row, 'Proposal Document')
                submission_date = val(row, 'Submission Date')
                contact_name    = org_name
                shortlisted_raw = val(row, 'Shortlisted', '').strip()
                # The key for applicationDocument in CSV should be exactly as per your CSV file
                csv_application_document = val(row, 'applicationDocument')

                # Ensure applicationDocument path is relative to MEDIA_ROOT
                
                service_folder = service_name.strip().lower().replace(' ', '_') if service_name else "unknown_service"
                if csv_application_document:
                    pdf_filename = csv_application_document.split('/')[-1]
                    application_doc_field = f"pdfs/{service_folder}/{pdf_filename}"
                else:
                    application_doc_field = None

                # --- TEMPLATE CREATION ---
                template, _ = FormTemplate.objects.get_or_create(
                    title=template_title,
                    defaults={
                        'is_active': True,
                        'start_date': datetime.datetime.now(),
                    }
                )

                # --- SERVICE CREATION ---
                service_obj, _ = Service.objects.get_or_create(
                    name=service_name,
                    defaults={
                        'description': f'Auto-created during import',
                        'is_active': True,
                        'created_by': None,
                    }
                )

                # --- USER CREATION/UPDATE ---
                applicant = User.objects.filter(email=email).first()
                unique_mobile = mobile
                if not applicant:
                    # If mobile already exists, append random digits to ensure uniqueness
                    if unique_mobile and User.objects.filter(mobile=unique_mobile).exists():
                        unique_mobile = f"{unique_mobile}{str(uuid.uuid4())[:4]}"
                    if not unique_mobile or User.objects.filter(mobile=unique_mobile).exists():
                        unique_mobile = f"99999{str(uuid.uuid4())[:5]}"
                    safe_email = email or f"{org_name.lower().replace(' ', '_')}@import.local"
                    count = 1
                    email_candidate = safe_email
                    while User.objects.filter(email=email_candidate).exists():
                        email_candidate = f"{safe_email.split('@')[0]}{count}@import.local"
                        count += 1
                    applicant = User.objects.create(
                        email=email_candidate,
                        mobile=unique_mobile,
                        full_name=org_name[:100],
                        gender='O',
                        organization=org_name,
                        is_active=True,
                        is_applicant=True
                    )
                    self.stdout.write(self.style.WARNING(
                        f'Auto-created user for organization "{org_name}" with email {applicant.email} and mobile {unique_mobile}'
                    ))
                else:
                    # Optionally update fields
                    updated = False
                    if not applicant.mobile and mobile:
                        if User.objects.filter(mobile=mobile).exclude(pk=applicant.pk).exists():
                            new_mobile = f"{mobile}{str(uuid.uuid4())[:4]}"
                        else:
                            new_mobile = mobile
                        applicant.mobile = new_mobile
                        updated = True
                    if org_name and not applicant.organization:
                        applicant.organization = org_name
                        updated = True
                    if updated:
                        applicant.save()

                # --- PARSE SUBMISSION DATE ---
                if submission_date:
                    try:
                        submission_dt = datetime.datetime.strptime(submission_date, '%d-%m-%Y')
                    except Exception:
                        submission_dt = None
                else:
                    submission_dt = None

                # --- FORM SUBMISSION CREATION/UPDATE ---
                forms, created = FormSubmission.objects.get_or_create(
                    proposal_id=proposal_id,
                    defaults={
                        'template': template,
                        'service': service_obj,
                        'applicant': applicant,
                        'status': status,
                        'form_id': f'FORM/{datetime.datetime.now().year}/{uuid.uuid4().hex[:6].upper()}',
                        'contact_name': contact_name,
                        'contact_email': email,
                        'applicationDocument': application_doc_field,
                        'subject': subject,
                        'description': description,
                        'org_type': org_type,
                        'is_active': True,
                        'created_at': submission_dt or datetime.datetime.now(),
                        'updated_at': submission_dt or datetime.datetime.now(),
                    }
                )
                # If already exists, update applicationDocument if needed
                if not created and application_doc_field:
                    if forms.applicationDocument != application_doc_field:
                        forms.applicationDocument = application_doc_field
                        forms.save(update_fields=["applicationDocument"])

                # --- SCREENING DECISION LOGIC ---
                if shortlisted_raw == '1':
                    admin_decision = 'shortlisted'
                    technical_decision = 'shortlisted'
                elif shortlisted_raw == '0':
                    admin_decision = 'not shortlisted'
                    technical_decision = 'not shortlisted'
                else:
                    admin_decision = 'pending'
                    technical_decision = 'pending'

                # --- SCREENING RECORD UPDATE OR CREATE ---
                from django.db.models import Max
                screening_record = ScreeningRecord.objects.filter(proposal=forms).order_by('-cycle').first()
                if not screening_record:
                    # Create new ScreeningRecord if none exists
                    last_cycle = ScreeningRecord.objects.filter(proposal=forms).aggregate(max_cycle=Max('cycle'))['max_cycle'] or 0
                    screening_record = ScreeningRecord.objects.create(
                        proposal=forms,
                        cycle=last_cycle + 1,
                        subject=subject,
                        description=description,
                        contact_name=contact_name,
                        contact_email=email,
                        admin_decision=admin_decision,
                        technical_evaluated=True,
                        admin_evaluated=True,
                    )
                    self.stdout.write(self.style.SUCCESS(
                        f"Created ScreeningRecord for {forms.proposal_id}: admin_decision={admin_decision}, admin_evaluated=True, technical_evaluated=True"
                    ))
                else:
                    screening_record.admin_decision = admin_decision
                    screening_record.technical_evaluated = True
                    screening_record.admin_evaluated = True
                    screening_record.save()
                    self.stdout.write(self.style.SUCCESS(
                        f"Updated ScreeningRecord for {forms.proposal_id}: admin_decision={admin_decision}, admin_evaluated=True, technical_evaluated=True"
                    ))

                # --- TECHNICAL SCREENING RECORD UPDATE OR CREATE ---
                tsr, tsr_created = TechnicalScreeningRecord.objects.get_or_create(
                    screening_record=screening_record,
                    defaults={
                        'technical_decision': technical_decision,
                        'technical_evaluated': True,
                    }
                )
                if not tsr_created:
                    tsr.technical_decision = technical_decision
                    tsr.technical_evaluated = True
                    tsr.save()
                self.stdout.write(self.style.SUCCESS(
                    f"{'Created' if tsr_created else 'Updated'} TechnicalScreeningRecord for proposal {forms.proposal_id}: technical_decision={technical_decision}, technical_evaluated=True"
                ))
