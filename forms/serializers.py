from rest_framework import serializers
from .models import QuizSubmission, AdmissionApplication

class QuizSubmissionListSerializer(serializers.ModelSerializer):
    admission_submitted = serializers.SerializerMethodField()
    application_number = serializers.SerializerMethodField()
    is_repeated_enquiry = serializers.SerializerMethodField()
    repeated_badge = serializers.SerializerMethodField()
    created_by_user = serializers.SerializerMethodField()
    added_by = serializers.SerializerMethodField()

    class Meta:
        model = QuizSubmission
        fields = [
            'id',
            'standard',
            'medium',
            'parent_name',
            'child_name',
            'surname',
            'vibhag',
            'language',
            'whatsapp_number',
            'email',
            'score',
            'tag',
            'qa_status',
            'is_eligible',
            'payment_status',
            'whatsapp_link_sent',
            'quiz_completed_at',
            'created_at',
            'admission_submitted',
            'application_number',
            'is_repeated_enquiry',
            'repeated_badge',
            'created_by',
            'created_by_user',
            'added_by'
        ]

    def get_created_by_user(self, obj):
        if obj.created_by:
            return {
                "id": obj.created_by.id,
                "username": obj.created_by.username,
                "full_name": obj.created_by.full_name or obj.created_by.username,
                "email": obj.created_by.email,
                "role": obj.created_by.role
            }
        return None

    def get_added_by(self, obj):
        if obj.created_by:
            return obj.created_by.full_name or obj.created_by.username
        return "Online / Self"

    def get_admission_submitted(self, obj):
        return hasattr(obj, 'admission_application')

    def get_application_number(self, obj):
        if hasattr(obj, 'admission_application'):
            return obj.admission_application.application_number
        return None

    def get_is_repeated_enquiry(self, obj):
        clean = "".join(filter(str.isdigit, str(obj.whatsapp_number)))
        phone_10 = clean[-10:] if len(clean) >= 10 else clean
        # Check if there is another older enquiry with the same child name and phone number
        older_exists = QuizSubmission.objects.filter(
            whatsapp_number__endswith=phone_10,
            child_name__iexact=obj.child_name.strip(),
            id__lt=obj.id
        ).exists()
        return older_exists

    def get_repeated_badge(self, obj):
        clean = "".join(filter(str.isdigit, str(obj.whatsapp_number)))
        phone_10 = clean[-10:] if len(clean) >= 10 else clean
        count = QuizSubmission.objects.filter(
            whatsapp_number__endswith=phone_10,
            child_name__iexact=obj.child_name.strip()
        ).count()
        if count > 1:
            return "Repeated Enquiry"  #  "Re-enquiry"
        return None


