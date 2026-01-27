# Admin Design System

Comprehensive design system for all admin pages to ensure visual consistency across the application.

---

## 🎨 Color Palette

### Dark Theme Base
```css
--bg-primary: #0f1419;           /* Main background */
--bg-card: rgba(255, 255, 255, 0.03);  /* Card backgrounds */
--bg-elevated: rgba(255, 255, 255, 0.05); /* Hover states */
```

### Text Colors
```css
--text-primary: #ffffff;         /* Headings, important text */
--text-secondary: rgba(255, 255, 255, 0.7); /* Body text */
--text-muted: rgba(255, 255, 255, 0.6);     /* Labels, hints */
--text-disabled: rgba(255, 255, 255, 0.5);  /* Disabled text */
```

### Borders
```css
--border-primary: rgba(255, 255, 255, 0.1);
--border-hover: rgba(255, 255, 255, 0.2);
--border-subtle: rgba(255, 255, 255, 0.05);
```

### Status Colors
```css
--success: #22c55e;              /* Green - approvals, success */
--error: #ef4444;                /* Red - rejections, errors */
--warning: #fb923c;              /* Orange - pending, warnings */
--info: #3b82f6;                 /* Blue - information */
```

### Brand Accent
```css
--accent-primary: #fb923c;       /* Orange - primary actions */
--accent-hover: #f97316;         /* Darker orange - hover state */
```

---

## 📐 Layout Structure

### Page Container
```css
.admin-page {
  min-height: 100vh;
  background: #0f1419;
  padding: 2rem;
}
```

### Header Pattern
All admin pages should follow this header structure:

```jsx
<div className="admin-header">
  <button onClick={() => navigate('/admin')} className="back-button">
    <ArrowLeft size={20} />
  </button>
  <div>
    <h1>Page Title</h1>
    <p className="subtitle">Page description</p>
  </div>
  <button onClick={refreshAction} className="btn-secondary">
    Refresh
  </button>
</div>
```

**Styles:**
```css
.admin-header {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 2rem;
  padding-bottom: 1.5rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.admin-header h1 {
  margin: 0;
  font-size: 2rem;
  font-weight: 700;
  color: #ffffff;
}

.admin-header .subtitle {
  margin: 0.25rem 0 0 0;
  font-size: 0.875rem;
  color: rgba(255, 255, 255, 0.6);
}
```

---

## 🔘 Buttons

### Back Button
```css
.back-button {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  color: rgba(255, 255, 255, 0.8);
}

.back-button:hover {
  background: rgba(255, 255, 255, 0.1);
  border-color: rgba(255, 255, 255, 0.2);
}
```

### Primary Button
```css
.btn-primary {
  padding: 0.625rem 1.25rem;
  background: #fb923c;
  color: white;
  border: none;
  border-radius: 8px;
  font-weight: 600;
  font-size: 0.875rem;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-primary:hover {
  background: #f97316;
}
```

### Secondary Button
```css
.btn-secondary {
  padding: 0.625rem 1.25rem;
  background: rgba(255, 255, 255, 0.05);
  color: rgba(255, 255, 255, 0.9);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  font-weight: 600;
  font-size: 0.875rem;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-secondary:hover {
  background: rgba(255, 255, 255, 0.1);
}
```

### Action Buttons
```css
/* Success/Approve */
.btn-success {
  background: #22c55e;
  color: white;
}

.btn-success:hover {
  background: #16a34a;
}

/* Danger/Reject */
.btn-danger {
  background: #ef4444;
  color: white;
}

.btn-danger:hover {
  background: #dc2626;
}
```

---

## 📊 Tables

### Standard Table Structure
```css
.data-table {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  overflow: hidden;
}

.data-table table {
  width: 100%;
  border-collapse: collapse;
}

.data-table thead {
  background: rgba(255, 255, 255, 0.05);
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.data-table th {
  padding: 1rem;
  text-align: left;
  font-size: 0.875rem;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.7);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.data-table td {
  padding: 1rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  color: #ffffff;
}

.data-table tbody tr:hover {
  background: rgba(255, 255, 255, 0.05);
}
```

---

## 📦 Cards & Containers

### Metric Card
```css
.metric-card {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  padding: 1.5rem;
  transition: all 0.2s;
}

.metric-card:hover {
  border-color: rgba(255, 255, 255, 0.2);
  background: rgba(255, 255, 255, 0.05);
}
```

### Action Card
```css
.action-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.75rem;
  padding: 1.5rem;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s;
  color: rgba(255, 255, 255, 0.9);
  font-weight: 600;
}

.action-card:hover {
  border-color: #fb923c;
  background: rgba(255, 255, 255, 0.05);
  box-shadow: 0 4px 12px rgba(251, 146, 60, 0.3);
  transform: translateY(-2px);
}
```

