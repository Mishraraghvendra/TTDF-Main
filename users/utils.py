# users/utils.py

from .models import Profile
from django.contrib.auth import get_user_model

User = get_user_model()
import json

def upsert_profile_and_user_from_submission(user, data, files=None):
   """
   Update or create Profile and User fields from form submission data.
   Accepts both standard and file data (for e.g. images/resume uploads).
   """

   profile, _ = Profile.objects.get_or_create(user=user)

   user_fields = ["full_name", "gender", "mobile", "email", "organization"]
   user_updated = False
   for field in user_fields:
       value = data.get(field)
       if value is not None and getattr(user, field, None) != value:
           setattr(user, field, value)
           user_updated = True
   if user_updated:
       user.save()

   numeric_fields = ["proposal_duration_years", "proposal_duration_months"]

   profile_map = {
       "applicantPhoto": "profile_image",
       "profile_image": "profile_image",
       "qualification": "qualification",
       "resume": "resume",
       "officialEmail": "applicant_official_email",
       "applicant_official_email": "applicant_official_email",
       "proposalDurationYears": "proposal_duration_years",
       "proposalDurationMonths": "proposal_duration_months",
       "proposal_duration_months": "proposal_duration_months",
       "proposalSubmittedBy": "proposal_submitted_by",
       "proposal_submitted_by": "proposal_submitted_by",
       "addressLine1": "address_line_1",
       "address_line_1": "address_line_1",
       "addressLine2": "address_line_2",
       "address_line_2": "address_line_2",
       "streetVillage": "street_village",
       "street_village": "street_village",
       "city": "city",
       "dob": "dob",
       "country": "country",
       "state": "state",
       "pincode": "pincode",
       "landline": "landline_number",
       "landline_number": "landline_number",
       "companyMobile": "company_mobile_no",
       "company_mobile_no": "company_mobile_no",
       "website": "website_link",
       "website_link": "website_link",
       "companyAsPerCfp": "companyAsPerCfp",
       "organization_registration_certificate": "organization_registration_certificate",
       "share_holding_pattern": "share_holding_pattern",
       "three_years_financial_report": "three_years_financial_report",
       "dsir_certificate": "dsir_certificate",
       "tan_pan_cin": "tan_pan_cin",
       "applicant_type": "applicant_type",
       "approval_certificate":"approval_certificate",
       "applicant_aadhar":"applicant_aadhar",
       "contact_name": "full_name",
       "contact_email": "email",
       "mobile": "mobile",
       "gender": "gender",
       "organization": "organization",
       "is_organization_domestic": "is_organization_domestic",
       "individualPanAttachment":"individualPanAttachment",
       "companyAsPerCfp":"companyAsPerCfp",
       "individualPAN":"individualPAN",
   }

   profile_data = data.get("profile", {})
   if isinstance(profile_data, str):
       try:
           profile_data = json.loads(profile_data)
       except json.JSONDecodeError:
           profile_data = {}

   for form_field, profile_field in profile_map.items():
       value = None
       if files and form_field in files:
           value = files[form_field]
       elif form_field in profile_data:
           value = profile_data[form_field]
       elif form_field in data:
           value = data[form_field]
       
       if value is not None:
           if profile_field in numeric_fields:
               if value == '' or value is None:
                   value = None
               else:
                   try:
                       value = int(value)
                   except (ValueError, TypeError):
                       value = None
           
           if value is not None:
               setattr(profile, profile_field, value)
   
   profile.save()
   return profile