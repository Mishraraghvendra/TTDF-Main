# dynamic_form/form_serializers.py 
from rest_framework import serializers
from .models import (
    FormSubmission, Collaborator, Equipment, ShareHolder,
    SubShareHolder, RDStaff, IPRDetails, FundLoanDocument, TeamMember
)
from users.models import User, Profile
from users.utils import upsert_profile_and_user_from_submission


class BasicDetailsSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = FormSubmission
        fields = [
            'id', 'form_id', 'proposal_id', 'status', 
            'individual_pan', 'pan_file', 'subject', 'description'
        ]
        read_only_fields = ['id', 'form_id', 'proposal_id']
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        
        if instance.applicant:
            data.update({
                'full_name': instance.applicant.full_name or '',
                'applicantName': instance.applicant.full_name or '',
                'gender': instance.applicant.gender or '',
                'mobile': instance.applicant.mobile or '',
                'email': instance.applicant.email or '',
                'organization': instance.applicant.organization or '',
            })
            
            if hasattr(instance.applicant, 'profile') and instance.applicant.profile:
                profile = instance.applicant.profile
                data.update({
                    'qualification': profile.qualification or '',
                    'proposal_submitted_by': profile.proposal_submitted_by or '',
                    'proposalBy': profile.proposal_submitted_by or '',
                    'address_line_1': profile.address_line_1 or '',
                    'addressLine1': profile.address_line_1 or '',
                    'address_line_2': profile.address_line_2 or '',
                    'addressLine2': profile.address_line_2 or '',
                    'street_village': profile.street_village or '',
                    'streetVillage': profile.street_village or '',
                    'city': profile.city or '',
                    'country': profile.country or '',
                    'state': profile.state or '', 
                    'pincode': profile.pincode or '',
                    'landline_number': profile.landline_number or '',
                    'landline': profile.landline_number or '',
                    'website_link': profile.website_link or '',
                    'website': profile.website_link or '',
                    'company_as_per_guidelines': profile.company_as_per_guidelines or '',
                    'ttdfCompany': profile.company_as_per_guidelines or '',
                    'profile_image': profile.profile_image.url if profile.profile_image else None,
                    'applicantPhoto': profile.profile_image.url if profile.profile_image else None,
                    'resume': profile.resume.url if profile.resume else None,
                    'organization_registration_certificate': profile.organization_registration_certificate.url if profile.organization_registration_certificate else None,
                    'registrationCertificate': profile.organization_registration_certificate.url if profile.organization_registration_certificate else None,
                    'share_holding_pattern': profile.share_holding_pattern.url if profile.share_holding_pattern else None,
                    'shareHoldingPattern': profile.share_holding_pattern.url if profile.share_holding_pattern else None,
                    'dsir_certificate': profile.dsir_certificate.url if profile.dsir_certificate else None,
                    'dsirCertificate': profile.dsir_certificate.url if profile.dsir_certificate else None,
                    'tan_pan_cin': profile.tan_pan_cin.url if profile.tan_pan_cin else None,
                    'individualPanAttachment': profile.tan_pan_cin.url if profile.tan_pan_cin else None,
                    'companyAsPerCfp': profile.companyAsPerCfp or '',
                    
                })
            else:
                data.update({
                    'qualification': '', 'proposal_submitted_by': '', 'proposalBy': '',
                    'address_line_1': '', 'addressLine1': '', 'address_line_2': '', 'addressLine2': '',
                    'street_village': '', 'streetVillage': '', 'city': '', 'country': '', 'state': '',
                    'pincode': '', 'landline_number': '', 'landline': '', 'website_link': '', 
                    'website': '', 'company_as_per_guidelines': '', 'ttdfCompany': '',
                    'profile_image': None, 'applicantPhoto': None, 'resume': None,
                    'organization_registration_certificate': None, 'registrationCertificate': None,
                    'share_holding_pattern': None, 'shareHoldingPattern': None,
                    'dsir_certificate': None, 'dsirCertificate': None,
                    'tan_pan_cin': None, 'individualPanAttachment': None,
                     'companyAsPerCfp': '',
                })
        else:
            data.update({
                'full_name': '', 'applicantName': '', 'gender': '', 'mobile': '', 'email': '', 'organization': '',
                'qualification': '', 'proposal_submitted_by': '', 'proposalBy': '',
                'address_line_1': '', 'addressLine1': '', 'address_line_2': '', 'addressLine2': '',
                'street_village': '', 'streetVillage': '', 'city': '', 'country': '', 'state': '',
                'pincode': '', 'landline_number': '', 'landline': '', 'website_link': '', 
                'website': '', 'company_as_per_guidelines': '', 'ttdfCompany': '',
                'profile_image': None, 'applicantPhoto': None, 'resume': None,
                'organization_registration_certificate': None, 'registrationCertificate': None,
                'share_holding_pattern': None, 'shareHoldingPattern': None,
                'dsir_certificate': None, 'dsirCertificate': None,
                'tan_pan_cin': None, 'individualPanAttachment': None,
                'companyAsPerCfp': '',
            })
        
        # Handle FormSubmission pan_file
        if instance.pan_file:
            data['pan_file'] = instance.pan_file.url
            data['panFile'] = instance.pan_file.url
        else:
            data['pan_file'] = None
            data['panFile'] = None
        
        return data
    
    def update(self, instance, validated_data):
        request = self.context.get('request')
        if not request:
            return instance
        
        # Convert request.data to regular dict and handle arrays
        request_data = {}
        for key, value in request.data.items():
            if isinstance(value, list) and len(value) > 0:
                request_data[key] = value[0]
            elif isinstance(value, list):
                request_data[key] = ''
            else:
                request_data[key] = value
        
        field_mappings = {
            'applicantName': 'full_name',
            'proposalBy': 'proposal_submitted_by',
            'addressLine1': 'address_line_1',
            'addressLine2': 'address_line_2',
            'streetVillage': 'street_village',
            'landline': 'landline_number',
            'website': 'website_link',
            'ttdfCompany': 'company_as_per_guidelines',
        }
        
        for frontend_field, backend_field in field_mappings.items():
            if frontend_field in request_data:
                request_data[backend_field] = request_data[frontend_field]
        
        upsert_profile_and_user_from_submission(
            request.user, 
            request_data,
            files=request.FILES
        )
        
        for field in ['individual_pan', 'pan_file', 'subject', 'description']:
            if field in validated_data:
                setattr(instance, field, validated_data[field])
        
        instance.save()
        return instance


class ShareHolderDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShareHolder
        fields = '__all__'
        read_only_fields = ['id', 'form_submission']


class SubShareHolderDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubShareHolder
        fields = '__all__'
        read_only_fields = ['id', 'form_submission']


class RDStaffDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = RDStaff
        fields = '__all__'
        read_only_fields = ['id', 'form_submission']


class EquipmentDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Equipment
        fields = '__all__'
        read_only_fields = ['id', 'form_submission']


class TeamMemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = TeamMember
        fields = '__all__'
        read_only_fields = ['id', 'form_submission']


    def validate(self, attrs):
        # On update, don't count self
        qs = TeamMember.objects.filter(
            form_submission=attrs.get('form_submission'),
            name=attrs.get('name'),
            otherdetails=attrs.get('otherdetails')
        )
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                {"non_field_errors": [
                    "A team member with the same name and other Designation exists for this proposal."
                ]}
            )
        return attrs     


class ConsortiumPartnerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Collaborator
        fields = '__all__'
        read_only_fields = ['id', 'form_submission']
    
    def validate_collaborator_type(self, value):
        """Map frontend values to backend values for collaborator_type"""
        print(f"🔄 Mapping collaborator_type: '{value}'")
      
        mapping = {
            'Principal Applicant': 'principalApplicant',
            'Consortium Partner': 'consortiumPartner',
            'principalApplicant': 'principalApplicant',  
            'consortiumPartner': 'consortiumPartner',    
        }
        
        mapped_value = mapping.get(value)
        if mapped_value:
            print(f"   ✅ Mapped '{value}' → '{mapped_value}'")
            return mapped_value
        
      
        valid_backend_values = ['principalApplicant', 'consortiumPartner']
        if value in valid_backend_values:
            print(f"   ✅ Value '{value}' is already valid")
            return value
        
        print(f"   ❌ Invalid collaborator_type: '{value}'")
        raise serializers.ValidationError(
            f"Invalid collaborator type '{value}'. "
            f"Valid options: {list(mapping.keys())}"
        )
    
    def validate_ttdf_company(self, value):
        """Map frontend values to backend values for ttdf_company"""
        print(f"🔄 Mapping ttdf_company: '{value}'")
        
        
        mapping = {
         
            'R&D institutions, Section 8 companies / Societies, Central & State government entities / PSUs /Autonomous Bodies/SPVs / Limited liability partnerships': 'rnd_section8_govt',
            
            'R&D Institutions, Section 8 companies / Societies, Central & State government entities / PSUs /Autonomous Bodies/SPVs / Limited liability partnerships': 'rnd_section8_govt',
            
       
            'Domestic companies with focus on telecom R&D, Use case development': 'domestic_company',
            'Start-ups/MSMEs': 'startup_msme',
            'Academic institutions': 'academic',
            
       
            'domestic_company': 'domestic_company',
            'startup_msme': 'startup_msme',
            'academic': 'academic',
            'rnd_section8_govt': 'rnd_section8_govt',
            
       
            '': '',
            None: '',
        }
        
        if value in mapping:
            mapped_value = mapping[value]
            print(f"   ✅ Mapped '{value}' → '{mapped_value}'")
            return mapped_value
        
        
        print(f"   ⚠️ Unknown ttdf_company value: '{value}' - setting to empty string")
        return '' 
    
    def validate(self, data):
        """Enhanced validation with detailed debugging"""
        
        
       
        for key, value in data.items():
            print(f"   {key}: '{value}' (type: {type(value).__name__})")
        
        errors = {}
        
       
        contact_name = data.get('contact_person_name_collab')
        if not contact_name or str(contact_name).strip() == '':
            errors['contact_person_name_collab'] = 'Contact person name is required'
            print("❌ contact_person_name_collab is missing or empty")
        else:
            print(f"✅ contact_person_name_collab: '{contact_name}'")
        
        # 2. Handle collaborator_type mapping
        print("\n2️⃣ Processing collaborator_type...")
        collaborator_type = data.get('collaborator_type')
        if collaborator_type:
            try:
                mapped_type = self.validate_collaborator_type(collaborator_type)
                data['collaborator_type'] = mapped_type
                print(f"✅ Final collaborator_type: '{mapped_type}'")
            except serializers.ValidationError as e:
                errors['collaborator_type'] = str(e.detail[0])
                print(f"❌ collaborator_type validation failed: {e}")
        else:
            data['collaborator_type'] = 'principalApplicant'  # Default
            print("⚠️ No collaborator_type provided, using default: 'principalApplicant'")
        
        # 3. Handle ttdf_company mapping
        print("\n3️⃣ Processing ttdf_company...")
        ttdf_company = data.get('ttdf_company')
        if ttdf_company:
            try:
                mapped_company = self.validate_ttdf_company(ttdf_company)
                data['ttdf_company'] = mapped_company
                print(f"✅ Final ttdf_company: '{mapped_company}'")
            except serializers.ValidationError as e:
                errors['ttdf_company'] = str(e.detail[0])
                print(f"❌ ttdf_company validation failed: {e}")
        else:
            print("ℹ️ No ttdf_company provided (optional)")
        
        # 4. Check other fields
        print("\n4️⃣ Checking other fields...")
        other_fields = ['organization_name_collab', 'organization_type_collab', 'pan_file_name_collab', 'mou_file_name_collab']
        for field in other_fields:
            value = data.get(field, '')
            if value and str(value).strip():
                print(f"✅ {field}: '{value}'")
            else:
                print(f"ℹ️ {field}: empty (optional)")
        
        # 5. Final validation result
        if errors:
            print(f"\n❌ VALIDATION FAILED:")
            for field, error in errors.items():
                print(f"   {field}: {error}")
            print("🔍" * 50)
            raise serializers.ValidationError(errors)
        
        print(f"\n✅ VALIDATION PASSED - Final mapped data:")
        for key, value in data.items():
            print(f"   {key}: '{value}'")
        print("🔍" * 50)
        return data
    
    def to_representation(self, instance):
        """Convert backend values back to frontend display values"""
        data = super().to_representation(instance)
        
        # Reverse mapping for frontend display
        collaborator_type_reverse_mapping = {
            'principalApplicant': 'Principal Applicant',
            'consortiumPartner': 'Consortium Partner',
        }
        
        ttdf_company_reverse_mapping = {
            'domestic_company': 'Domestic companies with focus on telecom R&D, Use case development',
            'startup_msme': 'Start-ups/MSMEs',
            'academic': 'Academic institutions',
            'rnd_section8_govt': 'R&D institutions, Section 8 companies / Societies, Central & State government entities / PSUs /Autonomous Bodies/SPVs / Limited liability partnerships',
        }
        
        # Apply reverse mapping
        if instance.collaborator_type:
            data['collaborator_type'] = collaborator_type_reverse_mapping.get(
                instance.collaborator_type, 
                instance.collaborator_type
            )
        
        if instance.ttdf_company:
            data['ttdf_company'] = ttdf_company_reverse_mapping.get(
                instance.ttdf_company, 
                instance.ttdf_company
            )
        
        
        data.update({
            'contactPersonName': instance.contact_person_name_collab or '',
            'organizationName': instance.organization_name_collab or '',
            'organizationType': instance.organization_type_collab or '',
            'ttdfCompany': data['ttdf_company'], 
            'pan': instance.pan_file_name_collab or '',
            'panFileName': instance.pan_file_name_collab or '',
            'mouFileName': instance.mou_file_name_collab or '',
            'applicantType': data['collaborator_type'], 
        })
        
        # Handle file URLs
        if instance.pan_file_collab:
            data['panFilePreview'] = instance.pan_file_collab.url
            data['pan_file_collab'] = instance.pan_file_collab.url
        else:
            data['panFilePreview'] = None
            data['pan_file_collab'] = None
            
        if instance.mou_file_collab:
            data['mouFilePreview'] = instance.mou_file_collab.url
            data['mou_file_collab'] = instance.mou_file_collab.url
        else:
            data['mouFilePreview'] = None
            data['mou_file_collab'] = None
        
        return data