class SubmitQuizSerializer(serializers.Serializer):
    submission_id = serializers.IntegerField(required=False, help_text="Existing enquiry ID if parent is submitting quiz")
    standard = serializers.CharField(
        required=False,
        default='Nursery',
        allow_blank=True,
        help_text="Standard dropdown: Nursery, Jr.KG, Sr.KG, 1 to 12"
    )
    medium = serializers.CharField(
        required=False,
        default='Gujarati',
        allow_blank=True,
        help_text="Medium: Gujarati / English"
    )
    parent_name = serializers.CharField(required=False, allow_blank=True, default="", help_text="Father Name / Parent Name")
    father_name = serializers.CharField(required=False, allow_blank=True, default="", help_text="Father Name (alias for parent_name)")
    child_name = serializers.CharField(required=False, allow_blank=True, default="", help_text="Student Name")
    surname = serializers.CharField(required=False, allow_blank=True, default="", help_text="SURNAME (Mandatory for new enquiry)")
    payment_status = serializers.CharField(required=False, default="RECEIVED", help_text="Payment status: RECEIVED / PENDING")
    vibhag = serializers.CharField(
        default='Shishu',
        required=False,
        allow_blank=True,
        help_text="Specify Vibhag: Shishu / Arun / Kesari / Kishore or Class (e.g. Nursery, 1, 2...)"
    )
    language = serializers.CharField(
        required=False,
        default='',
        allow_blank=True,
        help_text="Language: 'en' or 'gu'"
    )
    whatsapp_number = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
        help_text="10-digit WhatsApp number"
    )
    email = serializers.EmailField(
        required=False,
        allow_blank=True,
        default="",
        help_text="User email address for communication and form pre-fill"
    )
    frontend_base_url = serializers.CharField(
        required=False,
        default="",
        allow_blank=True,
        help_text="Optional Frontend domain, e.g., https://your-frontend.com"
    )
    answers = serializers.DictField(
        child=serializers.CharField(),
        required=False,
        default=dict,
        help_text="Dictionary of question IDs and selected option, e.g. {'1': 'B', '2': 'C', ...}"
    )

    def validate_answers(self, value):
        return value or {}

    def validate(self, attrs):
        submission_id = attrs.get('submission_id')
        whatsapp_number = attrs.get('whatsapp_number')
        surname = attrs.get('surname')
        if not submission_id:
            if not whatsapp_number:
                raise serializers.ValidationError({"whatsapp_number": "WhatsApp number is required when adding a new enquiry."})

            # Check if vibhag or standard is passed as a class/grade
            std = (attrs.get('standard') or '').strip()
            v = (attrs.get('vibhag') or '').strip()

            # Mapping of standard/class to official Shreyas Vibhag
            vibhag_map = {
                'nursery': ('Nursery', 'Shishu'),
                'jr.kg': ('Jr.KG', 'Shishu'),
                'sr.kg': ('Sr.KG', 'Arun'),
                '1': ('1', 'Arun'),
                '2': ('2', 'Arun'),
                '3': ('3', 'Kesari'),
                '4': ('4', 'Kesari'),
                '5': ('5', 'Kesari'),
                '6': ('6', 'Kesari'),
                '7': ('7', 'Kesari'),
                '8': ('8', 'Kishore'),
                '9': ('9', 'Kishore'),
                '10': ('10', 'Kishore'),
                '11': ('11-Science', 'Kishore'),
                '11-science': ('11-Science', 'Kishore'),
                '11-commerce': ('11-Commerce', 'Kishore'),
                '11-arts': ('11-Arts', 'Kishore'),
                '12': ('12-Science', 'Kishore'),
                '12-science': ('12-Science', 'Kishore'),
                '12-commerce': ('12-Commerce', 'Kishore'),
                '12-arts': ('12-Arts', 'Kishore'),
            }

            # If user sent class in 'vibhag' (e.g. "1", "2", "Nursery", etc.)
            if v.lower() in vibhag_map:
                mapped_std, mapped_vibhag = vibhag_map[v.lower()]
                attrs['vibhag'] = mapped_vibhag
                if not std or std == 'Nursery':
                    attrs['standard'] = mapped_std
            elif v.capitalize() in ['Shishu', 'Arun', 'Kesari', 'Kishore']:
                attrs['vibhag'] = v.capitalize()
            elif std.lower() in vibhag_map:
                attrs['vibhag'] = vibhag_map[std.lower()][1]
            else:
                attrs['vibhag'] = 'Shishu'

            # Ensure standard is populated properly
            if not attrs.get('standard') or attrs.get('standard') == 'Nursery':
                if v.lower() in vibhag_map:
                    attrs['standard'] = vibhag_map[v.lower()][0]

            # Ensure father_name / parent_name synchronization
            if not attrs.get('parent_name') and attrs.get('father_name'):
                attrs['parent_name'] = attrs['father_name']
            elif not attrs.get('father_name') and attrs.get('parent_name'):
                attrs['father_name'] = attrs['parent_name']
        return attrs



IMAGE_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.webp')
DOCUMENT_EXTENSIONS = ('.pdf', '.doc', '.docx', '.jpg', '.jpeg', '.png', '.webp')

def validate_uploaded_image(file_obj, field_name: str):
    """
    Validates that the uploaded file is strictly an image (JPG, JPEG, PNG, WEBP).
    Rejects PDF, DOC, DOCX or corrupted image files.
    """
    if not file_obj or isinstance(file_obj, str):
        return

    file_name = getattr(file_obj, 'name', '').lower()
    if file_name and not file_name.endswith(IMAGE_EXTENSIONS):
        raise serializers.ValidationError({
            field_name: f"Invalid format for {field_name}. Only image files ({', '.join(IMAGE_EXTENSIONS)}) are allowed. PDF or Word documents are not accepted."
        })

    # Validate image integrity using Pillow
    try:
        from PIL import Image
        initial_pos = file_obj.tell() if hasattr(file_obj, 'tell') else 0
        img = Image.open(file_obj)
        img.verify()
        if hasattr(file_obj, 'seek'):
            file_obj.seek(initial_pos)
    except Exception:
        raise serializers.ValidationError({
            field_name: f"Corrupted or invalid image file uploaded for {field_name}. Please upload a valid JPG/PNG/WEBP image."
        })


