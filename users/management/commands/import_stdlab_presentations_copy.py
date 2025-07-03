# presentation/management/commands/import_presentation_data.py
 
import os
from datetime import datetime
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import transaction
from presentation.models import Presentation
from dynamic_form.models import FormSubmission
 
User = get_user_model()
 
class Command(BaseCommand):
    help = 'Import presentation data with CORRECTED marks from actual CSV'
 
    def add_arguments(self, parser):
        parser.add_argument(
            '--override',
            action='store_true',
            help='Override existing presentation data'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run without making changes to database'
        )
 
    def handle(self, *args, **options):
        override = options['override']
        dry_run = options['dry_run']
       
        if dry_run:
            self.stdout.write(self.style.WARNING('🔍 DRY RUN MODE - No changes will be made'))
       
        # CORRECTED dataset with actual CSV data
        presentation_data = [
            # TTDF24QSTL007 - Actual averages: 57.1 (was wrong in previous script)
            {"ID": "TTDF24QSTL007", "Evaluator": "anirban.pathak@jiit.ac.in", "Marks": 69, "Remarks": "1. The group has the capability of performing the proposed task. They have already performed several experiments of similar nature.\n2. Cost of the project needs to be reduced considerably. The group has many equipment and it's an institute supported by the Department of Space. Procurement of multiple copies of the same equipment in the same lab must be avoided. There is no rationale behind the proposed budget.", "Video Link": "https://cdotmeet.cdot.in/playback/presentation/2.3/384f478cbf21081d78d1a32e4f6d028d1e519733-1744016940438/"},
            {"ID": "TTDF24QSTL007", "Evaluator": "raju@diat.ac.in", "Marks": 70, "Remarks": "The proposal is well-written and clearly presented, but it encompasses too many scientific objectives and requests a significantly large budget, including funding for several redundant instruments. To improve focus and feasibility, the project should concentrate on one or two key areas—such as free-space quantum key distribution (QKD) and standardization. The budget should then be revised to reflect this more targeted scope.", "Video Link": "https://cdotmeet.cdot.in/playback/presentation/2.3/384f478cbf21081d78d1a32e4f6d028d1e519733-1744016940438/"},
            {"ID": "TTDF24QSTL007", "Evaluator": "ddg.sri-dot@gov.in", "Marks": 60, "Remarks": "", "Video Link": "https://cdotmeet.cdot.in/playback/presentation/2.3/384f478cbf21081d78d1a32e4f6d028d1e519733-1744016940438/"},
            {"ID": "TTDF24QSTL007", "Evaluator": "ddgqt.tec-dot@gov.in", "Marks": 50, "Remarks": "The budget is on higher side due to proposal for procurement of equipments which are even available at present.", "Video Link": "https://cdotmeet.cdot.in/playback/presentation/2.3/384f478cbf21081d78d1a32e4f6d028d1e519733-1744016940438/"},
            {"ID": "TTDF24QSTL007", "Evaluator": "manjunath.r@qpiai.tech", "Marks": 40, "Remarks": "", "Video Link": "https://cdotmeet.cdot.in/playback/presentation/2.3/384f478cbf21081d78d1a32e4f6d028d1e519733-1744016940438/"},
            {"ID": "TTDF24QSTL007", "Evaluator": "gyanendra.d.tripathi@gmail.com", "Marks": 46, "Remarks": "", "Video Link": "https://cdotmeet.cdot.in/playback/presentation/2.3/384f478cbf21081d78d1a32e4f6d028d1e519733-1744016940438/"},
            {"ID": "TTDF24QSTL007", "Evaluator": "jbvreddy@nic.in", "Marks": 65, "Remarks": "", "Video Link": "https://cdotmeet.cdot.in/playback/presentation/2.3/384f478cbf21081d78d1a32e4f6d028d1e519733-1744016940438/"},
           
            # TTDF24QSTL009 - Average: 44.9
            {"ID": "TTDF24QSTL009", "Evaluator": "anirban.pathak@jiit.ac.in", "Marks": 45, "Remarks": "An abnormally over-budgeted proposal without any focus. The project is neither focused nor good. The team does not have proven capability.", "Video Link": "https://cdotmeet.cdot.in/playback/presentation/2.3/384f478cbf21081d78d1a32e4f6d028d1e519733-1744104247780/"},
            {"ID": "TTDF24QSTL009", "Evaluator": "raju@diat.ac.in", "Marks": 25, "Remarks": "The proposal is not recommended for funding due to its lack of focus, excessive scope, and disproportionate budget request. The project attempts to address too many objectives without a coherent or prioritized research plan, resulting in an incohesive narrative that lacks clear direction and measurable outcomes.", "Video Link": "https://cdotmeet.cdot.in/playback/presentation/2.3/384f478cbf21081d78d1a32e4f6d028d1e519733-1744104247780/"},
            {"ID": "TTDF24QSTL009", "Evaluator": "ddg.sri-dot@gov.in", "Marks": 54, "Remarks": "", "Video Link": "https://cdotmeet.cdot.in/playback/presentation/2.3/384f478cbf21081d78d1a32e4f6d028d1e519733-1744104247780/"},
            {"ID": "TTDF24QSTL009", "Evaluator": "ddgqt.tec-dot@gov.in", "Marks": 50, "Remarks": "Clarity in presentation was missing. High budgeted proposal.", "Video Link": "https://cdotmeet.cdot.in/playback/presentation/2.3/384f478cbf21081d78d1a32e4f6d028d1e519733-1744104247780/"},
            {"ID": "TTDF24QSTL009", "Evaluator": "manjunath.r@qpiai.tech", "Marks": 30, "Remarks": "", "Video Link": "https://cdotmeet.cdot.in/playback/presentation/2.3/384f478cbf21081d78d1a32e4f6d028d1e519733-1744104247780/"},
            {"ID": "TTDF24QSTL009", "Evaluator": "gyanendra.d.tripathi@gmail.com", "Marks": 49, "Remarks": "", "Video Link": "https://cdotmeet.cdot.in/playback/presentation/2.3/384f478cbf21081d78d1a32e4f6d028d1e519733-1744104247780/"},
            {"ID": "TTDF24QSTL009", "Evaluator": "jbvreddy@nic.in", "Marks": 61, "Remarks": "", "Video Link": "https://cdotmeet.cdot.in/playback/presentation/2.3/384f478cbf21081d78d1a32e4f6d028d1e519733-1744104247780/"},
           
            # TTDF24QSTL058 - Average: 48.6
            {"ID": "TTDF24QSTL058", "Evaluator": "anirban.pathak@jiit.ac.in", "Marks": 45, "Remarks": "The project is not focused. The team want to do many things and most of them are not related to the call. They coined some new terms to justify their activities related to quantum materials and quantum sensing as activities in the domain of quantum communication. In short the proposal is not relevant for DoT and obviously it's over-budgeted.", "Video Link": "https://cdotmeet.cdot.in/playback/presentation/2.3/384f478cbf21081d78d1a32e4f6d028d1e519733-1744104247780/"},
            {"ID": "TTDF24QSTL058", "Evaluator": "raju@diat.ac.in", "Marks": 30, "Remarks": "This proposal is for facility development in quantum materials at IISC, while aligned with the broad goals of advancing quantum technology, lacks the necessary specificity and scientific focus requirement of the present funding. The submission presents a generic outline without clearly articulated research objectives, defined scientific challenges.", "Video Link": "https://cdotmeet.cdot.in/playback/presentation/2.3/384f478cbf21081d78d1a32e4f6d028d1e519733-1744104247780/"},
            {"ID": "TTDF24QSTL058", "Evaluator": "ddg.sri-dot@gov.in", "Marks": 50, "Remarks": "", "Video Link": "https://cdotmeet.cdot.in/playback/presentation/2.3/384f478cbf21081d78d1a32e4f6d028d1e519733-1744104247780/"},
            {"ID": "TTDF24QSTL058", "Evaluator": "ddgqt.tec-dot@gov.in", "Marks": 50, "Remarks": "It is a high budgeted proposal, more towards sensing and metrology.", "Video Link": "https://cdotmeet.cdot.in/playback/presentation/2.3/384f478cbf21081d78d1a32e4f6d028d1e519733-1744104247780/"},
            {"ID": "TTDF24QSTL058", "Evaluator": "manjunath.r@qpiai.tech", "Marks": 40, "Remarks": "", "Video Link": "https://cdotmeet.cdot.in/playback/presentation/2.3/384f478cbf21081d78d1a32e4f6d028d1e519733-1744104247780/"},
            {"ID": "TTDF24QSTL058", "Evaluator": "gyanendra.d.tripathi@gmail.com", "Marks": 55, "Remarks": "", "Video Link": "https://cdotmeet.cdot.in/playback/presentation/2.3/384f478cbf21081d78d1a32e4f6d028d1e519733-1744104247780/"},
            {"ID": "TTDF24QSTL058", "Evaluator": "jbvreddy@nic.in", "Marks": 70, "Remarks": "", "Video Link": "https://cdotmeet.cdot.in/playback/presentation/2.3/384f478cbf21081d78d1a32e4f6d028d1e519733-1744104247780/"},
           
            # TTDF24QSTL037 - Average: 66.4
            {"ID": "TTDF24QSTL037", "Evaluator": "anirban.pathak@jiit.ac.in", "Marks": 72, "Remarks": "The team and the proposal is very good, but we need to check whether they (PI and Co-PI) have enough time for this project. We can invite list of other projects with them and check whether they will be able to deliver the proposed deliverable. Institute overhead and budget are in higher side. Budget must be reduced. Little bit of more focus on the call is needed and the fabrication claim needs to be revisited. They claimed that they will fabricate SNSPD. If that happens in India, we will be very happy, but during discussion they presented in a manner where most of the things will be procured and then a kind of assembling will happen. Finally, they are well funded by DST and some of the PIs have projects from NQM, they must revise budget and avoid buying same equipment from multiple funding windows.", "Video Link": "https://cdotmeet.cdot.in/playback/presentation/2.3/384f478cbf21081d78d1a32e4f6d028d1e519733-1744016940438/"},
            {"ID": "TTDF24QSTL037", "Evaluator": "raju@diat.ac.in", "Marks": 70, "Remarks": "The proposal demonstrates strong scientific potential but requires significant refinement in its overall scope. The PIs are encouraged to narrow their focus to a few well-defined research themes—for instance, the development of superconducting nanowire single-photon detectors (SNSPDs) and the use of 2D materials for quantum light sources and their standardization. Concentrating on these areas would enhance the proposal's coherence and impact. Additionally, the budget should be restructured to align with the revised, more focused research objectives.", "Video Link": "https://cdotmeet.cdot.in/playback/presentation/2.3/384f478cbf21081d78d1a32e4f6d028d1e519733-1744016940438/"},
            {"ID": "TTDF24QSTL037", "Evaluator": "ddg.sri-dot@gov.in", "Marks": 68, "Remarks": "", "Video Link": "https://cdotmeet.cdot.in/playback/presentation/2.3/384f478cbf21081d78d1a32e4f6d028d1e519733-1744016940438/"},
            {"ID": "TTDF24QSTL037", "Evaluator": "ddgqt.tec-dot@gov.in", "Marks": 65, "Remarks": "The proposal is for creation of testing facility for source and detectors used in quantum communication and for testing facility for the quantum sensors using NV center principal. The proposal is just in-line with the requirement it will test individual components used in quantum products.", "Video Link": "https://cdotmeet.cdot.in/playback/presentation/2.3/384f478cbf21081d78d1a32e4f6d028d1e519733-1744016940438/"},
            {"ID": "TTDF24QSTL037", "Evaluator": "manjunath.r@qpiai.tech", "Marks": 45, "Remarks": "", "Video Link": "https://cdotmeet.cdot.in/playback/presentation/2.3/384f478cbf21081d78d1a32e4f6d028d1e519733-1744016940438/"},
            {"ID": "TTDF24QSTL037", "Evaluator": "gyanendra.d.tripathi@gmail.com", "Marks": 67, "Remarks": "", "Video Link": "https://cdotmeet.cdot.in/playback/presentation/2.3/384f478cbf21081d78d1a32e4f6d028d1e519733-1744016940438/"},
            {"ID": "TTDF24QSTL037", "Evaluator": "jbvreddy@nic.in", "Marks": 78, "Remarks": "", "Video Link": "https://cdotmeet.cdot.in/playback/presentation/2.3/384f478cbf21081d78d1a32e4f6d028d1e519733-1744016940438/"},
           
            # TTDF24QSTL033 - Average: 40.4
            {"ID": "TTDF24QSTL033", "Evaluator": "anirban.pathak@jiit.ac.in", "Marks": 40, "Remarks": "The project is focused on PQC only and team has no authority to issue certificates.", "Video Link": "https://cdotmeet.cdot.in/playback/presentation/2.3/384f478cbf21081d78d1a32e4f6d028d1e519733-1744104247780/"},
            {"ID": "TTDF24QSTL033", "Evaluator": "raju@diat.ac.in", "Marks": 30, "Remarks": "The proposal is not even related to Standardization. The proposal is more oriented towards PQC.", "Video Link": "https://cdotmeet.cdot.in/playback/presentation/2.3/384f478cbf21081d78d1a32e4f6d028d1e519733-1744104247780/"},
            {"ID": "TTDF24QSTL033", "Evaluator": "ddg.sri-dot@gov.in", "Marks": 48, "Remarks": "", "Video Link": "https://cdotmeet.cdot.in/playback/presentation/2.3/384f478cbf21081d78d1a32e4f6d028d1e519733-1744104247780/"},
            {"ID": "TTDF24QSTL033", "Evaluator": "ddgqt.tec-dot@gov.in", "Marks": 50, "Remarks": "It is a joint collaboration with US. The scope is for setting up PQC lab only, it is an average proposal.", "Video Link": "https://cdotmeet.cdot.in/playback/presentation/2.3/384f478cbf21081d78d1a32e4f6d028d1e519733-1744104247780/"},
            {"ID": "TTDF24QSTL033", "Evaluator": "manjunath.r@qpiai.tech", "Marks": 10, "Remarks": "", "Video Link": "https://cdotmeet.cdot.in/playback/presentation/2.3/384f478cbf21081d78d1a32e4f6d028d1e519733-1744104247780/"},
            {"ID": "TTDF24QSTL033", "Evaluator": "gyanendra.d.tripathi@gmail.com", "Marks": 53, "Remarks": "", "Video Link": "https://cdotmeet.cdot.in/playback/presentation/2.3/384f478cbf21081d78d1a32e4f6d028d1e519733-1744104247780/"},
            {"ID": "TTDF24QSTL033", "Evaluator": "jbvreddy@nic.in", "Marks": 52, "Remarks": "", "Video Link": "https://cdotmeet.cdot.in/playback/presentation/2.3/384f478cbf21081d78d1a32e4f6d028d1e519733-1744104247780/"},
           
            # TTDF24QSTL038 - Average: 73.9
            {"ID": "TTDF24QSTL038", "Evaluator": "anirban.pathak@jiit.ac.in", "Marks": 73, "Remarks": "Its a good and balanced proposal. The team has experience of doing similar thing. Budget should be revisited and the other project of CDoT focused on single photon detector should be absorbed in it as that's just a subset of this project.", "Video Link": "https://cdotmeet.cdot.in/playback/presentation/2.3/384f478cbf21081d78d1a32e4f6d028d1e519733-1744016940438/"},
            {"ID": "TTDF24QSTL038", "Evaluator": "raju@diat.ac.in", "Marks": 70, "Remarks": "The proposal and presentation are clear; however, some of the scientific claims—particularly those related to MDI-QKD—have not been supported by peer-reviewed publications from this group. Additionally, the DOT institute is already part of the NQM hub, raising concerns about potential overlap in funding for similar research activities from multiple agencies. It is important to ensure that there is no duplication of funding or effort. That said, the PIs do appear to have the capability to establish a standardization laboratory, which could be a valuable contribution if appropriately scoped and managed.", "Video Link": "https://cdotmeet.cdot.in/playback/presentation/2.3/384f478cbf21081d78d1a32e4f6d028d1e519733-1744016940438/"},
            {"ID": "TTDF24QSTL038", "Evaluator": "ddg.sri-dot@gov.in", "Marks": 72, "Remarks": "", "Video Link": "https://cdotmeet.cdot.in/playback/presentation/2.3/384f478cbf21081d78d1a32e4f6d028d1e519733-1744016940438/"},
            {"ID": "TTDF24QSTL038", "Evaluator": "ddgqt.tec-dot@gov.in", "Marks": 70, "Remarks": "The proposal is in line with the call for proposal. It includes testing and evaluation quantum communication systems and components.", "Video Link": "https://cdotmeet.cdot.in/playback/presentation/2.3/384f478cbf21081d78d1a32e4f6d028d1e519733-1744016940438/"},
            {"ID": "TTDF24QSTL038", "Evaluator": "manjunath.r@qpiai.tech", "Marks": 85, "Remarks": "", "Video Link": "https://cdotmeet.cdot.in/playback/presentation/2.3/384f478cbf21081d78d1a32e4f6d028d1e519733-1744016940438/"},
            {"ID": "TTDF24QSTL038", "Evaluator": "gyanendra.d.tripathi@gmail.com", "Marks": 69, "Remarks": "", "Video Link": "https://cdotmeet.cdot.in/playback/presentation/2.3/384f478cbf21081d78d1a32e4f6d028d1e519733-1744016940438/"},
            {"ID": "TTDF24QSTL038", "Evaluator": "jbvreddy@nic.in", "Marks": 79, "Remarks": "", "Video Link": "https://cdotmeet.cdot.in/playback/presentation/2.3/384f478cbf21081d78d1a32e4f6d028d1e519733-1744016940438/"},
           
            # TTDF24QSTL056 - Average: 59.0
            {"ID": "TTDF24QSTL056", "Evaluator": "anirban.pathak@jiit.ac.in", "Marks": 61, "Remarks": "This project's deliverable is a subset of the other project submitted by the same organisation. This project can be merged with the other proposal of CDoT without any increase of fund for the other proposal submitted by Dr. Priya Malpani. It may be noted that the team is also almost the same as they confirmed during the presentation.", "Video Link": "https://cdotmeet.cdot.in/playback/presentation/2.3/384f478cbf21081d78d1a32e4f6d028d1e519733-1744016940438/"},
            {"ID": "TTDF24QSTL056", "Evaluator": "raju@diat.ac.in", "Marks": 40, "Remarks": "This can not be an individual proposal since such development can be part of over QKD development system proposal. This can be absorbed with other QKD proposal.", "Video Link": "https://cdotmeet.cdot.in/playback/presentation/2.3/384f478cbf21081d78d1a32e4f6d028d1e519733-1744016940438/"},
            {"ID": "TTDF24QSTL056", "Evaluator": "ddg.sri-dot@gov.in", "Marks": 62, "Remarks": "", "Video Link": "https://cdotmeet.cdot.in/playback/presentation/2.3/384f478cbf21081d78d1a32e4f6d028d1e519733-1744016940438/"},
            {"ID": "TTDF24QSTL056", "Evaluator": "ddgqt.tec-dot@gov.in", "Marks": 50, "Remarks": "The proposal is about testing of detectors including SNSPD and the setup time of lab is 3 years.", "Video Link": "https://cdotmeet.cdot.in/playback/presentation/2.3/384f478cbf21081d78d1a32e4f6d028d1e519733-1744016940438/"},
            {"ID": "TTDF24QSTL056", "Evaluator": "manjunath.r@qpiai.tech", "Marks": 90, "Remarks": "", "Video Link": "https://cdotmeet.cdot.in/playback/presentation/2.3/384f478cbf21081d78d1a32e4f6d028d1e519733-1744016940438/"},
            {"ID": "TTDF24QSTL056", "Evaluator": "gyanendra.d.tripathi@gmail.com", "Marks": 48, "Remarks": "", "Video Link": "https://cdotmeet.cdot.in/playback/presentation/2.3/384f478cbf21081d78d1a32e4f6d028d1e519733-1744016940438/"},
            {"ID": "TTDF24QSTL056", "Evaluator": "jbvreddy@nic.in", "Marks": 62, "Remarks": "", "Video Link": "https://cdotmeet.cdot.in/playback/presentation/2.3/384f478cbf21081d78d1a32e4f6d028d1e519733-1744016940438/"},
           
            # TTDF24QSTL050 - Average: 46.9
            {"ID": "TTDF24QSTL050", "Evaluator": "anirban.pathak@jiit.ac.in", "Marks": 48, "Remarks": "Lacks domain knowledge. Directed on quantum sensing and not focused on the call. They failed to justify the need for developing quantum algorithms and protocols for this project.", "Video Link": "https://cdotmeet.cdot.in/playback/presentation/2.3/384f478cbf21081d78d1a32e4f6d028d1e519733-1744104247780/"},
            {"ID": "TTDF24QSTL050", "Evaluator": "raju@diat.ac.in", "Marks": 35, "Remarks": "The proposal for developing quantum sensing systems does not meet the criteria of funding requirement. The research team lacks demonstrated experience in the field of quantum sensing, and there is no evidence of prior work or relevant qualifications to support successful execution of the proposed objectives. Additionally, the absence of essential equipment and a clear plan further limits the feasibility of the project.", "Video Link": "https://cdotmeet.cdot.in/playback/presentation/2.3/384f478cbf21081d78d1a32e4f6d028d1e519733-1744104247780/"},
            {"ID": "TTDF24QSTL050", "Evaluator": "ddg.sri-dot@gov.in", "Marks": 48, "Remarks": "", "Video Link": "https://cdotmeet.cdot.in/playback/presentation/2.3/384f478cbf21081d78d1a32e4f6d028d1e519733-1744104247780/"},
            {"ID": "TTDF24QSTL050", "Evaluator": "ddgqt.tec-dot@gov.in", "Marks": 50, "Remarks": "Scope is not in line with the proposal. Emphasis is more in sensing than setting lab.", "Video Link": "https://cdotmeet.cdot.in/playback/presentation/2.3/384f478cbf21081d78d1a32e4f6d028d1e519733-1744104247780/"},
            {"ID": "TTDF24QSTL050", "Evaluator": "manjunath.r@qpiai.tech", "Marks": 30, "Remarks": "", "Video Link": "https://cdotmeet.cdot.in/playback/presentation/2.3/384f478cbf21081d78d1a32e4f6d028d1e519733-1744104247780/"},
            {"ID": "TTDF24QSTL050", "Evaluator": "gyanendra.d.tripathi@gmail.com", "Marks": 45, "Remarks": "", "Video Link": "https://cdotmeet.cdot.in/playback/presentation/2.3/384f478cbf21081d78d1a32e4f6d028d1e519733-1744104247780/"},
            {"ID": "TTDF24QSTL050", "Evaluator": "jbvreddy@nic.in", "Marks": 72, "Remarks": "", "Video Link": "https://cdotmeet.cdot.in/playback/presentation/2.3/384f478cbf21081d78d1a32e4f6d028d1e519733-1744104247780/"},
           
            # TTDF24QSTL057 - Average: 47.7
            {"ID": "TTDF24QSTL057", "Evaluator": "anirban.pathak@jiit.ac.in", "Marks": 55, "Remarks": "PI lacks domain knowledge. The team is big and other members have relevant experience. A big team is causing an increase in the budget. The project will not lead to establishment of a single facility/lab for testing and standardization.", "Video Link": "https://cdotmeet.cdot.in/playback/presentation/2.3/384f478cbf21081d78d1a32e4f6d028d1e519733-1744104247780/"},
            {"ID": "TTDF24QSTL057", "Evaluator": "raju@diat.ac.in", "Marks": 40, "Remarks": "The proposal is not recommended for funding due to several structural and conceptual weaknesses. The involvement of an excessive number of Principal Investigators result in a fragmented and overly complex project framework. The use of a hub-and-spoke model lacks clear justification, and the role of the proposed host institution appears largely nominal, raising concerns about project coordination and accountability.", "Video Link": "https://cdotmeet.cdot.in/playback/presentation/2.3/384f478cbf21081d78d1a32e4f6d028d1e519733-1744104247780/"},
            {"ID": "TTDF24QSTL057", "Evaluator": "ddg.sri-dot@gov.in", "Marks": 48, "Remarks": "", "Video Link": "https://cdotmeet.cdot.in/playback/presentation/2.3/384f478cbf21081d78d1a32e4f6d028d1e519733-1744104247780/"},
            {"ID": "TTDF24QSTL057", "Evaluator": "ddgqt.tec-dot@gov.in", "Marks": 50, "Remarks": "The proposal is for 5-year program with 9 CoPI. Budget is at higher side.", "Video Link": "https://cdotmeet.cdot.in/playback/presentation/2.3/384f478cbf21081d78d1a32e4f6d028d1e519733-1744104247780/"},
            {"ID": "TTDF24QSTL057", "Evaluator": "manjunath.r@qpiai.tech", "Marks": 30, "Remarks": "", "Video Link": "https://cdotmeet.cdot.in/playback/presentation/2.3/384f478cbf21081d78d1a32e4f6d028d1e519733-1744104247780/"},
            {"ID": "TTDF24QSTL057", "Evaluator": "gyanendra.d.tripathi@gmail.com", "Marks": 41, "Remarks": "", "Video Link": "https://cdotmeet.cdot.in/playback/presentation/2.3/384f478cbf21081d78d1a32e4f6d028d1e519733-1744104247780/"},
            {"ID": "TTDF24QSTL057", "Evaluator": "jbvreddy@nic.in", "Marks": 70, "Remarks": "", "Video Link": "https://cdotmeet.cdot.in/playback/presentation/2.3/384f478cbf21081d78d1a32e4f6d028d1e519733-1744104247780/"},
        ]
       
        self.stdout.write('🔄 Starting CORRECTED presentation data import...')
        self.stdout.write('📊 ACTUAL AVERAGES FROM CSV:')
        self.stdout.write('   TTDF24QSTL007: 57.1 (69,70,60,50,40,46,65)')
        self.stdout.write('   TTDF24QSTL009: 44.9 (45,25,54,50,30,49,61)')
        self.stdout.write('   TTDF24QSTL058: 48.6 (45,30,50,50,40,55,70)')
        self.stdout.write('   TTDF24QSTL037: 66.4 (72,70,68,65,45,67,78)')
        self.stdout.write('   TTDF24QSTL033: 40.4 (40,30,48,50,10,53,52)')
        self.stdout.write('   TTDF24QSTL038: 73.9 (73,70,72,70,85,69,79)')
        self.stdout.write('   TTDF24QSTL056: 59.0 (61,40,62,50,90,48,62)')
        self.stdout.write('   TTDF24QSTL050: 46.9 (48,35,48,50,30,45,72)')
        self.stdout.write('   TTDF24QSTL057: 47.7 (55,40,48,50,30,41,70)')
        self.stdout.write('')
       
        # Statistics
        total_rows = len(presentation_data)
        created_count = 0
        updated_count = 0
        error_count = 0
        skipped_count = 0
       
        # Summary by proposal
        proposal_summary = {}
 
        try:
            if not dry_run:
                with transaction.atomic():
                    for i, row in enumerate(presentation_data, 1):
                        try:
                            result = self.process_row(row, override, dry_run)
                           
                            # Track by proposal
                            proposal_id = row['ID']
                            if proposal_id not in proposal_summary:
                                proposal_summary[proposal_id] = {'created': 0, 'updated': 0, 'skipped': 0, 'error': 0}
                           
                            if result == 'created':
                                created_count += 1
                                proposal_summary[proposal_id]['created'] += 1
                            elif result == 'updated':
                                updated_count += 1
                                proposal_summary[proposal_id]['updated'] += 1
                            elif result == 'skipped':
                                skipped_count += 1
                                proposal_summary[proposal_id]['skipped'] += 1
                               
                        except Exception as e:
                            error_count += 1
                            proposal_id = row.get('ID', 'unknown')
                            if proposal_id not in proposal_summary:
                                proposal_summary[proposal_id] = {'created': 0, 'updated': 0, 'skipped': 0, 'error': 0}
                            proposal_summary[proposal_id]['error'] += 1
                           
                            self.stdout.write(
                                self.style.ERROR(
                                    f'Error processing row {i} (Proposal: {proposal_id}, '
                                    f'Evaluator: {row.get("Evaluator", "unknown")}): {str(e)}'
                                )
                            )
                            continue
            else:
                # Dry run mode
                for i, row in enumerate(presentation_data, 1):
                    try:
                        result = self.process_row(row, override, dry_run)
                        proposal_id = row['ID']
                        if proposal_id not in proposal_summary:
                            proposal_summary[proposal_id] = {'created': 0, 'updated': 0, 'skipped': 0, 'error': 0}
                        proposal_summary[proposal_id]['created'] += 1
                        created_count += 1
                    except Exception as e:
                        error_count += 1
                        self.stdout.write(
                            self.style.ERROR(f'Error in dry run for row {i}: {str(e)}')
                        )
 
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error processing data: {str(e)}')
            )
            return
 
        # Print detailed summary
        self.stdout.write('\n' + '='*60)
        self.stdout.write('CORRECTED IMPORT SUMMARY')
        self.stdout.write('='*60)
        self.stdout.write(f'Total rows processed: {total_rows}')
        self.stdout.write(f'Created: {created_count}')
        self.stdout.write(f'Updated: {updated_count}')
        self.stdout.write(f'Skipped: {skipped_count}')
        self.stdout.write(f'Errors: {error_count}')
       
        self.stdout.write('\nPer Proposal Summary (with CORRECTED marks):')
        self.stdout.write('-' * 60)
        expected_averages = {
            'TTDF24QSTL007': 57.1,
            'TTDF24QSTL009': 44.9,
            'TTDF24QSTL058': 48.6,
            'TTDF24QSTL037': 66.4,
            'TTDF24QSTL033': 40.4,
            'TTDF24QSTL038': 73.9,
            'TTDF24QSTL056': 59.0,
            'TTDF24QSTL050': 46.9,
            'TTDF24QSTL057': 47.7,
        }
       
        for proposal_id, stats in proposal_summary.items():
            total_evaluators = sum(stats.values())
            expected_avg = expected_averages.get(proposal_id, 'N/A')
            self.stdout.write(
                f'{proposal_id}: {stats["created"]}C, {stats["updated"]}U, '
                f'{stats["skipped"]}S, {stats["error"]}E (Total: {total_evaluators}) - Expected Avg: {expected_avg}'
            )
       
        self.stdout.write('='*60)
       
        if dry_run:
            self.stdout.write(
                self.style.WARNING('🔍 DRY RUN COMPLETED - No changes were made to database')
            )
        elif error_count == 0:
            self.stdout.write(
                self.style.SUCCESS('✅ CORRECTED IMPORT completed successfully!')
            )
            self.stdout.write('🎯 Your frontend should now show the CORRECT average marks from the actual CSV')
        else:
            self.stdout.write(
                self.style.WARNING(f'⚠️  Import completed with {error_count} errors')
            )
 
    def process_row(self, row, override, dry_run):
        """Process a single data row"""
       
        # Extract data from row
        proposal_id = row['ID'].strip()
        evaluator_email = row['Evaluator'].strip()
        marks = int(row['Marks']) if row['Marks'] else None
        remarks = row['Remarks'].strip() if row['Remarks'] else None
        video_link = row['Video Link'].strip() if row['Video Link'] else None
       
        # Validate required fields
        if not proposal_id or not evaluator_email:
            raise ValueError(f"Missing required fields: proposal_id={proposal_id}, evaluator_email={evaluator_email}")
       
        if marks is None:
            raise ValueError(f"Missing marks for proposal {proposal_id}, evaluator {evaluator_email}")
 
        if dry_run:
            self.stdout.write(f'  [DRY RUN] Would process: {proposal_id} - {evaluator_email} - {marks} marks')
            return 'created'
 
        # Find the proposal
        try:
            proposal = FormSubmission.objects.get(proposal_id=proposal_id)
        except FormSubmission.DoesNotExist:
            raise ValueError(f"Proposal not found: {proposal_id}")
 
        # Find the evaluator
        try:
            evaluator = User.objects.get(email=evaluator_email)
        except User.DoesNotExist:
            # Create evaluator if doesn't exist
            self.stdout.write(
                self.style.WARNING(f'Creating user for email: {evaluator_email}')
            )
            evaluator = self.create_user_from_email(evaluator_email)
 
        # Check if presentation already exists
        presentation, created = Presentation.objects.get_or_create(
            proposal=proposal,
            evaluator=evaluator,
            defaults={
                'applicant': proposal.applicant,
            }
        )
 
        # Determine action
        if created:
            action = 'created'
            self.stdout.write(f'  ✓ Created presentation for {proposal_id} - {evaluator_email} - {marks} marks')
        elif override:
            action = 'updated'
            self.stdout.write(f'  ↻ Updated presentation for {proposal_id} - {evaluator_email} - {marks} marks (CORRECTED)')
        else:
            self.stdout.write(f'  - Skipped existing presentation for {proposal_id} - {evaluator_email}')
            return 'skipped'
 
        # Set the document path (same for all)
        document_path = 'presentation/documents/Tangible_Intangible_KuMFuGi.docx'
       
        # Update presentation data
        presentation.video_link = video_link
        presentation.document = document_path
        presentation.presentation_date = timezone.now()
        presentation.document_uploaded = True
       
        # Set evaluator data
        presentation.evaluator_marks = marks
        presentation.evaluator_remarks = remarks
        presentation.evaluated_at = timezone.now()
       
        # Set status based on completion
        presentation.final_decision = 'evaluated'
       
        # Save the presentation
        presentation.save()
       
        return action
 
    def create_user_from_email(self, email):
        """Create a user from email address"""
        username = email.split('@')[0]
       
        # Handle potential username conflicts
        base_username = username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}_{counter}"
            counter += 1
       
        # Create display name from email
        name_part = email.split('@')[0]
        full_name = name_part.replace('.', ' ').replace('_', ' ').title()
        name_parts = full_name.split()
       
        user = User.objects.create_user(
            email=email,
            username=username,
            first_name=name_parts[0] if name_parts else username,
            last_name=' '.join(name_parts[1:]) if len(name_parts) > 1 else '',
            password=User.objects.make_random_password(12)  # Generate random password
        )
       
        return user