class ConsortiumPartnerDetailsSerializer(serializers.ModelSerializer):
    collaborators = ConsortiumPartnerSerializer(many=True, read_only=True)
    shareholders = ShareHolderDetailSerializer(many=True, read_only=True)
    sub_shareholders = SubShareHolderDetailSerializer(many=True, read_only=True)
    rdstaff = RDStaffDetailSerializer(many=True, read_only=True)
    equipments = EquipmentDetailSerializer(many=True, read_only=True)
    
    class Meta:
        model = FormSubmission
        fields = [
            'id', 'form_id', 'proposal_id', 'ttdf_applied_before',
            'collaborators', 'shareholders', 'sub_shareholders', 
            'rdstaff', 'equipments'
        ]
        read_only_fields = ['id', 'form_id', 'proposal_id']
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Ensure ttdf_applied_before is always present
        data['ttdf_applied_before'] = instance.ttdf_applied_before or ''
        data['appliedBefore'] = instance.ttdf_applied_before or ''  # Frontend field name
        return data

class ProposalDetailsSerializer(serializers.ModelSerializer):
    team_members = TeamMemberSerializer(many=True, read_only=True)
    
    class Meta:
        model = FormSubmission
        fields = [
            'id', 'form_id', 'proposal_id', 'status',
            'subject', 'description', 'proposal_brief', 'grant_to_turnover_ratio',
            'proposed_village', 'use_case', 'proposal_abstract',
            'potential_impact', 'end_to_end_solution', 'team',
            'data_security_measures', 'required_support_details',
            'model_village', 'team_members'
        ]
        read_only_fields = ['id', 'form_id', 'proposal_id']
    
    def update(self, instance, validated_data):
        """Custom update method to handle proposal details saving"""
        # Update all the proposal-related fields
        proposal_fields = [
            'proposal_brief', 'grant_to_turnover_ratio', 'proposed_village',
            'use_case', 'proposal_abstract', 'potential_impact', 
            'end_to_end_solution', 'team', 'data_security_measures',
            'required_support_details', 'model_village', 'subject', 'description'
        ]
        
        for field in proposal_fields:
            if field in validated_data:
                setattr(instance, field, validated_data[field])
        
        instance.save()
        return instance
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        
        
        field_mappings = {
            'proposal_brief': 'proposalBrief',
            'grant_to_turnover_ratio': 'grantToTurnoverRatio',
            'proposed_village': 'proposedVillage',
            'use_case': 'useCase',
            'potential_impact': 'potentialImpact',
            'end_to_end_solution': 'endToEndSolution',
            'data_security_measures': 'dataSecurityMeasures',
            'model_village': 'modelVillage',
            'proposal_abstract': 'proposalAbstract',
            'team': 'teamDetails',
            'required_support_details': 'supportDetails'
        }
        
        for backend_field, frontend_field in field_mappings.items():
            value = getattr(instance, backend_field, '') or ''
            data[backend_field] = value
            data[frontend_field] = value  
        
        return data


