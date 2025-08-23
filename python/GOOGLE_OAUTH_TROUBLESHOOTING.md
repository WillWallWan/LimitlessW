# 🚨 Google OAuth Troubleshooting Guide

## Problem: "limitless has not completed the Google verification process"

This error occurs when your Google Cloud Project isn't properly configured for external access.

## 🛠️ Solution Steps:

### Step 1: Open Google Cloud Console
1. Go to: https://console.cloud.google.com/
2. Select your project (the one where you created the credentials)

### Step 2: Configure OAuth Consent Screen
1. Go to: **APIs & Services** → **OAuth consent screen**
2. Check your current setup:

#### If User Type = "Internal":
- ❌ **Problem**: Only works for Google Workspace users
- ✅ **Fix**: Change to "External"

#### If User Type = "External":
- Check **Publishing Status**:
  - If "**In production**" → Need Google verification (takes weeks)
  - If "**Testing**" → Perfect! Just need to add test users

### Step 3: Add Yourself as Test User (MOST LIKELY FIX)
1. In **OAuth consent screen** → **Test users**
2. Click **"+ ADD USERS"**
3. Add your email: `willwallwan@gmail.com`
4. Click **SAVE**

### Step 4: Verify Scopes
Make sure you have these scopes enabled:
- `https://www.googleapis.com/auth/calendar`
- `https://www.googleapis.com/auth/calendar.events`

### Step 5: Clear Cached Credentials
Your `token.pickle` file might be corrupted:
```bash
rm token.pickle
```

## 🎯 Quick Checklist:
- [ ] Project exists in Google Cloud Console
- [ ] Calendar API is enabled
- [ ] OAuth consent screen configured
- [ ] User type set to "External"
- [ ] Publishing status = "Testing"
- [ ] Your email added as test user
- [ ] Proper scopes configured
- [ ] Old token.pickle removed

## 🔄 After Making Changes:
1. Delete `token.pickle` (if it exists)
2. Run the calendar integration again
3. You should see the OAuth login flow
4. Grant permissions when prompted

## 📞 Still Having Issues?
The most common fix is adding yourself as a test user in the OAuth consent screen!


