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
                seatsPaidBaseline: entitlement.seats_paid,
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
