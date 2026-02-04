-- Update Personal Message from Founder template - Premium Dark Theme Design
UPDATE email_templates 
SET body_html = '<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Personal Message from SlateOne</title>
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, ''Segoe UI'', Roboto, ''Helvetica Neue'', Arial, sans-serif; background-color: #0F0F0F; color: #E5E7EB;">
    <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #0F0F0F; padding: 40px 20px;">
        <tr>
            <td align="center">
                <table width="600" cellpadding="0" cellspacing="0" style="background-color: #1A1A1A; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4); border: 1px solid #2A2A2A;">
                    <!-- Orange Accent Line -->
                    <tr>
                        <td style="height: 4px; background: linear-gradient(90deg, #F59E0B, #D97706);"></td>
                    </tr>
                    
                    <!-- Header -->
                    <tr>
                        <td style="padding: 32px 40px 24px 40px; text-align: left;">
                            <div style="display: flex; align-items: center;">
                                <span style="font-size: 24px; margin-right: 8px;">🎬</span>
                                <span style="font-family: ''Courier New'', Courier, monospace; font-size: 20px; font-weight: 700; color: #FFFFFF; letter-spacing: -0.5px;">SlateOne</span>
                            </div>
                        </td>
                    </tr>
                    
                    <!-- Content -->
                    <tr>
                        <td style="padding: 0 40px 32px 40px;">
                            <p style="margin: 0 0 24px 0; font-size: 15px; color: #9CA3AF; line-height: 1.6;">
                                Hi {{user_name}},
                            </p>
                            
                            <div style="margin: 0 0 40px 0; font-size: 15px; color: #E5E7EB; line-height: 1.7;">
                                {{message_body}}
                            </div>
                            
                            <!-- Signature Block -->
                            <div style="margin-top: 48px; padding-top: 32px; border-top: 1px solid #2A2A2A;">
                                <table cellpadding="0" cellspacing="0" style="width: 100%;">
                                    <tr>
                                        <td style="width: 60px; vertical-align: top; padding-right: 16px;">
                                            <img src="https://app.slateone.studio/profile_pic.png" alt="{{founder_name}}" style="width: 56px; height: 56px; border-radius: 50%; object-fit: cover; border: 2px solid #F59E0B;">
                                        </td>
                                        <td style="vertical-align: top;">
                                            <p style="margin: 0 0 4px 0; font-size: 16px; font-weight: 700; color: #FFFFFF; letter-spacing: -0.3px;">
                                                {{founder_name}}
                                            </p>
                                            <p style="margin: 0 0 12px 0; font-size: 14px; color: #9CA3AF; font-weight: 400;">
                                                {{founder_title}}
                                            </p>
                                            <p style="margin: 0; font-family: ''Courier New'', Courier, monospace; font-size: 14px; font-weight: 600; color: #F59E0B;">
                                                SlateOne
                                            </p>
                                        </td>
                                    </tr>
                                </table>
                            </div>
                        </td>
                    </tr>
                    
                    <!-- Footer -->
                    <tr>
                        <td style="padding: 40px 40px 32px 40px; border-top: 1px solid #2A2A2A; background-color: #141414;">
                            <p style="margin: 0 0 20px 0; font-size: 12px; color: #9CA3AF; text-align: center;">
                                This is a personal message from the SlateOne team.
                            </p>
                            
                            <!-- App URL - Prominent CTA -->
                            <div style="text-align: center; margin: 24px 0;">
                                <a href="https://app.slateone.studio" style="display: inline-block; padding: 12px 24px; background-color: #F59E0B; color: #000000; text-decoration: none; font-weight: 600; font-size: 14px; border-radius: 6px; letter-spacing: -0.2px;">
                                    Visit SlateOne Studio
                                </a>
                            </div>
                            
                            <!-- Company Tagline -->
                            <p style="margin: 24px 0 16px 0; font-size: 12px; color: #9CA3AF; font-style: italic; text-align: center;">
                                AI-Powered Script Breakdown & Production Management
                            </p>
                            
                            <!-- Social Links -->
                            <div style="text-align: center; margin: 20px 0;">
                                <a href="https://www.linkedin.com/company/slateone-studio" style="display: inline-block; color: #9CA3AF; text-decoration: none; font-size: 11px; padding: 4px 8px; border: 1px solid #2A2A2A; border-radius: 4px;">
                                    LinkedIn
                                </a>
                            </div>
                            
                            <!-- Legal -->
                            <p style="margin: 20px 0 0 0; color: #6B7280; font-size: 11px; text-align: center;">
                                © 2026 SlateOne. All rights reserved.
                            </p>
                            <p style="margin: 8px 0 0 0; color: #6B7280; font-size: 11px; text-align: center;">
                                Questions? Just reply to this email.
                            </p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>',
    body_text = 'Hi {{user_name}},

{{message_body}}

---

{{founder_name}}
{{founder_title}}
SlateOne

═══════════════════════════════════════

This is a personal message from the SlateOne team.

→ Visit SlateOne Studio
  app.slateone.studio

AI-Powered Script Breakdown & Production Management

LinkedIn: https://www.linkedin.com/company/slateone-studio

© 2026 SlateOne. All rights reserved.
Questions? Just reply to this email.'
WHERE name = 'Personal Message from Founder';
