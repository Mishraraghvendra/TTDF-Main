import csv
from datetime import datetime
from dateutil import parser as date_parser

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from users.models import Profile  # Change to your app's actual name if not 'users'

class Command(BaseCommand):
    help = "Import profiles from CSV. Update if user exists (by email or mobile), else create. Print all new created users at end."

    def add_arguments(self, parser):
        parser.add_argument('csv_path', type=str, help='Path to CSV file')

    def handle(self, *args, **options):
        csv_path = options['csv_path']
        User = get_user_model()
        new_users = []

        def parse_bool(value):
            if isinstance(value, str):
                return value.strip().lower() == "yes"
            return bool(value)

        def parse_int(value):
            try:
                return int(value)
            except (ValueError, TypeError):
                return None

        def parse_date(value):
            if not value or value == '' or value.lower() == "application submission date":
                return None
            # Try several strategies, including Excel serial numbers, native datetime, and flexible parsing
            try:
                # If already a datetime/date
                if isinstance(value, datetime):
                    return value.date()
                # If it's a float or int (Excel date)
                if isinstance(value, (float, int)):
                    import datetime as dt
            # Excel serial date (beware: Excel's day 0 is 1899-12-30)
                    return (dt.datetime(1899, 12, 30) + dt.timedelta(days=int(value))).date()
                # Flexible parser (handles most human formats)
                return date_parser.parse(str(value), dayfirst=True).date()
            except Exception as e:
                print(f"Could not parse date: '{value}' ({e})")  # For debug purposes
            return None



        with open(csv_path, encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                email = row.get('Applicant Email', '').strip()
                mobile = row.get('Applicant Mobile No.', '').strip()

                if not email:
                    self.stdout.write(self.style.WARNING("Skipping row with blank email"))
                    continue

                # Check for existing user by email or mobile
                user = User.objects.filter(email=email).first()
                created = False

                # Prevent duplicate mobile for different emails
                if not user and mobile:
                    existing_mobile_user = User.objects.filter(mobile=mobile).exclude(email=email).first()
                    if existing_mobile_user:
                        self.stdout.write(self.style.WARNING(
                            f"Skipping row: Mobile {mobile} already used by {existing_mobile_user.email} (different email)"
                        ))
                        continue
                    user = User.objects.filter(mobile=mobile).first()

                if user:
                    # Update user fields if new data is present
                    user.full_name = row.get('Applicant Name', user.full_name)
                    user.gender = row.get('Gender', user.gender)
                    if not user.mobile and mobile:
                        user.mobile = mobile
                    user.save()
                else:
                    user = User.objects.create(
                        email=email,
                        full_name=row.get('Applicant Name', ''),
                        gender=row.get('Gender', 'O')[0] if row.get('Gender') else 'O',
                        mobile=mobile,
                    )
                    created = True

                if created:
                    new_users.append(email)

                profile, _ = Profile.objects.get_or_create(user=user)
                profile.qualification = row.get('Qualification', '')
                profile.applicant_official_email = row.get('Applicant Official Email', '')
                profile.proposal_duration_years = parse_int(row.get('Proposal Duration (In Years)', ''))
                profile.proposal_duration_months = parse_int(row.get('Proposal Duration (In Months)', ''))
                profile.proposal_submitted_by = row.get('Proposal Submitted By', '')
                profile.address_line_1 = row.get('address_line_1', '')
                profile.address_line_2 = row.get('address_line_2', '')
                profile.street_village = row.get('street_village', '')
                profile.city = row.get('City', '')
                profile.country = row.get('Country', '')
                profile.state = row.get('State', '')
                profile.pincode = str(row.get('pincode', ''))
                profile.landline_number = str(row.get('landline_number', ''))
                profile.company_mobile_no = str(row.get('company_mobile_no', ''))
                profile.website_link = row.get('website_link', '')
                profile.company_as_per_guidelines = row.get('Company As Per TTDFGuideliness', '')
                profile.application_submission_date = parse_date(row.get('Application Submission Date', ''))
                profile.is_applied_before = parse_bool(row.get('Is applied for TTDF before', ''))
                profile.save()

        self.stdout.write(self.style.SUCCESS(f"\nNew users created ({len(new_users)}):"))
        for email in new_users:
            self.stdout.write(self.style.SUCCESS(email))
