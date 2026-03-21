import os
import resend

def send_reset_email(to_email: str, student_name: str, reset_token: str):
    """
    Sends a password reset email using Resend API.
    Works on Render free tier — no SMTP port blocking.
    """
    resend.api_key = os.getenv("RESEND_API_KEY")
    frontend_url = os.getenv("FRONTEND_URL", "https://gradeiq-upsa.vercel.app")
    reset_link = f"{frontend_url}/reset-password?token={reset_token}"

    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="UTF-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="margin:0; padding:0; background:#F0F4FF; font-family: Arial, sans-serif;">
      <div style="max-width:520px; margin:40px auto; background:#ffffff;
                  border-radius:16px; overflow:hidden;
                  box-shadow:0 4px 24px rgba(8,28,70,0.1);">

        <!-- Header -->
        <div style="background:#081C46; padding:32px 40px; text-align:center;">
          <h1 style="color:#FFC005; font-size:22px; margin:0; font-weight:900;
                     letter-spacing:-0.02em;">
            GradeIQ UPSA
          </h1>
          <p style="color:rgba(255,255,255,0.5); font-size:13px; margin:6px 0 0;">
            University of Professional Studies, Accra
          </p>
        </div>

        <!-- Body -->
        <div style="padding:40px;">
          <h2 style="color:#081C46; font-size:20px; margin:0 0 12px; font-weight:800;">
            Password Reset Request
          </h2>
          <p style="color:#4B5563; font-size:14px; line-height:1.7; margin:0 0 20px;">
            Hi <strong>{student_name}</strong>,
          </p>
          <p style="color:#4B5563; font-size:14px; line-height:1.7; margin:0 0 28px;">
            We received a request to reset your GradeIQ UPSA password.
            Click the button below to set a new password.
            This link expires in <strong>1 hour</strong>.
          </p>

          <!-- Button -->
          <div style="text-align:center; margin:0 0 28px;">
            <a href="{reset_link}"
               style="display:inline-block; background:#081C46; color:#FFC005;
                      text-decoration:none; padding:14px 36px; border-radius:10px;
                      font-size:15px; font-weight:800; letter-spacing:0.02em;">
              Reset My Password →
            </a>
          </div>

          <p style="color:#9CA3AF; font-size:12px; line-height:1.6; margin:0 0 8px;">
            If the button doesn't work, copy and paste this link:
          </p>
          <p style="color:#6B7280; font-size:11px; word-break:break-all;
                    background:#F0F4FF; padding:10px 14px; border-radius:8px;
                    margin:0 0 28px;">
            {reset_link}
          </p>

          <div style="border-top:1px solid #E5E7EB; padding-top:20px;">
            <p style="color:#9CA3AF; font-size:12px; line-height:1.6; margin:0;">
              If you didn't request a password reset, you can safely ignore this email.
            </p>
          </div>
        </div>

        <!-- Footer -->
        <div style="background:#F0F4FF; padding:20px 40px; text-align:center;">
          <p style="color:#9CA3AF; font-size:11px; margin:0;">
            © 2026 GradeIQ UPSA · Developed by Ahenkora Joshua Owusu
          </p>
          <p style="color:#9CA3AF; font-size:11px; margin:4px 0 0;">
            Scholarship with Professionalism
          </p>
        </div>

      </div>
    </body>
    </html>
    """

    params = {
        "from": "GradeIQ UPSA <onboarding@resend.dev>",
        "to": [to_email],
        "subject": "Reset Your GradeIQ UPSA Password",
        "html": html_body,
    }

    resend.Emails.send(params)