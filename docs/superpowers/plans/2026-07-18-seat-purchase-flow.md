# Seat Purchase Flow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the seat-pool overbooking race and connect the purchase flow to the invite flow — both entry points (proactive Billing purchase, reactive purchase-when-blocked from the invite modal) end with the Owner able to send a working invite.

**Architecture:** Backend: one function changes (`_fetch_seats_used` counts pending invites, not just accepted memberships). Frontend: a small sessionStorage-backed draft utility carries an in-progress invite across the PayFast redirect (which leaves and re-enters the SPA), consumed by a resume flow wired through `PaymentResultPage` → `ScriptHeader` → `TeamDrawer` → `InviteModal`.

**Tech Stack:** Flask + Supabase (backend), React 18 + Vite + react-router-dom + axios (frontend). No frontend test framework exists in this repo — frontend tasks are verified via `npm run build` plus manual browser walkthroughs, not automated tests.

## Global Constraints

- Backend: gate correctness on `pytest tests/` (per `CLAUDE.md`); `npm run lint` is broken repo-wide, so frontend is gated on `npm run build` only (per project memory).
- All backend calls from the frontend must go through the single `frontend/src/services/apiService.js` axios instance — no per-feature fetch/axios instances (per `CLAUDE.md`).
- Server is always the price/quantity/entitlement authority — the frontend never computes or trusts its own seat counts; it only reacts to what `/api/billing/entitlement` and `/api/scripts/<id>/invites` return.
- No new database tables or columns — this plan changes query logic and frontend flow only, per the approved design's "Out of scope" section (no per-seat assignment records).

---

### Task 1: Fix `_fetch_seats_used` to count pending invites, not just accepted memberships

**Files:**
- Modify: `backend/services/entitlement_service.py:47-52` (the function is currently at a nearby line but the docstring calls out `_fetch_seats_used` at line ~55 — locate by function name, not line number, since Task order may shift line numbers)
- Test: `backend/tests/test_entitlement_service.py`

**Interfaces:**
- Consumes: nothing new — `get_supabase_admin()` (already imported in this file), `datetime.now(timezone.utc)` (already imported).
- Produces: `_fetch_seats_used(owner_id: str) -> int` — same signature as today, callers (`get_entitlement`) are unaffected.

**Context.** Today `_fetch_seats_used` only counts *accepted* `script_members` rows. A pending `script_invites` row (status `'pending'`, not yet accepted) is invisible to the seat count, so multiple pending invites can each pass the `seats_used < seats_paid` check in `create_invite` before any of them are accepted — overbooking the pool. The fix: count distinct people across pending invites (matched by email, excluding expired ones) *and* accepted memberships (matched by user_id), deduped so a person who is pending on one script and already an accepted member on another (same owner) counts once.

- [ ] **Step 1: Write the failing tests**

Replace the existing `test_fetch_seats_used_dedupes_by_user_not_membership_row` test (it only mocks a single `script_members` table call; the new implementation calls `script_members`, then `script_invites`, and conditionally `profiles`) and add new cases. Add this block to `backend/tests/test_entitlement_service.py`, replacing the old test of the same name:

```python
class _FakeSeatsAdmin:
    """Routes get_supabase_admin().table(name) calls by table name for
    _fetch_seats_used tests. Each table's canned rows are passed in."""

    def __init__(self, members=None, invites=None, profiles=None):
        self._data = {
            'script_members': members or [],
            'script_invites': invites or [],
            'profiles': profiles or [],
        }

    def table(self, name):
        return _FakeSeatsQuery(self._data[name])


class _FakeSeatsQuery:
    def __init__(self, rows):
        self._rows = rows

    def select(self, *a, **k):
        return self

    def eq(self, *a, **k):
        return self

    def gt(self, *a, **k):
        return self

    def in_(self, *a, **k):
        return self

    def execute(self):
        class Resp:
            data = self._rows
        return Resp()


def test_fetch_seats_used_dedupes_by_user_not_membership_row(monkeypatch):
    # A single person invited to 3 scripts must consume 1 seat, not 3.
    admin = _FakeSeatsAdmin(members=[
        {'user_id': 'p1'}, {'user_id': 'p1'}, {'user_id': 'p1'},
    ])
    monkeypatch.setattr(es, "get_supabase_admin", lambda: admin)
    assert es._fetch_seats_used('owner1') == 1


def test_fetch_seats_used_counts_pending_invite(monkeypatch):
    # A pending (not yet accepted) invite must already reserve a seat.
    admin = _FakeSeatsAdmin(
        members=[],
        invites=[{'email': 'new@x.com'}],
    )
    monkeypatch.setattr(es, "get_supabase_admin", lambda: admin)
    assert es._fetch_seats_used('owner1') == 1


def test_fetch_seats_used_counts_pending_and_accepted_together(monkeypatch):
    admin = _FakeSeatsAdmin(
        members=[{'user_id': 'accepted1'}],
        invites=[{'email': 'pending@x.com'}],
        profiles=[{'id': 'accepted1', 'email': 'accepted1@x.com'}],
    )
    monkeypatch.setattr(es, "get_supabase_admin", lambda: admin)
    assert es._fetch_seats_used('owner1') == 2


def test_fetch_seats_used_dedupes_pending_invite_already_accepted_elsewhere(monkeypatch):
    # Same person: accepted on one script, still has an unrelated pending
    # invite row lingering (e.g. re-invited to a second script under the
    # same owner before the first invite's status caught up). Must count
    # as one seat, not two.
    admin = _FakeSeatsAdmin(
        members=[{'user_id': 'jane_id'}],
        invites=[{'email': 'jane@x.com'}],
        profiles=[{'id': 'jane_id', 'email': 'jane@x.com'}],
    )
    monkeypatch.setattr(es, "get_supabase_admin", lambda: admin)
    assert es._fetch_seats_used('owner1') == 1


def test_fetch_seats_used_email_match_is_case_insensitive(monkeypatch):
    admin = _FakeSeatsAdmin(
        members=[{'user_id': 'jane_id'}],
        invites=[{'email': 'JANE@X.COM'}],
        profiles=[{'id': 'jane_id', 'email': 'jane@x.com'}],
    )
    monkeypatch.setattr(es, "get_supabase_admin", lambda: admin)
    assert es._fetch_seats_used('owner1') == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && venv/bin/python -m pytest tests/test_entitlement_service.py -v -k fetch_seats_used`
