from django.contrib import admin
from django.utils.html import format_html
from .models import QuizSubmission, AdmissionApplication, AdminUser, AuditLog


@admin.register(AdminUser)
class AdminUserAdmin(admin.ModelAdmin):
    list_display = ('id', 'username', 'full_name', 'email', 'role', 'is_active', 'created_at', 'updated_at')
    list_filter = ('role', 'is_active', 'created_at')
    search_fields = ('username', 'full_name', 'email')
    readonly_fields = ('pin_hash', 'otp_code', 'otp_expires_at', 'created_at', 'updated_at')


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'actor_username', 'actor_email', 'actor_role', 'method', 'endpoint', 'response_status', 'ip_address', 'created_at')
    list_filter = ('method', 'response_status', 'actor_role', 'created_at')
    search_fields = ('actor_username', 'actor_email', 'endpoint', 'ip_address')
    readonly_fields = ('actor_username', 'actor_email', 'actor_role', 'method', 'endpoint', 'query_params', 'request_body', 'response_status', 'ip_address', 'user_agent', 'created_at')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(QuizSubmission)
class QuizSubmissionAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'child_name',
        'surname',
        'parent_name',
        'standard',
        'medium',
        'vibhag',
        'whatsapp_number',
        'score',
        'tag',
        'qa_status',
        'payment_status',
        'whatsapp_link_sent',
        'repeated_badge_display',
        'created_at'
    )
    list_filter = ('vibhag', 'standard', 'medium', 'payment_status', 'qa_status', 'tag', 'whatsapp_link_sent', 'created_at')
    search_fields = ('child_name', 'surname', 'parent_name', 'whatsapp_number', 'email')
    readonly_fields = ('created_at', 'quiz_completed_at')

    def repeated_badge_display(self, obj):
        clean = "".join(filter(str.isdigit, str(obj.whatsapp_number)))
        phone_10 = clean[-10:] if len(clean) >= 10 else clean
        count = QuizSubmission.objects.filter(
            whatsapp_number__endswith=phone_10,
            child_name__iexact=obj.child_name.strip()
        ).count()
        if count > 1:
            return format_html('<span style="color: #b78103; font-weight: bold; background: #fff3cd; padding: 2px 6px; border-radius: 4px;">Repeated Enquiry</span>')
        return format_html('<span style="color: #198754;">Unique</span>')
    repeated_badge_display.short_description = "Enquiry Badge"


@admin.register(AdmissionApplication)
class AdmissionApplicationAdmin(admin.ModelAdmin):
    list_display = (
        'application_number',
        'child_first_name',
        'child_surname',
        'standard',
        'medium',
        'vibhag',
        'father_name',
        'father_whatsapp',
        'mother_name',
        'agreed_to_rules',
        'created_at'
    )
    search_fields = (
        'application_number',
        'child_first_name',
        'child_surname',
        'father_name',
        'mother_name',
        'father_whatsapp',
        'mother_whatsapp',
        'father_email'
    )
    list_filter = (
        'vibhag',
        'standard',
        'medium',
        'agreed_to_rules',
        'created_at'
    )
    readonly_fields = ('application_number', 'created_at', 'form_submitted_at', 'terms_agreed_timestamp')
