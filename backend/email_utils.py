import os
import resend
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

resend.api_key = os.getenv("RESEND_API_KEY")
SMTP_FROM = os.getenv("SMTP_FROM", "StartupSphere <onboarding@resend.dev>")


def send_email(to_email: str, subject: str, html_body: str) -> bool:
    """
    Sends an email via Resend API. Returns True on success, False on failure.
    Failures are caught and logged — they should NEVER block login/signup.
    """
    try:
        resend.Emails.send({
            "from": SMTP_FROM,
            "to": [to_email],
            "subject": subject,
            "html": html_body,
        })
        return True

    except Exception as e:
        print(f"[EMAIL ERROR] Could not send email to {to_email}: {repr(e)}")
        return False


def send_login_alert(to_email: str, name: str):
    """Sends a 'new login detected' security notification email."""
    time_str = datetime.now().strftime("%d %b %Y, %I:%M %p")

    html_body = f"""
    <div style="font-family: 'Segoe UI', Arial, sans-serif; background:#06061a; padding:40px 20px;">
      <div style="max-width:480px;margin:0 auto;background:#0c0c28;border-radius:16px;padding:32px;border:1px solid rgba(108,99,255,0.2);">
        <div style="text-align:center;margin-bottom:24px;">
          <div style="font-size:32px;margin-bottom:8px;">🚀</div>
          <h2 style="color:#f0f0ff;margin:0;font-size:20px;">StartupSphere</h2>
        </div>
        <h3 style="color:#f0f0ff;font-size:17px;margin-bottom:8px;">New Login Detected</h3>
        <p style="color:#b4b4f0;font-size:14px;line-height:1.6;">
          Hi {name},<br><br>
          We noticed a new login to your StartupSphere account.
        </p>
        <div style="background:rgba(108,99,255,0.08);border-radius:10px;padding:16px;margin:20px 0;">
          <p style="color:#d2d2ff;font-size:13px;margin:0 0 8px;"><strong>Time:</strong> {time_str}</p>
          <p style="color:#d2d2ff;font-size:13px;margin:0;"><strong>Account:</strong> {to_email}</p>
        </div>
        <p style="color:#8a87b8;font-size:12px;line-height:1.6;">
          If this was you, no action is needed. If you don't recognize this activity,
          please reset your password immediately.
        </p>
        <div style="border-top:1px solid rgba(108,99,255,0.15);margin-top:24px;padding-top:16px;text-align:center;">
          <p style="color:#8a87b8;font-size:11px;margin:0;">© 2026 StartupSphere. Built for innovators 🚀</p>
        </div>
      </div>
    </div>
    """

    return send_email(to_email, "🔐 New Login to Your StartupSphere Account", html_body)


def send_welcome_email(to_email: str, name: str):
    """Sends a welcome email after signup."""
    html_body = f"""
    <div style="font-family: 'Segoe UI', Arial, sans-serif; background:#06061a; padding:40px 20px;">
      <div style="max-width:480px;margin:0 auto;background:#0c0c28;border-radius:16px;padding:32px;border:1px solid rgba(108,99,255,0.2);">
        <div style="text-align:center;margin-bottom:24px;">
          <div style="font-size:32px;margin-bottom:8px;">🚀</div>
          <h2 style="color:#f0f0ff;margin:0;font-size:20px;">Welcome to StartupSphere!</h2>
        </div>
        <p style="color:#b4b4f0;font-size:14px;line-height:1.6;">
          Hi {name},<br><br>
          Thanks for joining StartupSphere — the home for innovators, founders, and builders.
          You're now part of a community of 15,000+ people sharing and discovering startup ideas.
        </p>
        <p style="color:#b4b4f0;font-size:14px;line-height:1.6;">
          Get started by submitting your first idea or browsing what others are building.
        </p>
        <div style="border-top:1px solid rgba(108,99,255,0.15);margin-top:24px;padding-top:16px;text-align:center;">
          <p style="color:#8a87b8;font-size:11px;margin:0;">© 2026 StartupSphere. Built for innovators 🚀</p>
        </div>
      </div>
    </div>
    """

    return send_email(to_email, "🚀 Welcome to StartupSphere!", html_body)


