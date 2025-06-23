# Google OAuth Setup Guide

## Prerequisites
- A Google Cloud Console account
- A Google Cloud project

## Step 1: Create Google Cloud Project
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Google+ API (if not already enabled)

## Step 2: Configure OAuth Consent Screen
1. Go to "APIs & Services" > "OAuth consent screen"
2. Choose "External" user type
3. Fill in the required information:
   - App name: "Kido Learning"
   - User support email: Your email
   - Developer contact information: Your email
4. Add scopes:
   - `openid`
   - `email`
   - `profile`
5. Add test users (your email addresses)

## Step 3: Create OAuth 2.0 Credentials
1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "OAuth 2.0 Client IDs"
3. Choose "Web application"
4. Add authorized JavaScript origins:
   - `http://localhost:8501` (for development)
   - `https://yourdomain.com` (for production)
5. Add authorized redirect URIs:
   - `http://localhost:8501` (for development)
   - `https://yourdomain.com` (for production)
6. Click "Create"

## Step 4: Get Your Client ID
1. Copy the generated Client ID
2. Open `src/App.tsx`
3. Replace `YOUR_GOOGLE_CLIENT_ID_HERE` with your actual Client ID:

```typescript
const GOOGLE_CLIENT_ID = "123456789-abcdefghijklmnop.apps.googleusercontent.com";
```

## Step 5: Test the Setup
1. Start your development server: `npm start` (or your custom port)
2. Navigate to `http://localhost:8501`
3. You should see the login page with a Google Sign-In button
4. Click the button and test the authentication flow

## Troubleshooting Port 8501 Issues

If you're running on port 8501 instead of the default 3000:

1. **Check Google Cloud Console**: Ensure `http://localhost:8501` is added to both:
   - Authorized JavaScript origins
   - Authorized redirect URIs

2. **Clear Browser Cache**: Clear your browser cache and cookies

3. **Check Console Errors**: Open browser DevTools (F12) and check for errors in the Console tab

4. **Verify Client ID**: Ensure the Client ID in your code matches the one in Google Cloud Console

## Common Error Messages

- **"popup_closed_by_user"**: User closed the popup before completing sign-in
- **"access_denied"**: User denied permission or consent screen not configured
- **"invalid_client"**: Client ID is incorrect or not configured properly
- **"redirect_uri_mismatch"**: Redirect URI doesn't match authorized URIs (check port 8501)

## Security Notes
- Never commit your Client ID to public repositories
- Use environment variables in production
- Add your production domain to authorized origins before deploying

## Environment Variables (Optional)
For better security, you can use environment variables:

1. Create a `.env` file in the frontend directory:
```
REACT_APP_GOOGLE_CLIENT_ID=your_client_id_here
```

2. Update `src/App.tsx`:
```typescript
const GOOGLE_CLIENT_ID = process.env.REACT_APP_GOOGLE_CLIENT_ID || "YOUR_GOOGLE_CLIENT_ID_HERE";
```

## Production Deployment
1. Update authorized origins and redirect URIs in Google Cloud Console
2. Use environment variables for the Client ID
3. Ensure HTTPS is enabled on your domain
4. Test the authentication flow thoroughly 