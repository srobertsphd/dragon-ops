# Supabase Database Connection Setup Guide

**Created:** December 2025  
**Purpose:** Document how to obtain Supabase database connection strings for production and development environments.

---

## Overview

Supabase provides two types of database connections:
- **Direct Connection**: IPv6-only, may not work with IPv4-only networks (like WSL2)
- **Session Pooler**: IPv4-compatible, recommended for local development and most platforms

This guide explains how to obtain the Session Pooler connection string from Supabase dashboard.

---

## Step-by-Step: Getting Connection String

### Step 1: Access Connection Modal

1. Log into [Supabase Dashboard](https://supabase.com/dashboard)
2. Select your project (Production or Development)
3. **Click "Connect" button** in the top navigation bar
   - This opens the "Connect to your project" modal

### Step 2: Navigate to Connection String Tab

In the modal that appears:
1. Click on the **"Connection String"** tab (should be active by default)
2. You'll see connection configuration options

### Step 3: Select Session Pooler Method

1. Find the **"Method"** dropdown menu
2. Click the dropdown (currently shows "Direct connection")
3. Select **"Session Pooler"** from the dropdown options
   - This changes the connection string to use the pooler endpoint

### Step 4: Copy Connection String

1. The connection string field will update automatically
2. Copy the entire connection string
   - Format: `postgresql://postgres.xxxxx:[YOUR_PASSWORD]@aws-0-us-east-1.pooler.supabase.com:6543/postgres`
   - Notice: Different hostname (`.pooler.supabase.com`) and port (`6543`)

### Step 5: Verify IPv4 Compatibility

After selecting Session Pooler:
- The "Not IPv4 compatible" warning should disappear
- You should see "IPv4 compatible" or no warning at all
- This confirms the connection will work with IPv4-only networks

---

## Setting Up Environment Variables

### For Local Development (.env file)

```bash
# Production Database (reference only - not used locally)
DATABASE_URL_PROD=postgresql://postgres.xxxxx:[PROD_PASSWORD]@aws-0-us-east-1.pooler.supabase.com:6543/postgres

# Development Database (used for local development)
DATABASE_URL_DEV=postgresql://postgres.yyyyy:[DEV_PASSWORD]@aws-0-us-east-1.pooler.supabase.com:6543/postgres

# Active Database (points to DEV for local work)
DATABASE_URL=${DATABASE_URL_DEV}
```

**Important Notes:**
- Replace `[PROD_PASSWORD]` and `[DEV_PASSWORD]` with actual passwords
- Replace `xxxxx` and `yyyyy` with your actual project identifiers
- The `DATABASE_URL` variable is what Django reads
- Set it to `${DATABASE_URL_DEV}` for local development

### For Production (Render)

1. Go to Render Dashboard → Your App → Environment
2. Set `DATABASE_URL` environment variable to production Session Pooler URL
3. Render will use this instead of `.env` file
4. Production always uses production database

---

## Why Use Session Pooler?

### Direct Connection Issues:
- ❌ IPv6-only (may not work with WSL2, Vercel, GitHub Actions, Render, Retool)
- ❌ Requires IPv4 add-on purchase for IPv4 compatibility
- ❌ May have network connectivity issues

### Session Pooler Benefits:
- ✅ IPv4 compatible (works with all platforms)
- ✅ Free on Supabase free tier
- ✅ Better connection management
- ✅ Recommended for most use cases

---

## Troubleshooting

### Issue: "Network is unreachable" Error

**Symptoms:**
- Django can't connect to database
- Error shows IPv6 address (`2600:1f13:...`)
- `ping` command fails

**Solution:**
- Use Session Pooler connection string instead of Direct Connection
- Session Pooler uses IPv4 and works with WSL2

### Issue: Connection String Not Updating

**Solution:**
1. Make sure you selected "Session Pooler" from Method dropdown
2. Wait a moment for the connection string to update
3. If it doesn't update, try refreshing the modal

### Issue: Still Can't Connect After Using Pooler

**Check:**
1. Verify password is correct in connection string
2. Check Supabase project is "Active" (not paused)
3. Verify network restrictions allow your IP (Settings → Database → Network Restrictions)
4. Test connection from Supabase SQL Editor to verify database is accessible

---

## Quick Reference

### Getting Connection String:
1. Supabase Dashboard → Select Project
2. Click **"Connect"** (top navigation bar)
3. **"Connection String"** tab → **"Method"** dropdown → Select **"Session Pooler"**
4. Copy connection string

### For Production:
- Use production project's Session Pooler URL
- Set in Render environment variables

### For Development:
- Use development project's Session Pooler URL  
- Set in local `.env` file as `DATABASE_URL_DEV`
- Set `DATABASE_URL=${DATABASE_URL_DEV}` for local work

---

## Related Documentation

- [Django Database Configuration](../alano_club_site/settings.py)
- [Environment Setup](../.env.example)
- [Change Log - Database Setup](./CHANGE_LOG.md)

---

## Notes

- **Always use Session Pooler** for local development (WSL2 compatibility)
- **Both production and development** should use Session Pooler URLs
- Connection strings are project-specific - each Supabase project has its own pooler URL
- Passwords are set when creating the project - can be reset in Database Settings if needed

