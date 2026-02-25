#!/bin/bash
# Set GitHub secrets for email configuration

cd /home/david/projects/wohnung

echo "Setting GitHub secrets..."

gh secret set EMAIL_TO_1 --body "d.zhou@posteo.at"
gh secret set RESEND_API_KEY_1 --body "re_ZgE8mDW5_Q4KccP3ay1E75ScUzEPY2Cor"
gh secret set EMAIL_TO_2 --body "dana.kreuz@posteo.at"
gh secret set RESEND_API_KEY_2 --body "re_SvPKcYM4_3kLtc2WAm594LTifHxX3i7dN"
gh secret set EMAIL_FROM --body "onboarding@resend.dev"

echo "✅ All secrets set successfully!"
