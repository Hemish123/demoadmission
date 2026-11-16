import logging
import json
import random
from datetime import timedelta

from django.shortcuts import get_object_or_404
from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.core.mail import send_mail
from typing import Optional

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from .models import QuizSubmission, AdmissionApplication, AdminUser, AuditLog
from .jwt_auth import generate_jwt_token, decode_jwt_token, get_admin_user_from_token
from .questions_data import ALIGNED_ANSWERS
from .serializers import (
    SubmitQuizSerializer,
    QuizSubmissionListSerializer,
    AdmissionApplicationSerializer
)
from .whatsapp import (
    generate_whatsapp_link,
    send_whatsapp_template_message,
    send_whatsapp_booklet_template,
    send_payment_received_whatsapp_notifications,
    normalize_phone_number
)

logger = logging.getLogger(__name__)


# ==============================================================================
# Helper Functions
# ==============================================================================

def get_performance_tag(score: int) -> str:
    if score == 7:
        return "Outstanding"
    elif score == 6:
        return "Excellent"
    elif score == 5:
        return "Very Good"
    elif score == 4:
        return "Good"
    else:
        return "Needs Improvement"


def get_authenticated_admin_user(request) -> tuple[bool, Optional[AdminUser], str]:
    """
    Strict Token Authentication for Admin/Staff endpoints.
    Requires 'Authorization: Bearer <token>' in request headers.
    Returns (is_authenticated, admin_user_obj, role)
    """
    auth_header = request.headers.get('Authorization') or request.META.get('HTTP_AUTHORIZATION') or ""
    if auth_header and auth_header.lower().startswith('bearer '):
        user = get_admin_user_from_token(auth_header)
        if user:
            return True, user, user.role

    # Fallback only for Django superuser session in admin site
    if hasattr(request, 'user') and request.user.is_authenticated and request.user.is_staff:
        return True, None, "ADMIN"

    return False, None, "GUEST"


def enforce_admin_token(request, required_role: Optional[str] = None):
    """
    Helper to mandate valid Bearer Token for admin APIs.
    If invalid or missing token, returns Response with 401/403. Otherwise returns None.
    """
    is_auth, user, role = get_authenticated_admin_user(request)
    if not is_auth:
        return Response({
            "status": "error",
            "message": "Authentication required. Please provide a valid 'Authorization: Bearer <token>' header."
        }, status=status.HTTP_401_UNAUTHORIZED)

    if required_role and role != required_role:
        return Response({
            "status": "error",
            "message": f"Access restricted. Only users with role '{required_role}' are allowed."
        }, status=status.HTTP_403_FORBIDDEN)

    return None


# ==============================================================================
# Admin Authentication & User Management
# ==============================================================================

class AdminLoginView(APIView):
    """
    Two-Step Verification: Step 1 - Verify Username/Email & PIN, then send OTP to registered email.
    POST /api/admin/login/
    Body: {"email": "admin@shreyasfoundation.in", "pin": "1234"}
    """
    def post(self, request):
        identifier = (request.data.get("email") or request.data.get("username") or "").strip()
        pin = str(request.data.get("pin", "")).strip()

        if not identifier or not pin:
            return Response({
                "status": "error",
                "message": "Email/Username and PIN are required."
            }, status=status.HTTP_400_BAD_REQUEST)

        admin_user = AdminUser.objects.filter(
            Q(email__iexact=identifier) | Q(username__iexact=identifier),
            is_active=True
        ).first()

        if not admin_user or not admin_user.check_pin(pin):
            return Response({
                "status": "error",
                "message": "Invalid email/username or PIN."
            }, status=status.HTTP_401_UNAUTHORIZED)

        # Generate 6-digit OTP for 2-step verification
        otp = f"{random.randint(100000, 999999)}"
        admin_user.otp_code = otp
        admin_user.otp_expires_at = timezone.now() + timedelta(minutes=10)
        admin_user.save(update_fields=['otp_code', 'otp_expires_at'])

        subject = "Shreyas Foundation Admin - 2-Step Verification Login OTP"
        body = (
            f"Namaste {admin_user.full_name or admin_user.username},\n\n"
            f"Your 2-Step Verification OTP for logging into Shreyas Foundation Portal is: {otp}\n\n"
            f"If you did not attempt this login, please contact technical support immediately.\n\n"
            f"Shreyas Foundation Technical Team"
        )
        try:
            from .email_service import generate_otp_email_html
            sender = getattr(settings, 'DEFAULT_FROM_EMAIL', 'JMS Tech Solution <anand@jmstech.co>')
            html_message = generate_otp_email_html(
                recipient_name=admin_user.full_name or admin_user.username,
                otp_code=otp,
                purpose="login"
            )
            send_mail(
                subject=subject,
                message=body,
                from_email=sender,
                recipient_list=[admin_user.email],
                html_message=html_message,
                fail_silently=True
            )
            logger.info(f"2-Step verification OTP sent to {admin_user.email}")
        except Exception as e:
            logger.error(f"Failed to send 2-Step verification email OTP: {e}")

        # Mask email for privacy (e.g. pr***11@gmail.com)
        email_parts = admin_user.email.split('@')
        if len(email_parts) == 2 and len(email_parts[0]) > 2:
            masked_email = f"{email_parts[0][:2]}***{email_parts[0][-2:]}@{email_parts[1]}"
        else:
            masked_email = admin_user.email

        return Response({
            "status": "otp_required",
            "message": f"Credentials verified. 2-Step verification OTP has been sent to your email ({masked_email}).",
            "email": admin_user.email,
            "masked_email": masked_email,
            **({"debug_otp": otp} if settings.DEBUG else {})
        }, status=status.HTTP_200_OK)


class AdminVerifyLoginOTPView(APIView):
    """
    Two-Step Verification: Step 2 - Verify OTP & complete login, returns JWT permanent token.
    POST /api/admin/verify-login-otp/
    Body: {"email": "admin@shreyasfoundation.in", "otp": "123456"}
    """
    def post(self, request):
        identifier = (request.data.get("email") or request.data.get("username") or "").strip()
        otp = str(request.data.get("otp", "")).strip()

        if not identifier or not otp:
            return Response({
                "status": "error",
                "message": "Email/Username and OTP are required."
            }, status=status.HTTP_400_BAD_REQUEST)

        admin_user = AdminUser.objects.filter(
            Q(email__iexact=identifier) | Q(username__iexact=identifier),
            is_active=True
        ).first()

        if not admin_user:
            return Response({
                "status": "error",
                "message": "Admin user not found."
            }, status=status.HTTP_404_NOT_FOUND)

        if not admin_user.otp_code or admin_user.otp_code != otp:
            return Response({
                "status": "error",
                "message": "Invalid OTP code. Please check your email and try again."
            }, status=status.HTTP_400_BAD_REQUEST)

        if admin_user.otp_expires_at and admin_user.otp_expires_at < timezone.now():
            return Response({
                "status": "error",
                "message": "OTP has expired. Please log in again to receive a fresh OTP."
            }, status=status.HTTP_400_BAD_REQUEST)

        # Clear OTP after successful verification
        admin_user.otp_code = None
        admin_user.otp_expires_at = None
        admin_user.save(update_fields=['otp_code', 'otp_expires_at'])

        # Generate permanent JWT token
        token = generate_jwt_token(admin_user)

        logger.info(f"Admin 2-Step login successful for {admin_user.username} ({admin_user.email})")

        return Response({
            "status": "success",
            "message": "2-Step verification successful. Login completed.",
            "token": token,
            "token_type": "Bearer",
            "is_permanent": True,
            "user": {
                "id": admin_user.id,
                "username": admin_user.username,
                "full_name": admin_user.full_name,
                "email": admin_user.email,
                "role": admin_user.role
            }
        }, status=status.HTTP_200_OK)


