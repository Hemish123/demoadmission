from django.urls import path
from .views import (
    SubmitQuizView,
    VerifyPaymentAndSendWhatsAppView,
    AdmissionFormEligibilityCheckView,
    AdmissionApplicationView,
    AdminUserManagementView,
    AdminLoginView,
    ForgotPinRequestOTPView,
    ForgotPinVerifyAndResetView,
    AdminAuditLogView
)

urlpatterns = [
    # Admin User Management (Admin adds staff/users role-wise)
    path('admin/users/', AdminUserManagementView.as_view(), name='admin-users'),

    # Admin Login (Staff/Admin logs in with email + PIN)
    path('admin/login/', AdminLoginView.as_view(), name='admin-login'),
    path('admin/forgot-pin/request-otp/', ForgotPinRequestOTPView.as_view(), name='admin-forgot-pin-otp'),
    path('admin/forgot-pin/reset/', ForgotPinVerifyAndResetView.as_view(), name='admin-forgot-pin-reset'),

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
