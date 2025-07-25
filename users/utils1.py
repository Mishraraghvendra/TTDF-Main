# users/utils.py

from .models import Profile
from django.contrib.auth import get_user_model

User = get_user_model()
import json

# def upsert_profile_and_user_from_submission(user, data, files=None):
#     """
#     Update or create Profile and User fields from form submission data.
#     Accepts both standard and file data (for e.g. images/resume uploads).
#     """

#     profile, _ = Profile.objects.get_or_create(user=user)

#     # --- User fields
#     user_fields = ["full_name", "gender", "mobile", "email", "organization"]
#     user_updated = False
#     for field in user_fields:
#         value = data.get(field)
#         if value is not None and getattr(user, field, None) != value:
#             setattr(user, field, value)
#             user_updated = True
#     if user_updated:
#         user.save()

#     # --- define profile_map here
#     profile_map = {
#         "applicantPhoto": "profile_image",
#         "profile_image": "profile_image",   # <--- Add this line!
#         "qualification": "qualification",
#         "resume": "resume",
#         "officialEmail": "applicant_official_email",
#         "proposalDurationYears": "proposal_duration_years",
#         "proposalDurationMonths": "proposal_duration_months",
#         "proposalSubmittedBy": "proposal_submitted_by",
#         "addressLine1": "address_line_1",
#         "addressLine2": "address_line_2",
#         "streetVillage": "street_village",
#         "city": "city",
#         "country": "country",
#         "state": "state",
#         "pincode": "pincode",
#         "landline": "landline_number",
#         "companyMobile": "company_mobile_no",
#         "website": "website_link",
#         "companyAsPerCfp": "company_as_per_guidelines",
#         "registrationCertificate": "organization_registration_certificate",
#         "shareHoldingPattern": "share_holding_pattern",
#         "dsirCertificate": "dsir_certificate",
#         "tanPanCin": "tan_pan_cin",
#         "organizationType": "applicant_type",
#         # add more mappings as needed
#     }

#     # --- updated profile handling to accept nested 'profile' as dict or string
#     profile_data = data.get("profile", {})
#     # If profile_data is a string (e.g., sent as JSON via curl -F), parse it
#     if isinstance(profile_data, str):
#         try:
#             profile_data = json.loads(profile_data)
#         except json.JSONDecodeError:
#             profile_data = {}

#     for form_field, profile_field in profile_map.items():
#         value = None
#         if files and form_field in files:
#             value = files[form_field]
#         elif form_field in profile_data:
#             value = profile_data[form_field]
#         elif form_field in data:
#             value = data[form_field]
#         if value is not None:
#             setattr(profile, profile_field, value)
#     profile.save()
#     return profile


def upsert_profile_and_user_from_submission(user, data, files=None):
    """
    Update or create Profile and User fields from form submission data.
    Accepts both standard and file data (for e.g. images/resume uploads).
    """

    profile, _ = Profile.objects.get_or_create(user=user)

    # --- User fields
    user_fields = ["full_name", "gender", "mobile", "email", "organization"]
    user_updated = False
    for field in user_fields:
        value = data.get(field)
        if value is not None and getattr(user, field, None) != value:
            setattr(user, field, value)
            user_updated = True
    if user_updated:
        user.save()

    # --- Mappings for camelCase/alternate field names
    profile_map = {
        "applicantPhoto": "profile_image",
        "officialEmail": "applicant_official_email",
        "proposalDurationYears": "proposal_duration_years",
        "proposalDurationMonths": "proposal_duration_months",
        "proposalSubmittedBy": "proposal_submitted_by",
        "addressLine1": "address_line_1",
        "addressLine2": "address_line_2",
        "streetVillage": "street_village",
        "landline": "landline_number",
        "companyMobile": "company_mobile_no",
        "website": "website_link",
        "companyAsPerCfp": "company_as_per_guidelines",
        "registrationCertificate": "organization_registration_certificate",
        "shareHoldingPattern": "share_holding_pattern",
        "dsirCertificate": "dsir_certificate",
        "tanPanCin": "tan_pan_cin",
        "organizationType": "applicant_type",
        
    }

    # Accept both flat and nested profile fields
    profile_data = data.get("profile", {})
    if isinstance(profile_data, str):
        try:
            profile_data = json.loads(profile_data)
        except json.JSONDecodeError:
            profile_data = {}

    # 1. Set mapped/camelCase fields
    for form_field, profile_field in profile_map.items():
        value = None
        if files and form_field in files:
            value = files[form_field]
        elif form_field in profile_data:
            value = profile_data[form_field]
        elif form_field in data:
            value = data[form_field]
        if value is not None:
            setattr(profile, profile_field, value)

    # 2. Auto-set all fields matching Profile's own field names
    for field in [f.name for f in Profile._meta.get_fields() if f.concrete and f.name not in ["id", "user"]]:
        # Avoid overwriting mapped fields above
        if getattr(profile, field, None) not in [None, ""]:
            continue
        value = None
        if files and field in files:
            value = files[field]
        elif field in profile_data:
            value = profile_data[field]
        elif field in data:
            value = data[field]
        if value is not None:
            setattr(profile, field, value)

    profile.save()
    return profile
