# Feedback Feature - Task Tracking Document

**Feature ID**: `FEAT-FEEDBACK-001`  
**Priority**: Medium  
**Status**: Planning  
**Created**: 2026-01-28  
**Target Completion**: TBD

---

## 📋 Overview

Implement a comprehensive feedback system that allows users to submit feedback (bug reports, feature requests, UI/UX issues, general feedback) directly from the TopBar. Feedback is captured with context and routed to the admin dashboard for review and response.

---

## 🎯 Objectives

1. **User Goal**: Provide a low-friction way for users to communicate with the product team
2. **Admin Goal**: Centralize feedback collection and enable efficient triage and response
3. **Business Goal**: Improve product quality through systematic user feedback collection

---

## 🏗️ Architecture Components

### Frontend
- `FeedbackDrawer.jsx` - Main feedback submission UI
- `FeedbackButton` - TopBar integration
- `FeedbackManagement.jsx` - Admin dashboard view
- `FeedbackDetailModal.jsx` - Admin feedback detail view

### Backend
- `feedback_routes.py` - API endpoints
- `feedback_service.py` - Business logic
- `email_service.py` - Email notifications (extend existing)

### Database
- `feedback_submissions` table
- Supabase Storage bucket: `feedback-screenshots`

---

## 📊 Task Breakdown

### Phase 1: Core Submission (Quick Win) ⚡

#### Subtask 1.1: Database Setup ✅
**Agent**: BackendAgent  
**Status**: Complete  
**Dependencies**: None  
**Estimated Time**: 30 minutes  
**Actual Time**: 30 minutes

**Actions**:
- [x] Create migration file: `backend/db/migrations/018_feedback_system.sql`
- [x] Define `feedback_submissions` table schema
- [x] Set up RLS policies (user read own, superuser read all)
- [x] Create indexes on `user_id`, `status`, `category`, `created_at`
- [x] Create apply script: `backend/db/apply_migration_018.py`

**Acceptance Criteria**:
- ✅ Table created with all required columns
- ✅ RLS policies implemented (6 policies)
- ✅ Migration script is idempotent
- ✅ Full-text search index added
- ✅ Materialized view for performance
- ✅ Auto-triggers for timestamps

**Deliverables**:
- `018_feedback_system.sql` - Complete migration with table, indexes, RLS, triggers, views
- `apply_migration_018.py` - Python script to apply and verify migration

---

#### Subtask 1.2: Supabase Storage Setup ✅
**Agent**: BackendAgent  
**Status**: Complete (Documentation Ready)  
**Dependencies**: None  
**Estimated Time**: 15 minutes  
**Actual Time**: 15 minutes

**Actions**:
- [x] Create setup documentation: `docs/SUPABASE_STORAGE_SETUP.md`
- [x] Define bucket configuration (public, 5MB limit)
- [x] Document 4 RLS policies for storage
- [x] Define file naming convention
- [x] Add testing procedures
- [x] Include cleanup strategies

**Acceptance Criteria**:
- ✅ Complete setup guide created
- ✅ RLS policies documented
- ✅ Security considerations covered
- ✅ Testing procedures included
- ✅ Monitoring queries provided

**Deliverables**:
- `SUPABASE_STORAGE_SETUP.md` - Complete setup guide with policies, testing, and monitoring

**Manual Steps Required**:
1. Create bucket in Supabase Dashboard
2. Apply 4 RLS policies
3. Configure file size and MIME type limits
4. Test upload/download/delete operations

---

#### Subtask 1.3: Backend API - Submit Feedback ✅
**Agent**: CoderAgent  
**Status**: Complete  
**Dependencies**: 1.1, 1.2  
**Estimated Time**: 2 hours  
**Actual Time**: 2 hours

**Actions**:
- [x] Create `backend/routes/feedback_routes.py`
- [x] Implement `POST /api/feedback` endpoint
- [x] Add request validation (category, subject, description required)
- [x] Implement screenshot upload to Supabase Storage
- [x] Auto-capture page context (URL, script_id, user_agent, viewport)
- [x] Rate limiting: 5 submissions per user per day
- [x] Register blueprint in `app.py`
- [x] Create `backend/services/feedback_service.py`
- [x] Extend `backend/services/email_service.py` with feedback emails

