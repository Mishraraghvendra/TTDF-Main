from rest_framework import serializers
from .models import FormTemplate, FormSubmission, IPRDetails, FundLoanDocument, Collaborator, Equipment, RDStaff, ShareHolder, SubShareHolder
from milestones.serializers import MilestoneSerializer
from milestones.models import Milestone
from users.serializers import ProfileSerializer
from users.models import User, Profile
from django.utils import timezone
import json
import re


class IPRDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = IPRDetails
        fields = "__all__"
        read_only_fields = ("id", "created_at", "submission")


class FundLoanDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = FundLoanDocument
        fields = "__all__"
        read_only_fields = ("id", "form_submission")


class CollaboratorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Collaborator
        fields = "__all__"
        read_only_fields = ("id", "form_submission")


class EquipmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Equipment
        fields = "__all__"
        read_only_fields = ("id", "form_submission")


class ShareHolderSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShareHolder
        fields = "__all__"
        read_only_fields = ("id", "form_submission")


class RDStaffSerializer(serializers.ModelSerializer):
    class Meta:
        model = RDStaff
        fields = "__all__"
        read_only_fields = ("id", "form_submission")


class SubShareHolderSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubShareHolder
        fields = "__all__"
        read_only_fields = ("id", "form_submission")


class FormTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = FormTemplate
        fields = '__all__'


class UserShortSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "full_name", "gender", "mobile", "email", "organization"]


class FullProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        exclude = ["id", "user"]

class CollaboratorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Collaborator
        fields = '__all__'

    def validate(self, data):
        # Uniqueness for org name or PAN per village
        org_name = (data.get('organization_name_collab') or '').strip().lower()
        pan_name = (data.get('pan_file_name_collab') or '').strip().upper()
        form_submission = data.get('form_submission') or (self.instance and self.instance.form_submission)
        # Resolve FormSubmission instance if just ID
        if form_submission and not isinstance(form_submission, FormSubmission):
            form_submission = FormSubmission.objects.filter(pk=form_submission).first()
        proposed_village = getattr(form_submission, 'proposed_village', None)
        # Org check
        if org_name:
            qs = Collaborator.objects.filter(
                organization_name_collab__iexact=org_name,
                form_submission__proposed_village=proposed_village,
            )
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    f"Collaborator with organization name '{org_name}' already exists for village '{proposed_village}'."
                )
        # PAN check
        if pan_name:
            qs = Collaborator.objects.filter(
                pan_file_name_collab__iexact=pan_name,
                form_submission__proposed_village=proposed_village,
            )
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    f"Collaborator with PAN '{pan_name}' already exists for village '{proposed_village}'."
                )
        return data




