// frontend/src/components/cast/StatusBadge.jsx
import { Badge } from '../ui';

const MAP = {
    wishlist: { variant: 'neutral', label: 'Wishlist' },
    offer:    { variant: 'warning', label: 'Offer' },
    booked:   { variant: 'success', label: 'Booked' },
    declined: { variant: 'danger',  label: 'Declined' },
    released: { variant: 'neutral', label: 'Released', className: 'status-badge--released' },
};

export default function StatusBadge({ status }) {
    const cfg = MAP[status] || MAP.wishlist;
    return <Badge variant={cfg.variant} dot className={cfg.className}>{cfg.label}</Badge>;
}