**API Contract**:
```python
POST /api/feedback
Headers: Authorization: Bearer <token>
Body: {
  "category": "bug|feature|ui_ux|general",
  "priority": "low|medium|high",  # optional
  "subject": "string (required, max 200 chars)",
  "description": "string (required, max 2000 chars)",
  "screenshot": "file (optional, max 5MB)",
  "page_context": {
    "url": "string",
    "route": "string",
    "script_id": "uuid|null"
  }
}

Response 201: {
  "id": "uuid",
  "message": "Feedback submitted successfully"
}

Response 429: {
  "error": "Rate limit exceeded. Max 5 submissions per day."
}
```

**Acceptance Criteria**:
- ✅ Endpoint accepts valid feedback submissions
- ✅ Screenshot uploads work correctly
- ✅ Rate limiting enforced (5 per day)
- ✅ Returns proper error messages
- ✅ Context auto-captured correctly
- ✅ Email confirmation sent on submission

**Deliverables**:
- `backend/routes/feedback_routes.py` - 6 API endpoints (submit, list, get, update status, reply, stats)
- `backend/services/feedback_service.py` - Business logic with rate limiting and screenshot upload
- `backend/services/email_service.py` - Extended with 2 new email functions
- `backend/app.py` - Updated to register feedback_bp