class FundDetailsSerializer(serializers.ModelSerializer):
    fund_loan_documents = serializers.SerializerMethodField()
    
    class Meta:
        model = FormSubmission
        fields = [
            'id', 'form_id', 'proposal_id', 'status',
            'has_loan', 'fund_loan_description', 'fund_loan_amount',
            'bank_name', 'bank_branch', 'bank_account_number', 
            'ifsc_code', 'account_type', 'fund_loan_documents'
        ]
        read_only_fields = ['id', 'form_id', 'proposal_id', 'fund_loan_documents']
    
    def get_fund_loan_documents(self, obj):
        return [{'id': doc.id, 'document': doc.document.url if doc.document else None} 
                for doc in obj.fund_loan_documents.all()]
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        
    
        field_mappings = {
            'has_loan': 'hasLoan',
            'fund_loan_description': 'loanDescription',
            'fund_loan_amount': 'loanAmount',
            'bank_name': 'bankName',
            'bank_branch': 'bankBranch',
            'bank_account_number': 'bankAccountNumber',
            'ifsc_code': 'ifscCode',
            'account_type': 'accountType'
        }
        
        for backend_field, frontend_field in field_mappings.items():
            value = getattr(instance, backend_field, '') or ''
            data[backend_field] = value
            data[frontend_field] = value
        
        return data


