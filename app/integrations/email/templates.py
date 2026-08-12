"""
HTML email templates for BotForge AI transactional emails.

All templates are self-contained inline-CSS HTML strings — no external assets.
"""

from __future__ import annotations

_BASE = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>{title}</title>
</head>
<body style="margin:0;padding:0;background:#f4f6f9;font-family:'Segoe UI',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f6f9;padding:40px 0;">
    <tr>
      <td align="center">
        <table width="560" cellpadding="0" cellspacing="0"
               style="background:#ffffff;border-radius:12px;overflow:hidden;
                      box-shadow:0 2px 12px rgba(0,0,0,.08);">
          <!-- Header -->
          <tr>
            <td style="background:linear-gradient(135deg,#6366f1 0%,#8b5cf6 100%);
                        padding:32px 40px;text-align:center;">
              <h1 style="margin:0;color:#ffffff;font-size:24px;font-weight:700;
                          letter-spacing:-0.5px;">
                🤖 BotForge AI
              </h1>
            </td>
          </tr>
          <!-- Body -->
          <tr>
            <td style="padding:40px 40px 32px;">
              {body}
            </td>
          </tr>
          <!-- Footer -->
          <tr>
            <td style="padding:24px 40px;border-top:1px solid #e5e7eb;
                        text-align:center;color:#9ca3af;font-size:12px;">
              BotForge AI · AI Sales Platform<br/>
              <span style="color:#d1d5db;">
                If you did not request this email, you can safely ignore it.
              </span>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""

_BTN = """
<table width="100%" cellpadding="0" cellspacing="0" style="margin:28px 0;">
  <tr>
    <td align="center">
      <a href="{url}"
         style="display:inline-block;background:linear-gradient(135deg,#6366f1,#8b5cf6);
                color:#ffffff;text-decoration:none;font-size:15px;font-weight:600;
                padding:14px 36px;border-radius:8px;letter-spacing:0.3px;">
        {label}
      </a>
    </td>
  </tr>
</table>
"""

_FALLBACK_LINK = """
<p style="font-size:12px;color:#9ca3af;word-break:break-all;text-align:center;">
  Or copy this link into your browser:<br/>
  <a href="{url}" style="color:#6366f1;">{url}</a>
</p>
"""


def email_verification_html(*, full_name: str | None, verify_url: str) -> str:
    name = full_name or "there"
    body = f"""
      <h2 style="margin:0 0 8px;color:#111827;font-size:20px;font-weight:700;">
        Verify your email address
      </h2>
      <p style="margin:0 0 20px;color:#374151;font-size:15px;line-height:1.6;">
        Hi {name}, welcome to <strong>BotForge AI</strong>! 🎉<br/>
        Click the button below to confirm your email address and activate your account.
      </p>
      {_BTN.format(url=verify_url, label="Verify Email Address")}
      <p style="margin:16px 0 0;color:#6b7280;font-size:13px;text-align:center;">
        This link expires in <strong>24 hours</strong>.
      </p>
      {_FALLBACK_LINK.format(url=verify_url)}
    """
    return _BASE.format(title="Verify your email — BotForge AI", body=body)


def password_reset_html(*, full_name: str | None, reset_url: str) -> str:
    name = full_name or "there"
    body = f"""
      <h2 style="margin:0 0 8px;color:#111827;font-size:20px;font-weight:700;">
        Reset your password
      </h2>
      <p style="margin:0 0 20px;color:#374151;font-size:15px;line-height:1.6;">
        Hi {name}, we received a request to reset your BotForge AI password.<br/>
        Click the button below to choose a new password.
      </p>
      {_BTN.format(url=reset_url, label="Reset Password")}
      <p style="margin:16px 0 0;color:#6b7280;font-size:13px;text-align:center;">
        This link expires in <strong>1 hour</strong>. If you did not request a
        password reset, no action is required.
      </p>
      {_FALLBACK_LINK.format(url=reset_url)}
    """
    return _BASE.format(title="Reset your password — BotForge AI", body=body)


def lead_alert_html(
    *,
    owner_name: str | None,
    lead_name: str | None,
    lead_phone: str | None,
    lead_status: str,
    lead_temperature: str | None,
    bot_name: str,
    summary: str | None,
    dashboard_url: str,
) -> str:
    name = owner_name or "there"
    lead_display = lead_name or "Anonymous"
    temp_map = {"hot": "🔥 Hot", "warm": "🌤 Warm", "cold": "🧊 Cold"}
    temp_label = temp_map.get(lead_temperature or "", "Unknown temperature") if lead_temperature else ""
    temp_row = (
        f'<tr><td style="color:#6b7280;padding:4px 0;width:120px;">Temperature</td>'
        f'<td style="font-weight:600;padding:4px 0;">{temp_label}</td></tr>'
        if temp_label
        else ""
    )
    summary_row = (
        f'<p style="margin:16px 0 0;padding:12px 16px;background:#f9fafb;border-radius:8px;'
        f'font-size:14px;color:#374151;line-height:1.6;border:1px solid #e5e7eb;">'
        f'<strong>Summary:</strong> {summary}</p>'
        if summary
        else ""
    )
    phone_row = (
        f'<tr><td style="color:#6b7280;padding:4px 0;width:120px;">Phone</td>'
        f'<td style="font-weight:600;padding:4px 0;">{lead_phone}</td></tr>'
        if lead_phone
        else ""
    )
    body = f"""
      <h2 style="margin:0 0 8px;color:#111827;font-size:20px;font-weight:700;">
        New lead captured 🎯
      </h2>
      <p style="margin:0 0 20px;color:#374151;font-size:15px;line-height:1.6;">
        Hi {name}, your bot <strong>{bot_name}</strong> captured a new lead.
      </p>
      <table cellpadding="0" cellspacing="0" style="width:100%;margin:0 0 16px;">
        <tr><td style="color:#6b7280;padding:4px 0;width:120px;">Name</td>
            <td style="font-weight:600;padding:4px 0;">{lead_display}</td></tr>
        {phone_row}
        <tr><td style="color:#6b7280;padding:4px 0;">Status</td>
            <td style="font-weight:600;padding:4px 0;text-transform:capitalize;">{lead_status}</td></tr>
        {temp_row}
      </table>
      {summary_row}
      {_BTN.format(url=dashboard_url, label="View in Dashboard")}
    """
    return _BASE.format(title="New lead — BotForge AI", body=body)


def welcome_html(*, full_name: str | None, dashboard_url: str) -> str:
    name = full_name or "there"
    body = f"""
      <h2 style="margin:0 0 8px;color:#111827;font-size:20px;font-weight:700;">
        You're all set! 🚀
      </h2>
      <p style="margin:0 0 20px;color:#374151;font-size:15px;line-height:1.6;">
        Hi {name}, your BotForge AI account is verified and ready to go.<br/>
        Build AI-powered sales bots in minutes.
      </p>
      {_BTN.format(url=dashboard_url, label="Go to Dashboard")}
    """
    return _BASE.format(title="Welcome to BotForge AI!", body=body)
