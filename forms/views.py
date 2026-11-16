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
    Flow A: Step 1 - Secure Login with Email / Username + PIN
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

        token = generate_jwt_token(admin_user)

        return Response({
            "status": "success",
            "message": "Login successful.",
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
    User Management: Only Admin can create and list staff/academician users.
    POST /api/admin/users/ - Create new user (Role: ADMIN / STAFF / ACADEMICIAN)
    GET  /api/admin/users/ - List all users
    """
    def get(self, request):
        denied = enforce_admin_token(request, required_role='ADMIN')
        if denied:
            return denied

        users = AdminUser.objects.all().order_by('-created_at')
        data = [{
            "id": u.id,
            "username": u.username,
            "full_name": u.full_name,
            "email": u.email,
            "role": u.role,
            "is_active": u.is_active,
            "created_at": u.created_at
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
            f"Your OTP for resetting the Admin PIN is: {otp}\n"
            f"This OTP is valid for 10 minutes.\n\n"
            f"If you did not request this, please ignore this email.\n\n"
            f"Shreyas Foundation Technical Team"
        )
        try:
            sender = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@shreyasfoundation.in')
            send_mail(subject, body, sender, [admin_user.email], fail_silently=True)
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

        sub_id = request.query_params.get("id")
        if sub_id:
            submission = get_object_or_404(QuizSubmission, id=sub_id)
            serializer = QuizSubmissionListSerializer(submission)
            return Response({"status": "success", "data": serializer.data}, status=status.HTTP_200_OK)

        queryset = QuizSubmission.objects.all().order_by("-created_at")

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
        return Response({
            "status": "success",
            "total_enquiries": queryset.count(),
            "qa_passed": queryset.filter(qa_status="PASSED").count(),
            "qa_failed": queryset.filter(qa_status="FAILED").count(),
            "qa_pending": queryset.filter(qa_status="PENDING").count(),
            "fees_collected": queryset.filter(payment_status="RECEIVED").count(),
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
            payment_status=payment_status_input
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
        serializer = AdmissionApplicationSerializer(applications, many=True)
        return Response({
            "status": "success",
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
            application = serializer.save(submission=submission, form_submitted_at=timezone.now())
            logger.info(f"[POST /api/admission-form/] Form SUBMITTED SUCCESSFULLY! Application Number: {application.application_number}")
            return Response({
                "status": "success",
                "message": "Admission form submitted and stored successfully!",
                "application_id": application.id,
                "application_number": application.application_number,
                "vibhag": application.vibhag,
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
