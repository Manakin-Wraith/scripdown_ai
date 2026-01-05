# SlateOne (ScripDown AI) - Product Roadmap

A phased approach to delivering a focused, high-quality script breakdown platform.

---

## 🎯 Phase 1: Core MVP (Current)

**Goal**: Deliver the core value proposition — *AI-powered script breakdown with Stripboard export*.

### Features Included

| Feature | Status | Description |
|---------|--------|-------------|
| **Authentication** | ✅ Live | Login, Signup, Password Reset via Supabase Auth |
| **Script Upload** | ✅ Live | PDF upload with regex scene detection |
| **Script Library** | ✅ Live | List, view, delete scripts |
| **Scene Viewer** | ✅ Live | Master-detail layout with scene list and breakdown |
| **AI Scene Analysis** | ✅ Live | On-demand per-scene AI breakdown |
| **Stripboard** | ✅ Live | One-liner view with filtering and sorting |
| **Stripboard PDF Export** | ✅ Live | Download stripboard as PDF with metadata header |
| **Print Support** | ✅ Live | Browser-native print for stripboard |

### User Journey

```
Login/Signup → Upload PDF → View Script Library → Select Script
    → Browse Scenes → Analyze Scenes (AI) → View Breakdown
    → Open Stripboard → Print or Download PDF
```

### Technical Notes

- **Subscription**: Everyone gets "active" status (no enforcement)
- **Feature Flags**: `PHASE1_FREE_ACCESS = true` in both frontend and backend
- **Deferred Features**: removed from frontend UI

---

## 🔧 Phase 2: Polish & Export (Next)

**Goal**: Make the core experience production-ready with additional export capabilities.

### Planned Features

| Feature | Priority | Description |
|---------|----------|-------------|
| **Scene Breakdown PDF** | High | Export individual scene breakdowns as PDF |
| **CSV/Excel Export** | High | Export scene data for spreadsheets |
| **Scene Metadata Editing** | Medium | Edit scene headers (INT/EXT, setting, time) |
| **Script Metadata Display** | Medium | Show writer, contact info prominently |
| **Empty State Polish** | Medium | Consistent messaging across views |
| **Error Handling** | Medium | Graceful error states and recovery |

### Estimated Timeline
~2-3 weeks

---

## 👥 Phase 3: Collaboration

**Goal**: Enable team workflows for production teams.

### Planned Features

| Feature | Priority | Description |
|---------|----------|-------------|
| **Team Invites** | High | Invite team members to scripts |
| **Department Notes** | High | Add notes per scene by department |
| **Shared Script Access** | Medium | View-only and edit permissions |
| **Activity Feed** | Low | Track changes and updates |
| **Notifications** | Low | Email/in-app notifications |

### Estimated Timeline
~3-4 weeks

---

## 💰 Phase 4: Monetization & Advanced

**Goal**: Introduce paid tiers and power features.

### Planned Features

| Feature | Priority | Description |
|---------|----------|-------------|
| **Subscription Tiers** | High | Trial (14 days, 1 script) → Beta (R125, 6 months) |
| **Reports** | High | Scene breakdown, Day-out-of-Days, Location reports |
| **Scene Manager** | Medium | Split, merge, reorder scenes |
| **Script Locking** | Medium | Lock script for production with revision colors |
| **Shooting Script** | Medium | Generate shooting script from locked script |
| **Department Workspaces** | Low | Department-specific views and workflows |

### Estimated Timeline
~4-6 weeks

---

## 🚀 Future Considerations (Post-MVP)

- **Mobile App**: Tablet-first design for on-set use
- **Offline Support**: Service Worker + IndexedDB for offline access
- **Integrations**: Movie Magic Scheduling, Final Draft import
- **Advanced AI**: Character analysis, emotional arcs, budget estimation
- **Real-time Collaboration**: Live editing with WebSocket support

---

## Configuration Flags

### Backend (`backend/services/subscription_service.py`)
```python
PHASE1_FREE_ACCESS = True  # Set to False to enable subscription checks
```

### Frontend (`frontend/src/hooks/useSubscription.js`)
```javascript
const PHASE1_FREE_ACCESS = true;  // Set to false to enable subscription checks
```

---

## Files Modified for Phase 1 Simplification

### Frontend
- `App.jsx` - Simplified routes, deferred features commented out
- `Sidebar.jsx` - Added "Coming Soon" section for deferred features
- `ScriptHeader.jsx` - Simplified to Stripboard + Coming Soon indicators
- `Stripboard.jsx` - Added PDF download button
- `apiService.js` - Added `downloadStripboardPdf()` function
- `useSubscription.js` - Added Phase 1 bypass for active status

### Backend
- `script_routes.py` - Added `/scripts/<id>/stripboard/pdf` endpoint
- `subscription_service.py` - Added Phase 1 bypass for active status

---

## How to Enable Phase 4 (Subscriptions)

1. Set `PHASE1_FREE_ACCESS = False` in both:
   - `backend/services/subscription_service.py`
   - `frontend/src/hooks/useSubscription.js`

2. Uncomment deferred routes in `App.jsx`

3. Uncomment deferred imports in:
   - `Sidebar.jsx`
   - `ScriptHeader.jsx`

4. Test subscription flow with Yoco payment link

---

*Last Updated: December 2024*
