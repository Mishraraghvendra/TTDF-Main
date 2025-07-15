# dynamic_form/form_views.py 
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from milestones.models import Milestone
from django.shortcuts import get_object_or_404
from .models import (
    FormSubmission, Collaborator, Equipment, ShareHolder,
    SubShareHolder, RDStaff, IPRDetails, TeamMember
)
from .form_serializers import (
    BasicDetailsSerializer, ConsortiumPartnerDetailsSerializer,
    ProposalDetailsSerializer, FundDetailsSerializer, BudgetEstimateSerializer,
    FinanceDetailsSerializer, ObjectiveTimelineSerializer, IPRDetailsSerializer,
    ProjectDetailsSerializer, DeclarationSerializer,
    ConsortiumPartnerSerializer, ShareHolderDetailSerializer,
    SubShareHolderDetailSerializer, RDStaffDetailSerializer, EquipmentDetailSerializer,
    TeamMemberSerializer
)
from users.utils import upsert_profile_and_user_from_submission


class FormSectionViewSet(viewsets.ViewSet):
    """Base viewset for form sections"""
    permission_classes = [IsAuthenticated]
    
    def get_submission(self, submission_id):
        """Get form submission for current user"""
        return get_object_or_404(
            FormSubmission, 
            id=submission_id, 
            applicant=self.request.user
        )
    
    def get_or_create_submission(self, template_id=None, service_id=None):
        """Create new submission - don't reuse existing drafts"""
        
        if not template_id:
            return None
       
        from .models import FormTemplate
        from configuration.models import Service
        
        template = get_object_or_404(FormTemplate, id=template_id)
        service = get_object_or_404(Service, id=service_id) if service_id else None
        
        # Create new submission
        submission = FormSubmission.objects.create(
            template=template,
            service=service,
            applicant=self.request.user,
            status=FormSubmission.DRAFT
        )
        
        return submission


