import { serve } from "https://deno.land/std@0.168.0/http/server.ts"

const RESEND_API_KEY = Deno.env.get('RESEND_API_KEY')

serve(async (req) => {
  try {
    const { email, metadata } = await req.json()

    if (!email) {
      return new Response(
        JSON.stringify({ error: 'Email is required' }),
        { status: 400, headers: { 'Content-Type': 'application/json' } }
      )
    }

    if (!RESEND_API_KEY) {
      console.error('RESEND_API_KEY not configured')
      return new Response(
        JSON.stringify({ error: 'Email service not configured' }),
        { status: 500, headers: { 'Content-Type': 'application/json' } }
      )
    }

    // Send email via Resend
    const emailResponse = await fetch('https://api.resend.com/emails', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${RESEND_API_KEY}`
      },
      body: JSON.stringify({
        from: 'hello@slateone.studio',
        to: [email],
        subject: "Welcome to SlateOne - You're on the list!",
        html: generateWelcomeEmailHTML(),
        text: generateWelcomeEmailText()
      })
    })

    const emailData = await emailResponse.json()

    if (!emailResponse.ok) {
      console.error('Resend API error:', emailData)
      return new Response(
        JSON.stringify({ error: 'Failed to send email', details: emailData }),
        { status: 500, headers: { 'Content-Type': 'application/json' } }
      )
    }

    console.log(`Welcome email sent to ${email}:`, emailData.id)

    return new Response(
      JSON.stringify({ success: true, emailId: emailData.id }),
      { status: 200, headers: { 'Content-Type': 'application/json' } }
    )

  } catch (error) {
    console.error('Error in send-waitlist-welcome function:', error)
    return new Response(
      JSON.stringify({ error: error.message }),
      { status: 500, headers: { 'Content-Type': 'application/json' } }
    )
  }
})

function generateWelcomeEmailText(): string {
  return `Hi there,

Thanks for joining the SlateOne waitlist! We're building AI-powered script breakdown tools for film and television production teams.

What's next:
- We'll notify you when early access opens
- You'll get 30 days free to test all features
- Your feedback will shape the product

We're launching soon. Keep an eye on your inbox.

---
SlateOne - Script Breakdown
SlateOne.studio
Cape Town, South Africa

Questions? Reply to this email: hello@slateone.studio`
}

function generateWelcomeEmailHTML(): string {
  return `<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Welcome to SlateOne - You're on the list!</title>
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #F9FAFB; color: #111827;">
    <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #F9FAFB; padding: 40px 20px;">
        <tr>
            <td align="center">
                <table width="600" cellpadding="0" cellspacing="0" style="background-color: #FFFFFF; border-radius: 8px; overflow: hidden; border: 1px solid #E5E7EB;">
                    <!-- Header -->
                    <tr>
                        <td style="background-color: #F59E0B; padding: 32px; text-align: center;">
                            <h1 style="margin: 0; font-size: 24px; font-weight: 700; color: #000000;">
                                🎬 SlateOne
                            </h1>
                            <p style="margin: 8px 0 0 0; font-size: 14px; color: #78350F;">AI-Powered Script Breakdown</p>
                        </td>
                    </tr>
                    
                    <!-- Welcome Badge -->
                    <tr>
                        <td style="background-color: #10B981; padding: 12px; text-align: center;">
                            <p style="margin: 0; font-size: 14px; font-weight: 700; color: #FFFFFF; text-transform: uppercase; letter-spacing: 1px;">
                                ✓ You're on the waitlist
                            </p>
                        </td>
                    </tr>
                    
                    <!-- Content -->
                    <tr>
                        <td style="padding: 32px;">
                            <h2 style="margin: 0 0 16px 0; font-size: 22px; font-weight: 700; color: #111827; line-height: 1.3;">
                                Thanks for joining!
                            </h2>
                            
                            <p style="margin: 0 0 24px 0; font-size: 16px; color: #4B5563; line-height: 1.6;">
                                We're building AI-powered script breakdown tools for film and television production teams. You'll be among the first to know when we launch.
                            </p>
                            
                            <!-- What's Next -->
                            <div style="background-color: #F3F4F6; border-radius: 6px; padding: 20px; margin-bottom: 24px;">
                                <p style="margin: 0 0 12px 0; font-size: 14px; color: #374151; font-weight: 600;">What's next:</p>
                                
                                <p style="margin: 0 0 8px 0; font-size: 15px; color: #111827; line-height: 1.6;">
                                    ✓ We'll notify you when early access opens
                                </p>
                                <p style="margin: 0 0 8px 0; font-size: 15px; color: #111827; line-height: 1.6;">
                                    ✓ You'll get 30 days free to test all features
                                </p>
                                <p style="margin: 0; font-size: 15px; color: #111827; line-height: 1.6;">
                                    ✓ Your feedback will shape the product
                                </p>
                            </div>
                            
                            <p style="margin: 0 0 24px 0; font-size: 16px; color: #4B5563; line-height: 1.6;">
                                We're launching soon. Keep an eye on your inbox for updates.
                            </p>
                        </td>
                    </tr>
                    
                    <!-- Features Preview -->
                    <tr>
                        <td style="padding: 0 32px 32px 32px;">
                            <p style="margin: 0 0 16px 0; font-size: 14px; color: #6B7280; text-transform: uppercase; letter-spacing: 0.5px; font-weight: 600;">What you'll get:</p>
                            
                            <table width="100%" cellpadding="0" cellspacing="0">
                                <tr>
                                    <td style="padding: 12px 16px; background-color: #F9FAFB; border: 1px solid #E5E7EB; border-radius: 6px; margin-bottom: 8px;">
                                        <p style="margin: 0 0 4px 0; font-size: 15px; font-weight: 600; color: #111827;">📄 AI Script Analysis</p>
                                        <p style="margin: 0; font-size: 13px; color: #6B7280;">Automatic scene detection and breakdown</p>
                                    </td>
                                </tr>
                            </table>
                            
                            <table width="100%" cellpadding="0" cellspacing="0" style="margin-top: 8px;">
                                <tr>
                                    <td style="padding: 12px 16px; background-color: #F9FAFB; border: 1px solid #E5E7EB; border-radius: 6px;">
                                        <p style="margin: 0 0 4px 0; font-size: 15px; font-weight: 600; color: #111827;">👥 Team Collaboration</p>
                                        <p style="margin: 0; font-size: 13px; color: #6B7280;">Work together with your crew</p>
                                    </td>
                                </tr>
                            </table>
                            
                            <table width="100%" cellpadding="0" cellspacing="0" style="margin-top: 8px;">
                                <tr>
                                    <td style="padding: 12px 16px; background-color: #F9FAFB; border: 1px solid #E5E7EB; border-radius: 6px;">
                                        <p style="margin: 0 0 4px 0; font-size: 15px; font-weight: 600; color: #111827;">📊 Production Reports</p>
                                        <p style="margin: 0; font-size: 13px; color: #6B7280;">Export stripboards and breakdowns</p>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    
                    <!-- Footer -->
                    <tr>
                        <td style="padding: 24px 32px; border-top: 1px solid #E5E7EB; text-align: center;">
                            <p style="margin: 0 0 8px 0; font-size: 12px; color: #6B7280;">
                                Questions? Reply to this email at hello@slateone.studio
                            </p>
                            <p style="margin: 0; font-size: 11px; color: #9CA3AF; line-height: 1.6;">
                                SlateOne · SlateOne.studio · Cape Town, South Africa
                            </p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>`
}