def validate_uploaded_document(file_obj, field_name: str):
    """
    Validates that the uploaded file is a valid Document (PDF, DOC, DOCX) or clear document scan/image (JPG, PNG).
    """
    if not file_obj or isinstance(file_obj, str):
        return

    file_name = getattr(file_obj, 'name', '').lower()
    if file_name and not file_name.endswith(DOCUMENT_EXTENSIONS):
        raise serializers.ValidationError({
            field_name: f"Invalid file format for {field_name}. Only PDF, DOC, DOCX, or scanned images (JPG/PNG/WEBP) are allowed."
        })


class AdmissionApplicationSerializer(serializers.ModelSerializer):
    submission_id = serializers.IntegerField(write_only=True, required=False)
    child_first_name = serializers.CharField(required=False, allow_blank=True)
    vibhag = serializers.CharField(required=False, allow_blank=True)
    added_by = serializers.SerializerMethodField()
    created_by_user = serializers.SerializerMethodField()
    quiz_answers = serializers.SerializerMethodField()
    quiz_details = serializers.SerializerMethodField()

    class Meta:
        model = AdmissionApplication
        fields = '__all__'
        read_only_fields = ('application_number', 'created_at')

    def get_quiz_answers(self, obj):
        """Returns the parent's submitted answers dictionary { '1': 'B', ..., '11': '...' }"""
        if obj.submission and obj.submission.answers:
            return obj.submission.answers
        return {}

    def get_quiz_details(self, obj):
        """Returns structured questionnaire summary including MCQ score, written responses, and AI evaluations"""
        if not obj.submission:
            return None

        sub = obj.submission
        answers = sub.answers or {}
        ai_evals = answers.get("ai_evaluations", {})
        
        # Split MCQs vs Written responses
        mcq_answers = {str(k): v for k, v in answers.items() if str(k).isdigit() and int(k) <= 10}
        written_answers = {str(k): v for k, v in answers.items() if str(k).isdigit() and int(k) in [11, 12, 13, 14]}

        return {
            "submission_id": sub.id,
            "score": sub.score,
            "total_marks": 50,
            "qa_status": sub.qa_status,
            "tag": sub.tag,
            "is_eligible": sub.is_eligible,
            "quiz_completed_at": sub.quiz_completed_at,
            "answers": answers,
            "mcq_answers": mcq_answers,
            "written_answers": written_answers,
            "ai_evaluations": ai_evals
        }

    def get_added_by(self, obj):
        if obj.submission and obj.submission.created_by:
            return obj.submission.created_by.full_name or obj.submission.created_by.username
        return "Online / Self"

    def get_created_by_user(self, obj):
        if obj.submission and obj.submission.created_by:
            u = obj.submission.created_by
            return {
                "id": u.id,
                "username": u.username,
                "full_name": u.full_name or u.username,
                "email": u.email,
                "role": u.role
            }
        return None

    def validate(self, attrs):
        is_admin_update = self.context.get('is_admin_update', False)

        submission_id = attrs.get('submission_id')
        submission = None

        if not is_admin_update:
            if submission_id:
                try:
                    submission = QuizSubmission.objects.get(id=submission_id)
                    attrs['submission'] = submission
                except QuizSubmission.DoesNotExist:
                    raise serializers.ValidationError({"submission_id": "Invalid submission ID."})
            else:
                raise serializers.ValidationError({"submission_id": "submission_id is required."})

            # Mandatory Parent Profile Details Validation
            parent_required_fields = {
                # Mother required fields
                'mother_name': "Mother's name is required.",
                'mother_surname': "Mother's surname is required.",
                'mother_father_or_husband_name': "Mother's father/husband name is required.",
                'mother_education': "Mother's education is required.",
                'mother_occupation': "Mother's occupation is required.",
                'mother_annual_income': "Mother's annual income is required.",
                'mother_phone_residence': "Mother's residence phone number is required.",
                'mother_whatsapp': "Mother's WhatsApp number is required.",
                'mother_nationality': "Mother's nationality is required.",
                'mother_address_residence': "Mother's residential address is required.",
                # Father required fields
                'father_name': "Father's name is required.",
                'father_surname': "Father's surname is required.",
                'father_father_name': "Father's father name is required.",
                'father_education': "Father's education is required.",
                'father_occupation': "Father's occupation is required.",
                'father_annual_income': "Father's annual income is required.",
                'father_phone_residence': "Father's residence phone number is required.",
                'father_whatsapp': "Father's WhatsApp number is required.",
                'father_nationality': "Father's nationality is required.",
                'father_address_residence': "Father's residential address is required.",
            }

            field_errors = {}
            for field_name, err_msg in parent_required_fields.items():
                val = attrs.get(field_name)
                if val is None or str(val).strip() == '':
                    field_errors[field_name] = err_msg

            # Terms & Conditions validation
            if not attrs.get('agreed_to_rules'):
                field_errors['agreed_to_rules'] = "You must agree to the Shreyas Rules and Regulations to submit the application."

            # Record timestamp for terms & conditions acceptance
            from django.utils import timezone
            attrs['terms_agreed_timestamp'] = timezone.now()
            if not attrs.get('terms_agreed_date'):
                attrs['terms_agreed_date'] = timezone.now().date()

            # Doctor's Health Certificate validation
            if not attrs.get('health_certificate'):
                field_errors['health_certificate'] = "The doctor's certificate and health report must be uploaded."

            # Document validation rules based on grade/class:
            # 1. Below Std 1 (Nursery, Playgroup, Shishu, Balwadi, Jr.KG, Sr.KG): Alak Malak Certificate is COMPULSORY.
            # 2. Std 2 and above (Higher classes like Std 2, 3, 4, etc.): Previous year's report card/marksheet is COMPULSORY.
            # 3. Std 1: Base primary grade (Birth cert & Parent aadhar mandatory).

            std_raw = str(attrs.get('standard') or (submission.standard if submission else '') or '').strip()
            vibhag_raw = str(attrs.get('vibhag') or (submission.vibhag if submission else '') or '').strip()
            std_lower = std_raw.lower()
            vibhag_lower = vibhag_raw.lower()

            # Helper to check grade level
            is_below_std_1 = any(k in std_lower or k in vibhag_lower for k in [
                'play', 'nursery', 'shishu', 'toddler', 'balwadi', 'jr', 'sr', 'kg', 'kindergarten'
            ])
            # Check numeric standard (e.g. "1", "2", "3", "Std 2")
            import re
            num_match = re.search(r'\d+', std_raw)
            std_num = int(num_match.group()) if num_match else None

            is_std_2_or_above = (std_num is not None and std_num >= 2) or any(
                f"std {n}" in std_lower or f"grade {n}" in std_lower or f"class {n}" in std_lower for n in range(2, 13)
            )

            if is_below_std_1:
                # Below Std 1 requires Alak Malak Certificate compulsory
                if not attrs.get('alak_malak_certificate'):
                    field_errors['alak_malak_certificate'] = "Alak Malak Certificate is compulsory for admission below Std 1 (Nursery, Shishu, Balwadi, KG)."
            elif is_std_2_or_above:
                # Std 2 and above requires previous year's report card/marksheet compulsory
                if not attrs.get('previous_report_card'):
                    field_errors['previous_report_card'] = "Previous year's report card / marksheet is compulsory for admission in Std 2 and above."

            # Mandatory: Birth certificate & Parent Aadhar
            if not attrs.get('birth_certificate'):
                field_errors['birth_certificate'] = "Birth Certificate is compulsory and must be uploaded."

            if not (attrs.get('parent_aadhar_card') or attrs.get('child_aadhar_card')):
                field_errors['parent_aadhar_card'] = "Parent's Aadhar Card is compulsory and must be uploaded."

            # Signature validation (At least one parent/guardian must sign)
            if not (attrs.get('mother_signature') or attrs.get('father_signature') or attrs.get('guardian_signature')):
                field_errors['signatures'] = "At least one signature (Mother, Father, or Guardian) is required."

            if field_errors:
                raise serializers.ValidationError(field_errors)

        # -------------------------------------------------------------
        # File Formats Validation:
        # Strictly Images (JPG, JPEG, PNG, WEBP) for Photo & Signatures
        # Documents (PDF, DOC, DOCX, JPG, PNG) for Certificates & Reports
        # -------------------------------------------------------------
        image_fields = ['photograph_child', 'mother_signature', 'father_signature', 'guardian_signature']
        for img_field in image_fields:
            if attrs.get(img_field):
                validate_uploaded_image(attrs.get(img_field), img_field)

        doc_fields = [
            'birth_certificate', 'parent_aadhar_card', 'child_aadhar_card',
            'health_certificate', 'eye_checkup_certificate', 'caste_certificate',
            'previous_report_card', 'alak_malak_certificate'
        ]
        for doc_field in doc_fields:
            if attrs.get(doc_field):
                validate_uploaded_document(attrs.get(doc_field), doc_field)

        # Pre-fill automatic population & protection for users
        request = self.context.get('request')
        is_admin_update = self.context.get('is_admin_update', False)
        is_staff = bool(request and request.user and request.user.is_staff)
        is_admin = is_admin_update or is_staff

        if submission and not is_admin_update:
            # Fixed Vibhag, Standard, Medium copied from Enquiry
            attrs['vibhag'] = submission.vibhag
            if hasattr(submission, 'standard') and submission.standard:
                attrs['standard'] = submission.standard
            if hasattr(submission, 'medium') and submission.medium:
                attrs['medium'] = submission.medium

            if not is_admin:
                # If not admin, strictly overwrite with the verified submission data
                if submission.child_name:
                    attrs['child_first_name'] = submission.child_name
                
                if submission.surname:
                    attrs['child_surname'] = submission.surname
                    if not attrs.get('father_surname'):
                        attrs['father_surname'] = submission.surname
                    if not attrs.get('mother_surname'):
                        attrs['mother_surname'] = submission.surname
                
                if submission.parent_name:
                    # If father_name or mother_name is not provided, autofill with parent_name
                    if not attrs.get('father_name') and not attrs.get('mother_name'):
                        attrs['father_name'] = submission.parent_name
                    elif not attrs.get('father_name'):
                        attrs['father_name'] = submission.parent_name

                if submission.whatsapp_number:
                    attrs['father_whatsapp'] = submission.whatsapp_number
                    attrs['mother_whatsapp'] = attrs.get('mother_whatsapp') or submission.whatsapp_number
                
                if submission.email:
                    attrs['father_email'] = attrs.get('father_email') or submission.email
                    attrs['mother_email'] = attrs.get('mother_email') or submission.email
            else:
                # Even if admin, if they left them blank, autofill from submission
                if not attrs.get('child_first_name') and submission.child_name:
                    attrs['child_first_name'] = submission.child_name
                if not attrs.get('child_surname') and submission.surname:
                    attrs['child_surname'] = submission.surname
                if not attrs.get('father_whatsapp') and submission.whatsapp_number:
                    attrs['father_whatsapp'] = submission.whatsapp_number
                if not attrs.get('father_email') and submission.email:
                    attrs['father_email'] = submission.email

        return attrs