class BudgetEstimateSerializer(serializers.ModelSerializer):
    class Meta:
        model = FormSubmission
        fields = [
            'id', 'form_id', 'proposal_id', 'status',
            'budget_estimate', 'equipment_overhead', 'income_estimate',  
            'manpower_details', 'other_requirements'
        ]
        read_only_fields = ['id', 'form_id', 'proposal_id']
    
    def get_default_equipment_table(self):
        """Ensure equipment overhead always has proper structure"""
        return {
            "tables": [
                {
                    "id": "table-2",
                    "title": "Equipment Overhead",
                    "serviceOfferings": [
                        {
                            "id": "offering-1",
                            "name": "Enter Service Name...",
                            "items": [
                                {
                                    "id": "item-1",
                                    "description": "",
                                    "financials": {
                                        "capex": {
                                            "year0": {
                                                "description": "",
                                                "cost": 0,
                                                "qty": 0,
                                                "total": 0,
                                                "grant": 0,
                                                "remarks": "",
                                            },
                                        },
                                        "opex": {
                                            "year1": {
                                                "description": "",
                                                "cost": 0,
                                                "qty": 0,
                                                "total": 0,
                                                "grant": 0,
                                                "remarks": "",
                                            },
                                            "year2": {
                                                "description": "",
                                                "cost": 0,
                                                "qty": 0,
                                                "total": 0,
                                                "grant": 0,
                                                "remarks": "",
                                            },
                                        },
                                    },
                                },
                            ],
                        },
                    ],
                }
            ]
        }
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        
        # Handle JSON fields 
        data['budget_estimate'] = instance.budget_estimate or {}
        data['budgetEstimate'] = instance.budget_estimate or {}
        
        # 🔧 FIX: Ensure equipment_overhead always has proper structure
        equipment_overhead = instance.equipment_overhead or {}
        
        # If equipment_overhead is empty or missing tables, use default structure
        if not equipment_overhead or 'tables' not in equipment_overhead or not equipment_overhead['tables']:
            print("🔧 Equipment overhead missing or empty, using default structure")
            equipment_overhead = self.get_default_equipment_table()
        
        data['equipment_overhead'] = equipment_overhead
        
        data['income_estimate'] = instance.income_estimate or {}
        data['incomeEstimate'] = instance.income_estimate or {}
        data['manpower_details'] = instance.manpower_details or ''
        data['manpowerDetails'] = instance.manpower_details or ''
        data['other_requirements'] = instance.other_requirements or ''
        data['otherRequirements'] = instance.other_requirements or ''
        
        # Direct access to tables for backward compatibility
        if instance.budget_estimate and 'tables' in instance.budget_estimate:
            data['tables'] = instance.budget_estimate['tables']
        
        return data
    

class FinanceDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = FormSubmission
        fields = [
            'id', 'form_id', 'proposal_id', 'status','funds_requested','actual_contribution_applicant',
            'contribution_expected_source', 'contribution_item', 'contribution_amount',
            'fund_source_details', 'fund_item', 'fund_amount',
            'grant_from_ttdf', 'contribution_applicant', 'expected_other_contribution',
            'other_source_funding', 'total_project_cost', 'contribution_percentage',
            'grant_to_turnover_ratio',
         
            'contribution_rows', 'fund_rows'
        ]
        read_only_fields = ['id', 'form_id', 'proposal_id']
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        
 
        finance_fields = [
            'contribution_expected_source', 'contribution_item', 'contribution_amount',
            'fund_source_details', 'fund_item', 'fund_amount','funds_requested','actual_contribution_applicant',
            'grant_from_ttdf', 'contribution_applicant', 'expected_other_contribution',
            'other_source_funding', 'total_project_cost', 'contribution_percentage'
        ]
        
        for field in finance_fields:
            if data.get(field) is None:
                data[field] = ''
        
        
        data['contribution_rows'] = instance.contribution_rows or []
        data['fund_rows'] = instance.fund_rows or []
        data['contributionRows'] = instance.contribution_rows or []  
        data['fundRows'] = instance.fund_rows or []  
        
        return data
    
class ObjectiveTimelineSerializer(serializers.ModelSerializer):
    milestones = serializers.SerializerMethodField()
    
    class Meta:
        model = FormSubmission
        fields = [
            'id', 'form_id', 'proposal_id', 'status',
            'milestones' 
        ]
        read_only_fields = ['id', 'form_id', 'proposal_id', 'milestones']
    
    def get_milestones(self, obj):
        """Get milestone data from the milestone app"""
        milestones_data = []
        for milestone in obj.milestones.all().order_by('id'):
            milestones_data.append({
                'id': milestone.id,
                'title': milestone.title or '',
                'description': milestone.description or '',
                'activities': milestone.activities or '',
                'time_required': milestone.time_required or 0,
                'grant_from_ttdf': milestone.grant_from_ttdf or 0,
                'initial_contri_applicant': milestone.initial_contri_applicant or 0,
                'start_date': milestone.start_date.isoformat() if milestone.start_date else None,
                'due_date': milestone.due_date.isoformat() if milestone.due_date else None,
                'status': milestone.status or 'in_progress',
            })
        return milestones_data

