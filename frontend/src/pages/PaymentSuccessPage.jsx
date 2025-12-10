import React, { useState, useEffect } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { CheckCircle, Loader2, AlertCircle, Mail } from 'lucide-react';
import './PaymentSuccessPage.css';

const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL;

const PaymentSuccessPage = () => {
  const [searchParams] = useSearchParams();
  const [status, setStatus] = useState('loading'); // loading, success, error, email_required
  const [email, setEmail] = useState('');
  const [message, setMessage] = useState('');

  // Try to get email from URL params, localStorage, or ask user
  const emailFromUrl = searchParams.get('email');
  const emailFromStorage = typeof window !== 'undefined' ? localStorage.getItem('beta_payment_email') : null;

  useEffect(() => {
    if (emailFromUrl) {
      processPayment(emailFromUrl);
    } else if (emailFromStorage) {
      // Auto-process with stored email (from popup flow)
      setEmail(emailFromStorage);
      processPayment(emailFromStorage);
    } else {
      setStatus('email_required');
    }
  }, [emailFromUrl]);

  const processPayment = async (userEmail) => {
    setStatus('loading');
    try {
      const response = await fetch(`${SUPABASE_URL}/functions/v1/process-beta-payment`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
          email: userEmail,
          payment_reference: searchParams.get('reference') || null
        }),
      });

      const data = await response.json();

      if (response.ok) {
        setStatus('success');
        setMessage(data.already_paid 
          ? 'Your payment was already recorded. Check your email for login details!'
          : 'Payment confirmed! Check your email for login details within 24 hours.'
        );
        // Clear stored email after successful processing
        localStorage.removeItem('beta_payment_email');
      } else {
        setStatus('error');
        setMessage(data.error || 'Something went wrong. Please contact support.');
      }
    } catch (error) {
      console.error('Error:', error);
      setStatus('error');
      setMessage('Failed to process payment. Please contact support.');
    }
  };

  const handleEmailSubmit = (e) => {
    e.preventDefault();
    if (email) {
      processPayment(email);
    }
  };

  return (
    <div className="payment-success-container">
      <div className="payment-success-card">
        <div className="logo">
          <span className="logo-text">Slate<span className="logo-accent">One</span></span>
        </div>

        {status === 'loading' && (
          <div className="status-section">
            <Loader2 className="spinner" size={48} />
            <h2>Processing your payment...</h2>
            <p>Please wait while we confirm your beta access.</p>
          </div>
        )}

        {status === 'success' && (
          <div className="status-section success">
            <CheckCircle className="success-icon" size={64} />
            <h2>Welcome to SlateOne Beta! 🎬</h2>
            <p>{message}</p>
            <div className="next-steps">
              <h3>What happens next?</h3>
              <ul>
                <li>✓ Your payment has been recorded</li>
                <li>✓ We're setting up your account</li>
                <li>✓ You'll receive login credentials via email within 24 hours</li>
              </ul>
            </div>
            <Link to="/login" className="btn-primary">
              Go to Login
            </Link>
          </div>
        )}

        {status === 'error' && (
          <div className="status-section error">
            <AlertCircle className="error-icon" size={64} />
            <h2>Oops! Something went wrong</h2>
            <p>{message}</p>
            <div className="support-info">
              <p>Need help? Email us at <a href="mailto:hello@slateone.studio">hello@slateone.studio</a></p>
            </div>
            <button onClick={() => setStatus('email_required')} className="btn-secondary">
              Try Again
            </button>
          </div>
        )}

        {status === 'email_required' && (
          <div className="status-section email-form">
            <Mail className="mail-icon" size={48} />
            <h2>Confirm Your Payment</h2>
            <p>Enter the email you used to sign up for the waitlist.</p>
            <form onSubmit={handleEmailSubmit}>
              <input
                type="email"
                placeholder="your@email.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
              <button type="submit" className="btn-primary">
                Confirm Payment
              </button>
            </form>
          </div>
        )}

        <div className="footer-text">
          <p>Questions? <a href="mailto:hello@slateone.studio">Contact Support</a></p>
        </div>
      </div>
    </div>
  );
};

export default PaymentSuccessPage;