class AdminUserManagementView(APIView):
    """
    User Management: Only Admin can create, list, edit (PUT/PATCH), and delete users.
    GET    /api/admin/users/             - List all users or get single user (?id=...)
    POST   /api/admin/users/             - Create new user (Role: ADMIN / STAFF / ACADEMICIAN)
    PATCH  /api/admin/users/?id=<id>     - Edit user details (full_name, email, role, is_active, pin)
    DELETE /api/admin/users/?id=<id>     - Delete a user (Cannot delete yourself)
    """
    def get(self, request, user_id=None):
        denied = enforce_admin_token(request, required_role='ADMIN')
        if denied:
            return denied

        target_id = user_id or request.query_params.get("id")
        if target_id:
            user = get_object_or_404(AdminUser, id=target_id)
            return Response({
                "status": "success",
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "full_name": user.full_name,
                    "email": user.email,
                    "role": user.role,
                    "is_active": user.is_active,
                    "created_at": user.created_at,
                    "updated_at": user.updated_at
                }
            }, status=status.HTTP_200_OK)

        users = AdminUser.objects.all().order_by('-created_at')
        data = [{
            "id": u.id,
            "username": u.username,
            "full_name": u.full_name,
            "email": u.email,
            "role": u.role,
            "is_active": u.is_active,
            "created_at": u.created_at,
            "updated_at": u.updated_at
        } for u in users]
        return Response({"status": "success", "count": len(data), "users": data}, status=status.HTTP_200_OK)

    def post(self, request):
        denied = enforce_admin_token(request, required_role='ADMIN')
        if denied:
            return denied

        username = request.data.get("username", "").strip()
        full_name = request.data.get("full_name", "").strip()
        email = request.data.get("email", "").strip()
        pin = str(request.data.get("pin", "")).strip()
        role = request.data.get("role", "STAFF").strip().upper()

        if not email or not pin:
            return Response({
                "status": "error",
                "message": "Email and PIN are required."
            }, status=status.HTTP_400_BAD_REQUEST)

        if not username:
            username = email.split('@')[0]

        if len(pin) < 4:
            return Response({
                "status": "error",
                "message": "PIN must be at least 4 digits."
            }, status=status.HTTP_400_BAD_REQUEST)

        if AdminUser.objects.filter(username__iexact=username).exists():
            return Response({
                "status": "error",
                "message": f"Username '{username}' already exists. Please choose a different username."
            }, status=status.HTTP_400_BAD_REQUEST)

        if AdminUser.objects.filter(email__iexact=email).exists():
            return Response({
                "status": "error",
                "message": f"Email '{email}' is already registered."
            }, status=status.HTTP_400_BAD_REQUEST)

        valid_roles = [r[0] for r in AdminUser.ROLE_CHOICES]
        if role not in valid_roles:
            role = 'STAFF'

        user = AdminUser(
            username=username,
            full_name=full_name,
            email=email,
            role=role,
            is_active=True
        )
        user.set_pin(pin)
        user.save()

        logger.info(f"Admin created new user: {user.username} ({user.email}) with role: {user.role}")
        return Response({
            "status": "success",
            "message": f"User {user.email} created successfully with role '{user.role}'.",
            "user": {
                "id": user.id,
                "username": user.username,
                "full_name": user.full_name,
                "email": user.email,
                "role": user.role
            }
        }, status=status.HTTP_201_CREATED)

    def patch(self, request, user_id=None):
        """
        Edit User: Can update full_name, email, role, is_active, and reset PIN.
        Pass ID in query (?id=...) or in URL path.
        """
        denied = enforce_admin_token(request, required_role='ADMIN')
        if denied:
            return denied

        target_id = user_id or request.query_params.get("id") or request.data.get("id")
        if not target_id:
            return Response({
                "status": "error",
                "message": "User ID is required (pass ?id=<id> or in request body)."
            }, status=status.HTTP_400_BAD_REQUEST)

        user = AdminUser.objects.filter(id=target_id).first()
        if not user:
            return Response({
                "status": "error",
                "message": f"AdminUser with id {target_id} does not exist."
            }, status=status.HTTP_404_NOT_FOUND)

        if "full_name" in request.data:
            user.full_name = str(request.data["full_name"]).strip()

        if "email" in request.data:
            new_email = str(request.data["email"]).strip()
            if new_email and new_email.lower() != user.email.lower():
                if AdminUser.objects.filter(email__iexact=new_email).exclude(id=user.id).exists():
                    return Response({
                        "status": "error",
                        "message": f"Email '{new_email}' is already in use by another user."
                    }, status=status.HTTP_400_BAD_REQUEST)
                user.email = new_email

        if "username" in request.data:
            new_username = str(request.data["username"]).strip()
            if new_username and new_username.lower() != user.username.lower():
                if AdminUser.objects.filter(username__iexact=new_username).exclude(id=user.id).exists():
                    return Response({
                        "status": "error",
                        "message": f"Username '{new_username}' is already in use by another user."
                    }, status=status.HTTP_400_BAD_REQUEST)
                user.username = new_username

        if "role" in request.data:
            new_role = str(request.data["role"]).strip().upper()
            valid_roles = [r[0] for r in AdminUser.ROLE_CHOICES]
            if new_role in valid_roles:
                user.role = new_role

        if "is_active" in request.data:
            val = request.data["is_active"]
            user.is_active = (val is True or str(val).lower() == 'true')

        if "pin" in request.data and str(request.data["pin"]).strip():
            new_pin = str(request.data["pin"]).strip()
            if len(new_pin) < 4:
                return Response({
                    "status": "error",
                    "message": "PIN must be at least 4 digits."
                }, status=status.HTTP_400_BAD_REQUEST)
            user.set_pin(new_pin)

        user.save()
        logger.info(f"Admin updated user {user.id} ({user.username})")

        return Response({
            "status": "success",
            "message": f"User '{user.username}' updated successfully.",
            "user": {
                "id": user.id,
                "username": user.username,
                "full_name": user.full_name,
                "email": user.email,
                "role": user.role,
                "is_active": user.is_active,
                "updated_at": user.updated_at
            }
        }, status=status.HTTP_200_OK)

    def delete(self, request, user_id=None):
        """
        Delete User: Permanent deletion of a staff/academician/admin user.
        Pass ID in query (?id=...) or in URL path.
        Cannot delete the currently logged-in admin user.
        """
        denied = enforce_admin_token(request, required_role='ADMIN')
        if denied:
            return denied

        _, current_admin, _ = get_authenticated_admin_user(request)

        target_id = user_id or request.query_params.get("id") or request.data.get("id")
        if not target_id:
            return Response({
                "status": "error",
                "message": "User ID is required to delete (pass ?id=<id> or in request body)."
            }, status=status.HTTP_400_BAD_REQUEST)

        user = AdminUser.objects.filter(id=target_id).first()
        if not user:
            return Response({
                "status": "error",
                "message": f"AdminUser with id {target_id} does not exist."
            }, status=status.HTTP_404_NOT_FOUND)

        # Prevent admin from deleting themselves
        if current_admin and current_admin.id == user.id:
            return Response({
                "status": "error",
                "message": "You cannot delete your own admin account while logged in."
            }, status=status.HTTP_400_BAD_REQUEST)

        deleted_username = user.username
        deleted_email = user.email
        user.delete()

        logger.info(f"Admin deleted user: {deleted_username} ({deleted_email}, id: {target_id})")
        return Response({
            "status": "success",
            "message": f"User '{deleted_username}' ({deleted_email}) has been permanently deleted.",
            "deleted_user_id": int(target_id)
        }, status=status.HTTP_200_OK)