class FormSubmissionSerializer(serializers.ModelSerializer):
    # Assume nested serializers are defined elsewhere
    collaborators = CollaboratorSerializer(many=True, read_only=True)
    milestones = serializers.SerializerMethodField()
    # ... other fields/nested serializers ...

    class Meta:
        model = FormSubmission
        fields = '__all__'
        read_only_fields = [
            'id', 'applicant', 'form_id', 'proposal_id',
            'created_at', 'updated_at',
        ]

 
    

    def to_internal_value(self, data):
        import json, re
        json_fields = [
            'fund_loan_documents', 'iprdetails', 'collaborators', 'equipments',
            'shareholders', 'rdstaff', 'sub_shareholders', 'milestones'
        ]
        print("=== PROCESSING REQUEST DATA ===")
        print(f"Data type: {type(data)}")
        print(f"Available keys: {list(data.keys())[:20]}...")

        if not hasattr(self, '_nested_data'):
            self._nested_data = {}

        # Pass 1: Try basic JSON parsing for all fields (quick path, AJAX/fetch use case)
        for field in json_fields:
            field_data = data.get(field, None)
            if field_data and isinstance(field_data, str):
                try:
                    parsed = json.loads(field_data)
                    self._nested_data[field] = parsed if isinstance(parsed, list) else [parsed]
                    print(f"Parsed {field}: {len(self._nested_data[field])} items from JSON string")
                    continue  # skip to next field if handled
                except Exception as e:
                    print(f"Error parsing {field}: {e}")
                    self._nested_data[field] = []
                    continue

        # Pass 2: For any fields not set above, use the advanced logic (file upload, indexed, etc.)
        for field in json_fields:
            if field in self._nested_data:
                continue  # already parsed from above

            field_data = []

            # Array values (files or arrays) from multipart/form-data
            if hasattr(data, 'getlist'):
                array_values = data.getlist(field)
                if array_values and all(hasattr(f, 'read') and hasattr(f, 'name') for f in array_values if f):
                    # File arrays
                    if field == 'fund_loan_documents':
                        field_data = [{'document': file} for file in array_values if file]
                    elif field == 'rdstaff':
                        field_data = [{'resume': file} for file in array_values if file]
                    elif field == 'shareholders' or field == 'sub_shareholders':
                        field_data = [{'identity_document': file} for file in array_values if file]
                    elif field == 'collaborators':
                        field_data = [{'pan_file_collb': file} for file in array_values if file]
                    elif field == 'iprdetails':
                        field_data = [{'t_support_letter': file} for file in array_values if file]
                    else:
                        field_data = [{'file_field': file} for file in array_values if file]
                    print(f"✅ {field}: Found {len(field_data)} files as array")
                elif array_values and len(array_values) == 1 and isinstance(array_values[0], str):
                    # JSON string in array
                    try:
                        field_data = json.loads(array_values[0])
                        print(f"✅ {field}: Parsed from JSON string -> {len(field_data)} items")
                    except Exception as e:
                        print(f"❌ {field}: JSON parse failed: {e}")
                        field_data = []
                elif array_values and all(isinstance(v, str) for v in array_values):
                    for value in array_values:
                        try:
                            parsed_item = json.loads(value)
                            if isinstance(parsed_item, list):
                                field_data.extend(parsed_item)
                            else:
                                field_data.append(parsed_item)
                        except Exception:
                            field_data.append({'value': value})
                    print(f"✅ {field}: Parsed multiple JSON strings -> {len(field_data)} items")

            # Indexed fields: e.g., collaborators[0][contact_person_name_collab]
            if not field_data and hasattr(data, 'keys'):
                field_keys = [key for key in data.keys() if key.startswith(f"{field}[")]
                if field_keys:
                    indexed_items = {}
                    for key in field_keys:
                        match = re.match(rf"{field}\[(\d+)\]\[(.+)\]", key)
                        if match:
                            index = int(match.group(1))
                            sub_field = match.group(2)
                            if index not in indexed_items:
                                indexed_items[index] = {}
                            value = data.get(key)
                            if hasattr(data, 'getlist'):
                                values = data.getlist(key)
                                value = values[0] if values else ''
                            if sub_field in ['quantity', 'share_percentage', 'unit_price', 'amount', 'time_required', 'grant_from_ttdf', 'initial_contri_applicant']:
                                try:
                                    if '.' in str(value):
                                        value = float(value)
                                    else:
                                        value = int(value)
                                except (ValueError, TypeError):
                                    pass
                            indexed_items[index][sub_field] = value
                    for i in sorted(indexed_items.keys()):
                        field_data.append(indexed_items[i])
                    print(f"✅ {field}: Parsed {len(field_data)} items from indexed fields")

            # If still empty, maybe it's a direct list
            if not field_data:
                value = data.get(field)
                if isinstance(value, list):
                    field_data = value
                    print(f"✅ {field}: Already a list -> {len(field_data)} items")

            self._nested_data[field] = field_data

        # LOGGING final array sizes
        print("=== FINAL ARRAY SIZES ===")
        for field in json_fields:
            arr = self._nested_data.get(field, [])
            print(f"{field}: {len(arr)} items")
            if arr and len(arr) > 0:
                print(f"  First item: {arr[0]}")

        # Remove nested fields from data to avoid DRF errors
        for field in json_fields:
            if field in data:
                if hasattr(data, '_mutable'):
                    data._mutable = True
                    del data[field]
                    data._mutable = False
                else:
                    data.pop(field, None)
            keys_to_remove = [key for key in data.keys() if key.startswith(f"{field}[")]
            for key in keys_to_remove:
                if hasattr(data, '_mutable'):
                    data._mutable = True
                    del data[key]
                    data._mutable = False
                else:
                    data.pop(key, None)

        # Optionally: stash for validator access if you need
        self._pending_collaborators = self._nested_data.get('collaborators', [])
        self._pending_milestones = self._nested_data.get('milestones', [])

        return super().to_internal_value(data)


   
    def validate(self, data):

        current_status = data.get('status') or (self.instance and self.instance.status)
        if current_status != FormSubmission.SUBMITTED:
            return data
        # --- Print all Collaborators before ---
        print("\n=== ALL Collaborators in DB BEFORE VALIDATION ===")
        for c in Collaborator.objects.all():
            print(
                f"ID: {c.id} | Org: '{c.organization_name_collab}' | PAN: '{c.pan_file_name_collab}' | Village: '{getattr(c.form_submission, 'proposed_village', None)}' | Submission: {c.form_submission_id}"
            )
        print("=== END ALL COLLABORATORS IN DB ===\n")

        collaborators = getattr(self, '_pending_collaborators', [])
        proposed_village = data.get('proposed_village') or (self.instance and self.instance.proposed_village)
        orgs_seen = set()
        pans_seen = set()

        print("\n==== Collaborator Uniqueness Check START ====")
        print(f"Proposed village: {proposed_village}")
        print(f"Collaborators in submission: {len(collaborators)}")

        # 1. Intra-request duplicate check
        for collab in collaborators:
            org = (collab.get('organization_name_collab') or '').strip().lower()
            pan = (collab.get('pan_file_name_collab') or '').strip().upper()
            print(f"  Collaborator: org='{org}' pan='{pan}'")
            if org and org in orgs_seen:
                print(f"❌ Duplicate org in this submission: {org}")
                raise serializers.ValidationError(f"Duplicate organization '{org}' in collaborators for this submission.")
            if pan and pan in pans_seen:
                print(f"❌ Duplicate PAN in this submission: {pan}")
                raise serializers.ValidationError(f"Duplicate PAN '{pan}' in collaborators for this submission.")
            orgs_seen.add(org)
            pans_seen.add(pan)

        # 2. Database duplicate check (org)
        for org in orgs_seen:
            db_qs = Collaborator.objects.filter(
                organization_name_collab__iexact=org,
                form_submission__proposed_village=proposed_village,
                form_submission__status=FormSubmission.SUBMITTED,  # Only consider submitted forms!
            )
            if self.instance:
                db_qs = db_qs.exclude(form_submission=self.instance)
            if db_qs.exists():
                existing_collab = db_qs.first()
                submission = existing_collab.form_submission if existing_collab else None
                proposal_id = getattr(submission, 'proposal_id', None)
                form_id = getattr(submission, 'form_id', None)
                proposal_identifier = proposal_id or form_id or "Unknown"

                raise serializers.ValidationError({
                    "non_field_errors": [
                        f"Collaborator with organization '{org}' already exists for village '{proposed_village}'. Proposal ID: {proposal_identifier}"
                    ]
                })

        # Database duplicate check (PAN)
        for pan in pans_seen:
            if not pan:
                continue
            db_qs = Collaborator.objects.filter(
                pan_file_name_collab__iexact=pan,
                form_submission__proposed_village=proposed_village,
                form_submission__status=FormSubmission.SUBMITTED,  # Only block for submitted!
            )
            if self.instance:
                db_qs = db_qs.exclude(form_submission=self.instance)
            if db_qs.exists():
                existing_collab = db_qs.first()
                submission = existing_collab.form_submission if existing_collab else None
                proposal_id = getattr(submission, 'proposal_id', None)
                form_id = getattr(submission, 'form_id', None)
                proposal_identifier = proposal_id or form_id or "Unknown"

                raise serializers.ValidationError({
                    "non_field_errors": [
                        f"Collaborator with PAN '{pan}' already exists for village '{proposed_village}'. Proposal ID: {proposal_identifier}"
                    ]
                })

        print("==== Collaborator Uniqueness Check PASSED ====\n")

        # Template/business rule checks
        tpl = data.get('template') or (self.instance.template if self.instance else None)
        if tpl:
            now = timezone.now()
            if not tpl.is_active:
                raise serializers.ValidationError("Form not active.")
            if tpl.start_date and now < tpl.start_date:
                raise serializers.ValidationError("Not open yet.")
            if tpl.end_date and now > tpl.end_date:
                raise serializers.ValidationError("Deadline passed.")
            if self.instance and not self.instance.can_edit():
                raise serializers.ValidationError("Cannot edit after deadline/final submit.")
        
        return data

    def get_milestones(self, obj):
            # You must return serialized data for milestones!
            # (Assuming you have a related_name='milestones' on FormSubmission model)
            return MilestoneSerializer(obj.milestones.all(), many=True).data


    def get_service_name(self, obj):
        return obj.service.name if obj.service else None

    def get_last_updated(self, obj):
        if obj.updated_at:
            return timezone.localtime(obj.updated_at).strftime('%Y-%m-%d %H:%M:%S')
        return None

    def get_create_date(self, obj):
        if obj.created_at:
            return timezone.localtime(obj.created_at).strftime('%Y-%m-%d %H:%M:%S')
        return None

    def get_profile(self, obj):
        profile = getattr(obj.applicant, "profile", None)
        if not profile:
            return None
        return FullProfileSerializer(profile).data

    # def validate(self, data):
    #     from dynamic_form.models import Collaborator  # adjust import if needed

    #     collaborators = data.get('collaborators', [])
    #     proposed_village = data.get('proposed_village') or (self.instance and self.instance.proposed_village)
    #     orgs_seen = set()
    #     pans_seen = set()

    #     # === Print ALL collaborators in DB for debugging ===
    #     print("\n=== ALL Collaborators in DB BEFORE VALIDATION ===")
    #     all_collabs = Collaborator.objects.all().order_by("id")
    #     for c in all_collabs:
    #         print(f"ID: {c.id} | Org: '{c.organization_name_collab}' | PAN: '{c.pan_file_name_collab}' | Village: '{getattr(c.form_submission, 'proposed_village', None)}' | Submission: {getattr(c.form_submission, 'id', None)}")
    #     print("=== END ALL COLLABORATORS IN DB ===")

    #     print("\n==== Collaborator Uniqueness Check START ====")
    #     print(f"Proposed village: {proposed_village}")
    #     print(f"Collaborators in submission: {len(collaborators)}")

    #     # 1. Check for duplicates *within this request*
    #     for collab in collaborators:
    #         org = (collab.get('organization_name_collab') or '').strip().lower()
    #         pan = (collab.get('pan_file_name_collab') or '').strip().upper()
    #         print(f"  Collaborator: org='{org}' pan='{pan}'")
    #         if org and org in orgs_seen:
    #             print(f"❌ Duplicate org in this submission: {org}")
    #             raise serializers.ValidationError(f"Duplicate organization '{org}' in collaborators for this submission.")
    #         if pan and pan in pans_seen:
    #             print(f"❌ Duplicate PAN in this submission: {pan}")
    #             raise serializers.ValidationError(f"Duplicate PAN '{pan}' in collaborators for this submission.")
    #         orgs_seen.add(org)
    #         pans_seen.add(pan)

    #     # 2. Check against DB (print all found)
    #     for org in orgs_seen:
    #         db_qs = Collaborator.objects.filter(
    #             organization_name_collab__iexact=org,
    #             form_submission__proposed_village=proposed_village,
    #         )
    #         if self.instance:
    #             db_qs = db_qs.exclude(form_submission=self.instance)
    #         db_count = db_qs.count()
    #         print(f"DB check for org '{org}' in village '{proposed_village}': found {db_count} records.")
    #         if db_count > 0:
    #             for c in db_qs:
    #                 print(f"  -> DB match org: {c.organization_name_collab} | PAN: {c.pan_file_name_collab} | Submission: {getattr(c.form_submission, 'id', None)}")
    #             raise serializers.ValidationError(
    #                 f"Collaborator with organization '{org}' already exists for village '{proposed_village}'."
    #             )

    #     for pan in pans_seen:
    #         if not pan:
    #             continue
    #         db_qs = Collaborator.objects.filter(
    #             pan_file_name_collab__iexact=pan,
    #             form_submission__proposed_village=proposed_village,
    #         )
    #         if self.instance:
    #             db_qs = db_qs.exclude(form_submission=self.instance)
    #         db_count = db_qs.count()
    #         print(f"DB check for PAN '{pan}' in village '{proposed_village}': found {db_count} records.")
    #         if db_count > 0:
    #             for c in db_qs:
    #                 print(f"  -> DB match org: {c.organization_name_collab} | PAN: {c.pan_file_name_collab} | Submission: {getattr(c.form_submission, 'id', None)}")
    #             raise serializers.ValidationError(
    #                 f"Collaborator with PAN '{pan}' already exists for village '{proposed_village}'."
    #             )

    #     print("==== Collaborator Uniqueness Check PASSED ====\n")

    #     # --- Template/business rule checks
    #     tpl = data.get('template') or (self.instance.template if self.instance else None)
    #     if tpl:
    #         now = timezone.now()
    #         if not tpl.is_active:
    #             raise serializers.ValidationError("Form not active.")
    #         if tpl.start_date and now < tpl.start_date:
    #             raise serializers.ValidationError("Not open yet.")
    #         if tpl.end_date and now > tpl.end_date:
    #             raise serializers.ValidationError("Deadline passed.")
    #         if self.instance and not self.instance.can_edit():
    #             raise serializers.ValidationError("Cannot edit after deadline/final submit.")

    #     return data

    def _inject_file_objects(self, records, file_field_names):
        """Inject file objects from request.FILES into record dictionaries"""
        files = self.context['request'].FILES
        for rec in records:
            for field in file_field_names:
                val = rec.get(field)
                if isinstance(val, str) and val in files:
                    rec[field] = files[val]


    def create(self, validated_data):
        request = self.context['request']
        
        print("=== CREATE METHOD DEBUG ===")
        print(f"Validated data keys: {list(validated_data.keys())}")
        
        # Get nested data from the stored location
        nested_data = getattr(self, '_nested_data', {})
        fund_loan_documents = nested_data.get('fund_loan_documents', [])
        iprdetails = nested_data.get('iprdetails', [])
        collaborators = nested_data.get('collaborators', [])
        equipments = nested_data.get('equipments', [])
        shareholders = nested_data.get('shareholders', [])
        rdstaff = nested_data.get('rdstaff', [])
        sub_shareholders = nested_data.get('sub_shareholders', [])
        milestones = nested_data.get('milestones', [])

        print(f"fund_loan_documents: {len(fund_loan_documents)} items")
        print(f"iprdetails: {len(iprdetails)} items")
        print(f"collaborators: {len(collaborators)} items")
        print(f"equipments: {len(equipments)} items")
        print(f"shareholders: {len(shareholders)} items")
        print(f"rdstaff: {len(rdstaff)} items")
        print(f"sub_shareholders: {len(sub_shareholders)} items")
        print(f"milestones: {len(milestones)} items")

        # Set applicant
        validated_data['applicant'] = request.user
        
        # ✅ POPULATE JSON FIELDS IN MAIN MODEL
        if rdstaff:
            validated_data['rd_staff'] = rdstaff
            print(f"✅ Set rd_staff JSON field with {len(rdstaff)} items")
        
        if equipments:
            validated_data['equipment'] = equipments
            print(f"✅ Set equipment JSON field with {len(equipments)} items")
        
        # Create main submission
        submission = super().create(validated_data)

        # Inject file objects for indexed uploads (files referenced by name)
        self._inject_file_objects(fund_loan_documents, ['document'])
        self._inject_file_objects(iprdetails, ['t_support_letter'])
        self._inject_file_objects(collaborators, ['pan_file_collb', 'mou_file_collab'])
        self._inject_file_objects(equipments, [])
        self._inject_file_objects(shareholders, ['identity_document'])
        self._inject_file_objects(rdstaff, ['resume'])
        self._inject_file_objects(sub_shareholders, ['identity_document'])

        print("=== CREATING RELATED OBJECTS ===")
        
        # Create related objects
        for doc in fund_loan_documents:
            print(f"Creating FundLoanDocument: {doc}")
            try:
                FundLoanDocument.objects.create(form_submission=submission, **doc)
                print("✅ FundLoanDocument created successfully")
            except Exception as e:
                print(f"❌ Error creating FundLoanDocument: {e}")
        
        for ipr in iprdetails:
            print(f"Creating IPRDetails: {list(ipr.keys())}")
            try:
                IPRDetails.objects.create(submission=submission, **ipr)
                print("✅ IPRDetails created successfully")
            except Exception as e:
                print(f"❌ Error creating IPRDetails: {e}")
        
        for collab in collaborators:
            print(f"Creating Collaborator: {list(collab.keys())}")
            try:
                Collaborator.objects.create(form_submission=submission, **collab)
                print("✅ Collaborator created successfully")
            except Exception as e:
                print(f"❌ Error creating Collaborator: {e}")
        
        for equip in equipments:
            print(f"Creating Equipment: {list(equip.keys())}")
            try:
                Equipment.objects.create(form_submission=submission, **equip)
                print("✅ Equipment created successfully")
            except Exception as e:
                print(f"❌ Error creating Equipment: {e}")
        
        for sh in shareholders:
            print(f"Creating ShareHolder: {list(sh.keys())}")
            try:
                ShareHolder.objects.create(form_submission=submission, **sh)
                print("✅ ShareHolder created successfully")
            except Exception as e:
                print(f"❌ Error creating ShareHolder: {e}")
        
        for staff in rdstaff:
            print(f"Creating RDStaff: {list(staff.keys())}")
            try:
                RDStaff.objects.create(form_submission=submission, **staff)
                print("✅ RDStaff created successfully")
            except Exception as e:
                print(f"❌ Error creating RDStaff: {e}")
        
        for subsh in sub_shareholders:
            print(f"Creating SubShareHolder: {list(subsh.keys())}")
            try:
                SubShareHolder.objects.create(form_submission=submission, **subsh)
                print("✅ SubShareHolder created successfully")
            except Exception as e:
                print(f"❌ Error creating SubShareHolder: {e}")

        # ✅ CREATE MILESTONES
        for milestone_data in milestones:
            print(f"Creating Milestone: {list(milestone_data.keys())}")
            try:
                Milestone.objects.create(
                    proposal=submission,
                    created_by=request.user,
                    **milestone_data
                )
                print("✅ Milestone created successfully")
            except Exception as e:
                print(f"❌ Error creating Milestone: {e}")

        print("=== FINISHED CREATING OBJECTS ===")
        return submission

    def update(self, instance, validated_data):
        request = self.context['request']
        
        print("=== UPDATE METHOD DEBUG ===")
        print(f"Validated data keys: {list(validated_data.keys())}")
        
        # Get nested data from the stored location
        nested_data = getattr(self, '_nested_data', {})
        fund_loan_documents = nested_data.get('fund_loan_documents')
        iprdetails = nested_data.get('iprdetails')
        collaborators = nested_data.get('collaborators')
        equipments = nested_data.get('equipments')
        shareholders = nested_data.get('shareholders')
        rdstaff = nested_data.get('rdstaff')
        sub_shareholders = nested_data.get('sub_shareholders')
        milestones = nested_data.get('milestones')

        # ✅ UPDATE JSON FIELDS IN MAIN MODEL
        if rdstaff is not None:
            validated_data['rd_staff'] = rdstaff
            print(f"✅ Updated rd_staff JSON field with {len(rdstaff)} items")
        
        if equipments is not None:
            validated_data['equipment'] = equipments
            print(f"✅ Updated equipment JSON field with {len(equipments)} items")

        # Update main instance
        instance = super().update(instance, validated_data)

        # Update related objects if data is provided
        if fund_loan_documents is not None:
            print(f"Updating fund_loan_documents: {len(fund_loan_documents)} items")
            instance.fund_loan_documents.all().delete()
            self._inject_file_objects(fund_loan_documents, ['document'])
            for doc in fund_loan_documents:
                try:
                    FundLoanDocument.objects.create(form_submission=instance, **doc)
                    print("✅ FundLoanDocument updated successfully")
                except Exception as e:
                    print(f"❌ Error updating FundLoanDocument: {e}")

        if iprdetails is not None:
            print(f"Updating iprdetails: {len(iprdetails)} items")
            instance.iprdetails.all().delete()
            self._inject_file_objects(iprdetails, ['t_support_letter'])
            for ipr in iprdetails:
                try:
                    IPRDetails.objects.create(submission=instance, **ipr)
                    print("✅ IPRDetails updated successfully")
                except Exception as e:
                    print(f"❌ Error updating IPRDetails: {e}")

        if collaborators is not None:
            print(f"Updating collaborators: {len(collaborators)} items")
            instance.collaborators.all().delete()
            self._inject_file_objects(collaborators, ['pan_file_collb', 'mou_file_collab'])
            for collab in collaborators:
                try:
                    Collaborator.objects.create(form_submission=instance, **collab)
                    print("✅ Collaborator updated successfully")
                except Exception as e:
                    print(f"❌ Error updating Collaborator: {e}")

        if equipments is not None:
            print(f"Updating equipments: {len(equipments)} items")
            instance.equipments.all().delete()
            self._inject_file_objects(equipments, [])
            for equip in equipments:
                try:
                    Equipment.objects.create(form_submission=instance, **equip)
                    print("✅ Equipment updated successfully")
                except Exception as e:
                    print(f"❌ Error updating Equipment: {e}")

        if shareholders is not None:
            print(f"Updating shareholders: {len(shareholders)} items")
            instance.shareholders.all().delete()
            self._inject_file_objects(shareholders, ['identity_document'])
            for sh in shareholders:
                try:
                    ShareHolder.objects.create(form_submission=instance, **sh)
                    print("✅ ShareHolder updated successfully")
                except Exception as e:
                    print(f"❌ Error updating ShareHolder: {e}")

        if rdstaff is not None:
            print(f"Updating rdstaff: {len(rdstaff)} items")
            instance.rdstaff.all().delete()
            self._inject_file_objects(rdstaff, ['resume'])
            for staff in rdstaff:
                try:
                    RDStaff.objects.create(form_submission=instance, **staff)
                    print("✅ RDStaff updated successfully")
                except Exception as e:
                    print(f"❌ Error updating RDStaff: {e}")

        if sub_shareholders is not None:
            print(f"Updating sub_shareholders: {len(sub_shareholders)} items")
            instance.sub_shareholders.all().delete()
            self._inject_file_objects(sub_shareholders, ['identity_document'])
            for subsh in sub_shareholders:
                try:
                    SubShareHolder.objects.create(form_submission=instance, **subsh)
                    print("✅ SubShareHolder updated successfully")
                except Exception as e:
                    print(f"❌ Error updating SubShareHolder: {e}")

        # ✅ UPDATE MILESTONES
        if milestones is not None:
            print(f"Updating milestones: {len(milestones)} items")
            instance.milestones.all().delete()
            for milestone_data in milestones:
                try:
                    Milestone.objects.create(
                        proposal=instance,
                        created_by=request.user,
                        **milestone_data
                    )
                    print("✅ Milestone updated successfully")
                except Exception as e:
                    print(f"❌ Error updating Milestone: {e}")

        print("=== FINISHED UPDATING OBJECTS ===")
        return instance
    





    
















