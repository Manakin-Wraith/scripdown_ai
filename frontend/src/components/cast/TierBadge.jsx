const LABEL = { lead: 'LEAD', supporting: 'SUPP', featured: 'FEAT', background: 'BG' };

export default function TierBadge({ tier }) {
    if (!tier || !LABEL[tier]) return null;
    return <span className={`tier-badge tier-badge--${tier}`}>{LABEL[tier]}</span>;
}