class ForgotPinRequestOTPView(APIView):
    """
    Flow A: Step 2 - Forgot PIN: Send OTP to registered email
    POST /api/admin/forgot-pin/request-otp/
    Body: {"email": "admin@shreyasfoundation.in"} or {"username": "admin.shreyas"}
    """
    def post(self, request):
        identifier = (request.data.get("email") or request.data.get("username") or "").strip()
        if not identifier:
            return Response({
                "status": "error",
                "message": "Username or registered email is required."
            }, status=status.HTTP_400_BAD_REQUEST)

        admin_user = AdminUser.objects.filter(
            Q(email__iexact=identifier) | Q(username__iexact=identifier),
            is_active=True
        ).first()

        if not admin_user:
            return Response({
                "status": "error",
                "message": "No active admin user found with this email or username."
            }, status=status.HTTP_404_NOT_FOUND)

        otp = f"{random.randint(100000, 999999)}"
        admin_user.otp_code = otp
        admin_user.otp_expires_at = timezone.now() + timedelta(minutes=10)
        admin_user.save(update_fields=['otp_code', 'otp_expires_at'])

        subject = "Shreyas Foundation Admin - Password/PIN Reset OTP"
        body = (
            f"Namaste {admin_user.full_name or admin_user.username},\n\n"
            f"Your OTP for resetting the PIN is: {otp}\n"
            f"If you did not request this, please ignore this email.\n\n"
            f"Shreyas Foundation Technical Team"
        )
        try:
            from .email_service import generate_otp_email_html
            sender = getattr(settings, 'DEFAULT_FROM_EMAIL', 'JMS Tech Solution <anand@jmstech.co>')
            html_message = generate_otp_email_html(
                recipient_name=admin_user.full_name or admin_user.username,
                otp_code=otp,
                purpose="reset"
            )
            send_mail(
                subject=subject,
                message=body,
                from_email=sender,
                recipient_list=[admin_user.email],
                html_message=html_message,
                fail_silently=True
            )
            logger.info(f"Forgot PIN OTP sent to {admin_user.email}")
        except Exception as e:
            logger.error(f"Failed to send email OTP: {e}")

        return Response({
            "status": "success",
            "message": f"OTP has been sent to {admin_user.email} (valid for 10 minutes).",
            "email": admin_user.email,
            **({"debug_otp": otp} if settings.DEBUG else {})
        }, status=status.HTTP_200_OK)


class ForgotPinVerifyAndResetView(APIView):
    """
    Flow A: Step 2 - Verify OTP & Set New PIN
    POST /api/admin/forgot-pin/reset/
    Body: {"email": "admin@shreyasfoundation.in", "otp": "123456", "new_pin": "5678"}
    """
    def post(self, request):
        identifier = (request.data.get("email") or request.data.get("username") or "").strip()
        otp = request.data.get("otp", "").strip()
        new_pin = str(request.data.get("new_pin", "")).strip()

        if not identifier or not otp or not new_pin:
            return Response({
                "status": "error",
                "message": "Email/Username, OTP, and new_pin are required."
            }, status=status.HTTP_400_BAD_REQUEST)

        if len(new_pin) < 4:
            return Response({
                "status": "error",
                "message": "New PIN must be at least 4 digits."
            }, status=status.HTTP_400_BAD_REQUEST)

        admin_user = AdminUser.objects.filter(
            Q(email__iexact=identifier) | Q(username__iexact=identifier),
            is_active=True
        ).first()

        if not admin_user:
            return Response({
                "status": "error",
                "message": "Admin user not found."
            }, status=status.HTTP_404_NOT_FOUND)

        if not admin_user.otp_code or admin_user.otp_code != otp:
            return Response({
                "status": "error",
                "message": "Invalid OTP code."
            }, status=status.HTTP_400_BAD_REQUEST)

        if admin_user.otp_expires_at and admin_user.otp_expires_at < timezone.now():
            return Response({
                "status": "error",
                "message": "OTP has expired. Please request a new OTP."
            }, status=status.HTTP_400_BAD_REQUEST)

        admin_user.set_pin(new_pin)
        admin_user.otp_code = None
        admin_user.otp_expires_at = None
        admin_user.save(update_fields=['pin_hash', 'otp_code', 'otp_expires_at'])

        return Response({
            "status": "success",
            "message": "Admin PIN has been reset successfully. You can now login with your new PIN."
        }, status=status.HTTP_200_OK)


class AdminInteractionCalendarView(APIView):
    """
    Step 8: Backend Calendar Tab - Lists day-wise scheduled interviews/interactions for Admin.
    GET /api/admin/interaction-calendar/?date=YYYY-MM-DD
    Headers: Authorization: Bearer <ADMIN_PERMANENT_TOKEN>
    """
    def get(self, request):
        denied = enforce_admin_token(request)
        if denied:
            return denied

        filter_date_str = request.query_params.get("date")
        queryset = AdmissionApplication.objects.filter(
            interaction_date__isnull=False
        ).select_related('submission').order_by('interaction_date', 'interaction_slot_no', 'created_at')

        if filter_date_str:
            queryset = queryset.filter(interaction_date=filter_date_str)

        # Group day-wise & slot-wise for the Calendar UI
        calendar_data = {}
        for app in queryset:
            date_key = str(app.interaction_date)
            if date_key not in calendar_data:
                calendar_data[date_key] = {
                    "date": date_key,
                    "total_children": 0,
                    "slots": {
                        1: {"slot_no": 1, "time": "9:00 AM TO 10:00 AM", "count": 0, "children": []},
                        2: {"slot_no": 2, "time": "10:00 AM TO 11:00 AM", "count": 0, "children": []},
                        3: {"slot_no": 3, "time": "11:00 AM TO 12:00 PM", "count": 0, "children": []},
                        4: {"slot_no": 4, "time": "12:00 PM TO 1:00 PM", "count": 0, "children": []},
                    }
                }

            calendar_data[date_key]["total_children"] += 1
            slot_no = app.interaction_slot_no or 1
            if slot_no in calendar_data[date_key]["slots"]:
                calendar_data[date_key]["slots"][slot_no]["count"] += 1
                calendar_data[date_key]["slots"][slot_no]["children"].append({
                    "application_id": app.id,
                    "application_number": app.application_number,
                    "child_name": f"{app.child_first_name} {app.child_surname}".strip(),
                    "standard": app.standard,
                    "medium": app.medium,
                    "vibhag": app.vibhag,
                    "father_name": app.father_name,
                    "father_whatsapp": app.father_whatsapp or (app.submission.whatsapp_number if app.submission else ""),
                    "whatsapp_sent": app.interaction_whatsapp_sent
                })

        # Format output list
        days_list = []
        for date_key in sorted(calendar_data.keys()):
            day_obj = calendar_data[date_key]
            slots_list = [day_obj["slots"][s] for s in [1, 2, 3, 4]]
            days_list.append({
                "date": day_obj["date"],
                "total_scheduled": day_obj["total_children"],
                "capacity": 40,
                "is_full": day_obj["total_children"] >= 40,
                "slots": slots_list
            })

        return Response({
            "status": "success",
            "total_days_scheduled": len(days_list),
            "calendar": days_list
        }, status=status.HTTP_200_OK)


