import { Navigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { useState, useEffect } from 'react';
import { supabase } from '../../lib/supabase';

/**
 * AdminRoute - Protected route component for superuser-only pages
 * 
 * Usage:
 *   <Route path="/admin/*" element={<AdminRoute><AdminDashboard /></AdminRoute>} />
 */
export default function AdminRoute({ children }) {
  const { user, loading: authLoading } = useAuth();
  const [isSuperuser, setIsSuperuser] = useState(false);
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    async function checkSuperuser() {
      if (!user) {
        setChecking(false);
        return;
      }

      try {
        const { data, error } = await supabase
          .from('profiles')
          .select('is_superuser')
          .eq('id', user.id)
          .single();

        if (error) throw error;

        setIsSuperuser(data?.is_superuser === true);
      } catch (error) {
        console.error('Error checking superuser status:', error);
        setIsSuperuser(false);
      } finally {
        setChecking(false);
      }
    }

    checkSuperuser();
  }, [user]);

  // Show loading state while checking auth and superuser status
  if (authLoading || checking) {
    return (
      <div style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        height: '100vh',
        background: 'var(--gray-50)'
      }}>
        <div style={{ textAlign: 'center' }}>
          <div className="spinner" style={{
            width: '40px',
            height: '40px',
            border: '4px solid var(--gray-200)',
            borderTop: '4px solid var(--primary-600)',
            borderRadius: '50%',
            animation: 'spin 1s linear infinite',
            margin: '0 auto 1rem'
          }}></div>
          <p style={{ color: 'var(--gray-600)' }}>Verifying access...</p>
        </div>
      </div>
    );
  }

  // Redirect to login if not authenticated
  if (!user) {
    return <Navigate to="/login" replace />;
  }

  // Show access denied if not superuser
  if (!isSuperuser) {
    return (
      <div style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        height: '100vh',
        background: 'var(--gray-50)'
      }}>
        <div style={{
          textAlign: 'center',
          padding: '2rem',
          background: 'white',
          borderRadius: '12px',
          boxShadow: '0 4px 6px rgba(0,0,0,0.1)',
          maxWidth: '400px'
        }}>
          <div style={{
            fontSize: '48px',
            marginBottom: '1rem'
          }}>🔒</div>
          <h2 style={{
            fontSize: '1.5rem',
            fontWeight: '700',
            color: 'var(--gray-900)',
            marginBottom: '0.5rem'
          }}>Access Denied</h2>
          <p style={{
            color: 'var(--gray-600)',
            marginBottom: '1.5rem'
          }}>
            You don't have permission to access this area.
          </p>
          <button
            onClick={() => window.location.href = '/scripts'}
            style={{
              padding: '0.75rem 1.5rem',
              background: 'var(--primary-600)',
              color: 'white',
              border: 'none',
              borderRadius: '8px',
              fontSize: '1rem',
              fontWeight: '600',
              cursor: 'pointer'
            }}
          >
            Return to Dashboard
          </button>
        </div>
      </div>
    );
  }

  // User is authenticated and is superuser
  return children;
}