---

## 🏷️ Badges & Labels

### Status Badge
```css
.badge {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.25rem 0.75rem;
  border-radius: 6px;
  font-size: 0.75rem;
  font-weight: 600;
}

.badge.pending {
  background: rgba(251, 146, 60, 0.1);
  color: #fb923c;
  border: 1px solid rgba(251, 146, 60, 0.3);
}

.badge.success {
  background: rgba(34, 197, 94, 0.1);
  color: #22c55e;
  border: 1px solid rgba(34, 197, 94, 0.3);
}

.badge.error {
  background: rgba(239, 68, 68, 0.1);
  color: #ef4444;
  border: 1px solid rgba(239, 68, 68, 0.3);
}

.badge.urgent {
  background: #ef4444;
  color: white;
  animation: pulse 2s infinite;
}
```

---

## 🎭 Animations

### Pulse Animation
```css
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.7; }
}
```

### Slide Down
```css
@keyframes slideDown {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
```

### Spin (Loading)
```css
@keyframes spin {
  to { transform: rotate(360deg); }
}

.spinner {
  width: 48px;
  height: 48px;
  border: 4px solid rgba(255, 255, 255, 0.1);
  border-top-color: #fb923c;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}
```

---

## 🔔 Alert Banners

### Warning Alert
```css
.alert-banner {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem 1.5rem;
  border-radius: 12px;
  margin-bottom: 1.5rem;
  animation: slideDown 0.3s ease-out;
}

.alert-banner.warning {
  background: rgba(251, 146, 60, 0.1);
  border: 1px solid rgba(251, 146, 60, 0.3);
}

.alert-banner svg {
  flex-shrink: 0;
  color: #fb923c;
}

.alert-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.alert-content strong {
  color: #ffffff;
  font-weight: 600;
  font-size: 0.9375rem;
}

.alert-content span {
  color: rgba(255, 255, 255, 0.7);
  font-size: 0.875rem;
}
```

---

## 📱 Responsive Design

### Breakpoints
```css
/* Mobile */
@media (max-width: 768px) {
  .admin-page {
    padding: 1rem;
  }
  
  .admin-header {
    flex-wrap: wrap;
  }
  
  .admin-header h1 {
    font-size: 1.5rem;
  }
}

/* Tablet */
@media (max-width: 1024px) {
  .charts-grid {
    grid-template-columns: 1fr;
  }
}
```

---

## 🎯 Typography

### Headings
```css
h1 { font-size: 2rem; font-weight: 700; }
h2 { font-size: 1.5rem; font-weight: 600; }
h3 { font-size: 1.25rem; font-weight: 600; }
```

### Body Text
```css
body {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  font-size: 1rem;
  line-height: 1.5;
}
```

### Labels
```css
.label {
  font-size: 0.875rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: rgba(255, 255, 255, 0.7);
}
```

---

## ✅ Implementation Checklist

When creating a new admin page, ensure:

- [ ] Dark background (`#0f1419`)
- [ ] Header with back button, title, subtitle
- [ ] Consistent button styles (primary/secondary)
- [ ] Tables use dark theme with proper borders
- [ ] Cards have subtle backgrounds and borders
- [ ] Hover states on interactive elements
- [ ] Loading states with spinner
- [ ] Error states with red color
- [ ] Responsive design for mobile
- [ ] Proper spacing (2rem padding, 1rem gaps)
- [ ] Smooth transitions (0.2s)

---

## 📚 Component Examples

### Complete Page Template
```jsx
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import './AdminPage.css';

export default function AdminPage() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState(null);

  return (
    <div className="admin-page">
      {/* Header */}
      <div className="admin-header">
        <button onClick={() => navigate('/admin')} className="back-button">
          <ArrowLeft size={20} />
        </button>
        <div>
          <h1>Page Title</h1>
          <p className="subtitle">Page description</p>
        </div>
        <button onClick={loadData} className="btn-secondary">
          Refresh
        </button>
      </div>

      {/* Content */}
      {loading ? (
        <div className="loading-state">
          <div className="spinner"></div>
          <p>Loading...</p>
        </div>
      ) : (
        <div className="content">
          {/* Your content here */}
        </div>
      )}
    </div>
  );
}
```

---

## 🔄 Maintenance

This design system should be updated whenever:
- New components are added to admin pages
- Color schemes are adjusted
- New patterns emerge
- User feedback suggests improvements

Last updated: January 27, 2026