class AdminExportDataView(APIView):
    """
    Data Export API for Excel (.xlsx) and CSV:
    Query Parameters:
      - type: 'enquiries' | 'submitted' | 'pending' (default: 'enquiries')
      - period: 'today' | 'week' | 'month' | 'all' (default: 'all')
      - export_format (or file_format): 'excel' | 'csv' (default: 'excel')
    """
    def get(self, request):
        import csv
        from django.http import HttpResponse
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

        denied = enforce_admin_token(request)
        if denied:
            return denied

        _, logged_in_admin, role = get_authenticated_admin_user(request)

        export_type = (request.query_params.get("type") or request.GET.get("type") or "enquiries").lower().strip()
        period = (request.query_params.get("period") or request.GET.get("period") or "all").lower().strip()
        export_format = (request.query_params.get("export_format") or request.query_params.get("file_format") or request.GET.get("export_format") or "excel").lower().strip()

        now = timezone.now()
        start_date = None

        if period == "today":
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == "week":
            start_date = now - timedelta(days=7)
        elif period == "month":
            start_date = now - timedelta(days=30)

        # 1. Base Queryset Filtering
        if export_type in ["submitted", "submissions", "submitted_applications"]:
            filename_prefix = "Submitted_Applications"
            qs = AdmissionApplication.objects.select_related('submission', 'submission__created_by').order_by("-created_at")
            if role != 'ADMIN' and logged_in_admin:
                qs = qs.filter(submission__created_by=logged_in_admin)
            if start_date:
                qs = qs.filter(created_at__gte=start_date)

            headers = [
                "Application No", "Submission ID", "Student Name", "Surname",
                "Standard", "Medium", "Vibhag", "Father Name", "Mother Name",
                "Father WhatsApp", "Father Email", "Interaction Date", "Interaction Slot",
                "Interaction Time", "Rules Agreed", "Added By", "Submitted At"
            ]
            rows = []
            for app in qs:
                sub = app.submission
                added_by = (sub.created_by.full_name or sub.created_by.username) if sub and sub.created_by else "Online / Self"
                rows.append([
                    app.application_number,
                    f"#{sub.id}" if sub else "-",
                    app.child_first_name,
                    app.child_surname,
                    app.standard,
                    app.medium,
                    app.vibhag,
                    app.father_name,
                    app.mother_name,
                    app.father_whatsapp or (sub.whatsapp_number if sub else ""),
                    app.father_email or (sub.email if sub else ""),
                    str(app.interaction_date) if app.interaction_date else "-",
                    f"Slot {app.interaction_slot_no}" if app.interaction_slot_no else "-",
                    app.interaction_time or "-",
                    "Yes" if app.agreed_to_rules else "No",
                    added_by,
                    app.created_at.strftime("%d-%m-%Y %H:%M") if app.created_at else "-"
                ])

        elif export_type in ["pending", "pending_forms"]:
            filename_prefix = "Pending_Admission_Forms"
            qs = QuizSubmission.objects.filter(
                payment_status='RECEIVED',
                admission_application__isnull=True
            ).select_related('created_by').order_by("-created_at")

            if role != 'ADMIN' and logged_in_admin:
                qs = qs.filter(created_by=logged_in_admin)
            if start_date:
                qs = qs.filter(created_at__gte=start_date)

            headers = [
                "Submission ID", "Student Name", "Surname", "Parent / Father Name",
                "Standard", "Medium", "Vibhag", "WhatsApp Number", "Email",
                "Quiz Score", "QA Status", "Payment Status", "1-Time Reminder Sent",
                "Added By", "Registered Date"
            ]
            rows = []
            for sub in qs:
                added_by = (sub.created_by.full_name or sub.created_by.username) if sub.created_by else "Online / Self"
                rows.append([
                    f"#{sub.id}",
                    sub.child_name,
                    sub.surname,
                    sub.parent_name,
                    sub.standard,
                    sub.medium,
                    sub.vibhag,
                    sub.whatsapp_number,
                    sub.email,
                    f"{sub.score}/7",
                    sub.qa_status,
                    sub.payment_status,
                    sub.reminder_sent_at.strftime("%d-%m-%Y %H:%M") if sub.reminder_sent_at else "No",
                    added_by,
                    sub.created_at.strftime("%d-%m-%Y %H:%M") if sub.created_at else "-"
                ])

        else:  # Default: all enquiries
            filename_prefix = "Enquiries"
            qs = QuizSubmission.objects.select_related('created_by').order_by("-created_at")

            if role != 'ADMIN' and logged_in_admin:
                qs = qs.filter(created_by=logged_in_admin)
            if start_date:
                qs = qs.filter(created_at__gte=start_date)

            headers = [
                "Submission ID", "Student Name", "Surname", "Parent / Father Name",
                "Standard", "Medium", "Vibhag", "WhatsApp Number", "Email",
                "Quiz Score", "Performance Tag", "QA Status", "Payment Status",
                "Form Submitted?", "Application Number", "Added By", "Created At"
            ]
            rows = []
            for sub in qs:
                added_by = (sub.created_by.full_name or sub.created_by.username) if sub.created_by else "Online / Self"
                app_no = sub.admission_application.application_number if hasattr(sub, 'admission_application') and sub.admission_application else "-"
                rows.append([
                    f"#{sub.id}",
                    sub.child_name,
                    sub.surname,
                    sub.parent_name,
                    sub.standard,
                    sub.medium,
                    sub.vibhag,
                    sub.whatsapp_number,
                    sub.email,
                    f"{sub.score}/7",
                    sub.tag or "-",
                    sub.qa_status,
                    sub.payment_status,
                    "Yes" if hasattr(sub, 'admission_application') and sub.admission_application else "No",
                    app_no,
                    added_by,
                    sub.created_at.strftime("%d-%m-%Y %H:%M") if sub.created_at else "-"
                ])

        filename = f"{filename_prefix}_{period}_{timezone.now().strftime('%Y%m%d_%H%M%S')}"

        # 2. Return CSV Format
        if export_format == "csv":
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'
            writer = csv.writer(response)
            writer.writerow(headers)
            for row in rows:
                writer.writerow(row)
            return response

        # 3. Return Excel (.xlsx) Format with Styling
        wb = Workbook()
        ws = wb.active
        ws.title = filename_prefix[:30]

        # Header styling: Dark Blue background, bold white text
        header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
        header_align = Alignment(horizontal="center", vertical="center", wrap_text=True)

        ws.append(headers)
        ws.row_dimensions[1].height = 28

        for col_idx in range(1, len(headers) + 1):
            cell = ws.cell(row=1, column=col_idx)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_align

        # Append Data Rows with border and zebra striping
        thin_border = Border(
            left=Side(style='thin', color='E2E8F0'),
            right=Side(style='thin', color='E2E8F0'),
            top=Side(style='thin', color='E2E8F0'),
            bottom=Side(style='thin', color='E2E8F0')
        )
        data_font = Font(name="Calibri", size=10)
        alt_fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")

        for r_idx, row in enumerate(rows, start=2):
            ws.append(row)
            ws.row_dimensions[r_idx].height = 20
            for c_idx in range(1, len(row) + 1):
                cell = ws.cell(row=r_idx, column=c_idx)
                cell.font = data_font
                cell.border = thin_border
                cell.alignment = Alignment(vertical="center")
                if r_idx % 2 == 0:
                    cell.fill = alt_fill

        # Auto-fit column widths
        for col in ws.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            col_letter = col[0].column_letter
            ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

        import io
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)

        response = HttpResponse(
            output.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}.xlsx"'
        return response


class AdminAuditLogView(APIView):
    """
    Audit Logs: Strictly restricted to users with role 'ADMIN'.
    GET /api/admin/audit-logs/
    """
    def get(self, request):
        denied = enforce_admin_token(request, required_role='ADMIN')
        if denied:
            return denied

        queryset = AuditLog.objects.all().order_by('-created_at')

        method = request.query_params.get("method")
        if method:
            queryset = queryset.filter(method__iexact=method)

        actor = request.query_params.get("actor")
        if actor:
            queryset = queryset.filter(
                Q(actor_email__icontains=actor) | Q(actor_username__icontains=actor)
            )

        endpoint = request.query_params.get("endpoint")
        if endpoint:
            queryset = queryset.filter(endpoint__icontains=endpoint)

        limit = int(request.query_params.get("limit", 100))
        logs_slice = queryset[:limit]

        data = [{
            "id": log.id,
            "actor_username": log.actor_username,
            "actor_email": log.actor_email,
            "actor_role": log.actor_role,
            "method": log.method,
            "endpoint": log.endpoint,
            "query_params": log.query_params,
            "request_body": log.request_body,
            "response_status": log.response_status,
            "ip_address": log.ip_address,
            "user_agent": log.user_agent,
            "created_at": log.created_at
        } for log in logs_slice]

        return Response({
            "status": "success",
            "total_logs": queryset.count(),
            "returned_logs": len(data),
            "logs": data
        }, status=status.HTTP_200_OK)


# ==============================================================================
# Enquiries & Quiz Evaluation
# ==============================================================================

