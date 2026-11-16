"""
Helper utility for generating elegant, professional responsive HTML emails
for Shreyas Foundation Admin OTP Verification (Login 2FA & PIN Reset).
"""
from datetime import datetime

def generate_otp_email_html(recipient_name: str, otp_code: str, purpose: str = "login") -> str:
    """
    Renders a clean, high-conversion, professional HTML email template
    with Shreyas Foundation branding, styled 6-digit OTP badge, and security instructions.
    """
    current_year = datetime.now().year
    if purpose == "reset":
        title = "Admin PIN Reset Verification"
        badge_title = "YOUR PIN RESET CODE"
        intro_text = (
            "We received a request to reset your Shreyas Foundation Portal PIN. "
            "Please use the 6-digit verification code below to proceed."
        )
        warning_text = (
            "If you did not request a PIN reset, please ignore this email. "
            "Your existing PIN remains completely secure."
        )
    else:
        title = "Two-Step Verification Login Code"
        badge_title = "YOUR 2-STEP VERIFICATION CODE"
        intro_text = (
            "A login attempt was made to your Shreyas Foundation Portal. "
            "To complete your sign-in, please enter the one-time verification code below."
        )
        warning_text = (
            "If you did not attempt to log in to the admin portal, please contact the "
            "technical team immediately to secure your account."
        )

    # Separate individual digits for modern visual look
    digit_boxes = "".join([
        f'<span style="display:inline-block; width:38px; height:46px; line-height:46px; margin:0 4px; '
        f'background-color:#f1f5f9; border:1px solid #cbd5e1; border-radius:8px; font-size:24px; '
        f'font-weight:700; color:#0f172a; text-align:center; font-family:\'Courier New\', Courier, monospace;">{d}</span>'
        for d in str(otp_code)
    ])

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
</head>
<body style="margin:0; padding:0; background-color:#f8fafc; font-family:-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; -webkit-font-smoothing:antialiased;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background-color:#f8fafc; padding:30px 15px;">
    <tr>
      <td align="center">
        <!-- Main Card -->
        <table role="presentation" width="100%" max-width="540px" cellspacing="0" cellpadding="0" border="0" style="max-width:540px; background-color:#ffffff; border-radius:14px; box-shadow:0 4px 18px rgba(0,0,0,0.06); border:1px solid #e2e8f0; overflow:hidden;">
          
          <!-- Top Accent Bar -->
          <tr>
            <td style="height:6px; background:linear-gradient(90deg, #1e3a8a 0%, #2563eb 50%, #3b82f6 100%);"></td>
          </tr>

          <!-- Header -->
          <tr>
            <td style="padding:32px 36px 16px 36px; text-align:center;">
              <h1 style="margin:0 0 6px 0; font-size:22px; font-weight:800; color:#0f172a; letter-spacing:-0.5px;">
                SHREYAS FOUNDATION
              </h1>
            </td>
          </tr>

          <!-- Content Body -->
          <tr>
            <td style="padding:16px 36px 28px 36px;">
              <p style="margin:0 0 14px 0; font-size:15px; color:#334155; line-height:24px;">
                Namaste <strong>{recipient_name}</strong>,
              </p>
              <p style="margin:0 0 24px 0; font-size:14px; color:#475569; line-height:22px;">
                {intro_text}
              </p>

              <!-- OTP Container Box -->
              <div style="background-color:#f8fafc; border:1px dashed #cbd5e1; border-radius:12px; padding:24px 16px; text-align:center; margin:0 0 24px 0;">
                <p style="margin:0 0 12px 0; font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:1.2px; color:#64748b;">
                  {badge_title}
                </p>
                <div style="margin:0 auto; display:inline-block;">
                  {digit_boxes}
                </div>
              </div>

              <!-- Security Notice -->
              <div style="background-color:#fffbeb; border-left:4px solid #f59e0b; padding:12px 14px; border-radius:4px; margin:0 0 20px 0;">
                <p style="margin:0; font-size:12px; color:#92400e; line-height:18px;">
                  <strong>Security Note:</strong> {warning_text} Never share this code with anyone.
                </p>
              </div>

              <p style="margin:0; font-size:13px; color:#64748b; line-height:20px;">
                Warm regards,<br>
                <strong style="color:#0f172a;">Shreyas Foundation Technical Team</strong>
              </p>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="background-color:#f8fafc; border-top:1px solid #e2e8f0; padding:18px 36px; text-align:center;">
              <p style="margin:0; font-size:11px; color:#94a3b8; line-height:16px;">
                © {current_year} Shreyas Foundation, Ahmedabad. All rights reserved.<br>
                This is an automated security transmission. Please do not reply directly to this email.
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""
    return html_content

