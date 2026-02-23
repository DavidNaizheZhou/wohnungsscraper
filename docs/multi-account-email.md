# Multiple Email Accounts

The apartment scraper supports sending notifications to multiple recipients using separate Resend accounts.

## How It Works

Since Resend's free tier only allows sending to the registered email address, you can configure multiple Resend accounts to notify multiple people.

## Configuration Modes

### Single Account (Default)

```bash
# .env or GitHub Secrets
RESEND_API_KEY=re_xxx
EMAIL_TO=your.email@example.com
EMAIL_FROM=onboarding@resend.dev
```

### Multiple Accounts

```bash
# .env or GitHub Secrets
RESEND_API_KEY_1=re_firstkey_xxx
EMAIL_TO_1=first.person@example.com

RESEND_API_KEY_2=re_secondkey_xxx
EMAIL_TO_2=second.person@gmail.com

RESEND_API_KEY_3=re_thirdkey_xxx
EMAIL_TO_3=third.person@posteo.at

# Still needed for FROM address
EMAIL_FROM=onboarding@resend.dev
```

## Setup Steps

For each recipient:

1. **Create Resend Account**
   - Go to https://resend.com/signup
   - Register with the recipient's email address
   - Get the API key from dashboard

2. **Add to Configuration**
   - Local: Add to `.env` file (numbered: `_1`, `_2`, `_3`, etc.)
   - GitHub: Set secrets with numbered suffixes

3. **GitHub Secrets Example**
   ```bash
   gh secret set RESEND_API_KEY_1 --body "re_firstkey_xxx"
   gh secret set EMAIL_TO_1 --body "first@example.com"

   gh secret set RESEND_API_KEY_2 --body "re_secondkey_xxx"
   gh secret set EMAIL_TO_2 --body "second@example.com"

   gh secret set EMAIL_FROM --body "onboarding@resend.dev"
   ```

## How It Works

When apartments are found:
1. System generates one email with all apartments
2. Sends the same email using each configured account
3. Each recipient gets notified at their registered email

## Limits

- **Free Tier**: 3,000 emails/month per account
- **Recipients**: Each Resend account can only send to its registered email
- **Alternative**: To send to multiple emails from one account, you need domain verification

## Alternative: Domain Verification

If you own a domain, you can:
1. Verify your domain at https://resend.com/domains
2. Change `EMAIL_FROM` to `scraper@yourdomain.com`
3. Send to any email addresses in `EMAIL_TO` (comma-separated)

This is cleaner but requires domain ownership.

## Current Setup

Current configuration:
- Account 1: d.zhou@posteo.at (API key: re_ZgE8mDW5_Q4KccP3ay1E75ScUzEPY2Cor)

To add more recipients, follow the steps above!
