import { useState } from 'react';
import { getAnalyticsOverview } from '../../services/apiService';

/**
 * Simple test page to verify admin API endpoints
 * Access at: http://localhost:5173/admin/test
 */
export default function AdminTestPage() {
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  const testAPI = async () => {
    setLoading(true);
    setError(null);
    setData(null);

    try {
      console.log('Testing admin API...');
      const response = await getAnalyticsOverview();
      console.log('API Response:', response);
      setData(response);
    } catch (err) {
      console.error('API Error:', err);
      setError(err.response?.data?.error || err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      padding: '2rem',
      maxWidth: '800px',
      margin: '0 auto',
      fontFamily: 'system-ui, -apple-system, sans-serif'
    }}>
      <h1 style={{ marginBottom: '1rem' }}>Admin API Test</h1>
      
      <button
        onClick={testAPI}
        disabled={loading}
        style={{
          padding: '0.75rem 1.5rem',
          background: loading ? '#ccc' : '#4f46e5',
          color: 'white',
          border: 'none',
          borderRadius: '8px',
          fontSize: '1rem',
          fontWeight: '600',
          cursor: loading ? 'not-allowed' : 'pointer',
          marginBottom: '2rem'
        }}
      >
        {loading ? 'Testing...' : 'Test Analytics API'}
      </button>

      {error && (
        <div style={{
          padding: '1rem',
          background: '#fee',
          border: '1px solid #fcc',
          borderRadius: '8px',
          marginBottom: '1rem'
        }}>
          <h3 style={{ margin: '0 0 0.5rem 0', color: '#c00' }}>Error</h3>
          <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>{error}</pre>
        </div>
      )}

      {data && (
        <div style={{
          padding: '1rem',
          background: '#efe',
          border: '1px solid #cfc',
          borderRadius: '8px'
        }}>
          <h3 style={{ margin: '0 0 0.5rem 0', color: '#060' }}>Success!</h3>
          <pre style={{
            margin: 0,
            whiteSpace: 'pre-wrap',
            fontSize: '0.875rem',
            background: 'white',
            padding: '1rem',
            borderRadius: '4px',
            overflow: 'auto'
          }}>
            {JSON.stringify(data, null, 2)}
          </pre>
        </div>
      )}

      <div style={{
        marginTop: '2rem',
        padding: '1rem',
        background: '#f5f5f5',
        borderRadius: '8px'
      }}>
        <h3 style={{ marginTop: 0 }}>Instructions</h3>
        <ol style={{ lineHeight: '1.6' }}>
          <li>Make sure backend is running: <code>cd backend && python app.py</code></li>
          <li>Make sure you have superuser access in database</li>
          <li>Make sure you're logged in</li>
          <li>Click "Test Analytics API" button above</li>
        </ol>
        
        <h4>Expected Response:</h4>
        <pre style={{
          background: 'white',
          padding: '1rem',
          borderRadius: '4px',
          fontSize: '0.875rem'
        }}>
{`{
  "success": true,
  "data": {
    "global_stats": { ... },
    "subscription_metrics": { ... }
  }
}`}
        </pre>
      </div>
    </div>
  );
}
