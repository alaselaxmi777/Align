# ALIGN — Instagram Integration Setup Guide (Meta)

ALIGN supports connecting **Instagram Business and Creator accounts** via the official **Instagram API with Instagram Login** (Meta for Developers).

> [!IMPORTANT]
> **API Deprecation Notice:** Meta discontinued the legacy Instagram Basic Display API. ALIGN uses the modern **Instagram API with Instagram Login**. This API works exclusively with **Instagram Professional Accounts (Business or Creator)**. Personal Instagram accounts are not supported by Meta's Graph API. Users can convert any personal Instagram account to a Professional Creator account for free in the Instagram mobile app under *Settings > Account type and tools > Switch to professional account*.

---

## 1. Prerequisites
- A Meta (Facebook) Developer Account at [developers.facebook.com](https://developers.facebook.com).
- An Instagram Business or Creator account for testing.
- An ALIGN installation (local Docker setup or production server).

---

## 2. Step-by-Step Meta App Configuration

### Step 2.1: Create a Meta App
1. Go to [Meta for Developers](https://developers.facebook.com/apps/) and click **Create App**.
2. Select **Other** as the use case, then choose **Business** or **Consumer** as the app type.
3. Name your app (e.g., `ALIGN Community Discovery`) and enter your contact email.

### Step 2.2: Add Instagram Product
1. In the App Dashboard under **Add products to your app**, find **Instagram** and click **Set Up**.
2. Select **Instagram API with Instagram Login** (do NOT select legacy Basic Display).
3. Under Instagram settings, configure:
   - **Valid OAuth Redirect URIs:**
     - Development: `http://localhost:8000/api/v1/instagram/callback`
     - Production: `https://<your-domain>/api/v1/instagram/callback`
   - **Deauthorize Callback URL:**
     - `http://localhost:8000/api/v1/instagram/deauthorize` (or production HTTPS equivalent)
   - **Data Deletion Request Callback URL:**
     - `http://localhost:8000/api/v1/instagram/data-deletion` (or production HTTPS equivalent)

### Step 2.3: Retrieve App Credentials
1. Go to **App Settings > Basic**.
2. Copy your **App ID** and **App Secret**.
3. Under **App Review > Permissions and Features**, the minimum required scope is:
   - `instagram_business_basic` (permits reading username, account type, and user media).

### Step 2.4: Add Test Users (Development Mode)
While your Meta app is in **Development Mode**, only designated test users can authenticate:
1. Navigate to **App Roles > Roles**.
2. Scroll to **Instagram Testers** and click **Add Instagram Testers**.
3. Enter the `@username` of your Instagram Business or Creator test account.
4. On Instagram (mobile app or web), log in as that test user, navigate to **Settings > Website permissions > Apps and Websites > Tester Invites**, and **Accept** the invite.

> [!NOTE]
> **App Review for Production:** To allow any regular user to connect their Instagram account, submit the `instagram_business_basic` permission for Meta App Review and complete Meta Business Verification.

---

## 3. Environment Variables Configuration

In your `.env` file, configure the following variables:

```ini
# Enable the feature flag
INSTAGRAM_ENABLED=true

# Meta Application Credentials
INSTAGRAM_APP_ID=123456789012345
INSTAGRAM_APP_SECRET=your_32_character_meta_app_secret
INSTAGRAM_REDIRECT_URI=http://localhost:8000/api/v1/instagram/callback

# Fernet symmetric encryption key for tokens at rest
TOKEN_ENCRYPTION_KEY=your_generated_fernet_key
```

### Generating the `TOKEN_ENCRYPTION_KEY`
Run the following command in terminal or Python to generate a cryptographically secure 32-byte Fernet key:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

If `TOKEN_ENCRYPTION_KEY` is not provided in development, ALIGN deterministically derives a fallback Fernet key from `JWT_SECRET_KEY` to prevent runtime crashes.

---

## 4. Architectural Data Flow & Privacy

```
User Browser                  ALIGN API                    Meta Instagram Graph
     |                            |                                 |
     |--- 1. Connect Request ---->|                                 |
     |<-- 2. Authorize URL -------| (Signed CSRF state generated)   |
     |    (with state & scope)    |                                 |
     |                            |                                 |
     |--- 3. Redirect to Meta ------------------------------------>|
     |    (User approves scope)                                    |
     |<-- 4. Redirect with Code --|                                 |
     |                            |--- 5. Exchange code for token ->|
     |                            |<-- 6. Short-lived token --------|
     |                            |--- 7. Exchange for long-lived ->|
     |                            |<-- 8. 60-day long-lived token --|
     |                            | (Token encrypted with Fernet)   |
     |<-- 9. Redirect /settings --|                                 |
     |                            |                                 |
     |--- 10. Sync Request ------>|--- 11. Fetch /me/media -------->|
     |                            |<-- 12. Media, captions, tags ---|
     |                            | (Embeddings & Hashtags saved)   |
     |<-- 13. Sync Success -------|                                 |
```

### Privacy & Consent Guarantees
- **No Token Disclosure:** Access tokens are strictly encrypted at rest via Fernet and are never returned to the frontend or exposed in server logs.
- **Opt-in Recommendations:** User media is never used for recommendations unless the user explicitly toggles **"Use my Instagram posts to improve recommendations"**.
- **No Silent Interest Injection:** Inferred interests are presented as "Suggested Interests" that the user must explicitly Accept or Reject.
- **Complete Disconnect & Deletion:** Disconnecting the account immediately purges all encrypted tokens, synced media records, and pending suggested interests from the database.
