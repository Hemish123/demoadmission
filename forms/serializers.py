from rest_framework import serializers
from .models import QuizSubmission, AdmissionApplication

class QuizSubmissionListSerializer(serializers.ModelSerializer):
    admission_submitted = serializers.SerializerMethodField()
    application_number = serializers.SerializerMethodField()
    is_repeated_enquiry = serializers.SerializerMethodField()
    repeated_badge = serializers.SerializerMethodField()

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
            'repeated_badge'
        ]

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


class AdmissionApplicationSerializer(serializers.ModelSerializer):
    submission_id = serializers.IntegerField(write_only=True, required=False)
    child_first_name = serializers.CharField(required=False, allow_blank=True)
    vibhag = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = AdmissionApplication
        fields = '__all__'
        read_only_fields = ('application_number', 'created_at')

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

            # Terms & Conditions validation
            if not attrs.get('agreed_to_rules'):
                raise serializers.ValidationError({
                    "agreed_to_rules": "You must agree to the Shreyas Rules and Regulations to submit the application."
                })

            # Record timestamp for terms & conditions acceptance
            from django.utils import timezone
            attrs['terms_agreed_timestamp'] = timezone.now()
            if not attrs.get('terms_agreed_date'):
                attrs['terms_agreed_date'] = timezone.now().date()

            # Doctor's Health Certificate validation
            if not attrs.get('health_certificate'):
                raise serializers.ValidationError({
                    "health_certificate": "The doctor's certificate and health report must be uploaded."
                })

            # Previous year report card vs Alak Malak Certificate check based on vibhag
            vibhag = (submission.vibhag if submission else attrs.get('vibhag', '')).strip().lower()
            is_nursery = vibhag in ['shishu', 'nursery', 'shishu (શિશુ)']

            if is_nursery:
                if not attrs.get('alak_malak_certificate'):
                    raise serializers.ValidationError({
                        "alak_malak_certificate": "Alak Malak Certificate is required for Nursery (Shishu) applicants."
                    })
            else:
                if not attrs.get('previous_report_card'):
                    raise serializers.ValidationError({
                        "previous_report_card": "Previous year's report card is required for admission."
                    })

            # Signature validation (At least one parent/guardian must sign)
            if not (attrs.get('mother_signature') or attrs.get('father_signature') or attrs.get('guardian_signature')):
                raise serializers.ValidationError({
                    "signatures": "At least one signature (Mother, Father, or Guardian) is required."
                })

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