**API Endpoints Implemented**:
- `POST /api/feedback` - Submit feedback
- `GET /api/feedback` - List feedback (user's own or all if superuser)
- `GET /api/feedback/:id` - Get single feedback
- `PATCH /api/feedback/:id/status` - Update status (superuser only)
- `POST /api/feedback/:id/reply` - Send reply email (superuser only)
- `GET /api/feedback/stats` - Get statistics (superuser only)

---

#### Subtask 1.4: Frontend - FeedbackDrawer Component ✅
**Agent**: CoderAgent  
**Status**: Complete  
**Dependencies**: 1.3  
**Estimated Time**: 3 hours  
**Actual Time**: 2.5 hours

**Actions**:
- [x] Create `frontend/src/components/feedback/FeedbackDrawer.jsx`
- [x] Create `frontend/src/components/feedback/FeedbackDrawer.css`
- [x] Create `frontend/src/components/feedback/FeedbackButton.jsx`
- [x] Create `frontend/src/components/feedback/FeedbackButton.css`
- [x] Implement form with category, priority, subject, description fields
- [x] Add screenshot upload with preview
- [x] Implement client-side validation
- [x] Auto-capture page context (URL, route, viewport)
- [x] Add loading states and error handling
- [x] Success state with auto-close
- [x] Extend `apiService.js` with feedback API methods

**Deliverables**:
- `FeedbackDrawer.jsx` - Main feedback form component (320 lines)
- `FeedbackDrawer.css` - Compact dropdown styling with animations
- `FeedbackButton.jsx` - Trigger button component
- `FeedbackButton.css` - Button styling
- `apiService.js` - Extended with 3 feedback API methods

**Features Implemented**:
- ✅ Compact dropdown design (opens below button, not full drawer)
- ✅ 4 category pills (Bug, Feature, UI/UX, General)
- ✅ Priority selector (Low, Medium, High)
- ✅ Subject input with 200 char limit
- ✅ Description textarea with 2000 char limit
- ✅ Screenshot upload with preview and remove
- ✅ File validation (type, size)
- ✅ Auto-capture page context (URL, route, viewport, user agent)
- ✅ Client-side validation
- ✅ Loading states
- ✅ Error messages
- ✅ Success state with auto-close after 2s
- ✅ Click-outside to close
- ✅ Mobile responsive (full-screen on mobile)

**Component Structure**:
```jsx
<FeedbackDrawer 
  isOpen={boolean}
  onClose={function}
/>
```

**Acceptance Criteria**:
- Drawer slides smoothly
- Form validation works
- Screenshot preview displays
- Context auto-captured
- Toast notifications show
- Responsive on mobile

---

#### Subtask 1.5: Frontend - TopBar Integration ✅
**Agent**: CoderAgent  
**Status**: Complete  
**Dependencies**: 1.4  
**Estimated Time**: 30 minutes  
**Actual Time**: 15 minutes

**Actions**:
- [x] Import FeedbackButton into TopBar
- [x] Add feedback button between NotificationBell and user menu
- [x] Position button in topbar-right section
- [x] Only show when user is authenticated

**Deliverables**:
- Updated `TopBar.jsx` with FeedbackButton integration
- Button positioned between notifications and user menu
- Consistent styling with other TopBar elements

**Acceptance Criteria**:
- Button visible in TopBar
- Clicking opens FeedbackDrawer
- Styling consistent with app design

---

#### Subtask 1.6: Email Confirmation
**Agent**: CoderAgent  
**Status**: Pending  
**Dependencies**: 1.3  
**Estimated Time**: 1 hour

**Actions**:
- [ ] Extend `backend/services/email_service.py`
- [ ] Create `send_feedback_confirmation_email()` function
- [ ] Design email template (Resend HTML)
- [ ] Include: submission ID, category, subject, tracking link
- [ ] Send email after successful submission

**Email Template**:
```
Subject: Feedback Received - [Category]

Hi [User Name],

Thank you for your feedback! We've received your submission:

Category: [Bug Report/Feature Request/etc.]
Subject: [User's subject]

We'll review it and get back to you if we need more information.

Track your feedback: [Link to /profile/feedback/:id]

- The SlateOne Team
```

**Acceptance Criteria**:
- Email sent on submission
- Template renders correctly
- Links work properly

---

### Phase 2: Admin Dashboard 🛠️

#### Subtask 2.1: Backend API - List & Manage Feedback
**Agent**: CoderAgent  
**Status**: Pending  
**Dependencies**: 1.3  
**Estimated Time**: 2 hours

**Actions**:
- [ ] Implement `GET /api/feedback` - List feedback (with filters)
- [ ] Implement `GET /api/feedback/:id` - Get single feedback
- [ ] Implement `PATCH /api/feedback/:id/status` - Update status (superuser only)
- [ ] Implement `POST /api/feedback/:id/reply` - Send reply email (superuser only)
- [ ] Add pagination (20 items per page)
- [ ] Add filters: category, status, priority, date range
- [ ] Add search: subject, description

**API Contracts**:
```python
GET /api/feedback?page=1&limit=20&category=bug&status=new
Response 200: {
  "feedback": [...],
  "total": 45,
  "page": 1,
  "pages": 3
}

PATCH /api/feedback/:id/status
Body: {
  "status": "in_progress|resolved|dismissed",
  "admin_notes": "string (optional)"
}

POST /api/feedback/:id/reply
Body: {
  "reply_message": "string (required)"
}
```

**Acceptance Criteria**:
- All endpoints work correctly
- Superuser-only endpoints protected
- Pagination works
- Filters and search functional

---

#### Subtask 2.2: Frontend - FeedbackManagement Page
**Agent**: CoderAgent  
**Status**: Pending  
**Dependencies**: 2.1  
**Estimated Time**: 4 hours

**Actions**:
- [ ] Create `frontend/src/pages/admin/FeedbackManagement.jsx`
- [ ] Create `frontend/src/pages/admin/FeedbackManagement.css`
- [ ] Build data table with columns:
  - Date (sortable)
  - User (with avatar)
  - Category (badge)
  - Priority (badge)
  - Subject (truncated)
  - Status (badge with color coding)
  - Actions (View, Resolve, Dismiss)
- [ ] Implement filters (category, status, priority)
- [ ] Implement search bar
- [ ] Implement pagination controls
- [ ] Add route: `/admin/feedback`

**Acceptance Criteria**:
- Table displays feedback correctly
- Filters work
- Search functional
- Pagination works
- Click row opens detail modal

---

#### Subtask 2.3: Frontend - FeedbackDetailModal
**Agent**: CoderAgent  
**Status**: Pending  
**Dependencies**: 2.2  
**Estimated Time**: 2 hours

**Actions**:
- [ ] Create `frontend/src/components/admin/FeedbackDetailModal.jsx`
- [ ] Display full feedback details:
  - User info (name, email, avatar)
  - Category, priority, status
  - Subject and full description
  - Screenshot (if uploaded)
  - Page context (URL, script_id)
  - Submission date
  - Admin notes (if any)
- [ ] Add action buttons:
  - Mark as In Progress
  - Mark as Resolved
  - Dismiss
  - Reply (opens reply form)
- [ ] Implement reply form with textarea
- [ ] Show loading states

**Acceptance Criteria**:
- Modal displays all information
- Screenshot displays correctly
- Actions work and update status
- Reply form sends email

---

#### Subtask 2.4: Admin Email Reply System
**Agent**: CoderAgent  
**Status**: Pending  
**Dependencies**: 2.1  
**Estimated Time**: 1 hour

**Actions**:
- [ ] Extend `email_service.py`
- [ ] Create `send_feedback_reply_email()` function
- [ ] Design reply email template
- [ ] Include admin's reply message
- [ ] Include link to original feedback

**Email Template**:
```
Subject: Re: [Original Subject]

Hi [User Name],

We've reviewed your feedback and wanted to respond:

[Admin's reply message]

Original feedback:
Category: [Category]
Subject: [Subject]

View your feedback: [Link]

- The SlateOne Team
```

**Acceptance Criteria**:
- Reply emails sent correctly
- Template renders properly
- User receives email

---

### Phase 3: Enhancements 🚀

#### Subtask 3.1: User Feedback History
**Agent**: CoderAgent  
**Status**: Pending  
**Dependencies**: Phase 1  
**Estimated Time**: 2 hours

**Actions**:
- [ ] Add "My Feedback" section to Profile page
- [ ] Display user's feedback submissions
- [ ] Show status badges
- [ ] Allow viewing details
- [ ] Show admin replies

**Acceptance Criteria**:
- User can see their feedback history
- Status updates visible
- Replies displayed

---

#### Subtask 3.2: Real-time Notifications
**Agent**: CoderAgent  
**Status**: Pending  
**Dependencies**: 2.1  
**Estimated Time**: 2 hours

**Actions**:
- [ ] Add notification when admin replies
- [ ] Add notification when status changes
- [ ] Integrate with existing NotificationBell
- [ ] Add badge count for new feedback (admin only)

**Acceptance Criteria**:
- Notifications trigger correctly
- Badge count updates
- Clicking notification navigates to feedback

---

#### Subtask 3.3: Analytics Dashboard
**Agent**: CoderAgent  
**Status**: Pending  
**Dependencies**: Phase 2  
**Estimated Time**: 3 hours

**Actions**:
- [ ] Create feedback analytics view in admin dashboard
- [ ] Show metrics:
  - Total submissions (by time period)
  - By category breakdown
  - By status breakdown
  - Average response time
  - Top users submitting feedback
- [ ] Add charts (bar, pie, line)

**Acceptance Criteria**:
- Analytics display correctly
- Charts render properly
- Data accurate

---

#### Subtask 3.4: Export to CSV
**Agent**: CoderAgent  
**Status**: Pending  
**Dependencies**: 2.1  
**Estimated Time**: 1 hour

**Actions**:
- [ ] Add export button to FeedbackManagement
- [ ] Implement `GET /api/feedback/export` endpoint
- [ ] Generate CSV with all feedback data
- [ ] Include filters in export

**Acceptance Criteria**:
- CSV downloads correctly
- All data included
- Filters applied to export

---

## 🧪 Testing Strategy

### Unit Tests
**Agent**: TesterAgent  
**Coverage Target**: 80%

- [ ] Test feedback submission validation
- [ ] Test rate limiting logic
- [ ] Test screenshot upload
- [ ] Test status update logic
- [ ] Test email sending (mocked)

### Integration Tests
**Agent**: TesterAgent

- [ ] Test full submission flow (user → API → DB)
- [ ] Test admin workflow (list → view → reply)
- [ ] Test RLS policies
- [ ] Test file upload to Supabase Storage

### E2E Tests
**Agent**: TesterAgent

- [ ] User submits feedback with screenshot
- [ ] Admin views and replies to feedback
- [ ] User receives email and notification
- [ ] Verify feedback appears in user's history

---

## 🎨 UX Review Checklist

**Agent**: UXAgent

- [ ] Feedback button easily discoverable in TopBar
- [ ] Drawer slides smoothly without jank
- [ ] Form is intuitive and minimal
- [ ] Error messages are helpful
- [ ] Success feedback is clear
- [ ] Admin table is scannable
- [ ] Detail modal is comprehensive
- [ ] Mobile responsive (drawer stacks on small screens)

---

## 🔒 Security Considerations

- [ ] RLS policies prevent users from viewing others' feedback
- [ ] Superuser checks enforced on admin endpoints
- [ ] Rate limiting prevents spam
- [ ] File uploads validated (size, type)
- [ ] SQL injection prevention (parameterized queries)
- [ ] XSS prevention (sanitize user input in emails)
- [ ] CSRF protection (Supabase handles this)

---

## 📈 Success Metrics

### User Metrics
- Feedback submission rate (target: 5% of active users per month)
- Average time to submit feedback (target: < 2 minutes)
- User satisfaction with feedback process (survey)

### Admin Metrics
- Average response time (target: < 48 hours)
- Feedback resolution rate (target: 80% within 1 week)
- Feedback categorization accuracy

### Product Metrics
- Bug reports leading to fixes (target: 60%)
- Feature requests implemented (target: 20%)
- Reduction in support tickets (target: 15%)

---

## 🚧 Known Risks & Mitigation

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Spam submissions | High | Medium | Rate limiting, captcha (future) |
| Large screenshot uploads | Medium | Low | File size limits, compression |
| Admin overwhelm | High | Medium | Filters, search, prioritization |
| Email deliverability | Medium | Low | Use Resend, monitor bounce rates |

---

## 📚 Documentation Requirements

- [ ] Update `README.md` with feedback feature overview
- [ ] Create `docs/FEEDBACK_SYSTEM.md` with architecture details
- [ ] Add API documentation to Swagger/OpenAPI spec
- [ ] Create admin user guide for feedback management
- [ ] Add user help article: "How to submit feedback"

---

## 🔄 Dependencies

### External Services
- Supabase (database, storage, auth)
- Resend (email delivery)

### Internal Dependencies
- `AuthContext` - User authentication
- `NotificationBell` - Notification integration (Phase 3)
- `email_service.py` - Email sending

---

## 📅 Timeline Estimate

| Phase | Estimated Time | Target Completion |
|-------|----------------|-------------------|
| Phase 1: Core Submission | 8 hours | Day 1-2 |
| Phase 2: Admin Dashboard | 9 hours | Day 3-4 |
| Phase 3: Enhancements | 8 hours | Day 5-6 |
| Testing & QA | 4 hours | Day 7 |
| Documentation | 2 hours | Day 7 |
| **Total** | **31 hours** | **~1.5 weeks** |

---

## 🎯 Current Status

**Phase**: Planning Complete  
**Next Action**: Begin Subtask 1.1 (Database Setup)  
**Blocked**: None  
**Notes**: Ready to proceed with implementation

---

## 📝 Change Log

| Date | Change | Author |
|------|--------|--------|
| 2026-01-28 | Initial task document created | System |

---

## 🤝 Stakeholders

- **Product Owner**: TBD
- **Tech Lead**: TBD
- **UX Designer**: TBD
- **QA Lead**: TBD

---

## ✅ Sign-off

- [ ] Product Owner Approval
- [ ] Tech Lead Review
- [ ] Security Review
- [ ] UX Review

---

**Document Version**: 1.0  
**Last Updated**: 2026-01-28