class IPRDetailsSerializer(serializers.ModelSerializer):
    ipr_details = serializers.SerializerMethodField()
    
    class Meta:
        model = FormSubmission
        fields = [
            'id', 'form_id', 'proposal_id', 'status',
            'ipr_details'
        ]
        read_only_fields = ['id', 'form_id', 'proposal_id', 'ipr_details']
    
    def get_ipr_details(self, obj):
        ipr_data = []
        for ipr in obj.iprdetails.all():
            ipr_data.append({
                'id': ipr.id,
                'name': ipr.name or '',
                'national_importance': ipr.national_importance or '',
                'commercialization_potential': ipr.commercialization_potential or '',
                'risk_factors': ipr.risk_factors or '',
                'preliminary_work_done': ipr.preliminary_work_done or '',
                'technology_status': ipr.technology_status or '',
                'business_strategy': ipr.business_strategy or '',
                'based_on_ipr': ipr.based_on_ipr or '',
                'ip_ownership_details': ipr.ip_ownership_details or '',
                'ip_proposal': ipr.ip_proposal or '',
                'regulatory_approvals': ipr.regulatory_approvals or '',
                'status_approvals': ipr.status_approvals or '',
                'proof_of_status': ipr.proof_of_status.url if ipr.proof_of_status else None,
                't_name': ipr.t_name or '',
                't_designation': ipr.t_designation or '',
                't_mobile_number': ipr.t_mobile_number or '',
                't_email': ipr.t_email or '',
                't_address': ipr.t_address or '',
                't_support_letter': ipr.t_support_letter.url if ipr.t_support_letter else None,
            })
        return ipr_data


class ProjectDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = FormSubmission
        fields = [
            'id', 'form_id', 'proposal_id', 'status',
            'network_core', 'radio_access_network', 'fixed_wireless_access',
            'civil_electrical_infrastructure', 'centralised_servers_and_edge_analytics',
            'passive_components', 'software_components', 'sensor_network_costs',
            'installation_infrastructure_and_commissioning', 'operation_maintenance_and_warranty',
            'total_proposal_cost', 
            # ALL THREE FILE FIELDS
            'gantt_chart', 'technical_proposal', 'proposal_presentation'
        ]
        read_only_fields = ['id', 'form_id', 'proposal_id']
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        
        file_field_mapping = {
           
            'gantt_chart': 'ganttChart',
            'technical_proposal': 'dpr',  
            'proposal_presentation': 'presentation',  
        }
        
        for backend_field, frontend_field in file_field_mapping.items():
            file_obj = getattr(instance, backend_field, None)
            if file_obj:
                data[backend_field] = file_obj.url
                data[frontend_field] = file_obj.url  
            else:
                data[backend_field] = None
                data[frontend_field] = None
        
       
        cost_fields = [
            'network_core', 'radio_access_network', 'fixed_wireless_access',
            'civil_electrical_infrastructure', 'centralised_servers_and_edge_analytics',
            'passive_components', 'software_components', 'sensor_network_costs',
            'installation_infrastructure_and_commissioning', 'operation_maintenance_and_warranty',
            'total_proposal_cost'
        ]
        
        for field in cost_fields:
            if data.get(field) is None:
                data[field] = ''
        
        return data

class DeclarationSerializer(serializers.ModelSerializer):
    class Meta:
        model = FormSubmission
        fields = [
            'id', 'form_id', 'proposal_id', 'status',
            'declaration_document', 'declaration_1', 'declaration_2',
            'declaration_3', 'declaration_4', 'declaration_5'
        ]
        read_only_fields = ['id', 'form_id', 'proposal_id']
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        
        # Handle file field
        if instance.declaration_document:
            data['declaration_document'] = instance.declaration_document.url
        else:
            data['declaration_document'] = None
        
      
        for i in range(1, 6):
            field = f'declaration_{i}'
            if data.get(field) is None:
                data[field] = False
        
        return data