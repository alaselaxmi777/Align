# Google OAuth & Identity Services Setup Guide

ALIGN includes full backend token verification for Google authentication using Google's official `google-auth` library.

Follow these steps in the [Google Cloud Console](https://console.cloud.google.com/) to obtain your Web Client ID:

---

## 1. Create a Google Cloud Project
1. Log in to the [Google Cloud Console](https://console.cloud.google.com/).
2. Click **Select a project** > **New Project**.
3. Name your project (e.g. `align-intent-discovery`) and click **Create**.

---

## 2. Configure the OAuth Consent Screen
1. Go to **APIs & Services** > **OAuth consent screen**.
2. Select **External** user type and click **Create**.
3. Fill in the required fields:
   - **App name**: `ALIGN`
   - **User support email**: Your email address
   - **Developer contact information**: Your email address
4. Under **Scopes**, click **Add or Remove Scopes**:
   - Select `.../auth/userinfo.email`
   - Select `.../auth/userinfo.profile`
   - Select `openid`
5. Under **Test Users**, add your personal Google email so you can test during development.
6. Click **Save and Continue**.

---

## 3. Create Web OAuth Client ID
1. Navigate to **APIs & Services** > **Credentials**.
2. Click **Create Credentials** > **OAuth client ID**.
3. Choose **Application type**: **Web application**.
4. Set **Name**: `ALIGN Web Client`.
5. Under **Authorized JavaScript origins**, add:
   - `http://localhost:5173`
   - `http://localhost:3000`
   - `http://127.0.0.1:5173`
6. Under **Authorized redirect URIs**, add:
   - `http://localhost:5173`
   - `http://localhost:8000/api/v1/auth/google`
7. Click **Create**.
8. Copy the generated **Client ID** (it looks like `1234567890-abcdefg.apps.googleusercontent.com`).

---

## 4. Configure ALIGN Environment
Configured in `.env`:
```env
GOOGLE_CLIENT_ID=your_google_client_id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your_google_client_secret
VITE_GOOGLE_CLIENT_ID=your_google_client_id.apps.googleusercontent.com
```

> [!IMPORTANT]
> Make sure `http://localhost:5173` and `http://127.0.0.1:5173` are added under **Authorized JavaScript origins** in your Google Cloud Console for this OAuth client ID.


```env
GOOGLE_CLIENT_ID=your-client-id-here.apps.googleusercontent.com
```

### Security Notes:
- Never commit private client secrets or API keys to version control.
- ALIGN authenticates users by verifying the signed JWT ID token directly with Google's public key endpoint via `google.oauth2.id_token.verify_oauth2_token`.
- An invalid or expired token is immediately rejected with HTTP 400.
