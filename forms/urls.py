from django.urls import path
from .views import (
    SubmitQuizView,
    VerifyPaymentAndSendWhatsAppView,
    AdmissionFormEligibilityCheckView,
    AdmissionApplicationView,
    AdminUserManagementView,
    AdminLoginView,
    AdminVerifyLoginOTPView,
    ForgotPinRequestOTPView,
    ForgotPinVerifyAndResetView,
    AdminInteractionCalendarView,
    AdminExportDataView,
    AdminAuditLogView
)

urlpatterns = [
    # Admin User Management (Admin adds/edits/deletes staff/users role-wise)
    path('admin/users/', AdminUserManagementView.as_view(), name='admin-users'),
    path('admin/users/<int:user_id>/', AdminUserManagementView.as_view(), name='admin-user-detail'),

    # Admin Login (2-Step Verification)
    path('admin/login/', AdminLoginView.as_view(), name='admin-login'),
    path('admin/verify-login-otp/', AdminVerifyLoginOTPView.as_view(), name='admin-verify-login-otp'),
    path('admin/forgot-pin/request-otp/', ForgotPinRequestOTPView.as_view(), name='admin-forgot-pin-otp'),
    path('admin/forgot-pin/reset/', ForgotPinVerifyAndResetView.as_view(), name='admin-forgot-pin-reset'),

    # Step 8: Interaction Calendar for Admin
    path('admin/interaction-calendar/', AdminInteractionCalendarView.as_view(), name='admin-interaction-calendar'),

    # Export Data API (Excel & CSV for Enquiries, Submitted Apps, Pending Forms)
    path('admin/export/', AdminExportDataView.as_view(), name='admin-export'),

    # Admin Audit Logs (Only accessible by Admin)
    path('admin/audit-logs/', AdminAuditLogView.as_view(), name='admin-audit-logs'),

    # Enquiries & Quiz
    path('submit-quiz/', SubmitQuizView.as_view(), name='submit-quiz'),
    path('enquiries/', SubmitQuizView.as_view(), name='enquiries'),
    path('add-enquiry/', SubmitQuizView.as_view(), name='add-enquiry'),
    path('verify-payment/', VerifyPaymentAndSendWhatsAppView.as_view(), name='verify-payment'),

    # Admission Form
    path('admission-form/check-eligibility/', AdmissionFormEligibilityCheckView.as_view(), name='check-form-eligibility'),
    path('admission-form/', AdmissionApplicationView.as_view(), name='admission-form'),
]
