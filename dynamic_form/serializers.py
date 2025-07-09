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


class FormSubmissionSerializer(serializers.ModelSerializer):
    milestones = MilestoneSerializer(many=True, read_only=True)
    applicant = UserShortSerializer(read_only=True)
    profile = serializers.SerializerMethodField()
    service_name = serializers.SerializerMethodField()
    last_updated = serializers.SerializerMethodField()
    create_date = serializers.SerializerMethodField()

    class Meta:
        model = FormSubmission
        fields = '__all__'
        read_only_fields = [
            'id', 'applicant', 'form_id', 'proposal_id',
            'created_at', 'updated_at',
            'service_name', 'last_updated', 'create_date'
        ]

    def to_representation(self, instance):
        """Add nested data to the response"""
        data = super().to_representation(instance)
        
        # Add nested serialized data to response
        data['fund_loan_documents'] = FundLoanDocumentSerializer(instance.fund_loan_documents.all(), many=True).data
        data['iprdetails'] = IPRDetailsSerializer(instance.iprdetails.all(), many=True).data
        data['collaborators'] = CollaboratorSerializer(instance.collaborators.all(), many=True).data
        data['equipments'] = EquipmentSerializer(instance.equipments.all(), many=True).data
        data['shareholders'] = ShareHolderSerializer(instance.shareholders.all(), many=True).data
        data['rdstaff'] = RDStaffSerializer(instance.rdstaff.all(), many=True).data
        data['sub_shareholders'] = SubShareHolderSerializer(instance.sub_shareholders.all(), many=True).data
        
        return data

    def to_internal_value(self, data):
        json_fields = [
            'fund_loan_documents', 'iprdetails', 'collaborators', 'equipments',
            'shareholders', 'rdstaff', 'sub_shareholders', 'milestones'
        ]
        
        print("=== PROCESSING REQUEST DATA ===")
        print(f"Data type: {type(data)}")
        print(f"Available keys: {list(data.keys())[:20]}...")  # Show first 20 keys
        
        # Handle array fields that come as separate form fields or JSON strings
        for field in json_fields:
            field_data = []
            
            # NEW: Check for array values (multiple files with same field name)
            if hasattr(data, 'getlist'):
                array_values = data.getlist(field)
                
                # Handle multiple files with same field name (e.g., fund_loan_documents)
                if array_values and len(array_values) > 0:
                    # Check if these are file objects
                    if all(hasattr(value, 'read') and hasattr(value, 'name') for value in array_values if value):
                        # Special handling for fund_loan_documents (file-only model)
                        if field == 'fund_loan_documents':
                            field_data = [{'document': file} for file in array_values if file]
                            print(f"✅ {field}: Found {len(field_data)} files as array (no indexing)")
                        elif field == 'rdstaff':
                            # For rdstaff, if files are uploaded via array, create basic structure
                            field_data = [{'resume': file} for file in array_values if file]
                            print(f"✅ {field}: Found {len(field_data)} resume files as array")
                        elif field == 'shareholders':
                            field_data = [{'identity_document': file} for file in array_values if file]
                            print(f"✅ {field}: Found {len(field_data)} identity documents as array")
                        elif field == 'sub_shareholders':
                            field_data = [{'identity_document': file} for file in array_values if file]
                            print(f"✅ {field}: Found {len(field_data)} sub-shareholder documents as array")
                        elif field == 'collaborators':
                            field_data = [{'pan_file_collb': file} for file in array_values if file]
                            print(f"✅ {field}: Found {len(field_data)} collaborator files as array")
                        elif field == 'iprdetails':
                            field_data = [{'t_support_letter': file} for file in array_values if file]
                            print(f"✅ {field}: Found {len(field_data)} support letters as array")
                        else:
                            # Generic file handling
                            field_data = [{'file_field': file} for file in array_values if file]
                            print(f"✅ {field}: Found {len(field_data)} files as array")
                    
                    # Handle JSON string arrays
                    elif len(array_values) == 1 and isinstance(array_values[0], str):
                        try:
                            field_data = json.loads(array_values[0])
                            print(f"✅ {field}: Parsed from JSON string -> {len(field_data)} items")
                        except (json.JSONDecodeError, ValueError) as e:
                            print(f"❌ {field}: JSON parse failed: {e}")
                            field_data = []
                    
                    # Handle multiple JSON strings
                    elif all(isinstance(value, str) for value in array_values):
                        for value in array_values:
                            try:
                                parsed_item = json.loads(value)
                                if isinstance(parsed_item, list):
                                    field_data.extend(parsed_item)
                                else:
                                    field_data.append(parsed_item)
                            except (json.JSONDecodeError, ValueError):
                                # If not JSON, treat as simple string data
                                field_data.append({'value': value})
                        print(f"✅ {field}: Parsed multiple JSON strings -> {len(field_data)} items")
            
            # If no array values found, check for indexed array fields
            if not field_data and hasattr(data, 'keys'):
                # Collect all keys that start with this field name
                field_keys = [key for key in data.keys() if key.startswith(f"{field}[")]
                
                if field_keys:
                    print(f"Found indexed fields for {field}: {len(field_keys)} keys")
                    
                    # Group by index
                    indexed_items = {}
                    for key in field_keys:
                        # Parse key like "collaborators[0][contact_person_name_collab]"
                        match = re.match(rf"{field}\[(\d+)\]\[(.+)\]", key)
                        if match:
                            index = int(match.group(1))
                            sub_field = match.group(2)
                            
                            if index not in indexed_items:
                                indexed_items[index] = {}
                            
                            # Get the value
                            value = data.get(key)
                            if hasattr(data, 'getlist'):
                                # For QueryDict, get the first value
                                values = data.getlist(key)
                                value = values[0] if values else ''
                            
                            # Convert numeric strings to appropriate types
                            if sub_field in ['quantity', 'share_percentage', 'unit_price', 'amount', 'time_required', 'grant_from_ttdf', 'initial_contri_applicant']:
                                try:
                                    if '.' in str(value):
                                        value = float(value)
                                    else:
                                        value = int(value)
                                except (ValueError, TypeError):
                                    pass
                            
                            indexed_items[index][sub_field] = value
                    
                    # Convert to list, sorted by index
                    for i in sorted(indexed_items.keys()):
                        field_data.append(indexed_items[i])
                    
                    print(f"✅ {field}: Parsed {len(field_data)} items from indexed fields")
            
            # If still no data, check for single JSON string or list
            if not field_data:
                value = data.get(field)
                if value is not None:
                    if isinstance(value, str):
                        try:
                            field_data = json.loads(value)
                            print(f"✅ {field}: Parsed from JSON string -> {len(field_data)} items")
                        except (json.JSONDecodeError, ValueError) as e:
                            print(f"❌ {field}: JSON parse failed: {e}")
                            field_data = []
                    elif isinstance(value, list):
                        # Handle list that might contain JSON strings
                        if len(value) == 1 and isinstance(value[0], str):
                            try:
                                field_data = json.loads(value[0])
                                print(f"✅ {field}: Parsed from list[str] -> {len(field_data)} items")
                            except (json.JSONDecodeError, ValueError) as e:
                                print(f"❌ {field}: List parse failed: {e}")
                                field_data = []
                        else:
                            field_data = value
                            print(f"✅ {field}: Already a list -> {len(field_data)} items")
                    else:
                        print(f"❌ {field}: Unexpected type {type(value)}")
                        field_data = []
                else:
                    field_data = []
                    print(f"ℹ️ {field}: No data found, using empty list")
            
            # Store the processed array data - this will be accessed later in create/update
            # Don't add it to the main data dict to avoid validation issues
            if not hasattr(self, '_nested_data'):
                self._nested_data = {}
            self._nested_data[field] = field_data
        
        print("=== FINAL ARRAY SIZES ===")
        for field in json_fields:
            field_data = getattr(self, '_nested_data', {}).get(field, [])
            print(f"{field}: {len(field_data)} items")
            if field_data and len(field_data) > 0:
                print(f"  First item: {field_data[0]}")
        
        # Remove nested fields from data to avoid validation - CRITICAL STEP
        for field in json_fields:
            if field in data:
                if hasattr(data, '_mutable'):
                    data._mutable = True
                    del data[field]
                    data._mutable = False
                else:
                    data.pop(field, None)
            
            # Also remove any indexed field keys
            keys_to_remove = [key for key in data.keys() if key.startswith(f"{field}[")]
            for key in keys_to_remove:
                if hasattr(data, '_mutable'):
                    data._mutable = True
                    del data[key]
                    data._mutable = False
                else:
                    data.pop(key, None)
        
        return super().to_internal_value(data)

    def _inject_file_objects(self, records, file_field_names):
        """Inject file objects from request.FILES into record dictionaries"""
        files = self.context['request'].FILES
        for rec in records:
            for field in file_field_names:
                val = rec.get(field)
                if isinstance(val, str) and val in files:
                    rec[field] = files[val]

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

    def validate(self, data):
        # Only validate the main form template constraints
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