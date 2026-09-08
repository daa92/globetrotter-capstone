"""
app/notifications/email_templates.py

One consistent, on-brand shell for every email the app sends — a teal
header with the GT wordmark, a white content card, and a light footer —
instead of each call site hand-rolling its own bare HTML fragment (which
is what verification/password-reset/feedback emails used to do: a few
unstyled <p> tags, no header, no branding).

Email clients don't support external stylesheets, flexbox/grid, or most
modern CSS, so everything here is deliberately old-school: inline
styles, a single-column table layout, no JS, no @media queries assumed
to work — the one approach that renders consistently across Gmail,
Outlook, Apple Mail, and everything else.

IMPORTANT — verification/reset codes: some emails embed a copyable code
via `code_line()`. The surrounding test suite (tests/test_auth.py,
tests/test_verification_and_cleanup.py, tests/test_phone_and_password_reset.py)
extracts that code by looking for the literal substring "token: " and
reading up to the next "\n". `code_line()` preserves that exact
contract (a bare "token: {value}\n" text node with nothing else on that
line) while still rendering as a styled code chip — see its docstring.
"""
from app.config import settings

BRAND_TEAL = "#0F6B62"
BRAND_TEAL_DARK = "#0B4A44"
BRAND_GOLD = "#C9975C"
TEXT = "#1F2937"
MUTED = "#6B7280"
BORDER = "#E5E7EB"
BG = "#F3F4F6"


def code_line(token: str) -> str:
    """A "token: {value}" text node wrapped in a styled code-chip <div>,
    with the opening tag, the bare text, and the closing tag each on
    their own line — so 'token: ' + the token + '\\n' is still an exact,
    isolated substring (existing tests split on it), while an email
    client still renders a nicely boxed monospace code."""
    return (
        f'<div style="margin:16px 0 0;padding:14px 16px;background:{BG};'
        f'border:1px dashed {BORDER};border-radius:10px;font-family:'
        f'\'SFMono-Regular\',Consolas,Menlo,monospace;font-size:13px;'
        f'word-break:break-all;color:{TEXT};text-align:center;">\n'
        f"token: {token}\n"
        f"</div>"
    )


def render_email(
    *,
    preheader: str,
    heading: str,
    body_html: str,
    cta_label: str | None = None,
    cta_url: str | None = None,
    footnote: str | None = None,
) -> str:
    """The shared shell. `body_html` is the only per-email content —
    everything else (header, card, footer) is identical across every
    email the app sends."""
    cta_block = ""
    if cta_label and cta_url:
        cta_block = f"""
            <table role="presentation" cellpadding="0" cellspacing="0" style="margin:24px auto 0;">
              <tr>
                <td style="border-radius:999px;background:{BRAND_TEAL};">
                  <a href="{cta_url}" style="display:inline-block;padding:12px 30px;font-size:14px;font-weight:600;color:#ffffff;text-decoration:none;border-radius:999px;">
                    {cta_label}
                  </a>
                </td>
              </tr>
            </table>
        """

    footnote_block = ""
    if footnote:
        footnote_block = f'<p style="margin:24px 0 0;font-size:12px;line-height:1.6;color:{MUTED};">{footnote}</p>'

    return f"""<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{heading}</title>
  </head>
  <body style="margin:0;padding:0;background:{BG};font-family:-apple-system,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">
    <div style="display:none;max-height:0;overflow:hidden;opacity:0;">{preheader}</div>
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{BG};padding:32px 16px;">
      <tr>
        <td align="center">
          <table role="presentation" width="100%" style="max-width:480px;background:#ffffff;border-radius:18px;overflow:hidden;border:1px solid {BORDER};">
            <tr>
              <td style="background:linear-gradient(135deg,{BRAND_TEAL},{BRAND_TEAL_DARK});padding:28px 32px;">
                <span style="font-size:21px;font-weight:800;color:#ffffff;letter-spacing:-0.02em;">
                  GT<span style="color:{BRAND_GOLD};">Cam</span>
                </span>
              </td>
            </tr>
            <tr>
              <td style="padding:32px;">
                <h1 style="margin:0 0 14px;font-size:19px;font-weight:700;color:{TEXT};">{heading}</h1>
                <div style="font-size:14px;line-height:1.7;color:{TEXT};">{body_html}</div>
                {cta_block}
                {footnote_block}
              </td>
            </tr>
            <tr>
              <td style="padding:18px 32px;background:{BG};border-top:1px solid {BORDER};">
                <p style="margin:0;font-size:12px;color:{MUTED};">
                  GT — GlobeTrotter Cameroon &middot; Discover Cameroon, your way.
                </p>
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>"""


# ---------------------------------------------------------------------------
# Specific emails
# ---------------------------------------------------------------------------

def verification_email(username: str, token: str, ttl_minutes: int) -> str:
    link = f"{settings.FRONTEND_URL}/verify?token={token}"
    body_html = (
        f'<p style="margin:0 0 6px;">Welcome to GT, <strong>{username}</strong> 👋</p>'
        f'<p style="margin:0;">Confirm your email to activate your account — this link '
        f"and the code below both expire in {ttl_minutes} minutes.</p>"
        f"{code_line(token)}"
        f'<p style="margin:14px 0 0;font-size:13px;color:{MUTED};">'
        f"Still on the sign-up screen? Paste the code above there instead of clicking the button.</p>"
    )
    return render_email(
        preheader=f"Verify your GT account, {username}",
        heading="Confirm your email",
        body_html=body_html,
        cta_label="Verify my account",
        cta_url=link,
        footnote="Didn't create this account? You can safely ignore this email.",
    )


def password_reset_email(username: str, token: str, ttl_minutes: int) -> str:
    # The reset page (PasswordReset.jsx) is a manual two-step form — it
    # doesn't read a token from the URL, so the button just gets them
    # there; the code below is what they actually paste in.
    link = f"{settings.FRONTEND_URL}/password-reset"
    body_html = (
        f'<p style="margin:0 0 6px;">Hi <strong>{username}</strong>,</p>'
        f'<p style="margin:0;">We got a request to reset your GT password. '
        f"This code expires in {ttl_minutes} minutes.</p>"
        f"{code_line(token)}"
    )
    return render_email(
        preheader="Reset your GT password",
        heading="Reset your password",
        body_html=body_html,
        cta_label="Reset my password",
        cta_url=link,
        footnote="Didn't request this? Your password is still safe — just ignore this email.",
    )


def admin_feedback_email(username: str, category: str, message: str, rating: int | None) -> str:
    rating_html = f'<p style="margin:12px 0 0;">Rating: <strong>{rating}/5</strong></p>' if rating else ""
    body_html = (
        f'<p style="margin:0 0 6px;">New feedback from <strong>{username}</strong> '
        f'<span style="color:{MUTED};">({category})</span>:</p>'
        f'<p style="margin:12px 0 0;padding:14px 16px;background:{BG};border-radius:10px;white-space:pre-wrap;">{message}</p>'
        f"{rating_html}"
    )
    return render_email(
        preheader=f"New feedback: {category}",
        heading="New feedback received",
        body_html=body_html,
        cta_label="View in dashboard",
        cta_url="https://gtcam.vercel.app/admin-c746b9c7d7c57420",
    )


def broadcast_email(title: str, message: str) -> str:
    """For admin-authored notifications sent 'also as email' — the admin
    writes free-form text, so this just gives it the branded frame
    rather than trying to template arbitrary admin content."""
    body_html = f'<p style="margin:0;white-space:pre-wrap;">{message}</p>'
    return render_email(preheader=title, heading=title, body_html=body_html)