Expected: FAIL — `test_fetch_seats_used_counts_pending_invite` and the two dedupe/case-insensitive tests fail (function doesn't query `script_invites` yet); the membership-dedupe test still passes since the old code path handles it, but will break once you swap in `_FakeSeatsAdmin` if the old function only calls `.table()` once — confirm by running before editing.

- [ ] **Step 3: Implement the fix**

Replace `_fetch_seats_used` in `backend/services/entitlement_service.py`:

```python
def _fetch_seats_used(owner_id: str) -> int:
    """
    Seats are billed per team MEMBER (per person), not per membership row
    or per invite. A pending invite reserves a seat immediately — this is
    what prevents overbooking: without it, several pending invites could
    each pass the seats_used < seats_paid check before any of them were
    accepted. Accepting an invite is a no-op for this count; the person
    just moves from the pending half of the tally to the accepted half.

    `script_members` is a per-(script, user) table, so the same person
    invited to three scripts must consume one seat, not three. Pending
    invites are keyed by email (the invitee has no user_id yet); accepted
    memberships are keyed by user_id — so a person pending on one script
    and already accepted on another (same owner) is deduped by matching
    the pending invite's email against `profiles.email` for the accepted
    user_ids. supabase-py has no count-distinct, so dedupe in Python.
    """
    admin = get_supabase_admin()
    now = datetime.now(timezone.utc).isoformat()

    members_resp = admin.table('script_members').select('user_id').eq(
        'invited_by', owner_id
    ).execute()
    accepted_ids = {row['user_id'] for row in (members_resp.data or [])}

    invites_resp = admin.table('script_invites').select('email').eq(
        'invited_by', owner_id
    ).eq('status', 'pending').gt('expires_at', now).execute()
    pending_emails = {
        row['email'].strip().lower()
        for row in (invites_resp.data or []) if row.get('email')
    }

    if not pending_emails:
        return len(accepted_ids)

    accepted_emails = set()
    if accepted_ids:
        profiles_resp = admin.table('profiles').select('id, email').in_(
            'id', list(accepted_ids)
        ).execute()
        accepted_emails = {
            row['email'].strip().lower()
            for row in (profiles_resp.data or []) if row.get('email')
        }

    new_pending = pending_emails - accepted_emails
    return len(accepted_ids) + len(new_pending)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && venv/bin/python -m pytest tests/test_entitlement_service.py -v -k fetch_seats_used`
Expected: PASS — all 5 tests green.

- [ ] **Step 5: Run the full backend suite to confirm no regressions**

Run: `cd backend && venv/bin/python -m pytest tests/ -q`
Expected: all tests pass (389+ tests, matching pre-change baseline plus the new ones).

- [ ] **Step 6: Commit**

```bash
cd backend
git add services/entitlement_service.py tests/test_entitlement_service.py
git commit -m "fix(billing): count pending invites toward the seat limit

Prevents overbooking: previously seats_used only counted accepted
memberships, so several pending invites could each pass the
seats_used < seats_paid check before any were accepted."
```

---

### Task 2: Add a sessionStorage-backed pending-invite-draft utility

**Files:**
- Create: `frontend/src/utils/pendingSeatInviteDraft.js`

**Interfaces:**
- Consumes: nothing (uses only browser `sessionStorage`).
- Produces:
  - `stashPendingSeatInviteDraft({ scriptId, email, departmentCode, role })` — `void`
  - `readPendingSeatInviteDraft()` — returns `{ scriptId, email, departmentCode, role } | null`
  - `clearPendingSeatInviteDraft()` — `void`

**Context.** PayFast checkout is a full-page redirect off-origin and back — it leaves and re-enters the SPA, so an in-progress invite form (email/department/role) can't be held in React state across it. `sessionStorage` survives the round trip within the same tab. This utility is the single place that key name and shape live, since three components (`InviteModal`, `PaymentResultPage`, `TeamDrawer`) will read or write it.

- [ ] **Step 1: Write the file**

```javascript
// Carries an in-progress team invite across the PayFast checkout redirect,
// which leaves and re-enters the SPA (so React state alone can't survive it).
const STORAGE_KEY = 'slateone_pending_seat_invite_draft';

export function stashPendingSeatInviteDraft({ scriptId, email, departmentCode, role }) {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify({ scriptId, email, departmentCode, role }));
}

export function readPendingSeatInviteDraft() {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    try {
        return JSON.parse(raw);
    } catch {
        return null;
    }
}

export function clearPendingSeatInviteDraft() {
    sessionStorage.removeItem(STORAGE_KEY);
}
```

- [ ] **Step 2: Verify manually**

Run: `cd frontend && node -e "
global.sessionStorage = (() => { const m = new Map(); return { setItem: (k,v)=>m.set(k,v), getItem: (k)=>m.get(k)??null, removeItem: (k)=>m.delete(k) }; })();
import('./src/utils/pendingSeatInviteDraft.js').then(async (mod) => {
  console.log('empty read:', mod.readPendingSeatInviteDraft());
  mod.stashPendingSeatInviteDraft({ scriptId: 's1', email: 'a@b.com', departmentCode: 'costume', role: 'member' });
  console.log('after stash:', mod.readPendingSeatInviteDraft());
  mod.clearPendingSeatInviteDraft();
  console.log('after clear:', mod.readPendingSeatInviteDraft());
});
"`
Expected output:
```
empty read: null
after stash: { scriptId: 's1', email: 'a@b.com', departmentCode: 'costume', role: 'member' }
after clear: null
```

- [ ] **Step 3: Commit**

```bash
cd frontend
git add src/utils/pendingSeatInviteDraft.js
git commit -m "feat(billing): add pending-seat-invite-draft sessionStorage utility"
```

---

### Task 3: Add `createInvite` to `apiService.js`

**Files:**
- Modify: `frontend/src/services/apiService.js` (add after `createCheckout`, around line 2226)

**Interfaces:**
- Consumes: the shared `api` axios instance already defined in this file (handles auth headers automatically via its request interceptor).
- Produces: `createInvite(scriptId, { email, departmentCode, role })` — returns the parsed response body (`{ invite: {...} }`) on success; throws an axios error with `.response.status` and `.response.data` on failure (same shape every other function in this file already produces).

**Context.** `InviteModal.jsx` currently does a raw `fetch` with a manually-fetched Supabase session token, bypassing the shared `api` instance — inconsistent with the "all backend calls go through `apiService.js`" rule, and it means 402 detection in Task 4 would need bespoke fetch-response handling instead of the standard axios error shape every other call in this codebase already uses. Since Task 4 is rewriting this call path anyway to add 402 handling, this is the natural point to route it through `apiService.js`.

- [ ] **Step 1: Add the function**

Add to `frontend/src/services/apiService.js`, directly after the existing `createCheckout` function (before the `export default api;` line):

```javascript
export const createInvite = async (scriptId, { email, departmentCode, role }) => {
    const response = await api.post(`/api/scripts/${scriptId}/invites`, {
        email,
        department_code: departmentCode,
        role,
    });
    return response.data;
};
```

- [ ] **Step 2: Verify the build still compiles**

Run: `cd frontend && npm run build`
Expected: build succeeds with no new errors (this function isn't consumed yet — Task 4 wires it in).

- [ ] **Step 3: Commit**

```bash
cd frontend
git add src/services/apiService.js
git commit -m "feat(billing): add createInvite to apiService"
```

---

### Task 4: InviteModal — 402 handling, buy-seats CTA, and resume-from-draft

**Files:**
- Modify: `frontend/src/components/team/InviteModal.jsx`

**Interfaces:**
- Consumes:
  - `createInvite(scriptId, { email, departmentCode, role })` from Task 3
  - `createCheckout(chargeType, quantity)` from `apiService.js` (already exists, used by `BillingPage.jsx`)
  - `stashPendingSeatInviteDraft`, `clearPendingSeatInviteDraft` from Task 2
- Produces: `InviteModal` now accepts an additional optional prop `initialDraft: { email, departmentCode, role } | null` — when present, the form opens pre-filled with those values instead of blank. This is what Task 7's auto-open wiring will pass in.

**Context.** Today, submitting the invite form on a seat-exhausted account throws inside the raw `fetch` call, is caught, and shown only as a generic error toast — a dead end. Per the approved design (§3 reactive entry point), a `402 { code: 'no_seats_available' }` response should instead show a "buy seats" panel with a quantity picker; buying stashes the current form values as a draft (so they aren't lost across the PayFast redirect) before navigating to checkout.

- [ ] **Step 1: Replace the raw fetch calls and add 402 handling**

Replace the full contents of `frontend/src/components/team/InviteModal.jsx` with:

```jsx
/**
 * InviteModal - Send team invitations
 *
 * Allows script owners to invite team members by email
 * with department assignment. If the account has no free seats,
 * offers to buy more before retrying — see handleSubmit's 402 branch.
 */

import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
    Mail,
    Users,
    Copy,
    Check,
    Send,
    Link as LinkIcon,
    Lock,
    Sparkles,
    CreditCard
} from 'lucide-react';
import { useToast } from '../../context/ToastContext';
import { useEntitlement } from '../../hooks/useEntitlement';
import { getDepartments, createInvite, createCheckout } from '../../services/apiService';
import { stashPendingSeatInviteDraft } from '../../utils/pendingSeatInviteDraft';
import { Spinner, Button, Modal } from '../ui';
import './InviteModal.css';

const ROLES = [
    { value: 'member', label: 'Member', description: 'Can view and add notes' },
    { value: 'admin', label: 'Admin', description: 'Can manage team and settings' },
    { value: 'viewer', label: 'Viewer', description: 'View only access' },
];

const postToPayFast = ({ process_url, fields }) => {
    // PayFast requires a real form POST, not fetch.
    const form = document.createElement('form');
    form.method = 'POST';
    form.action = process_url;
    Object.entries(fields).forEach(([name, value]) => {
        const input = document.createElement('input');
        input.type = 'hidden';
        input.name = name;
        input.value = value;
        form.appendChild(input);
    });
    document.body.appendChild(form);
    form.submit();
};

const InviteModal = ({ isOpen, onClose, scriptId, scriptTitle, initialDraft = null }) => {
    const toast = useToast();
    const { entitlement } = useEntitlement();

    const [email, setEmail] = useState('');
    const [department, setDepartment] = useState('');
    const [role, setRole] = useState('member');
    const [loading, setLoading] = useState(false);
    const [inviteResult, setInviteResult] = useState(null);
    const [copied, setCopied] = useState(false);
    const [departments, setDepartments] = useState([]);
    const [seatsExhausted, setSeatsExhausted] = useState(false);
    const [seatQuantity, setSeatQuantity] = useState(1);
    const [buyingSeats, setBuyingSeats] = useState(false);

    const hasTeamAccess = entitlement?.can_use_teams ?? false;

    useEffect(() => {
        const fetchDepartments = async () => {
            try {
                const data = await getDepartments();
                if (data.departments) {
                    setDepartments(data.departments);
                }
            } catch (error) {
                console.error('Error fetching departments:', error);
            }
        };
        fetchDepartments();
    }, []);

    // Reset form when modal opens, restoring a stashed draft if one was
    // handed in (the Owner is resuming an invite after buying seats).
    useEffect(() => {
        if (!isOpen) return;
        setEmail(initialDraft?.email ?? '');
        setDepartment(initialDraft?.departmentCode ?? '');
        setRole(initialDraft?.role ?? 'member');
        setInviteResult(null);
        setCopied(false);
        setSeatsExhausted(false);
        setSeatQuantity(1);
    }, [isOpen, initialDraft]);

    const handleSubmit = async (e) => {
        e.preventDefault();

        if (!email || !department) {
            toast.error('Error', 'Please fill in all fields');
            return;
        }

        setLoading(true);
        setSeatsExhausted(false);

        try {
            const data = await createInvite(scriptId, { email, departmentCode: department, role });
            setInviteResult(data.invite);
            toast.success('Success', 'Invite created successfully!');
        } catch (error) {
            if (error.response?.status === 402 && error.response?.data?.code === 'no_seats_available') {
                setSeatsExhausted(true);
            } else {
                console.error('Error creating invite:', error);
                toast.error('Error', error.response?.data?.error || error.message);
            }
        } finally {
            setLoading(false);
        }
    };

    const handleBuySeats = async () => {
        setBuyingSeats(true);
        try {
            stashPendingSeatInviteDraft({
                scriptId,
                email,
                departmentCode: department,
                role,
            });
            const checkout = await createCheckout('tier_2_seats', seatQuantity);
            postToPayFast(checkout);
        } catch (error) {
            console.error('Error starting seat checkout:', error);
            toast.error('Error', 'Could not start checkout. Please try again.');
            setBuyingSeats(false);
        }
    };

    const copyInviteLink = async () => {
        if (!inviteResult?.invite_url) return;

        try {
            await navigator.clipboard.writeText(inviteResult.invite_url);
            setCopied(true);
            toast.success('Copied', 'Link copied to clipboard!');
            setTimeout(() => setCopied(false), 2000);
        } catch (error) {
            toast.error('Error', 'Failed to copy link');
        }
    };

    const sendAnotherInvite = () => {
        setEmail('');
        setDepartment('');
        setRole('member');
        setInviteResult(null);
        setCopied(false);
        setSeatsExhausted(false);
    };

    // If no team access, show the Tier 2 upsell rather than a disabled button.
    if (!hasTeamAccess) {
        return (
            <Modal
                isOpen={isOpen}
                onClose={onClose}
                size="md"
                title={
                    <div className="header-content">
                        <Users size={24} />
                        <div>
                            <h2>Invite Team Member</h2>
                            <p className="script-name">{scriptTitle}</p>
                        </div>
                    </div>
                }
            >
                <div className="invite-locked">
                    <div className="locked-content">
                        <div className="locked-icon">
                            <Lock size={32} />
                        </div>
                        <h3>Team Collaboration Locked</h3>
                        <p>Team invites require the Annual Team License. Subscribe to invite members and collaborate on your scripts.</p>
                        <Link to="/billing" className="upgrade-btn">
                            <Sparkles size={18} />
                            Get the Annual Team License
                        </Link>
                    </div>
                </div>
            </Modal>
        );
    }

    return (
        <Modal
            isOpen={isOpen}
            onClose={onClose}
            size="md"
            title={
                <div className="header-content">
                    <Users size={24} />
                    <div>
                        <h2>Invite Team Member</h2>
                        <p className="script-name">{scriptTitle}</p>
                    </div>
                </div>
            }
        >
            {seatsExhausted ? (
                <div className="invite-locked">
                    <div className="locked-content">
                        <div className="locked-icon">
                            <CreditCard size={32} />
                        </div>
                        <h3>All paid seats are in use</h3>
                        <p>Buy another seat to invite <strong>{email}</strong> as <strong>{role}</strong>. You'll come right back here to send the invite once it's confirmed.</p>
                        <label htmlFor="seat-qty">Seats to buy</label>
                        <select
                            id="seat-qty"
                            value={seatQuantity}
                            onChange={(e) => setSeatQuantity(Number(e.target.value))}
                        >
                            {[1, 2, 3, 5, 10].map((n) => <option key={n} value={n}>{n}</option>)}
                        </select>
                        <button className="submit-btn" disabled={buyingSeats} onClick={handleBuySeats}>
                            {buyingSeats ? <Spinner size={18} /> : <CreditCard size={18} />}
                            {buyingSeats ? 'Starting checkout...' : `Buy ${seatQuantity} seat${seatQuantity > 1 ? 's' : ''}`}
                        </button>
                        <button className="link-btn" onClick={() => setSeatsExhausted(false)}>
                            Back
                        </button>
                    </div>
                </div>
            ) : !inviteResult ? (
                <form onSubmit={handleSubmit} className="invite-form">
                    {/* Email Input */}
                    <div className="form-group">
                        <label>
                            <Mail size={16} />
                            Email Address
                        </label>
                        <input
                            type="email"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            placeholder="teammate@example.com"
                            required
                        />
                    </div>

                    {/* Department Selection */}
                    <div className="form-group">
                        <label>
                            <Users size={16} />
                            Department
                        </label>
                        <div className="department-grid">
                            {departments.map(dept => (
                                <button
                                    key={dept.code}
                                    type="button"
                                    className={`department-option ${department === dept.code ? 'selected' : ''}`}
                                    onClick={() => setDepartment(dept.code)}
                                    style={{
                                        '--dept-color': dept.color,
                                        borderColor: department === dept.code ? dept.color : undefined
                                    }}
                                >
                                    <span className="dept-dot" style={{ backgroundColor: dept.color }} />
                                    {dept.name}
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* Role Selection */}
                    <div className="form-group">
                        <label>Role</label>
                        <div className="role-options">
                            {ROLES.map(r => (
                                <label key={r.value} className={`role-option ${role === r.value ? 'selected' : ''}`}>
                                    <input
                                        type="radio"
                                        name="role"
                                        value={r.value}
                                        checked={role === r.value}
                                        onChange={(e) => setRole(e.target.value)}
                                    />
                                    <div className="role-content">
                                        <span className="role-name">{r.label}</span>
                                        <span className="role-desc">{r.description}</span>
                                    </div>
                                </label>
                            ))}
                        </div>
                    </div>

                    {/* Submit Button */}
                    <button type="submit" className="submit-btn" disabled={loading || !email || !department}>
                        {loading ? (
                            <>
                                <Spinner size={18} />
                                Creating Invite...
                            </>
                        ) : (
                            <>
                                <Send size={18} />
                                Create Invite Link
                            </>
                        )}
                    </button>
                </form>
            ) : (
                <div className="invite-success">
                    <div className="success-icon">
                        <Check size={32} />
                    </div>
                    <h3>Invite Sent!</h3>
                    <p>
                        {inviteResult.email_sent
                            ? <>We emailed the invite to <strong>{inviteResult.email}</strong> as <strong>{inviteResult.department}</strong>. You can also share the link below.</>
                            : <>Share this link with <strong>{inviteResult.email}</strong> to invite them as <strong>{inviteResult.department}</strong></>}
                    </p>

                    <div className="invite-link-box">
                        <LinkIcon size={16} />
                        <input type="text" value={inviteResult.invite_url} readOnly />
                        <button className="copy-btn" onClick={copyInviteLink}>
                            {copied ? <Check size={16} /> : <Copy size={16} />}
                            {copied ? 'Copied!' : 'Copy'}
                        </button>
                    </div>

                    <p className="expires-note">
                        This link expires in 7 days
                    </p>

                    <div className="success-actions">
                        <Button variant="secondary" onClick={sendAnotherInvite}>
                            Invite Another
                        </Button>
                        <Button variant="primary" onClick={onClose}>
                            Done
                        </Button>
                    </div>
                </div>
            )}
        </Modal>
    );
};

export default InviteModal;
```

Note: `API_BASE_URL` is removed — it was only used by the deleted raw `fetch` call. The `.link-btn` class doesn't exist in `InviteModal.css` yet; Step 2 adds it.

- [ ] **Step 2: Add the missing `.link-btn` style**

Open `frontend/src/components/team/InviteModal.css` and check for an existing plain-text-button style (e.g. how `sendAnotherInvite`'s secondary button or similar minimal buttons are styled elsewhere in this file). Add, near the other button styles:

```css
.link-btn {
    background: none;
    border: none;
    color: var(--text-secondary, #6b7280);
    text-decoration: underline;
    cursor: pointer;
    font-size: 0.875rem;
    margin-top: 8px;
}

.link-btn:hover {
    color: var(--text-primary, #111827);
}
```

If `InviteModal.css` already defines CSS custom properties for text colors under different names, use those instead of the `var(--text-secondary, #6b7280)` fallback pattern shown here — grep the file for `var(--text` to check before adding.

- [ ] **Step 3: Verify the build compiles**

Run: `cd frontend && npm run build`
Expected: build succeeds with no errors.

- [ ] **Step 4: Manual verification**

Run: `cd frontend && npm run dev`, then in the browser:
1. Open a tier-2 script's Team drawer, click "Invite Team Member."
2. Fill in an email/department/role and submit while seats are available — confirm the existing "Invite Sent!" success screen still works unchanged.
3. Using the backend running with `FLASK_ENV` unset to `development` (or temporarily monkeypatching `get_entitlement` to return `seats_used >= seats_paid`), submit an invite and confirm the "All paid seats are in use" panel appears with a working quantity selector and a "Buy N seats" button that navigates to a PayFast form (it's fine if the actual PayFast redirect isn't followed through in this manual check — confirming `postToPayFast` fires with real `process_url`/`fields` from the network tab is sufficient).

- [ ] **Step 5: Commit**

```bash
cd frontend
git add src/components/team/InviteModal.jsx src/components/team/InviteModal.css
git commit -m "feat(billing): handle no_seats_available in InviteModal

Adds a buy-seats panel (quantity picker + checkout) when create_invite
returns 402, stashing the in-progress invite as a draft so it survives
the PayFast redirect. Also routes invite creation through apiService
instead of a raw fetch, matching the rest of the codebase."
```

---

### Task 5: BillingPage — quantity picker for seat purchases

**Files:**
- Modify: `frontend/src/pages/BillingPage.jsx`

**Interfaces:**
- Consumes: `createCheckout` (already imported), `useEntitlement` (already imported).
- Produces: no new exports — internal state only.

**Context.** The proactive Billing-page path currently hardcodes `buy('tier_2_seats', 1)` — an Owner can only ever buy one seat at a time from Billing, unlike breakdown credits which already has a `[1, 5, 10]` quantity selector. Per the approved design (§3), the primary Billing path should let the Owner buy N seats in one purchase.

- [ ] **Step 1: Add a seat-specific quantity state and selector**

In `frontend/src/pages/BillingPage.jsx`, add a second quantity state (the existing `quantity` state is used by the breakdown-credits section and must stay separate — sharing one state would make the two purchase sections interfere with each other):

Replace:
```javascript
export default function BillingPage() {
    const { entitlement, loading } = useEntitlement();
    const [quantity, setQuantity] = useState(1);
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState(null);
```

with:
```javascript
export default function BillingPage() {
    const { entitlement, loading } = useEntitlement();
    const [quantity, setQuantity] = useState(1);
    const [seatQuantity, setSeatQuantity] = useState(1);
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState(null);
```

Replace the "Team seats" section:
```javascript
            {entitlement.tier === 'tier_2_annual_team' && entitlement.status === 'active' ? (
                <section>
                    <h2>Team seats</h2>
                    <p>{entitlement.seats_used} of {entitlement.seats_paid} seats in use</p>
                    <button disabled={busy} onClick={() => buy('tier_2_seats', 1)}>
                        Add a seat — R{PRICE_ZAR.tier_2_seats}/yr
                    </button>
                </section>
```

with:
```javascript
            {entitlement.tier === 'tier_2_annual_team' && entitlement.status === 'active' ? (
                <section>
                    <h2>Team seats</h2>
                    <p>{entitlement.seats_used} of {entitlement.seats_paid} seats in use</p>
                    <label htmlFor="seat-qty">Quantity</label>
                    <select id="seat-qty" value={seatQuantity}
                            onChange={(e) => setSeatQuantity(Number(e.target.value))}>
                        {[1, 2, 3, 5, 10].map((n) => <option key={n} value={n}>{n}</option>)}
                    </select>
                    <p>Total: R{PRICE_ZAR.tier_2_seats * seatQuantity}/yr</p>
                    <button disabled={busy} onClick={() => buy('tier_2_seats', seatQuantity)}>
                        Add {seatQuantity} seat{seatQuantity > 1 ? 's' : ''} — R{PRICE_ZAR.tier_2_seats}/yr each
                    </button>
                </section>
```

- [ ] **Step 2: Verify the build compiles**

Run: `cd frontend && npm run build`
Expected: build succeeds with no errors.

- [ ] **Step 3: Manual verification**

Run: `cd frontend && npm run dev`, navigate to `/billing` as a tier-2-active user, confirm the seat quantity selector shows `[1, 2, 3, 5, 10]`, the total updates when changed, and clicking "Add N seats" calls `createCheckout('tier_2_seats', N)` (check the network tab request body).

- [ ] **Step 4: Commit**

```bash
cd frontend
git add src/pages/BillingPage.jsx
git commit -m "feat(billing): let Owners buy multiple seats at once from Billing"
```

---

### Task 6: PaymentResultPage — resume routing after a seat purchase

**Files:**
- Modify: `frontend/src/pages/PaymentResultPage.jsx`

**Interfaces:**
- Consumes: `readPendingSeatInviteDraft` from Task 2's `frontend/src/utils/pendingSeatInviteDraft.js`; `useNavigate` from `react-router-dom` (new import).
- Produces: no new exports — behavior change only.

**Context.** Per the approved design (§3 step 3), once a `tier_2_seats` purchase settles and a draft is stashed (from Task 4's `handleBuySeats`), the Owner should land on their script's team page with the invite form ready to resume, instead of the generic "Thank you" screen. The page already polls `refetch()` up to 5 times over ~10s waiting for the ITN — this task reuses that same settle-check rather than adding a new one.

- [ ] **Step 1: Add the resume redirect**

Replace the full contents of `frontend/src/pages/PaymentResultPage.jsx`:

```jsx
import { useEffect, useState } from 'react';
import { useSearchParams, useNavigate, Link } from 'react-router-dom';
import { useEntitlement } from '../hooks/useEntitlement';
import { readPendingSeatInviteDraft } from '../utils/pendingSeatInviteDraft';

export default function PaymentResultPage({ outcome }) {
    const [params] = useSearchParams();
    const navigate = useNavigate();
    const { entitlement, refetch } = useEntitlement();
    const [waited, setWaited] = useState(0);

    // The ITN is a separate server-to-server call and may land after the
    // browser gets back here, so poll briefly rather than claim failure.
    useEffect(() => {
        if (outcome !== 'success' || waited >= 5) return;
        const t = setTimeout(() => { refetch(); setWaited((w) => w + 1); }, 2000);
        return () => clearTimeout(t);
    }, [outcome, waited, refetch]);

    const settled = entitlement?.can_run_breakdown || entitlement?.can_use_teams;

    // A seat purchase started from the invite modal's "buy seats" panel
    // stashes a draft before redirecting to PayFast — once the purchase
    // settles, send the Owner back to finish that invite instead of the
    // generic landing. The draft itself (email/department/role) is left
    // in sessionStorage for TeamDrawer (Task 7) to read and clear — this
    // page only needs scriptId to know where to route.
    useEffect(() => {
        if (outcome !== 'success' || params.get('type') !== 'tier_2_seats' || !settled) return;
        const draft = readPendingSeatInviteDraft();
        if (draft?.scriptId) {
            navigate(`/scenes/${draft.scriptId}?resume_invite=1`, { replace: true });
        }
    }, [outcome, params, settled, navigate]);

    if (outcome === 'cancel') {
        return (
            <div>
                <h1>Payment cancelled</h1>
                <p>You have not been charged.</p>
                <Link to="/billing">Back to billing</Link>
            </div>
        );
    }

    return (
        <div>
            <h1>Thank you</h1>
            {settled ? (
                <p>Your purchase is active. Type: {params.get('type')}</p>
            ) : (
                <p>Payment received — confirming with our payment provider. This
                   usually takes a few seconds.</p>
            )}
            <Link to="/">Continue</Link>
        </div>
    );
}
```

- [ ] **Step 2: Verify the build compiles**

Run: `cd frontend && npm run build`
Expected: build succeeds with no errors.

- [ ] **Step 3: Manual verification**

Run: `cd frontend && npm run dev`. In the browser console on any page, run:
```javascript
sessionStorage.setItem('slateone_pending_seat_invite_draft', JSON.stringify({ scriptId: 'REPLACE_WITH_A_REAL_SCRIPT_ID', email: 'a@b.com', departmentCode: 'costume', role: 'member' }));
```
Then navigate to `/payment/success?type=tier_2_seats`. Once the entitlement poll resolves `can_use_teams: true` (use a real tier-2-active test account, or temporarily mock `useEntitlement` to return `{ can_use_teams: true }` immediately), confirm the browser redirects to `/scenes/REPLACE_WITH_A_REAL_SCRIPT_ID?resume_invite=1`.

- [ ] **Step 4: Commit**

```bash
cd frontend
git add src/pages/PaymentResultPage.jsx
git commit -m "feat(billing): route back to the invite draft after a seat purchase settles"
```

---

### Task 7: Wire the resume-invite auto-open flow (ScriptHeader + TeamDrawer)

**Files:**
- Modify: `frontend/src/components/metadata/ScriptHeader.jsx`
- Modify: `frontend/src/components/team/TeamDrawer.jsx`

**Interfaces:**
- Consumes: `readPendingSeatInviteDraft`, `clearPendingSeatInviteDraft` from Task 2; `useSearchParams` from `react-router-dom` (new import in `ScriptHeader.jsx`); `InviteModal`'s new `initialDraft` prop from Task 4.
- Produces: no new exports — behavior change only. This is the last task; after it, the full loop (invite blocked → buy seats → redirect → resume) is wired end to end.

**Context.** `PaymentResultPage` (Task 6) navigates to `/scenes/<scriptId>?resume_invite=1`. `ScriptHeader` owns the `teamDrawerOpen` state and renders `TeamDrawer` on that route. This task makes `ScriptHeader` open the drawer when it sees `resume_invite=1`, and makes `TeamDrawer` — which owns `inviteModalOpen` and renders `InviteModal` — check for a matching stashed draft and auto-open the invite modal pre-filled, clearing the draft once consumed so it doesn't resurface on a later, unrelated drawer open.

- [ ] **Step 1: `ScriptHeader.jsx` — open the drawer on `resume_invite=1`**

In `frontend/src/components/metadata/ScriptHeader.jsx`, change the import line:
```javascript
import { useParams } from 'react-router-dom';
```
to:
```javascript
import { useParams, useSearchParams } from 'react-router-dom';
```

Add, inside the `ScriptHeader` component body, right after the existing `useState`/`useRef`/`useAuth` declarations (after the `isOwner` line):
```javascript
    const [searchParams, setSearchParams] = useSearchParams();

    // PaymentResultPage sends the Owner back here after a seat purchase
    // settles, with a stashed invite draft waiting to be resumed.
    useEffect(() => {
        if (searchParams.get('resume_invite') !== '1') return;
        setTeamDrawerOpen(true);
        const next = new URLSearchParams(searchParams);
        next.delete('resume_invite');
        setSearchParams(next, { replace: true });
    }, [searchParams, setSearchParams]);
```

- [ ] **Step 2: `TeamDrawer.jsx` — auto-open `InviteModal` with the stashed draft**

In `frontend/src/components/team/TeamDrawer.jsx`, add the import:
```javascript
import { readPendingSeatInviteDraft, clearPendingSeatInviteDraft } from '../../utils/pendingSeatInviteDraft';
```

Add a new state next to the existing `inviteModalOpen` state:
```javascript
    const [inviteModalOpen, setInviteModalOpen] = useState(false);
    const [resumedDraft, setResumedDraft] = useState(null);
```

Add a new `useEffect`, near the existing "Fetch team data when drawer opens" effect:
```javascript
    // If the Owner just came back from buying seats, resume the invite
    // they had in progress instead of making them retype it.
    useEffect(() => {
        if (!isOpen || !scriptId) return;
        const draft = readPendingSeatInviteDraft();
        if (draft && draft.scriptId === scriptId) {
            clearPendingSeatInviteDraft();
            setResumedDraft(draft);
            setInviteModalOpen(true);
        }
    }, [isOpen, scriptId]);
```

Find the `InviteModal` render block near the end of the file:
```jsx
            {/* Invite Modal */}
            <InviteModal
                isOpen={inviteModalOpen}
                onClose={handleInviteSuccess}
                scriptId={scriptId}
                scriptTitle={scriptTitle}
            />
```
and change it to pass the draft and clear it on close:
```jsx
            {/* Invite Modal */}
            <InviteModal
                isOpen={inviteModalOpen}
                onClose={() => { setResumedDraft(null); handleInviteSuccess(); }}
                scriptId={scriptId}
                scriptTitle={scriptTitle}
                initialDraft={resumedDraft}
            />
```

- [ ] **Step 3: Verify the build compiles**

Run: `cd frontend && npm run build`
Expected: build succeeds with no errors.

- [ ] **Step 4: Manual end-to-end verification**

Run: `cd frontend && npm run dev` and `cd backend && python app.py` (dev mode). As a tier-2-active test account with `seats_used >= seats_paid` (or temporarily force this via the backend as in Task 4 Step 4):
1. Open a script, open the Team drawer, click "Invite Team Member," fill in the form, submit — confirm the "All paid seats are in use" panel appears (Task 4).
2. Click "Buy N seats" — confirm `sessionStorage` now has `slateone_pending_seat_invite_draft` with the form's values (check DevTools > Application > Session Storage).
3. Since a real PayFast round trip isn't practical in this check, simulate the return: manually navigate to `/payment/success?type=tier_2_seats` with the draft still in `sessionStorage` and `can_use_teams` true (or seats now available) — confirm you land on `/scenes/<scriptId>?resume_invite=1`, the URL then drops the `resume_invite` param, the Team drawer opens automatically, and the Invite modal opens pre-filled with the original email/department/role.
4. Confirm `sessionStorage` no longer has the draft key after this (single-use).
5. Submit the resumed invite and confirm it succeeds now that seats are available.

- [ ] **Step 5: Commit**

```bash
cd frontend
git add src/components/metadata/ScriptHeader.jsx src/components/team/TeamDrawer.jsx
git commit -m "feat(billing): auto-open and pre-fill the invite modal on resume

Closes the loop: invite blocked by no_seats_available -> buy seats ->
PayFast redirect -> back on the script's team page with the original
invite ready to send."
```

---

## Plan-level verification

After all 7 tasks:

- [ ] Run: `cd backend && venv/bin/python -m pytest tests/ -q` — expect all tests passing.
- [ ] Run: `cd frontend && npm run build` — expect a clean build.
- [ ] Manual walkthrough (Task 7 Step 4) covers the full loop end to end.
- [ ] Confirm `docs/BACKLOG.md`'s "Discuss: user flow when a script Owner buys a Seat" entry is either removed or updated to point at this plan/spec, since it's now resolved rather than open — do this as a small follow-up commit once the plan is fully executed and verified, not as part of any task above (avoids marking it done before the code lands).