class SubmitQuizView(APIView):
    """
    GET: List all quiz submissions (Enquiries) for Admin Dashboard (Token Required)
    POST: Submit enquiry (Admin side with Token) OR Quiz answers (Parent side with submission_id)
    """
    def get(self, request):
        denied = enforce_admin_token(request)
        if denied:
            return denied

        _, logged_in_admin, role = get_authenticated_admin_user(request)

        sub_id = request.query_params.get("id")
        if sub_id:
            submission = get_object_or_404(QuizSubmission, id=sub_id)
            serializer = QuizSubmissionListSerializer(submission)
            return Response({"status": "success", "data": serializer.data}, status=status.HTTP_200_OK)

        queryset = QuizSubmission.objects.all().order_by("-created_at")

        # Role-based scoping:
        # ADMIN sees everything.
        # Other roles (STAFF, ACADEMICIAN) see only their own created enquiries.
        if role != 'ADMIN' and logged_in_admin:
            queryset = queryset.filter(created_by=logged_in_admin)

        vibhag = request.query_params.get("vibhag")
        if vibhag:
            queryset = queryset.filter(vibhag__iexact=vibhag)

        is_eligible = request.query_params.get("is_eligible")
        if is_eligible is not None:
            queryset = queryset.filter(is_eligible=(is_eligible.lower() == 'true'))

        payment_status = request.query_params.get("payment_status")
        if payment_status:
            queryset = queryset.filter(payment_status__iexact=payment_status)

        serializer = QuizSubmissionListSerializer(queryset, many=True)

        # Card summary counts
        total_count = queryset.count()
        fees_collected = queryset.filter(payment_status="RECEIVED").count()
        qa_passed = queryset.filter(qa_status="PASSED").count()
        qa_failed = queryset.filter(qa_status="FAILED").count()
        qa_pending = queryset.filter(qa_status="PENDING").count()
        submitted_forms = queryset.filter(admission_application__isnull=False).count()
        pending_forms = queryset.filter(payment_status="RECEIVED", admission_application__isnull=True).count()

        return Response({
            "status": "success",
            "scope": "ALL" if role == 'ADMIN' else "MY_ENQUIRIES",
            "user_role": role,
            "total_enquiries": total_count,
            "fees_collected": fees_collected,
            "fee_unpaid": total_count - fees_collected,
            "qa_passed": qa_passed,
            "qa_failed": qa_failed,
            "qa_pending": qa_pending,
            "submitted_forms": submitted_forms,
            "pending_forms": pending_forms,
            "data": serializer.data
        }, status=status.HTTP_200_OK)

    def post(self, request):
        logger.info(f"[POST /api/submit-quiz/] Request Data: {request.data}")
        serializer = SubmitQuizSerializer(data=request.data)
        if not serializer.is_valid():
            logger.error(f"[POST /api/submit-quiz/] Validation Failed: {serializer.errors}")
            return Response({
                "status": "error",
                "errors": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        submission_id = data.get("submission_id")
        standard = data.get("standard", "Nursery") or "Nursery"
        medium = data.get("medium", "Gujarati") or "Gujarati"
        parent_name = (data.get("parent_name") or data.get("father_name") or "").strip()
        child_name = data.get("child_name", "").strip()
        surname = data.get("surname", "").strip()
        vibhag = data.get("vibhag", "Shishu")
        payment_status_input = str(data.get("payment_status", "RECEIVED")).upper()
        if payment_status_input not in ['RECEIVED', 'PENDING']:
            payment_status_input = 'RECEIVED'
        language = data.get("language", "en") or "en"
        whatsapp_number = data.get("whatsapp_number", "")
        email = data.get("email", "")
        answers = data.get("answers", {})

        # Existing enquiry: Parent is submitting the 7 MCQs
        if submission_id:
            submission = QuizSubmission.objects.filter(id=submission_id).first()
            if not submission:
                return Response({
                    "status": "error",
                    "message": f"Enquiry with ID {submission_id} not found."
                }, status=status.HTTP_404_NOT_FOUND)

            existing_app = AdmissionApplication.objects.filter(submission=submission).first()
            if existing_app:
                return Response({
                    "status": "error",
                    "already_submitted": True,
                    "application_number": existing_app.application_number,
                    "message": f"Admission form already submitted (App No: {existing_app.application_number})."
                }, status=status.HTTP_400_BAD_REQUEST)

            if submission.qa_status in ["PASSED", "FAILED"]:
                return Response({
                    "status": "error",
                    "already_completed": True,
                    "submission_id": submission.id,
                    "score": submission.score,
                    "tag": submission.tag,
                    "message": f"Quiz has already been completed for this student with score {submission.score}/7 ({submission.tag}). Re-attempting the quiz is not allowed."
                }, status=status.HTTP_400_BAD_REQUEST)

            score = 0
            breakdown = {}
            for q_id, correct_ans in ALIGNED_ANSWERS.items():
                user_ans = answers.get(str(q_id)) or answers.get(q_id)
                if user_ans and str(user_ans).strip().upper() == correct_ans:
                    score += 1
                    breakdown[q_id] = {"selected": user_ans, "matched": True}
                else:
                    breakdown[q_id] = {"selected": user_ans, "matched": False}

            is_eligible = score >= 4
            qa_status = "PASSED" if is_eligible else "FAILED"
            tag = get_performance_tag(score)

            submission.answers = answers
            submission.score = score
            submission.is_eligible = is_eligible
            submission.qa_status = qa_status
            submission.tag = tag
            submission.quiz_completed_at = timezone.now()
            if language:
                submission.language = language
            submission.save()

            logger.info(f"[POST /api/submit-quiz/] Existing Submission {submission.id} graded: Score {score}/7 ({tag}), QA: {qa_status}")

            return Response({
                "status": "success",
                "submission_id": submission.id,
                "vibhag": submission.vibhag,
                "language": submission.language or "en",
                "qa_status": qa_status,
                "score": score,
                "total": len(ALIGNED_ANSWERS),
                "tag": tag,
                "can_fill_form": True,
                "payment_status": submission.payment_status,
                "message": f"Quiz completed! Score: {score}/7 ({tag}). You can now proceed to fill the admission form.",
                "breakdown": breakdown
            }, status=status.HTTP_200_OK)

        # New enquiry creation (Admin Side) -> Token is mandatory
        denied = enforce_admin_token(request)
        if denied:
            return denied

        _, logged_in_admin, _ = get_authenticated_admin_user(request)

        clean_phone = normalize_phone_number(whatsapp_number)
        clean_phone_10 = clean_phone[-10:] if len(clean_phone) >= 10 else clean_phone

        existing_app = AdmissionApplication.objects.filter(
            submission__whatsapp_number__endswith=clean_phone_10,
            child_first_name__iexact=child_name.strip()
        ).first()

        if existing_app:
            logger.warning(f"[POST /api/submit-quiz/] Form already submitted (App No: {existing_app.application_number}) for child '{child_name}'.")
            return Response({
                "status": "error",
                "already_submitted": True,
                "submission_id": existing_app.submission_id,
                "application_number": existing_app.application_number,
                "message": f"Admission application for '{child_name}' has already been submitted (App No: {existing_app.application_number}). You cannot re-take the quiz."
            }, status=status.HTTP_400_BAD_REQUEST)

        has_answers = bool(answers and len(answers) > 0)
        score = 0
        breakdown = {}

        if has_answers:
            for q_id, correct_ans in ALIGNED_ANSWERS.items():
                user_ans = answers.get(str(q_id)) or answers.get(q_id)
                if user_ans and str(user_ans).strip().upper() == correct_ans:
                    score += 1
                    breakdown[q_id] = {"selected": user_ans, "matched": True}
                else:
                    breakdown[q_id] = {"selected": user_ans, "matched": False}

            is_eligible = score >= 4
            qa_status = "PASSED" if is_eligible else "FAILED"
            tag = get_performance_tag(score)
            quiz_completed_at = timezone.now()
        else:
            score = 0
            is_eligible = False
            qa_status = "PENDING"
            tag = "Pending QA"
            quiz_completed_at = None

        # Decide notification language:
        # 1. If explicit 'language' is passed (gu / en), use it.
        # 2. Otherwise auto-determine from 'medium': Gujarati medium -> 'gu', English medium -> 'en'.
        notif_language = "gu"
        if data.get("language") and data.get("language") in ["gu", "en"]:
            notif_language = data.get("language")
        elif str(medium).lower().startswith("eng"):
            notif_language = "en"
        else:
            notif_language = "gu"

        submission = QuizSubmission.objects.create(
            standard=standard,
            medium=medium,
            parent_name=parent_name,
            child_name=child_name,
            surname=surname,
            vibhag=vibhag,
            language=notif_language,
            whatsapp_number=whatsapp_number,
            email=email,
            answers=answers,
            score=score,
            tag=tag,
            qa_status=qa_status,
            is_eligible=is_eligible,
            quiz_completed_at=quiz_completed_at,
            payment_status=payment_status_input,
            created_by=logged_in_admin
        )

        logger.info(f"[POST /api/submit-quiz/] Created Submission ID: {submission.id}, Standard: {standard}, Medium: {medium}, Language: {notif_language}, Payment: {payment_status_input}")

        base_url = (data.get("frontend_base_url") or getattr(settings, 'FRONTEND_BASE_URL', 'https://g53rw5qd-5173.inc1.devtunnels.ms')).rstrip('/')
        form_direct_url = f"{base_url}/admission-form/?submission_id={submission.id}"

        wa_result = {}
        if payment_status_input == 'RECEIVED':
            # Send both: 1. Admission form link template, 2. School booklet PDF template (in parent's chosen language: gu/en)
            wa_result = send_payment_received_whatsapp_notifications(
                submission.whatsapp_number,
                submission.id,
                language=notif_language
            )
            if wa_result.get("overall_success"):
                submission.whatsapp_link_sent = True
                submission.save(update_fields=['whatsapp_link_sent'])
                logger.info(f"[POST /api/submit-quiz/] WhatsApp notifications sent automatically to {submission.whatsapp_number} (Link: {wa_result.get('link_sent')}, Booklet: {wa_result.get('booklet_sent')})")
            else:
                logger.warning(f"[POST /api/submit-quiz/] Auto WhatsApp send failed: Link={wa_result.get('link_result')}, Booklet={wa_result.get('booklet_result')}")

        if not has_answers:
            message = f"Enquiry created for {child_name} (Std: {standard}, Med: {medium}). Payment: {payment_status_input}."
        elif is_eligible:
            message = f"Congratulations! You scored {score}/7 ({tag}) for Vibhag: {vibhag}. You are eligible to fill the admission form."
        else:
            message = f"You have scored {score}/7 ({tag}). Minimum 4 aligned answers are required to be eligible for admission."

        return Response({
            "status": "success",
            "submission_id": submission.id,
            "id": submission.id,
            "parent_name": submission.parent_name,
            "father_name": submission.parent_name,
            "child_name": submission.child_name,
            "student_name": submission.child_name,
            "surname": submission.surname,
            "whatsapp_number": submission.whatsapp_number,
            "email": submission.email,
            "medium": submission.medium,
            "standard": submission.standard,
            "vibhag": submission.vibhag,
            "payment_status": submission.payment_status,
            "language": submission.language or "en",
            "form_url": form_direct_url if submission.payment_status == 'RECEIVED' else "",
            "whatsapp_link_sent": submission.whatsapp_link_sent,
            "whatsapp_dispatch": {
                "triggered": payment_status_input == 'RECEIVED',
                "link_sent": wa_result.get("link_sent", False),
                "booklet_sent": wa_result.get("booklet_sent", False),
                "template_language": submission.language or language or "gu",
                "link_result": wa_result.get("link_result"),
                "booklet_result": wa_result.get("booklet_result")
            },
            "qa_status": qa_status,
            "score": score,
            "total": len(ALIGNED_ANSWERS),
            "tag": tag,
            "can_fill_form": is_eligible,
            "added_by": (logged_in_admin.full_name or logged_in_admin.username) if logged_in_admin else "Online / Self",
            "created_by": {
                "id": logged_in_admin.id,
                "username": logged_in_admin.username,
                "full_name": logged_in_admin.full_name,
                "email": logged_in_admin.email,
                "role": logged_in_admin.role
            } if logged_in_admin else None,
            "is_repeated_enquiry": QuizSubmission.objects.filter(
                whatsapp_number__endswith=clean_phone_10,
                child_name__iexact=child_name.strip(),
                id__lt=submission.id
            ).exists(),
            "repeated_badge": "Repeated Enquiry" if QuizSubmission.objects.filter(
                whatsapp_number__endswith=clean_phone_10,
                child_name__iexact=child_name.strip()
            ).count() > 1 else None,
            "message": message,
            "breakdown": breakdown,
            "submitted_data": {
                "parent_name": submission.parent_name,
                "child_name": submission.child_name,
                "surname": submission.surname,
                "whatsapp_number": submission.whatsapp_number,
                "email": submission.email,
                "medium": submission.medium,
                "standard": submission.standard,
                "vibhag": submission.vibhag,
                "payment_status": submission.payment_status
            }
        }, status=status.HTTP_200_OK)


class VerifyPaymentAndSendWhatsAppView(APIView):
    """
    Called after payment gateway callback or manual confirmation.
    POST /api/verify-payment/
    """
    def post(self, request):
        logger.info(f"[POST /api/verify-payment/] Request Data: {request.data}")
        submission_id = request.data.get("submission_id")
        payment_status_input = str(request.data.get("payment_status", "PENDING")).upper()
        transaction_id = request.data.get("transaction_id", "")
        frontend_base_url = request.data.get("frontend_base_url", "")

        if not submission_id:
            logger.error("[POST /api/verify-payment/] Missing submission_id")
            return Response({
                "status": "error",
                "message": "submission_id is required."
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            submission = QuizSubmission.objects.get(id=submission_id)
        except QuizSubmission.DoesNotExist:
            logger.error(f"[POST /api/verify-payment/] Submission ID {submission_id} does not exist.")
            return Response({
                "status": "error",
                "message": f"Quiz submission with ID {submission_id} not found."
            }, status=status.HTTP_404_NOT_FOUND)

        submission.payment_transaction_id = transaction_id

        if payment_status_input != "RECEIVED":
            logger.warning(f"[POST /api/verify-payment/] Payment status is {payment_status_input}, not RECEIVED.")
            submission.payment_status = payment_status_input
            submission.save(update_fields=['payment_status', 'payment_transaction_id'])
            return Response({
                "status": "error",
                "submission_id": submission.id,
                "payment_status": submission.payment_status,
                "whatsapp_link_sent": False,
                "message": "Payment not received! Admission form link will not be sent to WhatsApp."
            }, status=status.HTTP_400_BAD_REQUEST)

        submission.payment_status = "RECEIVED"
        submission.save(update_fields=['payment_status', 'payment_transaction_id'])
        logger.info(f"[POST /api/verify-payment/] Successfully updated DB: submission {submission.id} payment_status is now RECEIVED.")

        base_url = frontend_base_url.rstrip("/") if frontend_base_url else request.build_absolute_uri('/')[:-1]
        form_direct_url = f"{base_url}/admission-form/?submission_id={submission.id}"

        logger.info(f"[POST /api/verify-payment/] Triggering WhatsApp notifications (Form Link + Booklet PDF) to {submission.whatsapp_number}...")
        wa_result = send_payment_received_whatsapp_notifications(
            submission.whatsapp_number,
            submission.id,
            language=submission.language or "gu"
        )
        submission.whatsapp_link_sent = wa_result.get("overall_success", False)
        submission.save(update_fields=['whatsapp_link_sent'])

        if not wa_result.get("overall_success"):
            logger.error(f"[POST /api/verify-payment/] WhatsApp Template API Failed: Link={wa_result.get('link_result')}, Booklet={wa_result.get('booklet_result')}")
            return Response({
                "status": "error",
                "submission_id": submission.id,
                "vibhag": submission.vibhag,
                "payment_status": "RECEIVED",
                "whatsapp_link_sent": False,
                "whatsapp_error": wa_result,
                "message": "Payment received, but WhatsApp template message delivery failed."
            }, status=status.HTTP_502_BAD_GATEWAY)

        logger.info(f"[POST /api/verify-payment/] WhatsApp messages delivered successfully to {submission.whatsapp_number}!")
        return Response({
            "status": "success",
            "submission_id": submission.id,
            "vibhag": submission.vibhag,
            "payment_status": "RECEIVED",
            "whatsapp_link_sent": True,
            "whatsapp_number": submission.whatsapp_number,
            "form_url": form_direct_url,
            "link_sent": wa_result.get("link_sent"),
            "booklet_sent": wa_result.get("booklet_sent"),
            "message": f"Payment received! Admission form link and school booklet PDF sent to WhatsApp ({submission.whatsapp_number})."
        }, status=status.HTTP_200_OK)


# ==============================================================================
# Admission Form & Pre-fill 
# ==============================================================================

class AdmissionFormEligibilityCheckView(APIView):
    """
    Check if a submission_id is eligible, paid, and hasn't already submitted before opening form.
    GET /api/admission-form/check-eligibility/?submission_id=1
    """
    def get(self, request):
        submission_id = request.query_params.get("submission_id")
        logger.info(f"[GET /api/admission-form/check-eligibility/] checking submission_id: {submission_id}")

        if not submission_id:
            logger.error("[GET /api/admission-form/check-eligibility/] Missing submission_id param.")
            return Response({
                "status": "error",
                "message": "submission_id query parameter is required."
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            submission = QuizSubmission.objects.get(id=submission_id)
        except QuizSubmission.DoesNotExist:
            logger.error(f"[GET /api/admission-form/check-eligibility/] ID {submission_id} not found.")
            return Response({
                "status": "error",
                "message": f"Quiz submission {submission_id} does not exist."
            }, status=status.HTTP_404_NOT_FOUND)

        if submission.payment_status != "RECEIVED":
            logger.warning(f"[GET /api/admission-form/check-eligibility/] Submission {submission_id} payment is {submission.payment_status}.")
            return Response({
                "status": "error",
                "can_fill_form": False,
                "payment_status": submission.payment_status,
                "message": "Payment is not yet received. Please complete fee payment to unlock the admission form."
            }, status=status.HTTP_402_PAYMENT_REQUIRED)

        existing_application = AdmissionApplication.objects.filter(submission=submission).first()
        if existing_application:
            logger.warning(f"[GET /api/admission-form/check-eligibility/] Form already submitted with Application No: {existing_application.application_number}")
            return Response({
                "status": "already_submitted",
                "can_fill_form": False,
                "already_submitted": True,
                "application_number": existing_application.application_number,
                "submitted_at": existing_application.created_at,
                "message": f"This admission form has already been submitted (Application No: {existing_application.application_number}). You cannot submit it again."
            }, status=status.HTTP_200_OK)

        logger.info(f"[GET /api/admission-form/check-eligibility/] Submission {submission_id} is VALID and ELIGIBLE to open form.")
        return Response({
            "status": "success",
            "can_fill_form": True,
            "already_submitted": False,
            "submission_id": submission.id,
            "language": submission.language or "en",
            "score": submission.score,
            "tag": submission.tag,
            "vibhag": submission.vibhag,
            "message": "Eligible to fill admission form.",
            "prefilled_data": {
                "standard": submission.standard,
                "medium": submission.medium,
                "vibhag": submission.vibhag,
                "parent_name": submission.parent_name,
                "father_name": submission.parent_name,
                "student_name": submission.child_name,
                "child_name": submission.child_name,
                "child_first_name": submission.child_name,
                "surname": submission.surname,
                "child_surname": submission.surname,
                "father_surname": submission.surname,
                "mother_surname": submission.surname,
                "whatsapp_number": submission.whatsapp_number,
                "father_whatsapp": submission.whatsapp_number,
                "mother_whatsapp": submission.whatsapp_number,
                "email": submission.email,
                "father_email": submission.email,
                "mother_email": submission.email,
                "language": submission.language or "gu",
                "is_locked_for_user": True
            }
        }, status=status.HTTP_200_OK)


class AdmissionApplicationView(APIView):
    """
    GET: List all submitted admission forms (Admin - Token Required)
    POST: Submit completed admission form with signatures and documents (Parent - submission_id)
    PATCH: Admin endpoint to edit/update details (Admin - Token Required)
    DELETE: Admin endpoint to delete application/enquiry (Admin - Token Required)
    """
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get(self, request):
        denied = enforce_admin_token(request)
        if denied:
            return denied

        _, logged_in_admin, role = get_authenticated_admin_user(request)

        app_id = request.query_params.get("id")
        submission_id = request.query_params.get("submission_id")
        logger.info(f"[GET /api/admission-form/] params id={app_id}, submission_id={submission_id}")

        if app_id:
            application = AdmissionApplication.objects.filter(id=app_id).first()
            if not application:
                return Response({
                    "status": "error",
                    "message": f"Admission application with ID {app_id} not found."
                }, status=status.HTTP_404_NOT_FOUND)
            serializer = AdmissionApplicationSerializer(application)
            return Response({"status": "success", "data": serializer.data}, status=status.HTTP_200_OK)

        if submission_id:
            application = AdmissionApplication.objects.filter(submission_id=submission_id).first()
            if not application:
                return Response({
                    "status": "error",
                    "message": f"Admission application for submission_id {submission_id} not found. (The form may not have been submitted yet)."
                }, status=status.HTTP_404_NOT_FOUND)
            serializer = AdmissionApplicationSerializer(application)
            return Response({"status": "success", "data": serializer.data}, status=status.HTTP_200_OK)

        applications = AdmissionApplication.objects.all().order_by("-created_at")

        # Role-based scoping for Submitted Applications:
        # ADMIN sees all applications.
        # Other roles (STAFF / ACADEMICIAN) see only applications originating from their enquiries.
        if role != 'ADMIN' and logged_in_admin:
            applications = applications.filter(submission__created_by=logged_in_admin)

        serializer = AdmissionApplicationSerializer(applications, many=True)
        return Response({
            "status": "success",
            "scope": "ALL" if role == 'ADMIN' else "MY_APPLICATIONS",
            "user_role": role,
            "total_applications": applications.count(),
            "data": serializer.data
        }, status=status.HTTP_200_OK)

    def post(self, request):
        logger.info(f"[POST /api/admission-form/] Incoming request data keys: {list(request.data.keys())}")
        logger.info(f"[POST /api/admission-form/] Files uploaded: {list(request.FILES.keys())}")

        submission_id = request.data.get("submission_id")
        if not submission_id:
            logger.error("[POST /api/admission-form/] Missing submission_id")
            return Response({
                "status": "error",
                "message": "submission_id is required to verify quiz & payment eligibility."
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            submission = QuizSubmission.objects.get(id=submission_id)
        except QuizSubmission.DoesNotExist:
            logger.error(f"[POST /api/admission-form/] Submission {submission_id} does not exist.")
            return Response({
                "status": "error",
                "message": f"Quiz submission {submission_id} not found."
            }, status=status.HTTP_404_NOT_FOUND)

        if submission.payment_status != "RECEIVED":
            logger.error(f"[POST /api/admission-form/] Submission {submission_id} payment status is {submission.payment_status}.")
            return Response({
                "status": "error",
                "message": "Cannot submit form! Payment has not been received."
            }, status=status.HTTP_402_PAYMENT_REQUIRED)

        existing_app = AdmissionApplication.objects.filter(submission=submission).first()
        if existing_app:
            logger.warning(f"[POST /api/admission-form/] Form already submitted for submission_id {submission_id} with App No: {existing_app.application_number}")
            return Response({
                "status": "error",
                "can_fill_form": False,
                "already_submitted": True,
                "application_number": existing_app.application_number,
                "message": f"Form already submitted with Application No: {existing_app.application_number}. Multiple submissions are not allowed."
            }, status=status.HTTP_400_BAD_REQUEST)

        serializer = AdmissionApplicationSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            # 1. Save Application
            application = serializer.save(submission=submission, form_submitted_at=timezone.now())
            logger.info(f"[POST /api/admission-form/] Form SUBMITTED SUCCESSFULLY! Application Number: {application.application_number}")

            # 2. Dynamic Interaction Slot Auto-Allocation (10 kids/slot, 4 slots/day, Mon-Sat)
            from .slot_service import allocate_next_available_interaction_slot
            from .whatsapp import send_whatsapp_interaction_scheduled_message

            slot_info = allocate_next_available_interaction_slot()
            application.interaction_date = slot_info["date"]
            application.interaction_slot_no = slot_info["slot_no"]
            application.interaction_time = slot_info["time"]
            application.interaction_venue = slot_info["venue"]

            # 3. Send WhatsApp Notification to Parent
            recipient_phone = submission.whatsapp_number or application.father_whatsapp or application.mother_whatsapp
            wa_sent = False
            wa_response = {}
            if recipient_phone:
                wa_response = send_whatsapp_interaction_scheduled_message(
                    recipient_number=recipient_phone,
                    date_str=slot_info["date_str"],
                    slot_no=slot_info["slot_no"],
                    time_str=slot_info["time"],
                    template_name="shreyas_interaction_scheduled"
                )
                wa_sent = wa_response.get("success", False)
                application.interaction_whatsapp_sent = wa_sent

            application.save(update_fields=[
                'interaction_date',
                'interaction_slot_no',
                'interaction_time',
                'interaction_venue',
                'interaction_whatsapp_sent'
            ])

            logger.info(
                f"[POST /api/admission-form/] Interaction scheduled: Date={slot_info['date_str']}, "
                f"Slot={slot_info['slot_no']} ({slot_info['time']}), WhatsApp sent={wa_sent}"
            )

            return Response({
                "status": "success",
                "message": "Admission form submitted and stored successfully!",
                "application_id": application.id,
                "application_number": application.application_number,
                "vibhag": application.vibhag,
                "interaction_schedule": {
                    "date": slot_info["date_str"],
                    "slot_no": slot_info["slot_no"],
                    "time": slot_info["time"],
                    "venue": slot_info["venue"],
                    "whatsapp_sent": wa_sent,
                    "whatsapp_response": wa_response
                },
                "data": serializer.data
            }, status=status.HTTP_201_CREATED)

        logger.error(f"[POST /api/admission-form/] VALIDATION FAILED! Errors: {serializer.errors}")
        return Response({
            "status": "error",
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request):
        denied = enforce_admin_token(request)
        if denied:
            return denied

        app_id = request.data.get("id") or request.query_params.get("id")
        submission_id = request.data.get("submission_id") or request.query_params.get("submission_id")

        if not app_id and not submission_id:
            return Response({
                "status": "error",
                "message": "Either 'id' or 'submission_id' is required to update an application or enquiry."
            }, status=status.HTTP_400_BAD_REQUEST)

        application = None
        submission = None

        if app_id:
            application = AdmissionApplication.objects.filter(id=app_id).first()
            if not application:
                return Response({
                    "status": "error",
                    "message": f"AdmissionApplication with ID {app_id} not found."
                }, status=status.HTTP_404_NOT_FOUND)
            submission = application.submission
        elif submission_id:
            submission = QuizSubmission.objects.filter(id=submission_id).first()
            application = AdmissionApplication.objects.filter(submission_id=submission_id).first()
            if not submission and not application:
                return Response({
                    "status": "error",
                    "message": f"No Enquiry or Application found for submission_id {submission_id}."
                }, status=status.HTTP_404_NOT_FOUND)

        # 1. Update QuizSubmission fields
        phone_updated = False
        new_phone = (
            request.data.get('father_whatsapp') or
            request.data.get('mother_whatsapp') or
            request.data.get('whatsapp_number') or
            request.data.get('phone')
        )

        if submission:
            if new_phone and str(new_phone).strip() != submission.whatsapp_number:
                submission.whatsapp_number = str(new_phone).strip()
                phone_updated = True

            if 'child_first_name' in request.data:
                submission.child_name = str(request.data['child_first_name']).strip()
            elif 'child_name' in request.data:
                submission.child_name = str(request.data['child_name']).strip()

            if 'child_surname' in request.data:
                submission.surname = str(request.data['child_surname']).strip()
            elif 'surname' in request.data:
                submission.surname = str(request.data['surname']).strip()

            if 'father_first_name' in request.data:
                submission.parent_name = str(request.data['father_first_name']).strip()
            elif 'parent_name' in request.data:
                submission.parent_name = str(request.data['parent_name']).strip()

            if 'vibhag' in request.data:
                v = str(request.data['vibhag']).strip()
                # Map class number/name to vibhag if needed
                vibhag_map = {'1': 'Arun', '2': 'Arun', '3': 'Kesari', '4': 'Kesari', '5': 'Kesari', '6': 'Kesari', '7': 'Kesari', '8': 'Kishore', '9': 'Kishore', '10': 'Kishore', 'nursery': 'Shishu', 'jr.kg': 'Shishu', 'sr.kg': 'Arun'}
                submission.vibhag = vibhag_map.get(v.lower(), v.capitalize() if v.capitalize() in ['Shishu', 'Arun', 'Kesari', 'Kishore'] else submission.vibhag)

            if 'standard' in request.data:
                submission.standard = str(request.data['standard']).strip()

            if 'medium' in request.data:
                submission.medium = str(request.data['medium']).strip()

            if 'father_email' in request.data:
                submission.email = str(request.data['father_email']).strip()
            elif 'email' in request.data:
                submission.email = str(request.data['email']).strip()

            if 'payment_status' in request.data:
                submission.payment_status = str(request.data['payment_status']).strip().upper()

            submission.save()
            logger.info(f"[PATCH /api/admission-form/] Updated QuizSubmission {submission.id} (Phone: {submission.whatsapp_number})")

            # If phone changed and payment is RECEIVED, automatically trigger WhatsApp template link & booklet!
            if phone_updated and submission.payment_status == 'RECEIVED':
                logger.info(f"[PATCH /api/admission-form/] Phone updated to {submission.whatsapp_number}. Re-triggering WhatsApp notifications...")
                wa_res = send_payment_received_whatsapp_notifications(
                    submission.whatsapp_number,
                    submission.id,
                    language=submission.language or "gu"
                )
                if wa_res.get("overall_success"):
                    submission.whatsapp_link_sent = True
                    submission.save(update_fields=['whatsapp_link_sent'])

        # 2. If AdmissionApplication exists, update it too
        if application:
            serializer = AdmissionApplicationSerializer(
                application,
                data=request.data,
                partial=True,
                context={'request': request, 'is_admin_update': True}
            )
            if serializer.is_valid():
                updated_app = serializer.save()
                if phone_updated:
                    updated_app.father_whatsapp = submission.whatsapp_number
                    updated_app.save(update_fields=['father_whatsapp'])
                return Response({
                    "status": "success",
                    "message": "Application and enquiry updated successfully by Admin.",
                    "data": serializer.data
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    "status": "error",
                    "errors": serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)

        # 3. If application has not been submitted yet (pure enquiry edit)
        return Response({
            "status": "success",
            "message": f"Enquiry {submission.id} updated successfully by Admin.",
            "data": {
                "id": submission.id,
                "submission_id": submission.id,
                "child_name": submission.child_name,
                "surname": submission.surname,
                "parent_name": submission.parent_name,
                "whatsapp_number": submission.whatsapp_number,
                "standard": submission.standard,
                "medium": submission.medium,
                "vibhag": submission.vibhag,
                "payment_status": submission.payment_status,
                "whatsapp_link_sent": submission.whatsapp_link_sent
            }
        }, status=status.HTTP_200_OK)

    def delete(self, request):
        denied = enforce_admin_token(request)
        if denied:
            return denied

        app_id = request.query_params.get("id")
        submission_id = request.query_params.get("submission_id")

        if not app_id and not submission_id:
            return Response({
                "status": "error",
                "message": "Either 'id' or 'submission_id' query parameter is required to delete."
            }, status=status.HTTP_400_BAD_REQUEST)

        if app_id:
            application = AdmissionApplication.objects.filter(id=app_id).first()
            if application:
                app_number = application.application_number
                application_id = application.id
                sub_id = application.submission_id
                application.delete()
                QuizSubmission.objects.filter(id=sub_id).delete()
                logger.info(f"[DELETE /api/admission-form/] Application {app_number} and Submission {sub_id} deleted by Admin.")
                return Response({
                    "status": "success",
                    "message": f"Application {app_number} and associated enquiry deleted successfully.",
                    "deleted_id": application_id,
                    "application_number": app_number
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    "status": "error",
                    "message": f"Admission application with ID {app_id} not found."
                }, status=status.HTTP_404_NOT_FOUND)

        if submission_id:
            application = AdmissionApplication.objects.filter(submission_id=submission_id).first()
            submission = QuizSubmission.objects.filter(id=submission_id).first()

            if not application and not submission:
                return Response({
                    "status": "error",
                    "message": f"No application or enquiry found for submission_id {submission_id}."
                }, status=status.HTTP_404_NOT_FOUND)

            app_number = application.application_number if application else None
            child_name = submission.child_name if submission else (application.child_first_name if application else "")

            if application:
                application.delete()
            if submission:
                submission.delete()

            logger.info(f"[DELETE /api/admission-form/] Successfully deleted submission_id {submission_id} (Child: {child_name}, App: {app_number}).")
            return Response({
                "status": "success",
                "message": f"Successfully deleted enquiry/application for submission_id {submission_id} ({child_name}).",
                "submission_id": int(submission_id),
                "application_number": app_number
            }, status=status.HTTP_200_OK)