class EvaluationAssessmentSerializer(serializers.Serializer):
    """
    Serializer for Academicians/Educators filling Part Y Digital Assessment
    Cognitive Assessment 1: max 5
    Cognitive Assessment 2: max 5
    Affective Assessment: max 10
    Psychomotor Assessment: max 10
    Total Part Y: 30 marks
    """
    m_tag = serializers.CharField(required=False, allow_blank=True, default="")
    mi_tag = serializers.CharField(required=False, allow_blank=True, default="")
    cognitive_assessment_1 = serializers.FloatField(required=True, min_value=0.0, max_value=5.0)
    cognitive_assessment_2 = serializers.FloatField(required=True, min_value=0.0, max_value=5.0)
    affective_assessment = serializers.FloatField(required=True, min_value=0.0, max_value=10.0)
    psychomotor_assessment = serializers.FloatField(required=True, min_value=0.0, max_value=10.0)


class MeritRankBoardSerializer(serializers.ModelSerializer):
    student_name = serializers.SerializerMethodField()
    parent_name = serializers.SerializerMethodField()
    contact_number = serializers.SerializerMethodField()
    mcq_score = serializers.SerializerMethodField()

    class Meta:
        model = AdmissionApplication
        fields = [
            'id',
            'application_number',
            'merit_rank',
            'student_name',
            'parent_name',
            'standard',
            'medium',
            'vibhag',
            'contact_number',
            'mcq_score',
            'alak_malak_months',
            'alak_malak_score',
            'sibling_opted_vk',
            'sibling_score',
            'total_part_x_score',
            'evaluator_m',
            'evaluator_mi',
            'cognitive_assessment_1',
            'cognitive_assessment_2',
            'affective_assessment',
            'psychomotor_assessment',
            'total_part_y_score',
            'final_aggregate_score',
            'admission_status',
            'interaction_date',
            'interaction_time',
            'interaction_slot_no',
            'parent_confirmed_slot',
            'created_at'
        ]

    def get_student_name(self, obj):
        return f"{obj.child_first_name} {obj.child_surname}".strip()

    def get_parent_name(self, obj):
        return obj.father_name or obj.mother_name or (obj.submission.parent_name if obj.submission else "")

    def get_contact_number(self, obj):
        return obj.father_whatsapp or obj.mother_whatsapp or (obj.submission.whatsapp_number if obj.submission else "")

    def get_mcq_score(self, obj):
        if obj.mcq_score_part_x:
            return obj.mcq_score_part_x
        if obj.submission:
            return obj.submission.score
        return 0.0

