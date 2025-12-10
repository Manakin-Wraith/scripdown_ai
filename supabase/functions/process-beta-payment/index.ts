/**
 * Process Beta Payment - Supabase Edge Function
 * 
 * Called after user completes Yoco payment.
 * Records payment and prepares user for account creation.
 */

import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
}

interface PaymentRequest {
  email: string
  payment_reference?: string
}

Deno.serve(async (req) => {
  // Handle CORS preflight
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders })
  }

  try {
    const { email, payment_reference } = await req.json() as PaymentRequest

    if (!email) {
      return new Response(
        JSON.stringify({ error: 'Email is required' }),
        { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    // Normalize email
    const normalizedEmail = email.toLowerCase().trim()

    // Create Supabase client with service role for admin operations
    const supabaseAdmin = createClient(
      Deno.env.get('SUPABASE_URL') ?? '',
      Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? '',
      {
        auth: {
          autoRefreshToken: false,
          persistSession: false
        }
      }
    )

    // Check if payment already exists
    const { data: existingPayment, error: fetchError } = await supabaseAdmin
      .from('beta_payments')
      .select('*')
      .eq('email', normalizedEmail)
      .single()

    if (existingPayment && existingPayment.status === 'completed') {
      // Already paid - return success
      return new Response(
        JSON.stringify({ 
          success: true, 
          already_paid: true,
          message: 'Payment already recorded for this email'
        }),
        { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    // Record or update payment
    const paymentData = {
      email: normalizedEmail,
      payment_reference: payment_reference || null,
      status: 'completed',
      paid_at: new Date().toISOString(),
      metadata: {
        source: 'yoco_payment_link',
        processed_at: new Date().toISOString()
      }
    }

    const { data: payment, error: upsertError } = await supabaseAdmin
      .from('beta_payments')
      .upsert(paymentData, { onConflict: 'email' })
      .select()
      .single()

    if (upsertError) {
      console.error('Error recording payment:', upsertError)
      return new Response(
        JSON.stringify({ error: 'Failed to record payment', details: upsertError.message }),
        { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    // Check if user already exists in auth
    const { data: existingUsers } = await supabaseAdmin.auth.admin.listUsers()
    const existingUser = existingUsers?.users?.find(u => u.email === normalizedEmail)

    if (existingUser) {
      // User exists - update their profile subscription status
      await supabaseAdmin
        .from('profiles')
        .update({ 
          subscription_status: 'active',
          subscription_expires_at: null // Beta = no expiry for now
        })
        .eq('id', existingUser.id)

      // Link payment to user
      await supabaseAdmin
        .from('beta_payments')
        .update({ user_id: existingUser.id })
        .eq('email', normalizedEmail)

      return new Response(
        JSON.stringify({ 
          success: true, 
          user_exists: true,
          message: 'Payment recorded. Your account has been upgraded!'
        }),
        { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    // User doesn't exist yet - they'll need to sign up
    // The payment is recorded, so when they sign up with this email,
    // we can check beta_payments and auto-activate their account

    return new Response(
      JSON.stringify({ 
        success: true, 
        user_exists: false,
        message: 'Payment recorded! Check your email for account setup instructions within 24 hours.'
      }),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )

  } catch (error) {
    console.error('Error processing payment:', error)
    return new Response(
      JSON.stringify({ error: 'Internal server error' }),
      { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }
})
