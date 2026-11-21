# SMTP Email Configuration Guide

ALIGN supports transactional email delivery for password resets and notifications.

---

## 1. Environment Configuration

Add the following variables to your root `.env` file:

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-16-character-app-password
SMTP_FROM_EMAIL=noreply@align.local
SMTP_USE_TLS=true
```

---

## 2. Using Gmail SMTP

To use Gmail for automated emails:
1. Ensure **2-Step Verification** is enabled on your Google Account.
2. Visit [Google App Passwords](https://myaccount.google.com/apppasswords).
3. Select **App name**: `ALIGN Dev`.
4. Click **Create** to generate a 16-character App Password.
5. Set `SMTP_PASSWORD` to this generated 16-character password (without spaces).

---

## 3. Development Fallback Mode

If no SMTP server is configured in `.env`:
- ALIGN will issue secure, single-use reset tokens safely.
- In development, the reset endpoint logs the token to the backend server output:
  `[DEV NOTIFICATION] Password reset token for user@example.com: <token>`
- The token is also returned in the development response payload (`dev_token`) for immediate testing in the UI.
- No dummy/mock emails are reported as sent.