def send_verification_email(to_email: str, name: str, verify_link: str):
    """Sends an email verification link after signup."""
    html_body = f"""
    <div style="font-family: 'Segoe UI', Arial, sans-serif; background:#06061a; padding:40px 20px;">
      <div style="max-width:480px;margin:0 auto;background:#0c0c28;border-radius:16px;padding:32px;border:1px solid rgba(108,99,255,0.2);">
        <div style="text-align:center;margin-bottom:24px;">
          <div style="font-size:32px;margin-bottom:8px;">📧</div>
          <h2 style="color:#f0f0ff;margin:0;font-size:20px;">Verify Your Email</h2>
        </div>
        <p style="color:#b4b4f0;font-size:14px;line-height:1.6;">
          Hi {name},<br><br>
          Thanks for signing up for StartupSphere! Please confirm your email address
          to activate your account.
        </p>
        <div style="text-align:center;margin:28px 0;">
          <a href="{verify_link}" style="display:inline-block;background:linear-gradient(135deg,#6c63ff,#9b59f5);color:#fff;text-decoration:none;font-weight:700;font-size:14px;padding:14px 32px;border-radius:10px;">
            ✅ Verify My Email
          </a>
        </div>
        <p style="color:#8a87b8;font-size:12px;line-height:1.6;">
          This link will expire in 24 hours. If you didn't create a StartupSphere account,
          you can safely ignore this email.
        </p>
        <div style="border-top:1px solid rgba(108,99,255,0.15);margin-top:24px;padding-top:16px;text-align:center;">
          <p style="color:#8a87b8;font-size:11px;margin:0;">© 2026 StartupSphere. Built for innovators 🚀</p>
        </div>
      </div>
    </div>
    """

    return send_email(to_email, "📧 Verify Your StartupSphere Account", html_body)


def send_password_reset_email(to_email: str, name: str, reset_link: str):
    """Sends a password reset link."""
    html_body = f"""
    <div style="font-family: 'Segoe UI', Arial, sans-serif; background:#06061a; padding:40px 20px;">
      <div style="max-width:480px;margin:0 auto;background:#0c0c28;border-radius:16px;padding:32px;border:1px solid rgba(108,99,255,0.2);">
        <div style="text-align:center;margin-bottom:24px;">
          <div style="font-size:32px;margin-bottom:8px;">🔑</div>
          <h2 style="color:#f0f0ff;margin:0;font-size:20px;">Reset Your Password</h2>
        </div>
        <p style="color:#b4b4f0;font-size:14px;line-height:1.6;">
          Hi {name},<br><br>
          We received a request to reset your StartupSphere password. Click the button below
          to choose a new password.
        </p>
        <div style="text-align:center;margin:28px 0;">
          <a href="{reset_link}" style="display:inline-block;background:linear-gradient(135deg,#6c63ff,#9b59f5);color:#fff;text-decoration:none;font-weight:700;font-size:14px;padding:14px 32px;border-radius:10px;">
            🔑 Reset Password
          </a>
        </div>
        <p style="color:#8a87b8;font-size:12px;line-height:1.6;">
          This link will expire in 1 hour. If you didn't request a password reset,
          you can safely ignore this email — your password will remain unchanged.
        </p>
        <div style="border-top:1px solid rgba(108,99,255,0.15);margin-top:24px;padding-top:16px;text-align:center;">
          <p style="color:#8a87b8;font-size:11px;margin:0;">© 2026 StartupSphere. Built for innovators 🚀</p>
        </div>
      </div>
    </div>
    """

    return send_email(to_email, "🔑 Reset Your StartupSphere Password", html_body)