class BasicDetailsViewSet(FormSectionViewSet):
    """Section 1: Basic Details API"""
    
    @action(detail=False, methods=['get'], url_path='retrieve')
    def get_basic_details(self, request):
        """Get basic details for current user's submission"""
        submission_id = request.query_params.get('submission_id')
        if not submission_id:
            return Response(
                {'error': 'submission_id is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        submission = self.get_submission(submission_id)
        serializer = BasicDetailsSerializer(submission)
        return Response({
            'success': True,
            'data': serializer.data
        })
    
    @action(detail=False, methods=['post', 'patch'], url_path='update')
    def update_basic_details(self, request):
        """Update basic details"""
        submission_id = request.data.get('submission_id')
        template_id = request.data.get('template_id')
        service_id = request.data.get('service_id')
        
        if submission_id:
            submission = self.get_submission(submission_id)
        else:
            submission = self.get_or_create_submission(template_id, service_id)
        
        serializer = BasicDetailsSerializer(
            submission, 
            data=request.data, 
            partial=True,
            context={'request': request}
        )
        
        if serializer.is_valid():
            with transaction.atomic():
                serializer.save()
                return Response({
                    'success': True,
                    'message': 'Basic details saved successfully',
                    'data': serializer.data
                })
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class ConsortiumPartnerViewSet(FormSectionViewSet):
    """Section 2: Consortium Partner Details API"""
    
    @action(detail=False, methods=['get'], url_path='retrieve')
    def get_consortium_details(self, request):
        """Get consortium partner details"""
        submission_id = request.query_params.get('submission_id')
        if not submission_id:
            return Response({'error': 'submission_id is required'}, status=400)
        
        submission = self.get_submission(submission_id)
        serializer = ConsortiumPartnerDetailsSerializer(submission)
        return Response({
            'success': True,
            'data': serializer.data
        })
    
    @action(detail=False, methods=['post'])
    def add_collaborator(self, request):
        """Add new collaborator with detailed debugging"""
        print("\n" + "="*60)
        print("🚀 ADD_COLLABORATOR API CALLED")
        print("="*60)
        
        # Print request details
        print(f"📥 Request Method: {request.method}")
        print(f"📥 Content Type: {request.content_type}")
        print(f"📥 User: {request.user}")
        
        # Print ALL request data
        print(f"\n📋 Request.data contents:")
        if hasattr(request.data, 'items'):
            for key, value in request.data.items():
                print(f"   {key}: {value} (type: {type(value)})")
        else:
            print(f"   Raw data: {request.data}")
        
        # Print ALL request files
        print(f"\n📎 Request.FILES contents:")
        if hasattr(request.FILES, 'items'):
            for key, file in request.FILES.items():
                print(f"   {key}: {file.name if hasattr(file, 'name') else file} (size: {file.size if hasattr(file, 'size') else 'unknown'})")
        else:
            print(f"   Raw files: {request.FILES}")
        
        
        submission_id = request.data.get('submission_id')
        print(f"\n🔍 Checking submission_id: {submission_id}")
        
        if not submission_id:
            print("❌ submission_id is missing!")
            return Response({
                'success': False,
                'errors': {'submission_id': 'submission_id is required'}
            }, status=status.HTTP_400_BAD_REQUEST)
        
 
        try:
            submission = self.get_submission(submission_id)
            print(f"✅ Found submission: {submission.id} (Status: {submission.status})")
        except Exception as e:
            print(f"❌ Submission lookup failed: {e}")
            return Response({
                'success': False,
                'errors': {'submission_id': f'Invalid submission_id: {str(e)}'}
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check required field before serializer
        contact_name = request.data.get('contact_person_name_collab')
        print(f"\n🔍 Pre-validation check - contact_person_name_collab: '{contact_name}'")
        
        if not contact_name or str(contact_name).strip() == '':
            print("❌ Contact person name is empty!")
            return Response({
                'success': False,
                'errors': {'contact_person_name_collab': 'Contact person name is required and cannot be empty'}
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Create serializer
        print(f"\n🔄 Creating serializer with request.data...")
        serializer = ConsortiumPartnerSerializer(data=request.data)
        
        print(f"🔄 Running serializer.is_valid()...")
        if serializer.is_valid():
            print("✅ Serializer validation PASSED")
            
            try:
                print(f"🔄 Saving collaborator to database...")
                collaborator = serializer.save(form_submission=submission)
                print(f"✅ Successfully saved collaborator with ID: {collaborator.id}")
                
                response_data = {
                    'success': True,
                    'message': 'Collaborator added successfully',
                    'data': serializer.data
                }
                print(f"📤 Returning success response: {response_data}")
                return Response(response_data)
                
            except Exception as save_error:
                print(f"❌ Database save error: {save_error}")
                print(f"   Error type: {type(save_error)}")
                import traceback
                print(f"   Traceback: {traceback.format_exc()}")
                
                return Response({
                    'success': False,
                    'errors': {'database_error': f'Failed to save: {str(save_error)}'}
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        else:
            print("❌ Serializer validation FAILED")
            print(f"📋 Detailed serializer errors:")
            for field, errors in serializer.errors.items():
                print(f"   {field}: {errors}")
            
            return Response({
                'success': False,
                'message': 'Validation failed',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['patch'])
    def update_collaborator(self, request):
        """Update existing collaborator with enhanced debugging"""
        print("\n" + "="*60)
        print("🔄 UPDATE_COLLABORATOR API CALLED")
        print("="*60)
        
        # Print request details
        print(f"📥 Request Method: {request.method}")
        print(f"📥 Content Type: {request.content_type}")
        print(f"📥 User: {request.user}")
        
        # Print ALL request data
        print(f"\n📋 Request.data contents:")
        if hasattr(request.data, 'items'):
            for key, value in request.data.items():
                print(f"   {key}: {value} (type: {type(value)})")
        else:
            print(f"   Raw data: {request.data}")
        
        # Print ALL request files
        print(f"\n📎 Request.FILES contents:")
        if hasattr(request.FILES, 'items'):
            for key, file in request.FILES.items():
                print(f"   {key}: {file.name if hasattr(file, 'name') else file}")
        else:
            print(f"   Raw files: {request.FILES}")
        
        # Check collaborator_id
        collaborator_id = request.data.get('collaborator_id')
        print(f"\n🔍 Checking collaborator_id: {collaborator_id}")
        
        if not collaborator_id:
            print("❌ collaborator_id is missing!")
            return Response({
                'success': False,
                'errors': {'collaborator_id': 'collaborator_id is required for update'}
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Try to get collaborator
        try:
            collaborator = get_object_or_404(
                Collaborator, 
                id=collaborator_id,
                form_submission__applicant=request.user
            )
            print(f"✅ Found collaborator: {collaborator.id} (Contact: {collaborator.contact_person_name_collab})")
        except Exception as e:
            print(f"❌ Collaborator lookup failed: {e}")
            return Response({
                'success': False,
                'errors': {'collaborator_id': f'Invalid collaborator_id or permission denied: {str(e)}'}
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check required field before serializer
        contact_name = request.data.get('contact_person_name_collab')
        print(f"\n🔍 Pre-validation check - contact_person_name_collab: '{contact_name}'")
        
        if not contact_name or str(contact_name).strip() == '':
            print("❌ Contact person name is empty!")
            return Response({
                'success': False,
                'errors': {'contact_person_name_collab': 'Contact person name is required and cannot be empty'}
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Create serializer for update
        print(f"\n🔄 Creating serializer for update with request.data...")
        serializer = ConsortiumPartnerSerializer(
            collaborator, 
            data=request.data, 
            partial=True  
        )
        
        print(f"🔄 Running serializer.is_valid()...")
        if serializer.is_valid():
            print("✅ Serializer validation PASSED")
            
            try:
                print(f"🔄 Updating collaborator in database...")
                updated_collaborator = serializer.save()
                print(f"✅ Successfully updated collaborator with ID: {updated_collaborator.id}")
                
                response_data = {
                    'success': True,
                    'message': 'Collaborator updated successfully',
                    'data': serializer.data
                }
                print(f"📤 Returning success response")
                return Response(response_data)
                
            except Exception as save_error:
                print(f"❌ Database save error: {save_error}")
                print(f"   Error type: {type(save_error)}")
                import traceback
                print(f"   Traceback: {traceback.format_exc()}")
                
                return Response({
                    'success': False,
                    'errors': {'database_error': f'Failed to update: {str(save_error)}'}
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        else:
            print("❌ Serializer validation FAILED")
            print(f"📋 Detailed serializer errors:")
            for field, errors in serializer.errors.items():
                print(f"   {field}: {errors}")
            
            return Response({
                'success': False,
                'message': 'Validation failed',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['patch'])
    def update_shareholder(self, request):
        """Update existing shareholder"""
        shareholder_id = request.data.get('shareholder_id')
        shareholder = get_object_or_404(
            ShareHolder, 
            id=shareholder_id,
            form_submission__applicant=request.user
        )
        
        serializer = ShareHolderDetailSerializer(
            shareholder, 
            data=request.data, 
            partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response({
                'success': True,
                'message': 'Shareholder updated successfully',
                'data': serializer.data
            })
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=400)
    
    @action(detail=False, methods=['post'])
    def add_sub_shareholder(self, request):
        """Add a new sub-shareholder"""
        try:
            submission_id = request.data.get('submission_id')
            if not submission_id:
                return Response({'success': False, 'message': 'submission_id is required'}, 
                              status=status.HTTP_400_BAD_REQUEST)

            try:
                submission = FormSubmission.objects.get(id=submission_id)
            except FormSubmission.DoesNotExist:
                return Response({'success': False, 'message': 'Submission not found'}, 
                              status=status.HTTP_404_NOT_FOUND)

            # Create sub-shareholder
            sub_shareholder_data = {
                'form_submission': submission,
                'share_holder_name': request.data.get('share_holder_name', ''),
                'share_percentage': request.data.get('share_percentage', 0),
                'identity_document_name': request.data.get('identity_document_name', ''),
                'organization_name_subholder': request.data.get('organization_name_subholder', ''),
            }

            sub_shareholder = SubShareHolder.objects.create(**sub_shareholder_data)

            # Handle file upload
            if 'identity_document' in request.FILES:
                sub_shareholder.identity_document = request.FILES['identity_document']
                sub_shareholder.save()

            return Response({
                'success': True, 
                'message': 'Sub-shareholder added successfully',
                'data': {'id': sub_shareholder.id}
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({'success': False, 'message': str(e)}, 
                          status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['patch'])
    def update_sub_shareholder(self, request):
        """Update an existing sub-shareholder"""
        try:
            sub_shareholder_id = request.data.get('sub_shareholder_id')
            if not sub_shareholder_id:
                return Response({'success': False, 'message': 'sub_shareholder_id is required'}, 
                              status=status.HTTP_400_BAD_REQUEST)

            try:
                sub_shareholder = SubShareHolder.objects.get(id=sub_shareholder_id)
            except SubShareHolder.DoesNotExist:
                return Response({'success': False, 'message': 'Sub-shareholder not found'}, 
                              status=status.HTTP_404_NOT_FOUND)

            # Update fields
            sub_shareholder.share_holder_name = request.data.get('share_holder_name', sub_shareholder.share_holder_name)
            sub_shareholder.share_percentage = request.data.get('share_percentage', sub_shareholder.share_percentage)
            sub_shareholder.identity_document_name = request.data.get('identity_document_name', sub_shareholder.identity_document_name)
            sub_shareholder.organization_name_subholder = request.data.get('organization_name_subholder', sub_shareholder.organization_name_subholder)

            # Handle file upload
            if 'identity_document' in request.FILES:
                sub_shareholder.identity_document = request.FILES['identity_document']

            sub_shareholder.save()

            return Response({
                'success': True, 
                'message': 'Sub-shareholder updated successfully'
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'success': False, 'message': str(e)}, 
                          status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['delete'])
    def delete_sub_shareholder(self, request):
        """Delete a sub-shareholder"""
        try:
            sub_shareholder_id = request.query_params.get('sub_shareholder_id')
            if not sub_shareholder_id:
                return Response({'success': False, 'message': 'sub_shareholder_id is required'}, 
                              status=status.HTTP_400_BAD_REQUEST)

            try:
                sub_shareholder = SubShareHolder.objects.get(id=sub_shareholder_id)
            except SubShareHolder.DoesNotExist:
                return Response({'success': False, 'message': 'Sub-shareholder not found'}, 
                              status=status.HTTP_404_NOT_FOUND)

            sub_shareholder.delete()

            return Response({
                'success': True, 
                'message': 'Sub-shareholder deleted successfully'
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'success': False, 'message': str(e)}, 
                          status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['delete'])
    def delete_shareholder(self, request):
        """Delete shareholder"""
        shareholder_id = request.query_params.get('shareholder_id')
        shareholder = get_object_or_404(
            ShareHolder, 
            id=shareholder_id,
            form_submission__applicant=request.user
        )
        shareholder.delete()
        return Response({
            'success': True,
            'message': 'Shareholder deleted successfully'
        })

    @action(detail=False, methods=['patch'])
    def update_rdstaff(self, request):
        """Update existing R&D staff"""
        staff_id = request.data.get('staff_id')
        staff = get_object_or_404(
            RDStaff, 
            id=staff_id,
            form_submission__applicant=request.user
        )
        
        serializer = RDStaffDetailSerializer(
            staff, 
            data=request.data, 
            partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response({
                'success': True,
                'message': 'R&D Staff updated successfully',
                'data': serializer.data
            })
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=400)

    @action(detail=False, methods=['delete'])
    def delete_rdstaff(self, request):
        """Delete R&D staff"""
        staff_id = request.query_params.get('staff_id')
        staff = get_object_or_404(
            RDStaff, 
            id=staff_id,
            form_submission__applicant=request.user
        )
        staff.delete()
        return Response({
            'success': True,
            'message': 'R&D Staff deleted successfully'
        })

    @action(detail=False, methods=['patch'])
    def update_equipment(self, request):
        """Update existing equipment"""
        equipment_id = request.data.get('equipment_id')
        equipment = get_object_or_404(
            Equipment, 
            id=equipment_id,
            form_submission__applicant=request.user
        )
        
        serializer = EquipmentDetailSerializer(
            equipment, 
            data=request.data, 
            partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response({
                'success': True,
                'message': 'Equipment updated successfully',
                'data': serializer.data
            })
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=400)

    @action(detail=False, methods=['delete'])
    def delete_equipment(self, request):
        """Delete equipment"""
        equipment_id = request.query_params.get('equipment_id')
        equipment = get_object_or_404(
            Equipment, 
            id=equipment_id,
            form_submission__applicant=request.user
        )
        equipment.delete()
        return Response({
            'success': True,
            'message': 'Equipment deleted successfully'
        })

    @action(detail=False, methods=['delete'])
    def delete_collaborator(self, request):
        """Delete collaborator"""
        collaborator_id = request.query_params.get('collaborator_id')
        collaborator = get_object_or_404(
            Collaborator, 
            id=collaborator_id,
            form_submission__applicant=request.user
        )
        collaborator.delete()
        return Response({
            'success': True,
            'message': 'Collaborator deleted successfully'
        })
    
    @action(detail=False, methods=['post'])
    def add_shareholder(self, request):
        """Add new shareholder"""
        submission_id = request.data.get('submission_id')
        submission = self.get_submission(submission_id)
        
        serializer = ShareHolderDetailSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(form_submission=submission)
            return Response({
                'success': True,
                'message': 'Shareholder added successfully',
                'data': serializer.data
            })
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=400)
    
    @action(detail=False, methods=['post'])
    def add_rdstaff(self, request):
        """Add new R&D staff"""
        submission_id = request.data.get('submission_id')
        submission = self.get_submission(submission_id)
        
        serializer = RDStaffDetailSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(form_submission=submission)
            return Response({
                'success': True,
                'message': 'R&D Staff added successfully',
                'data': serializer.data
            })
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=400)
    
    @action(detail=False, methods=['post'])
    def add_equipment(self, request):
        """Add new equipment"""
        submission_id = request.data.get('submission_id')
        submission = self.get_submission(submission_id)
        
        serializer = EquipmentDetailSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(form_submission=submission)
            return Response({
                'success': True,
                'message': 'Equipment added successfully',
                'data': serializer.data
            })
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=400)
    
    @action(detail=False, methods=['patch'])
    def update_general(self, request):
        """Update general consortium partner fields like ttdf_applied_before"""
        submission_id = request.data.get('submission_id')
        submission = self.get_submission(submission_id)
        
        # Update only the specific fields in FormSubmission
        allowed_fields = ['ttdf_applied_before']
        for field in allowed_fields:
            if field in request.data:
                setattr(submission, field, request.data[field])
        
        submission.save()
        
        serializer = ConsortiumPartnerDetailsSerializer(submission)
        return Response({
            'success': True,
            'message': 'Consortium partner details updated successfully',
            'data': serializer.data
        })


class ProposalDetailsViewSet(FormSectionViewSet):
    """Section 3: Proposal Details API"""
    
    @action(detail=False, methods=['get'], url_path='retrieve')
    def get_proposal_details(self, request):
        submission_id = request.query_params.get('submission_id')
        submission = self.get_submission(submission_id)
        serializer = ProposalDetailsSerializer(submission)
        return Response({'success': True, 'data': serializer.data})
    
    @action(detail=False, methods=['post', 'patch'], url_path='update')
    def update_proposal_details(self, request):
        submission_id = request.data.get('submission_id')
        submission = self.get_submission(submission_id)
        
        print(f"\n🔍 PROPOSAL DETAILS UPDATE DEBUG:")
        print(f"   Submission ID: {submission_id}")
        print(f"   Request data keys: {list(request.data.keys())}")
        print(f"   Request data: {dict(request.data)}")
        
        serializer = ProposalDetailsSerializer(
            submission, 
            data=request.data, 
            partial=True
        )
        
        print(f"   Serializer validation...")
        if serializer.is_valid():
            print(f"   ✅ Serializer valid")
            print(f"   Validated data: {serializer.validated_data}")
            
            try:
                updated_instance = serializer.save()
                print(f"   ✅ Saved successfully")
                
                return Response({
                    'success': True,
                    'message': 'Proposal details saved successfully',
                    'data': serializer.data
                })
            except Exception as save_error:
                print(f"   ❌ Save error: {save_error}")
                return Response({
                    'success': False,
                    'message': f'Save error: {str(save_error)}'
                }, status=500)
        else:
            print(f"   ❌ Serializer errors: {serializer.errors}")
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=400)
    
    @action(detail=False, methods=['post'])
    def add_team_member(self, request):
        """Add new team member"""
        submission_id = request.data.get('submission_id')
        submission = self.get_submission(submission_id)
        
        serializer = TeamMemberSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(form_submission=submission)
            return Response({
                'success': True,
                'message': 'Team member added successfully',
                'data': serializer.data
            })
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=400)
    
    @action(detail=False, methods=['patch'])
    def update_team_member(self, request):
        """Update existing team member"""
        team_member_id = request.data.get('team_member_id')
        team_member = get_object_or_404(
            TeamMember, 
            id=team_member_id,
            form_submission__applicant=request.user
        )
        
        serializer = TeamMemberSerializer(
            team_member, 
            data=request.data, 
            partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response({
                'success': True,
                'message': 'Team member updated successfully',
                'data': serializer.data
            })
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=400)
    
    @action(detail=False, methods=['delete'])
    def delete_team_member(self, request):
        """Delete team member"""
        team_member_id = request.query_params.get('team_member_id')
        team_member = get_object_or_404(
            TeamMember, 
            id=team_member_id,
            form_submission__applicant=request.user
        )
        team_member.delete()
        return Response({
            'success': True,
            'message': 'Team member deleted successfully'
        })


class FundDetailsViewSet(FormSectionViewSet):
    """Section 4: Fund Details API"""
    
    @action(detail=False, methods=['get'], url_path='retrieve')
    def get_fund_details(self, request):
        submission_id = request.query_params.get('submission_id')
        submission = self.get_submission(submission_id)
        serializer = FundDetailsSerializer(submission)
        return Response({'success': True, 'data': serializer.data})
    
    @action(detail=False, methods=['post', 'patch'], url_path='update')
    def update_fund_details(self, request):
        submission_id = request.data.get('submission_id')
        submission = self.get_submission(submission_id)
        
        serializer = FundDetailsSerializer(
            submission, 
            data=request.data, 
            partial=True
        )
        
        if serializer.is_valid():
            serializer.save()
            return Response({
                'success': True,
                'message': 'Fund details saved successfully',
                'data': serializer.data
            })
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=400)


class BudgetEstimateViewSet(FormSectionViewSet):
    """Section 5: Budget Estimate API"""
    
    @action(detail=False, methods=['get'], url_path='retrieve')
    def get_budget_estimate(self, request):
        submission_id = request.query_params.get('submission_id')
        submission = self.get_submission(submission_id)
        serializer = BudgetEstimateSerializer(submission)
        return Response({'success': True, 'data': serializer.data})
    
    @action(detail=False, methods=['post', 'patch'], url_path='update')
    def update_budget_estimate(self, request):
        submission_id = request.data.get('submission_id')
        submission = self.get_submission(submission_id)
        
        serializer = BudgetEstimateSerializer(
            submission, 
            data=request.data, 
            partial=True
        )
        
        if serializer.is_valid():
            serializer.save()
            return Response({
                'success': True,
                'message': 'Budget estimate saved successfully',
                'data': serializer.data
            })
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=400)


class FinanceDetailsViewSet(FormSectionViewSet):
    """Section 6: Finance Details API"""
    
    @action(detail=False, methods=['get'], url_path='retrieve')
    def get_finance_details(self, request):
        submission_id = request.query_params.get('submission_id')
        submission = self.get_submission(submission_id)
        serializer = FinanceDetailsSerializer(submission)
        return Response({'success': True, 'data': serializer.data})
    
    @action(detail=False, methods=['post', 'patch'], url_path='update')
    def update_finance_details(self, request):
        submission_id = request.data.get('submission_id')
        submission = self.get_submission(submission_id)
        
        serializer = FinanceDetailsSerializer(
            submission, 
            data=request.data, 
            partial=True
        )
        
        if serializer.is_valid():
            serializer.save()
            return Response({
                'success': True,
                'message': 'Finance details saved successfully',
                'data': serializer.data
            })
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=400)


class ObjectiveTimelineViewSet(FormSectionViewSet):
    """Section 7: Objective-wise Timelines API"""
    
    @action(detail=False, methods=['get'], url_path='retrieve')
    def get_timeline_details(self, request):
        """Get timeline details for a submission"""
        submission_id = request.query_params.get('submission_id')
        if not submission_id:
            return Response({
                'success': False,
                'error': 'submission_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)
            
        submission = self.get_submission(submission_id)
        serializer = ObjectiveTimelineSerializer(submission)
        return Response({
            'success': True, 
            'data': serializer.data
        })
    
    @action(detail=False, methods=['post', 'patch'], url_path='update')
    def update_timeline_details(self, request):
        """Update timeline details with enhanced milestone handling"""
        submission_id = request.data.get('submission_id')
        if not submission_id:
            return Response({
                'success': False,
                'error': 'submission_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)
            
        submission = self.get_submission(submission_id)
        
        print(f"\n🔍 OBJECTIVE TIMELINE UPDATE DEBUG:")
        print(f"   Submission ID: {submission_id}")
        print(f"   Request data keys: {list(request.data.keys())}")
        
        # Handle milestone data - check both 'milestones' and 'milestoneData'
        milestone_data = request.data.get('milestones', request.data.get('milestoneData', []))
        print(f"   Raw milestone data type: {type(milestone_data)}")
        print(f"   Raw milestone data: {milestone_data}")
        
        # Handle case where milestone_data comes as JSON string
        if isinstance(milestone_data, str):
            try:
                import json
                milestone_data = json.loads(milestone_data)
                print(f"   ✅ Successfully parsed JSON string to list")
            except json.JSONDecodeError as e:
                print(f"   ❌ Failed to parse JSON: {e}")
                return Response({
                    'success': False,
                    'error': f'Invalid JSON in milestones: {str(e)}'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        # Ensure milestone_data is a list
        if not isinstance(milestone_data, list):
            print(f"   ❌ milestone_data is not a list: {type(milestone_data)}")
            return Response({
                'success': False,
                'error': 'Milestones must be a list'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        print(f"   Final milestone data: {milestone_data}")
        
        # Filter out empty milestones BEFORE processing
        valid_milestones = []
        for i, milestone_info in enumerate(milestone_data):
            if not isinstance(milestone_info, dict):
                continue
                
            # Check for actual content
            scope_of_work = (
                milestone_info.get('scopeOfWork') or 
                milestone_info.get('milestoneName') or 
                milestone_info.get('title') or 
                ""
            ).strip()
            
            activities = milestone_info.get('activities', '').strip()
            time_required = milestone_info.get('timeRequiredMonths') or milestone_info.get('timeRequired') or 0
            
            # Only include milestones with actual content
            if scope_of_work and activities and float(time_required) > 0:
                valid_milestones.append({
                    'index': i,
                    'data': milestone_info,
                    'scope_of_work': scope_of_work,
                    'activities': activities,
                    'time_required': float(time_required)
                })
                print(f"   ✅ Valid milestone {i+1}: {scope_of_work}")
            else:
                print(f"   ⏭️ Skipping incomplete milestone {i+1}")
        
        try:
            with transaction.atomic():
                # Get existing milestones for this proposal
                existing_milestones = {
                    m.id: m for m in Milestone.objects.filter(proposal=submission)
                }
                processed_milestone_ids = set()
                
                print(f"   📋 Found {len(existing_milestones)} existing milestones")
                print(f"   📋 Processing {len(valid_milestones)} valid new milestones")
                
                # Process each valid milestone
                for milestone_info in valid_milestones:
                    milestone_data_item = milestone_info['data']
                    scope_of_work = milestone_info['scope_of_work']
                    
                    print(f"   🔄 Processing milestone: {scope_of_work}")
                    
                    # Extract other milestone data
                    description = milestone_data_item.get('description', '').strip()
                    activities = milestone_info['activities']
                    time_required = milestone_info['time_required']
                    
                    # Handle grant amounts
                    grant_from_ttdf = float(milestone_data_item.get('ttdfGrantINR') or 
                                          milestone_data_item.get('grantFromTtdf') or 0)
                    
                    # Handle applicant contribution
                    initial_contri_applicant = float(milestone_data_item.get('applicantContributionINR') or 
                                                   milestone_data_item.get('initialContriApplicant') or 0)
                    
                    # Handle dates
                    start_date = milestone_data_item.get('startDate')
                    due_date = (milestone_data_item.get('endDate') or 
                              milestone_data_item.get('dueDate'))
                    
                    # Check if this is an update to existing milestone
                    milestone_id = milestone_data_item.get('id')
                    existing_milestone = None
                    
                    if milestone_id and milestone_id in existing_milestones:
                        existing_milestone = existing_milestones[milestone_id]
                        processed_milestone_ids.add(milestone_id)
                        print(f"   🔄 Updating existing milestone {milestone_id}")
                    else:
                        print(f"   ➕ Creating new milestone")
                    
                    # Create or update milestone
                    if existing_milestone:
                        # Update existing milestone
                        existing_milestone.title = scope_of_work
                        existing_milestone.description = description
                        existing_milestone.activities = activities
                        existing_milestone.time_required = int(time_required)
                        existing_milestone.grant_from_ttdf = int(grant_from_ttdf)
                        existing_milestone.initial_contri_applicant = int(initial_contri_applicant)
                        existing_milestone.start_date = start_date
                        existing_milestone.due_date = due_date
                        existing_milestone.updated_by = request.user
                        existing_milestone.save()
                        
                        print(f"   ✅ Updated milestone {existing_milestone.id}: {existing_milestone.title}")
                    else:
                        # Create new milestone
                        milestone = Milestone.objects.create(
                            proposal=submission,
                            title=scope_of_work,
                            description=description,
                            activities=activities,
                            time_required=int(time_required),
                            grant_from_ttdf=int(grant_from_ttdf),
                            initial_contri_applicant=int(initial_contri_applicant),
                            start_date=start_date,
                            due_date=due_date,
                            status='in_progress',
                            created_by=request.user
                        )
                        processed_milestone_ids.add(milestone.id)
                        print(f"   ✅ Created milestone {milestone.id}: {milestone.title}")
                
                # Delete milestones that are no longer in the form
                milestones_to_delete = set(existing_milestones.keys()) - processed_milestone_ids
                if milestones_to_delete:
                    deleted_count = Milestone.objects.filter(
                        id__in=milestones_to_delete,
                        proposal=submission
                    ).delete()[0]
                    print(f"   🗑️ Deleted {deleted_count} removed milestones: {milestones_to_delete}")
                
                print(f"   ✅ Successfully processed {len(valid_milestones)} milestones")
                
        except Exception as e:
            print(f"   ❌ Error saving milestones: {e}")
            import traceback
            print(f"   Traceback: {traceback.format_exc()}")
            return Response({
                'success': False,
                'error': f'Error saving milestones: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Get updated data
        serializer = ObjectiveTimelineSerializer(submission)
        
        return Response({
            'success': True,
            'message': f'Timeline details saved successfully ({len(valid_milestones)} milestones processed)',
            'data': serializer.data
        })
    
    @action(detail=False, methods=['post'])
    def clear_auto_generated_milestones(self, request):
        """Clear auto-generated milestone names for a submission"""
        submission_id = request.data.get('submission_id')
        if not submission_id:
            return Response({
                'success': False,
                'error': 'submission_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        submission = self.get_submission(submission_id)
        
        # Find milestones with auto-generated names
        import re
        auto_generated_milestones = Milestone.objects.filter(
            proposal=submission,
            title__regex=r'^Milestone \d+$'
        )
        
        count = auto_generated_milestones.count()
        if count > 0:
            # Delete the auto-generated milestones entirely
            auto_generated_milestones.delete()
            
            return Response({
                'success': True,
                'message': f'Deleted {count} auto-generated milestones'
            })
        else:
            return Response({
                'success': True,
                'message': 'No auto-generated milestones found'
            })
class IPRDetailsViewSet(FormSectionViewSet):
    """Section 8: IPR Details API"""
    
    @action(detail=False, methods=['get'], url_path='retrieve')
    def get_ipr_details(self, request):
        submission_id = request.query_params.get('submission_id')
        submission = self.get_submission(submission_id)
        serializer = IPRDetailsSerializer(submission)
        return Response({'success': True, 'data': serializer.data})
    
    @action(detail=False, methods=['post', 'patch'], url_path='update')
    def update_ipr_details(self, request):
        submission_id = request.data.get('submission_id')
        if not submission_id:
            return Response({
                'success': False,
                'error': 'submission_id is required'
            }, status=400)
        
        submission = self.get_submission(submission_id)
        
        # Handle the JSON data
        ipr_details_data = request.data.get('ipr_details', [])
        
        print(f"🔍 IPR Update - Submission: {submission_id}")
        print(f"🔍 Raw IPR Details Data: {ipr_details_data}")
        print(f"🔍 All Files in request: {list(request.FILES.keys())}")
        
        # Handle case where data comes as JSON string
        if isinstance(ipr_details_data, str):
            try:
                import json
                ipr_details_data = json.loads(ipr_details_data)
            except json.JSONDecodeError as e:
                return Response({
                    'success': False,
                    'error': f'Invalid JSON in ipr_details: {str(e)}'
                }, status=400)
        
        if not isinstance(ipr_details_data, list):
            return Response({
                'success': False,
                'error': 'ipr_details must be a list'
            }, status=400)
        
        try:
            with transaction.atomic():
                # Get existing IPR records
                existing_iprs = {ipr.id: ipr for ipr in IPRDetails.objects.filter(submission=submission)}
                processed_ids = set()
                
                # Process each IPR detail
                for index, ipr_data in enumerate(ipr_details_data):
                    if not isinstance(ipr_data, dict):
                        continue
                    
                    ipr_id = ipr_data.get('id')
                    
                    # Determine if this is an update or create
                    if ipr_id and ipr_id > 0 and ipr_id in existing_iprs:
                        # Update existing record
                        ipr_detail = existing_iprs[ipr_id]
                        processed_ids.add(ipr_id)
                        print(f"🔄 Updating existing IPR detail {ipr_id} at index {index}")
                    else:
                        # Create new record
                        ipr_detail = IPRDetails(submission=submission)
                        print(f"➕ Creating new IPR detail for index {index}")
                    
                    # Update all text fields
                    ipr_detail.national_importance = ipr_data.get('national_importance', '')
                    ipr_detail.commercialization_potential = ipr_data.get('commercialization_potential', '')
                    ipr_detail.risk_factors = ipr_data.get('risk_factors', '')
                    ipr_detail.preliminary_work_done = ipr_data.get('preliminary_work_done', '')
                    ipr_detail.technology_status = ipr_data.get('technology_status', '')
                    ipr_detail.business_strategy = ipr_data.get('business_strategy', '')
                    ipr_detail.based_on_ipr = ipr_data.get('based_on_ipr', '')
                    ipr_detail.ip_ownership_details = ipr_data.get('ip_ownership_details', '')
                    ipr_detail.ip_proposal = ipr_data.get('ip_proposal', '')
                    ipr_detail.regulatory_approvals = ipr_data.get('regulatory_approvals', '')
                    ipr_detail.status_approvals = ipr_data.get('status_approvals', '')
                    ipr_detail.t_name = ipr_data.get('t_name', '')
                    ipr_detail.t_designation = ipr_data.get('t_designation', '')
                    ipr_detail.t_mobile_number = ipr_data.get('t_mobile_number', '')
                    ipr_detail.t_email = ipr_data.get('t_email', '')
                    ipr_detail.t_address = ipr_data.get('t_address', '')
                    
                   
                    possible_proof_keys = [
                        f'proof_of_status_{index}',  # Indexed key
                        'proof_of_status',        
                    ]
                    
                    possible_support_keys = [
                        f't_support_letter_{index}',  
                        't_support_letter',         
                    ]
                    
                    # Handle proof_of_status file
                    proof_file_found = False
                    for key in possible_proof_keys:
                        if key in request.FILES:
                            ipr_detail.proof_of_status = request.FILES[key]
                            print(f"📎 SUCCESS: Attached proof_of_status for IPR {index} using key '{key}': {request.FILES[key].name}")
                            proof_file_found = True
                            break
                    
                    if not proof_file_found:
                        print(f"ℹ️ No new proof_of_status file found for IPR {index}. Keeping existing file.")
                    
                   
                    support_file_found = False
                    for key in possible_support_keys:
                        if key in request.FILES:
                            ipr_detail.t_support_letter = request.FILES[key]
                            print(f"📎 SUCCESS: Attached t_support_letter for IPR {index} using key '{key}': {request.FILES[key].name}")
                            support_file_found = True
                            break
                    
                    if not support_file_found:
                        print(f"ℹ️ No new t_support_letter file found for IPR {index}. Keeping existing file.")
                    
                  
                    ipr_detail.save()
                   
                    proof_status = "Has file" if ipr_detail.proof_of_status else "No file"
                    support_status = "Has file" if ipr_detail.t_support_letter else "No file"
                    print(f"   📁 Final file status - Proof: {proof_status}, Support: {support_status}")
                
                # Delete any IPR records that were removed from the form
                ids_to_delete = set(existing_iprs.keys()) - processed_ids
                if ids_to_delete:
                    IPRDetails.objects.filter(id__in=ids_to_delete).delete()
                    print(f"🗑️ Deleted {len(ids_to_delete)} removed IPR details: {ids_to_delete}")
                
                return Response({
                    'success': True,
                    'message': f'IPR details saved successfully ({len(ipr_details_data)} forms processed)'
                })
                
        except Exception as e:
            print(f"❌ Error saving IPR details: {e}")
            import traceback
            print(f"❌ Traceback: {traceback.format_exc()}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=500)


class ProjectDetailsViewSet(FormSectionViewSet):
    """Section 9: Project Details API"""
    
    @action(detail=False, methods=['get'], url_path='retrieve')
    def get_project_details(self, request):
        submission_id = request.query_params.get('submission_id')
        submission = self.get_submission(submission_id)
        serializer = ProjectDetailsSerializer(submission)
        return Response({'success': True, 'data': serializer.data})
    
    @action(detail=False, methods=['post', 'patch'], url_path='update')
    def update_project_details(self, request):
        submission_id = request.data.get('submission_id')
        submission = self.get_submission(submission_id)
        
        print(f"\n🔍 PROJECT DETAILS UPDATE DEBUG:")
        print(f"   Submission ID: {submission_id}")
        print(f"   Request data keys: {list(request.data.keys())}")
        print(f"   Request files keys: {list(request.FILES.keys())}")
        
        # Handle file uploads 
        file_updated = False
        
        # Map the correct file field names
        if 'gantt_chart' in request.FILES:
            submission.gantt_chart = request.FILES['gantt_chart']
            file_updated = True
            print(f"   ✅ Updated gantt_chart: {request.FILES['gantt_chart'].name}")
        
        if 'technical_proposal' in request.FILES:
            submission.technical_proposal = request.FILES['technical_proposal']
            file_updated = True
            print(f"   ✅ Updated technical_proposal: {request.FILES['technical_proposal'].name}")
        
        if 'proposal_presentation' in request.FILES:
            submission.proposal_presentation = request.FILES['proposal_presentation']
            file_updated = True
            print(f"   ✅ Updated proposal_presentation: {request.FILES['proposal_presentation'].name}")
        
      
        serializer = ProjectDetailsSerializer(
            submission, 
            data=request.data, 
            partial=True
        )
        
        if serializer.is_valid():
            # Save the serializer data (non-file fields)
            serializer.save()
            
            # Save file changes if any
            if file_updated:
                submission.save()
            
            print(f"   ✅ Project details saved successfully")
            
            return Response({
                'success': True,
                'message': 'Project details saved successfully',
                'data': serializer.data
            })
        else:
            print(f"   ❌ Serializer errors: {serializer.errors}")
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=400)
class DeclarationViewSet(FormSectionViewSet):
    """Declaration API"""
    
    @action(detail=False, methods=['get'], url_path='retrieve')
    def get_declaration(self, request):
        submission_id = request.query_params.get('submission_id')
        submission = self.get_submission(submission_id)
        serializer = DeclarationSerializer(submission)
        return Response({'success': True, 'data': serializer.data})
    
    @action(detail=False, methods=['post', 'patch'], url_path='update')
    def update_declaration(self, request):
        submission_id = request.data.get('submission_id')
        submission = self.get_submission(submission_id)
        
        serializer = DeclarationSerializer(
            submission, 
            data=request.data, 
            partial=True
        )
        
        if serializer.is_valid():
            serializer.save()
            return Response({
                'success': True,
                'message': 'Declaration saved successfully',
                'data': serializer.data
            })
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=400)


class FormSubmissionControlViewSet(FormSectionViewSet):
    """Form submission control - submit, get status, etc."""
    
    @action(detail=False, methods=['post'], url_path='submit')
    def submit_form(self, request):
        """Submit the complete form"""
        submission_id = request.data.get('submission_id')
        submission = self.get_submission(submission_id)
        
        # Validate all required sections are complete
        validation_errors = self._validate_complete_submission(submission)
        if validation_errors:
            return Response({
                'success': False,
                'message': 'Form validation failed',
                'errors': validation_errors
            }, status=400)
        
        # Update status to submitted
        submission.status = FormSubmission.SUBMITTED
        submission.save()
        
        return Response({
            'success': True,
            'message': 'Form submitted successfully',
            'proposal_id': submission.proposal_id,
            'form_id': submission.form_id
        })
    
    @action(detail=False, methods=['get'], url_path='status')
    def get_status(self, request):
        """Get form submission status"""
        submission_id = request.query_params.get('submission_id')
        if not submission_id:
            return Response({
                'success': False,
                'error': 'submission_id is required'
            }, status=400)
            
        submission = self.get_submission(submission_id)
        
        return Response({
            'success': True,
            'data': {
                'id': submission.id,
                'form_id': submission.form_id,
                'proposal_id': submission.proposal_id,
                'status': submission.status,
                'created_at': submission.created_at,
                'updated_at': submission.updated_at,
                'can_edit': submission.can_edit(),
                'completed_sections': submission.completed_sections or []
            }
        })
    
    @action(detail=False, methods=['get'], url_path='list')
    def list_submissions(self, request):
        """List all submissions for current user"""
        submissions = FormSubmission.objects.filter(
            applicant=request.user
        ).order_by('-updated_at')
        
        data = []
        for submission in submissions:
            data.append({
                'id': submission.id,
                'form_id': submission.form_id,
                'proposal_id': submission.proposal_id,
                'status': submission.status,
                'service_name': submission.service.name if submission.service else None,
                'created_at': submission.created_at,
                'updated_at': submission.updated_at,
                'can_edit': submission.can_edit(),
                'completed_sections': submission.completed_sections or []
            })
        
        return Response({
            'success': True,
            'data': data
        })
    
    @action(detail=False, methods=['post'], url_path='create-new')
    def create_new_submission(self, request):
        """Create new form submission"""
        template_id = request.data.get('template_id')
        service_id = request.data.get('service_id')
        
        if not template_id:
            return Response({
                'success': False,
                'error': 'template_id is required'
            }, status=400)
        
        submission = self.get_or_create_submission(template_id, service_id)
        
        return Response({
            'success': True,
            'message': 'New form submission created',
            'data': {
                'id': submission.id,
                'form_id': submission.form_id,
                'status': submission.status
            }
        })
    
    @action(detail=False, methods=['post'], url_path='update-completion')
    def update_section_completion(self, request):
        """Update section completion status"""
        submission_id = request.data.get('submission_id')
        section_index = request.data.get('section_index')
        is_completed = request.data.get('is_completed', False)
        
        if not submission_id or section_index is None:
            return Response({
                'success': False,
                'error': 'submission_id and section_index are required'
            }, status=400)
            
        submission = self.get_submission(submission_id)
        
        # Initialize completed_sections if it doesn't exist
        if not submission.completed_sections:
            submission.completed_sections = []
        
        # Update completion status
        if is_completed and section_index not in submission.completed_sections:
            submission.completed_sections.append(section_index)
        elif not is_completed and section_index in submission.completed_sections:
            submission.completed_sections.remove(section_index)
        
        submission.save()
        
        return Response({
            'success': True,
            'message': 'Section completion status updated',
            'data': {
                'completed_sections': submission.completed_sections
            }
        })
    
    @action(detail=False, methods=['get'], url_path='completion-status')
    def get_section_completion_status(self, request):
        """Get section completion status"""
        submission_id = request.query_params.get('submission_id')
        if not submission_id:
            return Response({
                'success': False,
                'error': 'submission_id is required'
            }, status=400)
            
        submission = self.get_submission(submission_id)
        
        return Response({
            'success': True,
            'data': {
                'completed_sections': submission.completed_sections or []
            }
        })
    
    def _validate_complete_submission(self, submission):
        """Validate that all required sections are complete"""
        errors = {}
        
      
        if not submission.individual_pan:
            errors['basic_details'] = 'Individual PAN is required'
        
        if hasattr(submission.applicant, 'profile') and not submission.applicant.profile.qualification:
            errors['basic_details'] = 'Qualification is required'
        
        return errors